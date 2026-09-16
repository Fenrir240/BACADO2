import json
import sqlite3
import time
from pathlib import Path

import streamlit as st

from services.auth_service import DB_PATH, init_auth_db


WORKS_FILE = Path("data/works.json")
VALID_CATEGORIES = {"my", "other"}


def load_works() -> list[dict]:
    if not WORKS_FILE.exists():
        return []

    with open(WORKS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def _get_current_user_id() -> int | None:
    user = st.session_state.get("auth_user")

    if not user:
        return None

    try:
        return int(user["id"])
    except (KeyError, TypeError, ValueError):
        return None


def _init_work_categories_db() -> None:
    init_auth_db()

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_work_categories (
                user_id INTEGER NOT NULL,
                work_id TEXT NOT NULL,
                category TEXT NOT NULL CHECK (category IN ('my', 'other')),
                updated_at INTEGER NOT NULL,
                PRIMARY KEY (user_id, work_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        connection.commit()


def get_works_for_current_user() -> list[dict]:
    works = load_works()
    user_id = _get_current_user_id()

    if user_id is None:
        return works

    _init_work_categories_db()

    with sqlite3.connect(DB_PATH) as connection:
        rows = connection.execute(
            """
            SELECT work_id, category
            FROM user_work_categories
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchall()

    categories_by_work = {work_id: category for work_id, category in rows}

    return [
        {
            **work,
            "category": categories_by_work.get(work["id"], work.get("category", "other")),
        }
        for work in works
    ]


def get_my_works() -> list[dict]:
    works = get_works_for_current_user()
    return [work for work in works if work["category"] == "my"]


def get_other_works() -> list[dict]:
    works = get_works_for_current_user()
    return [work for work in works if work["category"] == "other"]


def move_work(work_id: str, new_category: str) -> None:
    works = load_works()

    if new_category not in VALID_CATEGORIES:
        raise ValueError(f"Categorie invalida: {new_category}")

    if not any(work["id"] == work_id for work in works):
        raise ValueError(f"Opera necunoscuta: {work_id}")

    user_id = _get_current_user_id()

    if user_id is None:
        raise RuntimeError("Trebuie sa fii autentificat pentru a muta o opera.")

    _init_work_categories_db()

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO user_work_categories (user_id, work_id, category, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, work_id) DO UPDATE SET
                category = excluded.category,
                updated_at = excluded.updated_at
            """,
            (user_id, work_id, new_category, int(time.time())),
        )
        connection.commit()
