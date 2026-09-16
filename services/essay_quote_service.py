"""Leagă citatele marcate în secvențe de secțiunile corespunzătoare din eseu."""

from __future__ import annotations

from services.annotation_service import get_scene_quotes
from services.understanding_service import load_relevant_sequences


LEGACY_RELEVANT_SEQUENCES = {
    "ion": [
        {"id": "cositul", "title": "Cositul"},
        {"id": "sarutarea", "title": "Sărutarea pământului"},
    ]
}


def _sequence_sections(sections: list[dict]) -> list[dict]:
    result = []
    for section in sections:
        section_id = str(section.get("id") or "").strip().lower()
        if (
            str(section.get("kind") or "").strip().lower() == "sequence"
            or section_id.startswith("secventa_")
            or section_id.startswith("scena_")
        ):
            result.append(section)
    return result


def _matching_relevant_sequence(
    section: dict,
    essay_sections: list[dict],
    relevant_sequences: list[dict],
) -> dict | None:
    section_id = str(section.get("id") or "").strip().lower()
    if not section_id:
        return None

    for sequence in relevant_sequences:
        sequence_id = str(sequence.get("id") or "").strip().lower()
        if sequence_id == section_id or sequence_id.startswith(section_id + "_"):
            return sequence

    ordered_sections = _sequence_sections(essay_sections)
    for index, candidate in enumerate(ordered_sections):
        if str(candidate.get("id") or "").strip().lower() == section_id:
            return relevant_sequences[index] if index < len(relevant_sequences) else None
    return None


def quotes_for_essay_section(
    work_id: str,
    section: dict,
    essay_sections: list[dict],
) -> list[dict]:
    """Returnează citatele elevului asociate secvenței analizate în eseu."""
    if section not in _sequence_sections([section]):
        return []
    try:
        relevant_sequences = load_relevant_sequences(work_id)
    except FileNotFoundError:
        relevant_sequences = LEGACY_RELEVANT_SEQUENCES.get(str(work_id), [])
    except ValueError:
        return []
    if not relevant_sequences:
        return []

    sequence = _matching_relevant_sequence(section, essay_sections, relevant_sequences)
    if sequence is None:
        return []
    return [
        {
            "sequence_id": str(sequence.get("id") or ""),
            "sequence_title": str(sequence.get("title") or section.get("title") or "Secvență"),
            "text": text,
        }
        for text in get_scene_quotes(work_id, str(sequence.get("id") or ""))
    ]


def quote_instructions(quotes: list[dict]) -> str:
    """Construiește instrucțiunea strictă trimisă modelului pentru integrarea citatelor."""
    if not quotes:
        return ""
    rendered = "\n".join(
        f"- Din «{quote['sequence_title']}»: „{quote['text']}”" for quote in quotes
    )
    return (
        "CITATE MARCATE DE ELEV ÎN SECȚIUNEA «ÎNȚELEGE OPERA»:\n"
        f"{rendered}\n\n"
        "Integrează obligatoriu aceste citate, exact în forma de mai sus, în comentariul "
        "literar generat pentru această secvență și explică semnificația fiecăruia. "
        "Nu inventa și nu modifica textul citatelor."
    )


def ensure_quotes_present(text: str, quotes: list[dict]) -> str:
    """Garantează că un răspuns generat nu poate omite citatele alese de elev."""
    result = str(text or "").strip()
    missing = [quote for quote in quotes if quote["text"] not in result]
    if not missing:
        return result
    appendix = "\n\n".join(
        f"Citat relevant selectat de elev: „{quote['text']}”." for quote in missing
    )
    return "\n\n".join(part for part in (result, appendix) if part)
