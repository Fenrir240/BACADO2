"""Validare offline a pachetului publicat pentru o operă lirică."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


EXERCISE_FILES = {
    "chronology": "chronology.json",
    "matching": "matching.json",
    "completion": "completion.json",
    "multiple_choice": "multiple_choice.json",
}


def _read_object(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"Lipsește artefactul obligatoriu: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Artefactul {path} nu conține un obiect JSON.")
    return payload


def _require_text(value: Any, label: str, errors: list[str]) -> str:
    text = str(value or "").strip()
    if not text:
        errors.append(f"Lipsește {label}.")
    return text


def _normalized_text(value: Any) -> str:
    text = str(value or "").translate(
        str.maketrans({"„": '"', "”": '"', "«": '"', "»": '"', "’": "'", "–": "-", "—": "-", "/": " "})
    )
    return " ".join(text.split()).casefold()


def _quote_is_in_poem(value: Any, poem_text: str) -> bool:
    candidate = _normalized_text(value).strip('"')
    normalized_poem = _normalized_text(poem_text)
    if len(candidate) >= 4 and candidate in normalized_poem:
        return True
    fragments = [
        _normalized_text(fragment).strip('" ,.;:-')
        for fragment in re.split(r"(?:\.{3,}|…+|[»\"]\s*,\s*[«\"])", str(value or ""))
    ]
    substantive = [fragment for fragment in fragments if len(fragment.split()) >= 3]
    return bool(substantive) and all(fragment in normalized_poem for fragment in substantive)


def validate_poetry_artifacts(root: Path, work_id: str, graph: dict) -> dict:
    """Validează întregul bundle înainte ca acesta să fie promovat și înregistrat."""
    root = root.resolve()
    understanding = root / "data" / "generated_works" / work_id / "intelegere-opera"
    essay_dir = root / "data" / "generated_works" / work_id / "construieste-eseu"
    exercises_dir = root / "data" / "exercises" / work_id
    errors: list[str] = []

    graph_stanzas = {
        int(node["stanza_number"]): str(node.get("quote") or "").strip()
        for node in graph.get("nodes", [])
        if isinstance(node, dict)
        and node.get("type") == "Stanza"
        and node.get("stanza_number") is not None
    }
    poem_text = "\n\n".join(graph_stanzas[number] for number in sorted(graph_stanzas))
    graph_node_ids = {
        str(node.get("id") or "")
        for node in graph.get("nodes", [])
        if isinstance(node, dict) and node.get("id")
    }

    sheet = _read_object(understanding / "fisa-pedagogica.json")
    required_sheet_objects = ("identity", "literary_context", "lyrical_situation", "structure", "prosody")
    required_sheet_lists = (
        "genre_and_species", "themes_and_ideas", "composition_and_language",
        "key_vocabulary", "common_misconceptions", "learning_objectives", "evidence_bank",
    )
    for field in required_sheet_objects:
        if not isinstance(sheet.get(field), dict) or not sheet[field]:
            errors.append(f"Fișa pedagogică nu conține secțiunea {field}.")
    for field in required_sheet_lists:
        if not isinstance(sheet.get(field), list) or not sheet[field]:
            errors.append(f"Fișa pedagogică nu conține secțiunea {field}.")
    if len(sheet.get("learning_objectives", [])) != 8:
        errors.append("Fișa pedagogică trebuie să aibă exact 8 obiective de învățare.")
    if len(sheet.get("evidence_bank", [])) != 10:
        errors.append("Fișa pedagogică trebuie să aibă exact 10 dovezi textuale.")
    for evidence in sheet.get("evidence_bank", []):
        is_graph_fact = (
            isinstance(evidence, dict)
            and evidence.get("stanza") is None
            and str(evidence.get("node_id") or "") in graph_node_ids
        )
        if not is_graph_fact and not _quote_is_in_poem(
            evidence.get("quote") if isinstance(evidence, dict) else "", poem_text
        ):
            errors.append("Fișa pedagogică are un citat care nu apare în textul poeziei.")
    generation = sheet.get("generation") if isinstance(sheet.get("generation"), dict) else {}
    if not str(generation.get("model") or "").startswith("qwen/"):
        errors.append("Fișa pedagogică nu are proveniență Qwen verificabilă.")

    whole_work = _read_object(understanding / "toata-opera.json")
    tableaux = whole_work.get("tableaux")
    if not isinstance(tableaux, list) or not tableaux:
        errors.append("toata-opera.json nu conține tablouri lirice.")

    published_stanzas: dict[int, str] = {}
    for tableau in tableaux if isinstance(tableaux, list) else []:
        if not isinstance(tableau, dict):
            errors.append("Un tablou liric este invalid.")
            continue
        _require_text(tableau.get("simple_verbalization"), "explicația simplă a tabloului", errors)
        _require_text(tableau.get("elevated_verbalization"), "interpretarea academică a tabloului", errors)
        for stanza in tableau.get("stanzas", []):
            if isinstance(stanza, dict) and stanza.get("number") is not None:
                published_stanzas[int(stanza["number"])] = str(stanza.get("text") or "").strip()
    if published_stanzas != graph_stanzas:
        errors.append("Textul strofelor publicate nu coincide exact cu textul din knowledge graph.")

    literary = _read_object(understanding / "curent-literar.json")
    material = literary.get("literary_current")
    if not isinstance(material, dict):
        errors.append("curent-literar.json nu conține literary_current.")
    else:
        movement = material.get("movement") if isinstance(material.get("movement"), dict) else {}
        for field in ("name", "definition", "work_classification"):
            _require_text(movement.get(field), f"movement.{field}", errors)
        traits = material.get("traits")
        if not isinstance(traits, list) or len(traits) != 2:
            errors.append("Curentul literar trebuie să conțină exact două trăsături.")
        else:
            for trait in traits:
                if not isinstance(trait, dict):
                    errors.append("O trăsătură literară este invalidă.")
                    continue
                _require_text(trait.get("title"), "titlul trăsăturii", errors)
                _require_text(trait.get("explanation"), "explicația trăsăturii", errors)
                evidence = trait.get("evidence_from_work")
                if not isinstance(evidence, list) or not evidence:
                    errors.append("O trăsătură nu are dovezi din operă.")

    voices = _read_object(understanding / "voci-si-imagini.json")
    if not isinstance(voices.get("voices"), list) or not voices["voices"]:
        errors.append("voci-si-imagini.json nu conține voci lirice.")
    mindmaps = _read_object(understanding / "personaje-mindmaps.json")
    relation_graph = mindmaps.get("relation_graph")
    if not isinstance(relation_graph, dict):
        errors.append("Lipsește graful relațiilor lirice.")
    else:
        nodes = relation_graph.get("nodes")
        edges = relation_graph.get("edges")
        if not isinstance(nodes, dict) or not nodes:
            errors.append("Graful liric trebuie să aibă nodes indexate după ID.")
        if not isinstance(edges, list):
            errors.append("Graful liric trebuie să aibă o listă edges.")
        elif isinstance(nodes, dict):
            for edge in edges:
                if (
                    not isinstance(edge, dict)
                    or edge.get("source") not in nodes
                    or edge.get("target") not in nodes
                ):
                    errors.append("O muchie a grafului liric referă noduri inexistente.")

    sequences = _read_object(understanding / "secvente-relevante.json").get("sequences")
    required_sequence_fields = {"id", "button_label", "title", "chapter", "source", "text"}
    if not isinstance(sequences, list) or len(sequences) != 2:
        errors.append("Trebuie publicate exact două secvențe relevante.")
    elif any(not isinstance(item, dict) or not required_sequence_fields.issubset(item) for item in sequences):
        errors.append("O secvență relevantă nu respectă schema UI.")

    composition = _read_object(understanding / "elemente-compozitionale.json")
    elements = composition.get("elements")
    if not isinstance(elements, list) or len(elements) < 2:
        errors.append("Lipsesc schemele compoziționale lirice.")
        element_ids: set[str] = set()
    else:
        element_ids = {str(item.get("id") or "") for item in elements if isinstance(item, dict)}
        if len(element_ids) != len(elements) or "" in element_ids:
            errors.append("Schemele compoziționale au ID-uri lipsă sau duplicate.")
        for element in elements:
            if not isinstance(element, dict):
                errors.append("O schemă compozițională este invalidă.")
                continue
            _require_text(element.get("title"), "titlul schemei compoziționale", errors)
            _require_text(element.get("focus"), "ideea centrală a schemei", errors)
            if not isinstance(element.get("branches"), list) or not element["branches"]:
                errors.append("O schemă compozițională nu are ramuri.")
            else:
                for branch in element["branches"]:
                    if not isinstance(branch, dict):
                        errors.append("O ramură compozițională este invalidă.")
                        continue
                    _require_text(
                        branch.get("explanation") or branch.get("content"),
                        "explicația ramurii compoziționale",
                        errors,
                    )

    flashcards = _read_object(root / "data" / "flashcards" / f"{work_id}.json").get("cards")
    allowed_categories = {"context", "curent", "teme", "structura", "voci", "limbaj", "prozodie", "citate"}
    if not isinstance(flashcards, list) or len(flashcards) != 24:
        errors.append("Banca trebuie să conțină exact 24 de flashcarduri.")
    else:
        card_ids = [str(card.get("id") or "") for card in flashcards if isinstance(card, dict)]
        if len(card_ids) != len(flashcards) or len(card_ids) != len(set(card_ids)):
            errors.append("Flashcardurile au ID-uri lipsă sau duplicate.")
        for card in flashcards:
            if (
                not isinstance(card, dict)
                or card.get("category") not in allowed_categories
                or not card.get("source_refs")
                or not str(card.get("front") or "").strip()
                or not str(card.get("back") or "").strip()
            ):
                errors.append("Un flashcard nu are categorie semantică, surse sau conținut.")

    for bank_name, filename in EXERCISE_FILES.items():
        bank = _read_object(exercises_dir / filename).get("exercises")
        if not isinstance(bank, list) or not bank:
            errors.append(f"Banca {bank_name} nu conține exercises.")
            continue
        if bank_name == "multiple_choice":
            if len(bank) != 10:
                errors.append("Banca multiple_choice trebuie să conțină exact 10 grile.")
            for item in bank:
                options = item.get("options") if isinstance(item, dict) else []
                if (
                    not isinstance(options, list)
                    or len(options) != 4
                    or len(set(options)) != 4
                    or item.get("answer") not in options
                    or not item.get("source_refs")
                    or not str(item.get("explanation") or "").strip()
                ):
                    errors.append("O grilă nu respectă schema UI.")
        elif bank_name == "chronology":
            if len(bank) != 3:
                errors.append("Banca chronology trebuie să conțină exact 3 exerciții.")
            for item in bank:
                ordered = item.get("items") if isinstance(item, dict) else []
                positions = [step.get("position") for step in ordered if isinstance(step, dict)]
                if (
                    len(ordered) < 3
                    or positions != list(range(1, len(ordered) + 1))
                    or any(not step.get("source_refs") for step in ordered if isinstance(step, dict))
                ):
                    errors.append("Un exercițiu de ordonare nu respectă schema UI.")
        elif bank_name == "matching":
            if len(bank) != 3:
                errors.append("Banca matching trebuie să conțină exact 3 exerciții.")
            for item in bank:
                pairs = item.get("pairs", []) if isinstance(item, dict) else []
                if (
                    len(pairs) != 4
                    or len({str(pair.get("left")) for pair in pairs if isinstance(pair, dict)}) != 4
                    or len({str(pair.get("right")) for pair in pairs if isinstance(pair, dict)}) != 4
                ):
                    errors.append("Un exercițiu de asociere nu are patru perechi univoce.")
        elif bank_name == "completion":
            if len(bank) != 4:
                errors.append("Banca completion trebuie să conțină exact 4 exerciții.")
            for item in bank:
                text = str(item.get("text") or "") if isinstance(item, dict) else ""
                answers = item.get("answers", []) if isinstance(item, dict) else []
                rebuilt = text
                for answer in answers:
                    rebuilt = rebuilt.replace("____", str(answer), 1)
                if (
                    text.count("____") != 3
                    or len(answers) != 3
                    or _normalized_text(rebuilt).strip('"') not in _normalized_text(poem_text)
                    or not item.get("source_refs")
                ):
                    errors.append("Un exercițiu de completare nu reconstruiește un fragment exact al poeziei.")

    essay = _read_object(essay_dir / "eseu.json")
    validation = essay.get("validation")
    if not isinstance(validation, dict) or not validation.get("valid"):
        errors.append("Blueprint-ul eseului nu a trecut validarea internă.")
    sections = essay.get("sections")
    if not isinstance(sections, list) or not sections:
        errors.append("Blueprint-ul eseului nu conține secțiuni.")
    else:
        section_ids = {str(section.get("id") or "") for section in sections if isinstance(section, dict)}
        for section in sections:
            if not isinstance(section, dict) or not str(section.get("instructions") or "").strip():
                errors.append("O secțiune de eseu nu are instrucțiuni.")
        for element_id in essay.get("default_composition_element_ids", []):
            if str(element_id) not in element_ids:
                errors.append(f"Elementul implicit {element_id} nu există în schemele publicate.")
            expected_section = f"element_{element_id}"
            if expected_section not in section_ids:
                errors.append(f"Secțiunea {expected_section} lipsește din blueprint-ul eseului.")

    report = {
        "schema_version": 2,
        "work_id": work_id,
        "valid": not errors,
        "errors": errors,
    }
    if errors:
        raise ValueError("Pachetul liric este invalid: " + " | ".join(errors))
    return report
