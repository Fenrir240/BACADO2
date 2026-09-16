import json
import sqlite3
import time

import streamlit as st

from services.auth_service import DB_PATH, init_auth_db


DEFAULT_PROGRESS = {
    "score": 0,
    "summary_done": False,
    "literary_current_done": False,
    "summary_quiz_done": False,
    "summary_quiz_score": 0,
    "quick_flashcards_score": 0,
    "quick_flashcard_awards": [],
    "quick_exercises_score": 0,
    "quick_exercise_awards": [],
    "quick_tests_score": 0,
    "quick_test_awards": [],
    "characters_done": False,
    "characters_quiz_done": False,
    "characters_quiz_score": 0,
    "scenes_done": False,
    "scenes_quiz_done": False,
    "scenes_quiz_score": 0,
    "structure_done": False,
    "structure_quiz_done": False,
    "structure_quiz_score": 0,
    "composition_selected_elements": [],
    "characters_ai_xp": 0,
    "characters_ai_xp_applied_to_score": 0,
    "characters_ai_pending_question": "",
    "characters_ai_deferred_questions": [],
    "quiz_done": False,
    "mindmap_opened": False,
    "essay_unlocked": False,
    "current_step": "Neinceput",
    "progress_orb_position": None,
    "progress_orb_acknowledged_score": 0,
}


def _get_current_user_id() -> int | None:
    user = st.session_state.get("auth_user")

    if not user:
        return None

    try:
        return int(user["id"])
    except (KeyError, TypeError, ValueError):
        return None


def _init_progress_db() -> None:
    init_auth_db()

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_progress (
                user_id INTEGER NOT NULL,
                work_id TEXT NOT NULL,
                progress_json TEXT NOT NULL,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY (user_id, work_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        connection.commit()


def _get_progress_store() -> dict:
    if "progress_by_work" not in st.session_state:
        st.session_state["progress_by_work"] = {}

    return st.session_state["progress_by_work"]


def get_work_progress(work_id: str) -> dict:
    user_id = _get_current_user_id()

    if user_id is not None:
        return _get_persisted_work_progress(user_id, work_id)

    store = _get_progress_store()

    if work_id not in store:
        store[work_id] = DEFAULT_PROGRESS.copy()

    if _looks_like_old_demo_progress(work_id, store[work_id]):
        store[work_id] = DEFAULT_PROGRESS.copy()

    _apply_unscored_conversation_xp(store[work_id])

    for key, value in DEFAULT_PROGRESS.items():
        store[work_id].setdefault(key, value)

    return store[work_id]


def _get_persisted_work_progress(user_id: int, work_id: str) -> dict:
    cache_key = f"progress_by_work_user_{user_id}"

    if cache_key not in st.session_state:
        st.session_state[cache_key] = {}

    user_store = st.session_state[cache_key]

    if work_id not in user_store:
        user_store[work_id] = _load_progress_from_db(user_id, work_id)

    if _looks_like_old_demo_progress(work_id, user_store[work_id]):
        user_store[work_id] = DEFAULT_PROGRESS.copy()
        _save_progress_to_db(user_id, work_id, user_store[work_id])

    if _apply_unscored_conversation_xp(user_store[work_id]):
        _save_progress_to_db(user_id, work_id, user_store[work_id])

    for key, value in DEFAULT_PROGRESS.items():
        user_store[work_id].setdefault(key, value)

    return user_store[work_id]


def _load_progress_from_db(user_id: int, work_id: str) -> dict:
    _init_progress_db()

    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(
            """
            SELECT progress_json
            FROM user_progress
            WHERE user_id = ? AND work_id = ?
            """,
            (user_id, work_id),
        ).fetchone()

    if row is None:
        progress = DEFAULT_PROGRESS.copy()
        _save_progress_to_db(user_id, work_id, progress)
        return progress

    try:
        progress = json.loads(row[0])
    except json.JSONDecodeError:
        progress = DEFAULT_PROGRESS.copy()

    if not isinstance(progress, dict):
        progress = DEFAULT_PROGRESS.copy()

    for key, value in DEFAULT_PROGRESS.items():
        progress.setdefault(key, value)

    return progress


def _save_progress(work_id: str, progress: dict) -> None:
    user_id = _get_current_user_id()

    if user_id is None:
        return

    _save_progress_to_db(user_id, work_id, progress)


def _save_progress_to_db(user_id: int, work_id: str, progress: dict) -> None:
    _init_progress_db()

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO user_progress (user_id, work_id, progress_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, work_id) DO UPDATE SET
                progress_json = excluded.progress_json,
                updated_at = excluded.updated_at
            """,
            (
                user_id,
                work_id,
                json.dumps(progress, ensure_ascii=False),
                int(time.time()),
            ),
        )
        connection.commit()


def mark_summary_done(work_id: str) -> None:
    progress = get_work_progress(work_id)
    progress["summary_done"] = True

    if progress["score"] == 0:
        progress["current_step"] = "Personaje"

    _save_progress(work_id, progress)


def update_summary_quiz_score(work_id: str, earned_points: int) -> None:
    progress = get_work_progress(work_id)
    previous_points = progress.get("summary_quiz_score", 0)
    earned_points = max(0, min(earned_points, 10))

    progress["score"] = max(0, min(progress["score"] - previous_points + earned_points, 100))
    progress["summary_quiz_score"] = earned_points
    progress["summary_quiz_done"] = True
    progress["quiz_done"] = True
    progress["essay_unlocked"] = progress["score"] >= 70

    if progress["essay_unlocked"]:
        progress["current_step"] = "Eseu deblocat"
    else:
        progress["current_step"] = "Personaje"

    _save_progress(work_id, progress)


def award_quick_flashcard_point(work_id: str, card_id: str) -> bool:
    """Award one persistent progress point for a correctly solved flashcard.

    A card identifier is stored with the progress record, so reruns and refreshes
    cannot award the same point multiple times.
    """
    progress = get_work_progress(work_id)
    awarded_cards = progress.get("quick_flashcard_awards", [])
    if not isinstance(awarded_cards, list):
        awarded_cards = []

    if card_id in awarded_cards:
        return False

    awarded_cards.append(card_id)
    progress["quick_flashcard_awards"] = awarded_cards
    progress["quick_flashcards_score"] = int(progress.get("quick_flashcards_score", 0) or 0) + 1
    progress["score"] = max(0.0, min(float(progress.get("score", 0) or 0) + 1, 100.0))
    progress["essay_unlocked"] = progress["score"] >= 70
    _save_progress(work_id, progress)
    return True


def award_quick_exercise_points(work_id: str, exercise_id: str) -> bool:
    """Award two progress points once for a correctly solved quick exercise."""
    progress = get_work_progress(work_id)
    awarded_exercises = progress.get("quick_exercise_awards", [])
    if not isinstance(awarded_exercises, list):
        awarded_exercises = []

    if exercise_id in awarded_exercises:
        return False

    awarded_exercises.append(exercise_id)
    progress["quick_exercise_awards"] = awarded_exercises
    progress["quick_exercises_score"] = int(progress.get("quick_exercises_score", 0) or 0) + 2
    progress["score"] = max(0.0, min(float(progress.get("score", 0) or 0) + 2, 100.0))
    progress["essay_unlocked"] = progress["score"] >= 70
    _save_progress(work_id, progress)
    return True


def award_quick_test_points(work_id: str, correct_question_ids: list[str]) -> float:
    """Acordă 0,5 puncte o singură dată pentru fiecare grilă rezolvată corect."""
    progress = get_work_progress(work_id)
    awarded_questions = progress.get("quick_test_awards", [])
    if not isinstance(awarded_questions, list):
        awarded_questions = []

    known_ids = {str(question_id) for question_id in awarded_questions}
    new_ids = []
    for question_id in correct_question_ids:
        question_id = str(question_id).strip()
        if question_id and question_id not in known_ids:
            known_ids.add(question_id)
            new_ids.append(question_id)

    if not new_ids:
        return 0

    earned_points = len(new_ids) * 0.5
    previous_score = max(0.0, min(float(progress.get("score", 0) or 0), 100.0))
    progress["quick_test_awards"] = [*awarded_questions, *new_ids]
    progress["quick_tests_score"] = (
        float(progress.get("quick_tests_score", 0) or 0) + earned_points
    )
    progress["score"] = min(previous_score + earned_points, 100.0)
    _refresh_essay_unlock(progress)
    _save_progress(work_id, progress)
    return progress["score"] - previous_score


def mark_characters_done(work_id: str) -> None:
    progress = get_work_progress(work_id)
    progress["characters_done"] = True
    progress["current_step"] = "Evaluare personaje"
    _save_progress(work_id, progress)


def mark_scenes_done(work_id: str) -> None:
    progress = get_work_progress(work_id)
    progress["scenes_done"] = True
    progress["current_step"] = "Elemente de structura"
    _save_progress(work_id, progress)


def update_characters_quiz_score(work_id: str, earned_points: int) -> None:
    progress = get_work_progress(work_id)
    previous_points = progress.get("characters_quiz_score", 0)
    earned_points = max(0, min(earned_points, 15))

    progress["score"] = max(0, min(progress["score"] - previous_points + earned_points, 100))
    progress["characters_quiz_score"] = earned_points
    progress["characters_quiz_done"] = True
    progress["essay_unlocked"] = progress["score"] >= 70

    if progress["essay_unlocked"]:
        progress["current_step"] = "Eseu deblocat"
    else:
        progress["current_step"] = "Secvente relevante"

    _save_progress(work_id, progress)


def mark_mindmap_opened(work_id: str) -> None:
    progress = get_work_progress(work_id)
    progress["mindmap_opened"] = True
    _save_progress(work_id, progress)


def update_composition_selection(work_id: str, element_ids: list[str]) -> None:
    """Persistă cele două elemente compoziționale alese pentru schema eseului."""
    allowed = {"incipit_final", "conflict", "title"}
    selected = []
    for element_id in element_ids:
        element_id = str(element_id).strip()
        if element_id in allowed and element_id not in selected:
            selected.append(element_id)
    if len(selected) > 2:
        raise ValueError("Pot fi selectate maximum două elemente compoziționale.")
    progress = get_work_progress(work_id)
    progress["composition_selected_elements"] = selected
    _save_progress(work_id, progress)


def update_quiz_score(work_id: str, score: int) -> None:
    progress = get_work_progress(work_id)

    progress["score"] = score
    progress["quiz_done"] = True
    progress["essay_unlocked"] = score >= 70

    if score >= 70:
        progress["current_step"] = "Eseu deblocat"
    else:
        progress["current_step"] = "Recapituleaza si reincearca"

    _save_progress(work_id, progress)


def get_characters_ai_progress(work_id: str) -> dict:
    progress = get_work_progress(work_id)

    return {
        "xp": int(progress.get("characters_ai_xp", 0) or 0),
        "pending_question": progress.get("characters_ai_pending_question", "") or "",
        "deferred_questions": _normalize_deferred_questions(
            progress.get("characters_ai_deferred_questions", [])
        ),
    }


def update_characters_ai_progress(
    work_id: str,
    xp: int,
    pending_question: str | None,
    deferred_questions: list[str] | None = None,
) -> None:
    progress = get_work_progress(work_id)
    total_xp = max(0, int(xp))
    applied_xp = max(0, int(progress.get("characters_ai_xp_applied_to_score", 0) or 0))
    new_score_points = max(total_xp - applied_xp, 0)

    if new_score_points:
        progress["score"] = max(
            0,
            min(float(progress.get("score", 0) or 0) + new_score_points, 100.0),
        )
        _refresh_essay_unlock(progress)

    progress["characters_ai_xp"] = total_xp
    progress["characters_ai_xp_applied_to_score"] = max(applied_xp, total_xp)
    progress["characters_ai_pending_question"] = pending_question or ""
    if deferred_questions is not None:
        progress["characters_ai_deferred_questions"] = _normalize_deferred_questions(
            deferred_questions
        )
    _save_progress(work_id, progress)


def _normalize_deferred_questions(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    questions = []
    for item in value:
        question = str(item or "").strip()
        if question and question not in questions:
            questions.append(question)
    return questions


def reset_work_progress(work_id: str) -> None:
    user_id = _get_current_user_id()

    if user_id is not None:
        cache_key = f"progress_by_work_user_{user_id}"
        progress = DEFAULT_PROGRESS.copy()

        if cache_key not in st.session_state:
            st.session_state[cache_key] = {}

        st.session_state[cache_key][work_id] = progress
        _save_progress_to_db(user_id, work_id, progress)
        return

    store = _get_progress_store()
    store[work_id] = DEFAULT_PROGRESS.copy()


def save_progress_orb_position(work_id: str, position: dict) -> None:
    progress = get_work_progress(work_id)
    try:
        x = max(0, int(position.get("x", 0)))
        y = max(0, int(position.get("y", 0)))
    except (AttributeError, TypeError, ValueError):
        return

    progress["progress_orb_position"] = {"x": x, "y": y}
    _save_progress(work_id, progress)


def acknowledge_progress_orb(work_id: str) -> None:
    progress = get_work_progress(work_id)
    progress["progress_orb_acknowledged_score"] = float(progress.get("score", 0) or 0)
    _save_progress(work_id, progress)


def _looks_like_old_demo_progress(work_id: str, progress: dict) -> bool:
    return (
        work_id == "ion"
        and "summary_quiz_score" not in progress
        and progress.get("score") == 100
        and progress.get("essay_unlocked")
    )


def _apply_unscored_conversation_xp(progress: dict) -> bool:
    if "characters_ai_xp" not in progress:
        return False

    conversation_xp = max(0, int(progress.get("characters_ai_xp", 0) or 0))
    applied_xp = max(0, int(progress.get("characters_ai_xp_applied_to_score", 0) or 0))
    new_score_points = max(conversation_xp - applied_xp, 0)
    progress["characters_ai_xp_applied_to_score"] = max(applied_xp, conversation_xp)

    if new_score_points == 0:
        return False

    progress["score"] = max(
        0,
        min(float(progress.get("score", 0) or 0) + new_score_points, 100.0),
    )
    _refresh_essay_unlock(progress)
    return True


def _refresh_essay_unlock(progress: dict) -> None:
    progress["essay_unlocked"] = float(progress.get("score", 0) or 0) >= 70

    if progress["essay_unlocked"]:
        progress["current_step"] = "Eseu deblocat"
