"""Contract comun pentru schemele compoziționale generate și selecția din eseu."""

from __future__ import annotations

import json
import re
from pathlib import Path


ELEMENT_TITLES = {
    "incipit_final": "Relația incipit–final",
    "conflict": "Conflictul",
    "title": "Titlul",
    "opposition_symmetry": "Relații de opoziție și simetrie",
    "semantic_figures": "Limbaj și figuri semantice",
}
ESSAY_SECTION_IDS = {
    "incipit_final": "element_incipit_final",
    "conflict": "element_conflict",
    "title": "element_title",
    "opposition_symmetry": "element_opposition_symmetry",
    "semantic_figures": "element_semantic_figures",
}

LEGACY_ELEMENT_IDS = {
    "element_titlu": "title",
    "element_opozitie": "opposition_symmetry",
    "element_limbaj": "semantic_figures",
}


def composition_path(work_id: str) -> Path:
    return (
        Path("data")
        / "generated_works"
        / work_id
        / "intelegere-opera"
        / "elemente-compozitionale.json"
    )


def load_composition_schemas(work_id: str) -> dict:
    path = composition_path(work_id)
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("elements"), list):
        raise ValueError(f"Fișierul {path} nu respectă schema elementelor compoziționale.")
    essay_paragraphs = _composition_essay_paragraphs(work_id)
    payload = dict(payload)
    payload["elements"] = [
        _normalize_composition_element(element, essay_paragraphs)
        for element in payload["elements"]
        if isinstance(element, dict)
    ]
    return payload


def _composition_essay_paragraphs(work_id: str) -> dict[str, str]:
    """Leagă schemele vizuale de paragrafele canonice publicate pentru eseu."""
    path = essay_blueprint_path(work_id)
    if not path.is_file():
        return {}
    try:
        blueprint = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    sections = blueprint.get("sections") if isinstance(blueprint, dict) else []
    if not isinstance(sections, list):
        return {}
    return {
        str(section.get("id")): str(section.get("canonical_text") or "").strip()
        for section in sections
        if isinstance(section, dict) and section.get("id")
    }


def _normalize_composition_element(
    element: dict,
    essay_paragraphs: dict[str, str],
) -> dict:
    """Acceptă atât schema Qwen compactă, cât și contractul UI extins."""
    normalized = dict(element)
    normalized["central_idea"] = str(
        normalized.get("central_idea") or normalized.get("focus") or ""
    ).strip()

    branches = []
    for branch in normalized.get("branches", []):
        if not isinstance(branch, dict):
            continue
        branch = dict(branch)
        explanation = str(
            branch.get("explanation") or branch.get("content") or ""
        ).strip()
        branch["explanation"] = explanation
        branch["key_idea"] = str(branch.get("key_idea") or explanation).strip()
        branches.append(branch)
    normalized["branches"] = branches

    formulas = normalized.get("memory_formula")
    if not isinstance(formulas, list) or not any(str(value).strip() for value in formulas):
        formulas = [branch.get("heading", "") for branch in branches[:3]]
    normalized["memory_formula"] = [
        str(value).strip() for value in formulas if str(value).strip()
    ]

    element_id = str(normalized.get("id") or "")
    normalized["essay_paragraph"] = str(
        normalized.get("essay_paragraph")
        or essay_paragraphs.get(ESSAY_SECTION_IDS.get(element_id, f"element_{element_id}"), "")
    ).strip()
    return normalized


def infer_composition_element_ids(model_essay: str) -> list[str]:
    """Extrage, în ordinea eseului-model, cele două elemente dezvoltate explicit."""
    selected: list[str] = []
    paragraphs = [
        " ".join(paragraph.split())
        for paragraph in re.split(r"\n\s*\n", str(model_essay or ""))
        if paragraph.strip()
    ]
    for paragraph in paragraphs:
        normalized = paragraph.casefold()
        is_composition_paragraph = (
            "element compozi" in normalized
            or "element de compozi" in normalized
            or "element de limbaj" in normalized
            or "element stilistic" in normalized
        )
        if not is_composition_paragraph:
            continue
        element_id = None
        if "incipit" in normalized and "final" in normalized:
            element_id = "incipit_final"
        elif re.search(r"\bconflict", normalized):
            element_id = "conflict"
        elif re.search(r"\btitl", normalized):
            element_id = "title"
        elif re.search(r"\bopozi|\bsimetri", normalized):
            element_id = "opposition_symmetry"
        elif re.search(r"\blimbaj|\bfigur", normalized):
            element_id = "semantic_figures"
        if element_id and element_id not in selected:
            selected.append(element_id)
        if len(selected) == 2:
            break
    return selected


def essay_blueprint_path(work_id: str) -> Path:
    return (
        Path("data")
        / "generated_works"
        / work_id
        / "construieste-eseu"
        / "eseu.json"
    )


def default_composition_element_ids(work_id: str) -> list[str]:
    """Încarcă selecția implicită publicată sau o deduce din eseul-model canonic."""
    path = essay_blueprint_path(work_id)
    if not path.is_file():
        return []
    try:
        blueprint = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return []
    declared = blueprint.get("default_composition_element_ids")
    if isinstance(declared, list):
        result = []
        for value in declared:
            element_id = LEGACY_ELEMENT_IDS.get(str(value), str(value))
            if element_id in ELEMENT_TITLES and element_id not in result:
                result.append(element_id)
        if result:
            return result[:2]
    source = blueprint.get("source") if isinstance(blueprint.get("source"), dict) else {}
    model_path = Path(str(source.get("model_essay") or ""))
    if not model_path.is_file():
        model_path = path.with_name("eseu-model.md")
    try:
        model_essay = model_path.read_text(encoding="utf-8")
    except OSError:
        return []
    return infer_composition_element_ids(model_essay)


def selected_elements_for_essay(work_id: str, progress: dict) -> list[dict]:
    selected_ids = progress.get("composition_selected_elements", [])
    if not isinstance(selected_ids, list):
        selected_ids = []
    try:
        payload = load_composition_schemas(work_id)
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        payload = {"elements": []}
    by_id = {
        str(element.get("id")): element
        for element in payload["elements"]
        if isinstance(element, dict) and element.get("id")
    }
    effective_ids: list[str] = []
    for element_id in selected_ids:
        element_id = str(element_id)
        if element_id in by_id and element_id not in effective_ids:
            effective_ids.append(element_id)
        if len(effective_ids) == 2:
            break
    if len(effective_ids) < 2:
        for element_id in default_composition_element_ids(work_id):
            if element_id in by_id and element_id not in effective_ids:
                effective_ids.append(element_id)
            if len(effective_ids) == 2:
                break
    if len(effective_ids) < 2:
        for element_id in by_id:
            if element_id not in effective_ids:
                effective_ids.append(element_id)
            if len(effective_ids) == 2:
                break
    result = []
    for element_id in effective_ids:
        element = by_id.get(element_id, {})
        result.append(
            {
                "id": element_id,
                "section_id": ESSAY_SECTION_IDS.get(element_id, f"element_{element_id}"),
                "title": str(element.get("title") or ELEMENT_TITLES.get(element_id) or element_id),
                "essay_paragraph": str(element.get("essay_paragraph") or "").strip(),
                "central_idea": str(
                    element.get("central_idea") or element.get("focus") or ""
                ).strip(),
            }
        )
    return result
