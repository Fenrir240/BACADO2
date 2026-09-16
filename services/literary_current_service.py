"""Încarcă materialul Qwen despre curentul literar al unei opere."""

from __future__ import annotations

import json
from pathlib import Path


def literary_current_path(work_id: str) -> Path:
    return (
        Path("data")
        / "generated_works"
        / work_id
        / "intelegere-opera"
        / "curent-literar.json"
    )


def load_literary_current(work_id: str) -> dict:
    path = literary_current_path(work_id)
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    material = payload.get("literary_current") if isinstance(payload, dict) else None
    if not isinstance(material, dict):
        raise ValueError(f"Fișierul {path} nu conține literary_current.")
    movement = material.get("movement") if isinstance(material.get("movement"), dict) else {}
    if not movement.get("definition") and movement.get("context"):
        movement["definition"] = movement["context"]
    if not movement.get("work_classification"):
        movement["work_classification"] = str(
            material.get("work_classification") or movement.get("context") or ""
        )
    material["movement"] = movement
    for trait in material.get("traits", []):
        if not isinstance(trait, dict):
            continue
        if not trait.get("evidence_from_work") and isinstance(trait.get("evidence_quotes"), list):
            trait["evidence_from_work"] = trait["evidence_quotes"]
    return payload


def literary_current_reader_text(payload: dict) -> str:
    material = payload.get("literary_current", {})
    movement = material.get("movement", {})
    lines = [
        "DEFINIȚIE",
        str(movement.get("definition") or ""),
    ]
    period = str(movement.get("period") or "").strip()
    if period:
        lines.extend(["", "PERIOADĂ", period])
    lines.extend(
        ["", "ÎNCADRAREA OPEREI", str(movement.get("work_classification") or "")]
    )
    historical_context = str(movement.get("historical_context") or "").strip()
    if historical_context:
        lines.extend(["", "CONTEXT LITERAR", historical_context])
    lines.extend(["", "TRĂSĂTURI ILUSTRATE ÎN OPERĂ"])
    for index, trait in enumerate(material.get("traits", []), start=1):
        if not isinstance(trait, dict):
            continue
        lines.extend(
            [
                "",
                f"{index}. {trait.get('title', 'Trăsătură')}",
                str(trait.get("explanation") or ""),
            ]
        )
        evidence = [str(value).strip() for value in trait.get("evidence_from_work", []) if str(value).strip()]
        if evidence:
            lines.append("În operă: " + " • ".join(evidence))
        essay_use = str(trait.get("essay_use") or "").strip()
        if essay_use:
            lines.append("În eseu: " + essay_use)
    synthesis = str(material.get("bac_synthesis") or "").strip()
    if synthesis:
        lines.extend(["", "DE REȚINUT PENTRU BAC", synthesis])
    return "\n".join(lines).strip()
