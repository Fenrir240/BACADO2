"""Încărcarea și rotația băncilor de exerciții preconstruite."""

from __future__ import annotations

import copy
import json
import random
from functools import lru_cache
from pathlib import Path
from typing import Iterable


ROOT_DIR = Path(__file__).resolve().parents[1]
EXERCISE_DIR = ROOT_DIR / "data" / "exercises"
FLASHCARD_DIR = ROOT_DIR / "data" / "flashcards"

EXERCISE_FILES = {
    "Ordine cronologică": "chronology.json",
    "Asociere": "matching.json",
    "Completare": "completion.json",
    "Alege răspunsul": "multiple_choice.json",
}


def quick_testing_available(work_id: str) -> bool:
    """Confirmă că toate băncile există și respectă contractele consumate de UI."""
    try:
        flashcard_payload = _read_payload(FLASHCARD_DIR / f"{work_id}.json")
        cards = flashcard_payload.get("cards")
        if not isinstance(cards, list) or not cards:
            return False
        card_ids = [str(card.get("id") or "").strip() for card in cards if isinstance(card, dict)]
        if (
            len(card_ids) != len(cards)
            or any(not card_id for card_id in card_ids)
            or len(set(card_ids)) != len(card_ids)
            or any(
                not str(card.get("front") or "").strip()
                or not str(card.get("back") or "").strip()
                for card in cards
            )
        ):
            return False
        return all(
            bool(load_prebuilt_exercises(work_id, exercise_type))
            for exercise_type in EXERCISE_FILES
        )
    except (OSError, ValueError, json.JSONDecodeError):
        return False


@lru_cache(maxsize=32)
def load_prebuilt_exercises(work_id: str, exercise_type: str) -> tuple[dict, ...]:
    """Încarcă și validează banca cerută; rezultatul din cache nu este modificat."""
    if exercise_type == "Întoarce cartea":
        path = FLASHCARD_DIR / f"{work_id}.json"
        payload = _read_payload(path)
        exercises = payload.get("quick_sets", [])
    else:
        filename = EXERCISE_FILES.get(exercise_type)
        if not filename:
            raise ValueError(f"Tip de exercițiu necunoscut: {exercise_type}")
        path = EXERCISE_DIR / work_id / filename
        payload = _read_payload(path)
        exercises = payload.get("exercises", [])

    if not isinstance(exercises, list) or not exercises:
        raise ValueError(f"Banca {path} nu conține exerciții.")
    normalized = []
    seen_ids = set()
    for exercise in exercises:
        if not isinstance(exercise, dict):
            raise ValueError(f"Banca {path} conține un exercițiu invalid.")
        exercise_id = str(exercise.get("id", "")).strip()
        if not exercise_id or exercise_id in seen_ids:
            raise ValueError(f"Banca {path} conține ID-uri lipsă sau duplicate.")
        _validate_contract(exercise_type, exercise)
        exercise = _normalize_for_ui(exercise_type, exercise)
        seen_ids.add(exercise_id)
        normalized.append(exercise)
    return tuple(normalized)


def choose_prebuilt_exercise(
    work_id: str,
    exercise_type: str,
    excluded_ids: Iterable[str] | None = None,
) -> dict:
    """Returnează primul item nevăzut; după epuizare începe un ciclu nou."""
    exercises = load_prebuilt_exercises(work_id, exercise_type)
    excluded = {str(value) for value in (excluded_ids or [])}
    selected = next(
        (exercise for exercise in exercises if str(exercise["id"]) not in excluded),
        exercises[0],
    )
    result = copy.deepcopy(selected)
    if exercise_type == "Ordine cronologică":
        random.shuffle(result["items"])
    return result


def multiple_choice_test_items(work_id: str, count: int, offset: int = 0) -> list[tuple]:
    """Construiește un test de grilă dintr-o fereastră circulară a băncii."""
    exercises = load_prebuilt_exercises(work_id, "Alege răspunsul")
    if count <= 0:
        raise ValueError("Numărul întrebărilor trebuie să fie pozitiv.")
    if count > len(exercises):
        raise ValueError("Banca nu conține suficiente întrebări pentru test.")
    return [
        (
            exercises[(offset + index) % len(exercises)]["question"],
            list(exercises[(offset + index) % len(exercises)]["options"]),
            exercises[(offset + index) % len(exercises)]["answer"],
        )
        for index in range(count)
    ]


def _read_payload(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Nu există banca de exerciții {path}.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Banca {path} nu conține un obiect JSON.")
    return payload


def _validate_contract(exercise_type: str, exercise: dict) -> None:
    if exercise_type == "Ordine cronologică":
        items = exercise.get("items", [])
        positions = [item.get("position") for item in items if isinstance(item, dict)]
        if (
            len(items) < 3
            or len(positions) != len(items)
            or positions != list(range(1, len(items) + 1))
            or any(not str(item.get("event", "")).strip() for item in items)
        ):
            raise ValueError("Un exercițiu cronologic nu respectă schema UI.")
    elif exercise_type == "Asociere":
        pairs = exercise.get("pairs", [])
        if len(pairs) < 3 or any(
            not isinstance(pair, dict)
            or not str(pair.get("left", "")).strip()
            or not str(pair.get("right", "")).strip()
            for pair in pairs
        ):
            raise ValueError("Un exercițiu de asociere nu respectă schema UI.")
    elif exercise_type == "Completare":
        if str(exercise.get("text", "")).count("____") != 3 or len(exercise.get("answers", [])) != 3:
            raise ValueError("Un exercițiu de completare nu respectă schema UI.")
    elif exercise_type == "Alege răspunsul":
        options = exercise.get("options", [])
        if (
            not str(exercise.get("question", "")).strip()
            or len(options) != 4
            or len(set(options)) != 4
            or exercise.get("answer") not in options
        ):
            raise ValueError("O grilă nu respectă schema UI.")
    elif exercise_type == "Întoarce cartea":
        cards = exercise.get("cards", [])
        if len(cards) < 2 or any(
            not isinstance(card, dict)
            or not str(card.get("prompt", "")).strip()
            or not str(card.get("answer", "")).strip()
            for card in cards
        ):
            raise ValueError("Un set de flashcarduri nu respectă schema UI.")


def _normalize_for_ui(exercise_type: str, exercise: dict) -> dict:
    """Adaptează băncile lirice și narative la același contract consumat de UI."""
    normalized = copy.deepcopy(exercise)
    if exercise_type != "Ordine cronologică":
        return normalized

    exercise_id = str(normalized.get("id") or "chronology")
    for index, item in enumerate(normalized.get("items", []), start=1):
        if not isinstance(item, dict) or str(item.get("event_id") or "").strip():
            continue
        position = item.get("position", index)
        item["event_id"] = f"{exercise_id}_item_{position}"
    return normalized
