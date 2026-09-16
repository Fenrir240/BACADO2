"""Încarcă blueprint-ul generat pentru secțiunea „Construiește eseul”."""

from __future__ import annotations

import json
from pathlib import Path


def essay_blueprint_path(work_id: str) -> Path:
    return (
        Path("data")
        / "generated_works"
        / str(work_id)
        / "construieste-eseu"
        / "eseu.json"
    )


def load_essay_blueprint(work_id: str) -> dict:
    path = essay_blueprint_path(work_id)
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Fișierul {path} nu conține un obiect JSON.")
    validation = payload.get("validation")
    if not isinstance(validation, dict) or not validation.get("valid"):
        raise ValueError(
            f"Blueprint-ul {path} nu a trecut validarea strictă a eseului-model."
        )
    sections = payload.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ValueError(f"Blueprint-ul {path} nu conține secțiuni.")
    normalized_sections = []
    legacy_section_ids = {
        "element_titlu": "element_title",
        "element_opozitie": "element_opposition_symmetry",
        "element_limbaj": "element_semantic_figures",
    }
    for raw_section in sections:
        if not isinstance(raw_section, dict):
            raise ValueError(f"Blueprint-ul {path} conține o secțiune invalidă.")
        section = dict(raw_section)
        section["id"] = legacy_section_ids.get(str(section.get("id") or ""), section.get("id"))
        if not str(section.get("instructions") or "").strip():
            section["instructions"] = str(section.get("prompt_instruction") or "").strip()
        if not section["instructions"]:
            raise ValueError(
                f"Secțiunea {section.get('id', '?')} din {path} nu are instrucțiuni."
            )
        normalized_sections.append(section)
    payload["sections"] = normalized_sections

    defaults = payload.get("default_composition_element_ids")
    if isinstance(defaults, list):
        legacy_element_ids = {
            "element_titlu": "title",
            "element_opozitie": "opposition_symmetry",
            "element_limbaj": "semantic_figures",
        }
        payload["default_composition_element_ids"] = [
            legacy_element_ids.get(str(value), str(value)) for value in defaults
        ]
    return payload
