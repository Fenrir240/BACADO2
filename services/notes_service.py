import sqlite3
import time

import streamlit as st

from services.auth_service import DB_PATH, init_auth_db


VALID_NOTE_SCOPES = {
    "summary",
    "literary_current",
    "characters",
    "scenes",
    "composition",
}


def _get_current_user_id() -> int:
    user = st.session_state.get("auth_user")

    if not user:
        raise RuntimeError("Trebuie sa fii autentificat pentru a folosi carnetelul.")

    try:
        return int(user["id"])
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError("Utilizatorul autentificat nu are un ID valid.") from error


def _validate_scope(scope: str) -> None:
    if scope not in VALID_NOTE_SCOPES:
        raise ValueError(f"Tip de carnetel invalid: {scope}")


def _init_notes_db() -> None:
    init_auth_db()

    with sqlite3.connect(DB_PATH) as connection:
        existing = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'user_notes'"
        ).fetchone()
        existing_sql = str(existing[0] or "")
        if existing and any(f"'{scope}'" not in existing_sql for scope in VALID_NOTE_SCOPES):
            connection.execute("DROP INDEX IF EXISTS idx_user_notes_lookup")
            connection.execute("ALTER TABLE user_notes RENAME TO user_notes_legacy")
            connection.execute(
                """
                CREATE TABLE user_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    work_id TEXT NOT NULL,
                    scope TEXT NOT NULL CHECK (scope IN ('summary', 'literary_current', 'characters', 'scenes', 'composition')),
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                INSERT INTO user_notes (
                    id, user_id, work_id, scope, title, content, created_at, updated_at
                )
                SELECT id, user_id, work_id, scope, title, content, created_at, updated_at
                FROM user_notes_legacy
                """
            )
            connection.execute("DROP TABLE user_notes_legacy")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                work_id TEXT NOT NULL,
                scope TEXT NOT NULL CHECK (scope IN ('summary', 'literary_current', 'characters', 'scenes', 'composition')),
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_user_notes_lookup
            ON user_notes (user_id, work_id, scope, updated_at)
            """
        )
        connection.commit()


def get_notes(work_id: str, scope: str) -> list[dict]:
    _validate_scope(scope)
    user_id = _get_current_user_id()
    _init_notes_db()

    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT id, title, content
            FROM user_notes
            WHERE user_id = ? AND work_id = ? AND scope = ?
            ORDER BY created_at, id
            """,
            (user_id, work_id, scope),
        ).fetchall()

    return [dict(row) for row in rows]


def create_note(work_id: str, scope: str, title: str, content: str = "") -> dict:
    _validate_scope(scope)
    user_id = _get_current_user_id()
    _init_notes_db()
    now = int(time.time())
    clean_title = title.strip() or "Notita fara titlu"
    clean_content = content.strip()

    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            """
            INSERT INTO user_notes (
                user_id, work_id, scope, title, content, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, work_id, scope, clean_title, clean_content, now, now),
        )
        connection.commit()
        note_id = cursor.lastrowid

    return {
        "id": note_id,
        "title": clean_title,
        "content": clean_content,
    }


def update_note(note_id: int, title: str, content: str) -> dict:
    user_id = _get_current_user_id()
    _init_notes_db()
    clean_title = title.strip() or "Notita fara titlu"
    clean_content = content.strip()

    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            """
            UPDATE user_notes
            SET title = ?, content = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (clean_title, clean_content, int(time.time()), note_id, user_id),
        )
        connection.commit()

    if cursor.rowcount == 0:
        raise ValueError("Notita nu exista sau apartine altui utilizator.")

    return {
        "id": note_id,
        "title": clean_title,
        "content": clean_content,
    }


def delete_note(note_id: int) -> None:
    user_id = _get_current_user_id()
    _init_notes_db()

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            "DELETE FROM user_notes WHERE id = ? AND user_id = ?",
            (note_id, user_id),
        )
        connection.commit()
