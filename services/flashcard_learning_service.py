from __future__ import annotations

from functools import lru_cache
import json
import random
import sqlite3
import time
from pathlib import Path

import streamlit as st

from services.auth_service import DB_PATH, init_auth_db


DECK_DIR = Path("data/flashcards")
RECENT_CARD_LIMIT = 8
CATEGORY_COOLDOWN = 3
CHARACTER_COOLDOWN = 4
RETRY_DISTANCE = 5


# Incarca banca de flashcarduri a unei opere, ii valideaza cardurile si construieste
# structurile de cautare folosite ulterior pentru selectarea rapida a urmatorului card.
@lru_cache(maxsize=16)
def load_flashcard_deck(work_id: str) -> dict:
    path = DECK_DIR / f"{work_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Nu există o bancă de flashcarduri pentru {work_id}.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    cards = payload.get("cards", [])
    edges = payload.get("edges", [])
    if not isinstance(cards, list) or not cards:
        raise ValueError("Banca de flashcarduri nu conține carduri valide.")
    ids = [str(card.get("id", "")) for card in cards]
    if len(ids) != len(set(ids)):
        raise ValueError("Banca de flashcarduri conține ID-uri duplicate.")
    payload["cards_by_id"] = {card["id"]: card for card in cards}
    payload["adjacency"] = _build_adjacency(edges, payload["cards_by_id"])
    return payload


# Transforma lista de legaturi semantice intr-o lista de vecini pentru fiecare card.
# Este necesara pentru a gasi eficient carduri inrudite dupa un raspuns gresit.
def _build_adjacency(edges: list[dict], cards_by_id: dict) -> dict[str, list[dict]]:
    adjacency = {card_id: [] for card_id in cards_by_id}
    for edge in edges:
        source = str(edge.get("source", ""))
        target = str(edge.get("target", ""))
        if source not in adjacency or target not in adjacency or source == target:
            continue
        try:
            weight = float(edge.get("weight", 0))
        except (TypeError, ValueError):
            continue
        relation = str(edge.get("relation", "legatura_semantica"))
        adjacency[source].append({"card_id": target, "weight": weight, "relation": relation})
        adjacency[target].append({"card_id": source, "weight": weight, "relation": relation})
    for neighbors in adjacency.values():
        neighbors.sort(key=lambda item: item["weight"], reverse=True)
    return adjacency


# Extrage ID-ul utilizatorului autentificat din sesiunea Streamlit; intoarce None
# pentru vizitatori, astfel incat progresul lor sa poata fi pastrat doar in sesiune.
def _get_current_user_id() -> int | None:
    user = st.session_state.get("auth_user")
    if not user:
        return None
    try:
        return int(user["id"])
    except (KeyError, TypeError, ValueError):
        return None


# Creeaza, daca este necesar, tabela si indexul SQLite pentru progresul flashcardurilor.
# Asigura existenta structurii de stocare inaintea oricarei citiri sau actualizari.
def _init_progress_db() -> None:
    init_auth_db()
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_flashcard_progress (
                user_id INTEGER NOT NULL,
                work_id TEXT NOT NULL,
                card_id TEXT NOT NULL,
                correct_count INTEGER NOT NULL DEFAULT 0,
                wrong_count INTEGER NOT NULL DEFAULT 0,
                seen_count INTEGER NOT NULL DEFAULT 0,
                mastered INTEGER NOT NULL DEFAULT 0,
                last_result TEXT NOT NULL DEFAULT '',
                last_seen_at INTEGER NOT NULL,
                PRIMARY KEY (user_id, work_id, card_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_flashcard_progress_lookup
            ON user_flashcard_progress (user_id, work_id, mastered, last_seen_at)
            """
        )
        connection.commit()


# Construieste cheia unica din session_state pentru progresul unui utilizator anonim.
# Separa progresul intre opere si evita amestecarea rezultatelor din sesiunea curenta.
def _anonymous_progress_key(work_id: str) -> str:
    return f"anonymous_flashcard_progress_{work_id}"


# Returneaza ID-urile cardurilor deja rezolvate corect pentru opera ceruta.
# Lista este necesara pentru ca selectorul sa nu mai afiseze cardurile invatate.
def get_mastered_card_ids(work_id: str) -> set[str]:
    user_id = _get_current_user_id()
    if user_id is None:
        store = st.session_state.get(_anonymous_progress_key(work_id), {})
        return {card_id for card_id, item in store.items() if item.get("mastered")}

    _init_progress_db()
    with sqlite3.connect(DB_PATH) as connection:
        rows = connection.execute(
            """
            SELECT card_id
            FROM user_flashcard_progress
            WHERE user_id = ? AND work_id = ? AND mastered = 1
            """,
            (user_id, work_id),
        ).fetchall()
    return {row[0] for row in rows}


# Calculeaza statisticile de progres: carduri invatate, raspunsuri date si greseli.
# Aceste valori sunt folosite pentru informarea elevului in interfata sesiunii.
def get_flashcard_stats(work_id: str) -> dict:
    user_id = _get_current_user_id()
    if user_id is None:
        store = st.session_state.get(_anonymous_progress_key(work_id), {})
        return {
            "mastered": sum(bool(item.get("mastered")) for item in store.values()),
            "seen": sum(int(item.get("seen_count", 0)) for item in store.values()),
            "wrong": sum(int(item.get("wrong_count", 0)) for item in store.values()),
        }

    _init_progress_db()
    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(
            """
            SELECT COALESCE(SUM(mastered), 0),
                   COALESCE(SUM(seen_count), 0),
                   COALESCE(SUM(wrong_count), 0)
            FROM user_flashcard_progress
            WHERE user_id = ? AND work_id = ?
            """,
            (user_id, work_id),
        ).fetchone()
    return {"mastered": int(row[0]), "seen": int(row[1]), "wrong": int(row[2])}


# Inregistreaza rezultatul unui card si actualizeaza contoarele si starea "invatat".
# Persista in SQLite pentru utilizatorii autentificati si in sesiune pentru vizitatori.
def record_flashcard_outcome(work_id: str, card_id: str, correct: bool) -> None:
    user_id = _get_current_user_id()
    if user_id is None:
        key = _anonymous_progress_key(work_id)
        store = st.session_state.setdefault(key, {})
        item = store.setdefault(
            card_id,
            {"correct_count": 0, "wrong_count": 0, "seen_count": 0, "mastered": False},
        )
        item["seen_count"] += 1
        if correct:
            item["correct_count"] += 1
            item["mastered"] = True
        else:
            item["wrong_count"] += 1
        item["last_result"] = "correct" if correct else "wrong"
        item["last_seen_at"] = int(time.time())
        return

    _init_progress_db()
    now = int(time.time())
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO user_flashcard_progress (
                user_id, work_id, card_id, correct_count, wrong_count,
                seen_count, mastered, last_result, last_seen_at
            ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
            ON CONFLICT(user_id, work_id, card_id) DO UPDATE SET
                correct_count = correct_count + excluded.correct_count,
                wrong_count = wrong_count + excluded.wrong_count,
                seen_count = seen_count + 1,
                mastered = MAX(mastered, excluded.mastered),
                last_result = excluded.last_result,
                last_seen_at = excluded.last_seen_at
            """,
            (
                user_id,
                work_id,
                card_id,
                1 if correct else 0,
                0 if correct else 1,
                1 if correct else 0,
                "correct" if correct else "wrong",
                now,
            ),
        )
        connection.commit()


# Creeaza starea initiala a unei sesiuni adaptive de flashcarduri.
# Aceasta memoreaza istoricul recent, reincercarile si regulile de diversificare.
def create_flashcard_session() -> dict:
    return {
        "started": True,
        "current_id": None,
        "recent": [],
        "retry_queue": [],
        "pending_related_from": None,
        "avoid_category_once": None,
        "shown_count": 0,
    }


# Actualizeaza sesiunea dupa raspuns: elimina cardul curent, iar daca raspunsul este
# gresit, programeaza reafisarea lui si solicita intre timp un card inrudit semantic.
def register_session_outcome(session: dict, card: dict, correct: bool) -> None:
    card_id = card["id"]
    session["current_id"] = None
    session["retry_queue"] = [
        item for item in session.get("retry_queue", []) if item.get("card_id") != card_id
    ]
    if correct:
        return
    session["retry_queue"].append({"card_id": card_id, "remaining": RETRY_DISTANCE})
    session["pending_related_from"] = card_id


# Alege urmatorul card neinvatat respectand reincercarile, legaturile semantice si
# regulile de varietate; intoarce None cand toate cardurile au fost invatate.
def choose_next_flashcard(deck: dict, session: dict, mastered_ids: set[str]) -> str | None:
    cards_by_id = deck["cards_by_id"]
    retry_queue = [
        item
        for item in session.get("retry_queue", [])
        if item.get("card_id") in cards_by_id and item.get("card_id") not in mastered_ids
    ]
    session["retry_queue"] = retry_queue
    available = {card_id for card_id in cards_by_id if card_id not in mastered_ids}
    if not available:
        session["current_id"] = None
        return None

    due = next((item for item in retry_queue if int(item.get("remaining", 0)) <= 0), None)
    if due:
        selected_id = due["card_id"]
        retry_queue.remove(due)
        return _commit_selection(session, selected_id)

    delayed_ids = {item["card_id"] for item in retry_queue}
    selectable = available - delayed_ids
    if not selectable:
        earliest = min(retry_queue, key=lambda item: int(item.get("remaining", 0)))
        retry_queue.remove(earliest)
        return _commit_selection(session, earliest["card_id"])

    related_from = session.pop("pending_related_from", None)
    if related_from:
        selected_id = _choose_related(deck, session, related_from, selectable)
        if selected_id:
            session["avoid_category_once"] = cards_by_id[selected_id].get("category", "general")
            return _commit_selection(session, selected_id)

    avoid_category = session.pop("avoid_category_once", None)
    selected_id = _choose_diverse(cards_by_id, session, selectable, avoid_category)
    return _commit_selection(session, selected_id)


# Cauta cel mai relevant vecin semantic al cardului indicat, dintre candidatii valizi.
# Este folosit dupa o greseala pentru a consolida imediat conceptul asociat.
def _choose_related(deck: dict, session: dict, source_id: str, candidates: set[str]) -> str | None:
    neighbors = [
        item for item in deck["adjacency"].get(source_id, []) if item["card_id"] in candidates
    ]
    if not neighbors:
        return None
    neighbor_ids = [item["card_id"] for item in neighbors]
    filtered = _apply_diversity_filters(deck["cards_by_id"], session, neighbor_ids, None)
    allowed = set(filtered or neighbor_ids)
    return next(item["card_id"] for item in neighbors if item["card_id"] in allowed)


# Selecteaza aleatoriu un card dintre candidatii filtrati si echilibreaza personajele.
# Previne sesiuni monotone si distributii care ar face imposibila alternarea ulterioara.
def _choose_diverse(
    cards_by_id: dict,
    session: dict,
    candidates: set[str],
    avoid_category: str | None,
) -> str:
    candidate_ids = sorted(candidates)
    character_counts: dict[str, int] = {}
    for card_id in candidate_ids:
        character = _primary_character(cards_by_id[card_id])
        if character:
            character_counts[character] = character_counts.get(character, 0) + 1

    # Do not postpone a frequent character until it becomes mathematically
    # impossible to finish the deck without three consecutive appearances.
    if character_counts:
        urgent_character, urgent_count = max(
            character_counts.items(), key=lambda item: item[1]
        )
        other_count = len(candidate_ids) - urgent_count
        recent_ids = [
            card_id for card_id in session.get("recent", []) if card_id in cards_by_id
        ]
        recent_characters = [
            _primary_character(cards_by_id[card_id]) for card_id in recent_ids[-2:]
        ]
        urgent_would_be_third = (
            len(recent_characters) == 2
            and recent_characters[0] == recent_characters[1] == urgent_character
        )
        if urgent_count > 2 * other_count and not urgent_would_be_third:
            urgent_ids = [
                card_id
                for card_id in candidate_ids
                if _primary_character(cards_by_id[card_id]) == urgent_character
            ]
            urgent_filtered = _apply_diversity_filters(
                cards_by_id,
                session,
                urgent_ids,
                avoid_category,
            )
            return random.choice(urgent_filtered or urgent_ids)

    filtered = _apply_diversity_filters(
        cards_by_id,
        session,
        candidate_ids,
        avoid_category,
    )
    return random.choice(filtered or candidate_ids)


# Aplica regulile de varietate pentru cardurile recente, categorii si personaje.
# Este necesara pentru a evita repetitiile, fara a elimina definitiv candidati valizi.
def _apply_diversity_filters(
    cards_by_id: dict,
    session: dict,
    candidate_ids: list[str],
    avoid_category: str | None,
) -> list[str]:
    recent_ids = [card_id for card_id in session.get("recent", []) if card_id in cards_by_id]
    candidates = list(candidate_ids)

    # This is the hard diversity rule. Apply it before cooldown preferences so
    # an otherwise valid alternative is not discarded by a softer filter.
    if len(recent_ids) >= 2:
        last_characters = [
            _primary_character(cards_by_id[card_id]) for card_id in recent_ids[-2:]
        ]
        if last_characters[0] and last_characters[0] == last_characters[1]:
            no_third = [
                card_id
                for card_id in candidates
                if _primary_character(cards_by_id[card_id]) != last_characters[0]
            ]
            if no_third:
                candidates = no_third

    if avoid_category:
        different = [
            card_id for card_id in candidates if cards_by_id[card_id].get("category", "general") != avoid_category
        ]
        if different:
            candidates = different

    not_recent = [card_id for card_id in candidates if card_id not in recent_ids[-RECENT_CARD_LIMIT:]]
    if not_recent:
        candidates = not_recent

    recent_categories = {
        cards_by_id[card_id].get("category", "general") for card_id in recent_ids[-CATEGORY_COOLDOWN:]
    }
    category_fresh = [
        card_id for card_id in candidates if cards_by_id[card_id].get("category", "general") not in recent_categories
    ]
    if category_fresh:
        candidates = category_fresh

    recent_characters = {
        _primary_character(cards_by_id[card_id])
        for card_id in recent_ids[-CHARACTER_COOLDOWN:]
        if _primary_character(cards_by_id[card_id])
    }
    character_counts: dict[str, int] = {}
    for card_id in candidates:
        character = _primary_character(cards_by_id[card_id])
        if character:
            character_counts[character] = character_counts.get(character, 0) + 1
    pressure_threshold = 1 / (CHARACTER_COOLDOWN + 1)
    pressured_characters = {
        character
        for character, count in character_counts.items()
        if count / max(1, len(candidates)) > pressure_threshold
    }
    character_fresh_or_pressured = [
        card_id
        for card_id in candidates
        if not _primary_character(cards_by_id[card_id])
        or _primary_character(cards_by_id[card_id]) not in recent_characters
        or _primary_character(cards_by_id[card_id]) in pressured_characters
    ]
    if character_fresh_or_pressured:
        candidates = character_fresh_or_pressured
    return candidates


# Normalizeaza si returneaza personajul principal al unui card, daca exista.
# Valoarea comuna permite compararea consecventa in filtrele de diversitate.
def _primary_character(card: dict) -> str:
    characters = card.get("characters", [])
    return str(characters[0]).strip().casefold() if characters else ""


# Confirma alegerea cardului, avanseaza distanta pana la reincercari si actualizeaza
# istoricul sesiunii; centralizeaza modificarile necesare dupa fiecare selectie.
def _commit_selection(session: dict, selected_id: str) -> str:
    for item in session.get("retry_queue", []):
        if item.get("card_id") != selected_id:
            item["remaining"] = int(item.get("remaining", 0)) - 1
    recent = session.setdefault("recent", [])
    recent.append(selected_id)
    del recent[:-10]
    session["shown_count"] = int(session.get("shown_count", 0)) + 1
    session["current_id"] = selected_id
    return selected_id
