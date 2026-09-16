import json
import sqlite3
import time

import streamlit as st

from services.auth_service import DB_PATH, init_auth_db


def _get_current_user_id() -> int | None:
    user = st.session_state.get("auth_user")

    if not user:
        return None

    try:
        return int(user["id"])
    except (KeyError, TypeError, ValueError):
        return None


QUOTE_ANNOTATION_PURPOSE = "quote"
LEGACY_QUOTE_COLOR = "#8b5cf6"


def is_quote_annotation(annotation: dict) -> bool:
    """Recunoaște atât citatele noi, cât și sublinierile mov create anterior."""
    if not isinstance(annotation, dict):
        return False
    if str(annotation.get("purpose") or "").strip().lower() == QUOTE_ANNOTATION_PURPOSE:
        return True
    return (
        str(annotation.get("type") or "").strip().lower() == "underline"
        and str(annotation.get("color") or "").strip().lower() == LEGACY_QUOTE_COLOR
    )


def get_scene_quotes(work_id: str, sequence_id: str) -> list[str]:
    """Returnează, fără duplicate, fragmentele marcate explicit drept citat."""
    quotes: list[str] = []
    seen: set[str] = set()
    for annotation in get_scene_annotations(work_id, sequence_id):
        if not is_quote_annotation(annotation):
            continue
        text = str(annotation.get("text") or "").strip()
        normalized = " ".join(text.split()).casefold()
        if text and normalized not in seen:
            quotes.append(text)
            seen.add(normalized)
    return quotes


def _init_annotation_db() -> None:
    init_auth_db()

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_scene_annotations (
                user_id INTEGER NOT NULL,
                work_id TEXT NOT NULL,
                sequence_id TEXT NOT NULL,
                annotations_json TEXT NOT NULL,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY (user_id, work_id, sequence_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        connection.commit()


def get_scene_annotations(work_id: str, sequence_id: str) -> list[dict]:
    user_id = _get_current_user_id()

    if user_id is None:
        return _get_session_scene_annotations(work_id, sequence_id)

    _init_annotation_db()

    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(
            """
            SELECT annotations_json
            FROM user_scene_annotations
            WHERE user_id = ? AND work_id = ? AND sequence_id = ?
            """,
            (user_id, work_id, sequence_id),
        ).fetchone()

    if row is None:
        return []

    return _parse_annotations(row[0])


def save_scene_annotations(
    work_id: str,
    sequence_id: str,
    annotations: list[dict],
) -> None:
    clean_annotations = _clean_annotations(annotations)
    user_id = _get_current_user_id()

    if user_id is None:
        st.session_state[_session_key(work_id, sequence_id)] = clean_annotations
        return

    _init_annotation_db()

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO user_scene_annotations (
                user_id,
                work_id,
                sequence_id,
                annotations_json,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, work_id, sequence_id) DO UPDATE SET
                annotations_json = excluded.annotations_json,
                updated_at = excluded.updated_at
            """,
            (
                user_id,
                work_id,
                sequence_id,
                json.dumps(clean_annotations, ensure_ascii=False),
                int(time.time()),
            ),
        )
        connection.commit()


def _get_session_scene_annotations(work_id: str, sequence_id: str) -> list[dict]:
    return st.session_state.get(_session_key(work_id, sequence_id), [])


def _session_key(work_id: str, sequence_id: str) -> str:
    return f"scene_annotations_{work_id}_{sequence_id}"


def _parse_annotations(raw_json: str) -> list[dict]:
    try:
        annotations = json.loads(raw_json)
    except json.JSONDecodeError:
        return []

    if not isinstance(annotations, list):
        return []

    return _clean_annotations(annotations)


def _clean_annotations(annotations: list[dict]) -> list[dict]:
    clean_annotations = []

    for annotation in annotations:
        if not isinstance(annotation, dict):
            continue

        try:
            start = int(annotation.get("start", -1))
            end = int(annotation.get("end", -1))
        except (TypeError, ValueError):
            continue

        if start < 0 or end <= start:
            continue

        annotation_type = annotation.get("type")
        if annotation_type not in {"highlight", "underline", "note"}:
            continue

        color = str(annotation.get("color", "#fde68a"))[:24]
        purpose = (
            QUOTE_ANNOTATION_PURPOSE
            if is_quote_annotation({**annotation, "type": annotation_type, "color": color})
            else ""
        )
        clean_annotations.append(
            {
                "id": str(annotation.get("id", ""))[:80],
                "type": annotation_type,
                "color": color,
                "start": start,
                "end": end,
                "text": str(annotation.get("text", ""))[:1200],
                "note": str(annotation.get("note", ""))[:1200],
                "purpose": purpose,
                "createdAt": int(annotation.get("createdAt", int(time.time() * 1000)) or 0),
            }
        )

    return clean_annotations
