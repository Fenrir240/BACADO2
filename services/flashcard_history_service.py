import sqlite3
import time

import streamlit as st

from services.auth_service import DB_PATH, init_auth_db


HISTORY_LIMIT = 60
HISTORY_MIGRATION_KEY = "flashcard_history_correct_answers_only_v1"


def _get_current_user_id() -> int | None:
    user = st.session_state.get("auth_user")

    if not user:
        return None

    try:
        return int(user["id"])
    except (KeyError, TypeError, ValueError):
        return None


def _init_flashcard_history_db() -> None:
    init_auth_db()

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_flashcard_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                work_id TEXT NOT NULL,
                category TEXT NOT NULL CHECK (category IN ('opera', 'personaje')),
                question TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                UNIQUE (user_id, work_id, category, question),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_flashcard_history_lookup
            ON user_flashcard_history (user_id, work_id, category, created_at DESC, id DESC)
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS app_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        migration_done = connection.execute(
            "SELECT 1 FROM app_metadata WHERE key = ?",
            (HISTORY_MIGRATION_KEY,),
        ).fetchone()
        if migration_done is None:
            # În versiunile anterioare se salvau toate întrebările generate,
            # fără să știm dacă elevul răspunsese corect. Le eliminăm o singură
            # dată pentru ca istoricul să respecte noua regulă.
            connection.execute("DELETE FROM user_flashcard_history")
            connection.execute(
                "INSERT INTO app_metadata (key, value) VALUES (?, ?)",
                (HISTORY_MIGRATION_KEY, "done"),
            )
        connection.commit()


def get_flashcard_history(work_id: str, category: str) -> list[str]:
    """Return recent correctly answered questions for the current user."""
    user_id = _get_current_user_id()

    if user_id is None:
        return st.session_state.get(_session_key(work_id, category), [])

    _init_flashcard_history_db()

    with sqlite3.connect(DB_PATH) as connection:
        rows = connection.execute(
            """
            SELECT question
            FROM user_flashcard_history
            WHERE user_id = ? AND work_id = ? AND category = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (user_id, work_id, category, HISTORY_LIMIT),
        ).fetchall()

    return [row[0] for row in reversed(rows)]


def save_flashcard_history(work_id: str, category: str, questions: list[str]) -> None:
    """Persist correctly answered questions, separately for each user."""
    clean_questions = list(dict.fromkeys(
        question.strip() for question in questions if isinstance(question, str) and question.strip()
    ))
    if not clean_questions:
        return

    user_id = _get_current_user_id()

    if user_id is None:
        key = _session_key(work_id, category)
        st.session_state[key] = (st.session_state.get(key, []) + clean_questions)[-HISTORY_LIMIT:]
        return

    _init_flashcard_history_db()
    now = int(time.time())

    with sqlite3.connect(DB_PATH) as connection:
        connection.executemany(
            """
            INSERT INTO user_flashcard_history (user_id, work_id, category, question, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, work_id, category, question) DO NOTHING
            """,
            [(user_id, work_id, category, question, now) for question in clean_questions],
        )
        connection.execute(
            """
            DELETE FROM user_flashcard_history
            WHERE id IN (
                SELECT id
                FROM user_flashcard_history
                WHERE user_id = ? AND work_id = ? AND category = ?
                ORDER BY created_at DESC, id DESC
                LIMIT -1 OFFSET ?
            )
            """,
            (user_id, work_id, category, HISTORY_LIMIT),
        )
        connection.commit()


def _session_key(work_id: str, category: str) -> str:
    return f"quick_flashcards_history_{work_id}_{category}"
