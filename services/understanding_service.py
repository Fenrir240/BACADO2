"""Încarcă artefactele generate pentru secțiunea „Înțelege opera”."""

from __future__ import annotations

import json
from pathlib import Path


def understanding_dir(work_id: str) -> Path:
    return Path("data") / "generated_works" / str(work_id) / "intelegere-opera"


def load_relevant_sequences(work_id: str) -> list[dict]:
    path = understanding_dir(work_id) / "secvente-relevante.json"
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    sequences = payload.get("sequences") if isinstance(payload, dict) else None
    if not isinstance(sequences, list) or not sequences:
        raise ValueError(f"Fișierul {path} nu conține secvențe relevante.")
    required = {"id", "button_label", "title", "chapter", "source", "text"}
    if any(not isinstance(item, dict) or not required.issubset(item) for item in sequences):
        raise ValueError(f"Fișierul {path} conține o secvență incompletă.")
    return sequences
