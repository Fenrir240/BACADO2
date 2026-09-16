"""Persistența eseului și a fragmentelor sale pentru fiecare utilizator și operă."""

import json
import sqlite3
import time

import streamlit as st

from services.auth_service import DB_PATH, init_auth_db


EMPTY_ESSAY_STATE = {
    "exists": False,
    "essay_text": "",
    "sections": {},
    "drafts": {},
}


def _get_current_user_id() -> int | None:
    user = st.session_state.get("auth_user")
    if not user:
        return None
    try:
        return int(user["id"])
    except (KeyError, TypeError, ValueError):
        return None


def _init_essay_db() -> None:
    init_auth_db()
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_essays (
                user_id INTEGER NOT NULL,
                work_id TEXT NOT NULL,
                essay_text TEXT NOT NULL DEFAULT '',
                sections_json TEXT NOT NULL DEFAULT '{}',
                drafts_json TEXT NOT NULL DEFAULT '{}',
                updated_at INTEGER NOT NULL,
                PRIMARY KEY (user_id, work_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        connection.commit()


def load_essay_state(work_id: str) -> dict:
    """Încarcă eseul utilizatorului autentificat pentru opera cerută."""
    user_id = _get_current_user_id()
    if user_id is None:
        return _empty_state()

    _init_essay_db()
    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(
            """
            SELECT essay_text, sections_json, drafts_json
            FROM user_essays
            WHERE user_id = ? AND work_id = ?
            """,
            (user_id, str(work_id)),
        ).fetchone()

    if row is None:
        return _empty_state()

    return {
        "exists": True,
        "essay_text": str(row[0] or ""),
        "sections": _parse_text_mapping(row[1]),
        "drafts": _parse_text_mapping(row[2]),
    }


def save_essay_state(
    work_id: str,
    essay_text: str,
    sections: dict,
    drafts: dict,
) -> bool:
    """Salvează atomic textul complet și fragmentele; întoarce False fără login."""
    user_id = _get_current_user_id()
    if user_id is None:
        return False

    clean_sections = _clean_text_mapping(sections)
    clean_drafts = _clean_text_mapping(drafts)
    _init_essay_db()
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO user_essays (
                user_id, work_id, essay_text, sections_json, drafts_json, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, work_id) DO UPDATE SET
                essay_text = excluded.essay_text,
                sections_json = excluded.sections_json,
                drafts_json = excluded.drafts_json,
                updated_at = excluded.updated_at
            """,
            (
                user_id,
                str(work_id),
                str(essay_text),
                json.dumps(clean_sections, ensure_ascii=False),
                json.dumps(clean_drafts, ensure_ascii=False),
                int(time.time()),
            ),
        )
        connection.commit()
    return True


def _empty_state() -> dict:
    return {
        "exists": False,
        "essay_text": EMPTY_ESSAY_STATE["essay_text"],
        "sections": {},
        "drafts": {},
    }


def _parse_text_mapping(raw_json: str) -> dict[str, str]:
    try:
        value = json.loads(raw_json)
    except (json.JSONDecodeError, TypeError):
        return {}
    return _clean_text_mapping(value)


def _clean_text_mapping(value: dict) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): str(text)
        for key, text in value.items()
        if str(key).strip() and isinstance(text, str)
    }
