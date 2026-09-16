from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from collections import deque
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = ROOT / "cercetare" / "graf2" / "knowledge-graph.json"
OUTPUT_DIR = ROOT / "cercetare-qwen" / "prompturi rezumate capitole"
EMPIRICAL_CHARS_PER_TOKEN = 900_220 / 286_471

EVENT_ATTRIBUTES = (
    "event_id",
    "chapter_id",
    "chapter_order",
    "global_order",
    "title",
    "canonical_description",
    "participants",
    "location",
    "time_context",
    "preconditions",
    "causes",
    "action",
    "immediate_effects",
    "long_term_effects",
    "state_transitions",
    "motivations",
    "conflicts",
    "themes",
    "importance",
    "confidence",
    "simple_narration",
    "elevated_narration",
    "simple_transition",
    "elevated_transition",
)

ALLOWED_NODE_TYPES = {
    "Chapter",
    "NarrativeEvent",
    "NarrativeState",
    "Character",
    "Location",
    "Theme",
    "Conflict",
    "Symbol",
    "Motif",
    "LiteraryTechnique",
    "Value",
    "Institution",
}

RELEVANT_PREDICATES = {
    "occurs_in_chapter",
    "occurs_at",
    "occurs_before",
    "immediately_precedes",
    "causes",
    "contributes_to",
    "enables",
    "results_in",
    "has_participant",
    "changes_state_of",
    "expresses_theme",
    "expresses_motif",
    "symbolizes",
    "contrasts_with",
    "parallels",
    "loves",
    "is_married_to",
    "is_parent_of",
    "is_child_of",
    "is_rival_of",
    "has_opening_state",
    "has_closing_state",
}


PROMPT_TEMPLATE = """# Rezumat factual — __CHAPTER_TITLE__

Ești un verbalizator factual. Transformă numai evenimentele verificate din `GRAPH_PACKET`
într-un rezumat pentru Bacalaureat. Nu folosi memoria proprie despre roman și nu completa goluri.

## Reguli obligatorii

1. Folosește exclusiv `verified_events`, în ordinea `order`.
2. Acoperă toate și numai ID-urile din `chapter.verified_event_sequence`.
3. Nu folosi `excluded_events`; ele sunt păstrate doar pentru audit.
4. Fiecare propoziție trebuie să aibă unul sau cel mult două `event_ids`.
5. Pentru fiecare propoziție returnează numai `event_ids`; citatele rămân în packet și sunt
   asociate local de validator. Nu copia citatele în răspuns.
6. `fact` este reformularea canonică, iar `provenance.evidence_quote` este dovada primară.
   Păstrează numai detaliile compatibile cu ambele și preferă formularea mai prudentă dacă
   citatul susține doar o parte din `fact`.
7. Nu adăuga cauze, intenții, consecințe, intensificări sau precizări temporale absente
   din `fact` și din citatul-sursă. Sunt interzise în special cuvinte precum
   „instantaneu”, „definitiv”, „complet”, „exclusiv” și „singura soluție” dacă nu apar în dovezi.
8. Nu transforma interpretările simbolice în fapte. Rezumatul conține numai acțiuni și stări narative.
9. Scrie concis, orientativ 80-220 de cuvinte, în 2-4 paragrafe. Acoperirea factuală are
   prioritate față de lungime; nu adăuga informații pentru a atinge o limită minimă.
10. `sentence_text` trebuie să reproducă exact propoziția corespunzătoare din `summary`.
11. Dacă datele verificate sunt insuficiente, păstrează rezumatul mai scurt și explică în
    `validation_notes`; nu inventa nimic.

Returnează exclusiv JSON valid:

```json
{
  "task": "chapter_summary",
  "chapter_id": "__CHAPTER_ID__",
  "chapter_title": "__CHAPTER_TITLE__",
  "status": "generated",
  "summary": "Rezumatul factual.",
  "sentence_evidence": [
    {
      "sentence_index": 1,
      "sentence_text": "Propoziția exactă din summary.",
      "event_ids": ["EV_..."]
    }
  ],
  "coverage": {
    "covered_event_ids": ["EV_..."],
    "excluded_event_ids": [],
    "event_count_expected": __EVENT_COUNT__,
    "event_count_covered": __EVENT_COUNT__
  },
  "style": {"language": "ro", "word_count": 0, "paragraph_count": 0},
  "validation_notes": []
}
```

## GRAPH_PACKET

{{GRAPH_PACKET}}
"""


def load_graph() -> dict[str, Any]:
    return json.loads(GRAPH_PATH.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(character for character in value if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def compact_node(node: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": node["id"],
        "type": node["type"],
        "label": node["label"],
        "description": node["description"],
        "chapter_ids": node.get("chapter_ids", []),
        "importance": node.get("importance"),
        "confidence": node.get("confidence"),
        "assertion_type": node.get("assertion_type"),
    }
    if node["type"] == "NarrativeEvent":
        attrs = node.get("attributes", {})
        result["attributes"] = {field: attrs[field] for field in EVENT_ATTRIBUTES if field in attrs}
    elif node.get("attributes"):
        result["attributes"] = node["attributes"]
    return result


def compact_edge(edge: dict[str, Any]) -> dict[str, Any]:
    result = {
        "id": edge["id"],
        "source": edge["source"],
        "predicate": edge["predicate"],
        "target": edge["target"],
        "assertion_type": edge["assertion_type"],
    }
    if edge.get("qualifiers"):
        result["qualifiers"] = edge["qualifiers"]
    return result


def boundary_state(
    graph: dict[str, Any], node_by_id: dict[str, dict[str, Any]], chapter_index: int, direction: int
) -> dict[str, Any] | None:
    neighbor_index = chapter_index + direction
    if not 0 <= neighbor_index < len(graph["chapters"]):
        return None
    neighbor = graph["chapters"][neighbor_index]
    state_id = neighbor["closing_state"] if direction < 0 else neighbor["opening_state"]
    state = node_by_id[state_id]
    return {
        "chapter_id": neighbor["id"],
        "chapter_title": neighbor["title"],
        "state_id": state_id,
        "state_label": state["label"],
        "state_description": state["description"],
    }


def build_packet(graph: dict[str, Any], chapter_index: int) -> dict[str, Any]:
    chapter = graph["chapters"][chapter_index]
    node_by_id = {node["id"]: node for node in graph["nodes"]}
    verified_events: list[dict[str, Any]] = []
    excluded_events: list[dict[str, Any]] = []
    for event_id in chapter["event_sequence"]:
        event = node_by_id[event_id]
        attrs = event.get("attributes", {})
        verification = attrs.get("verification", {})
        if event.get("assertion_type") != "explicit_fact":
            excluded_events.append(
                {
                    "id": event_id,
                    "order": attrs.get("chapter_order"),
                    "reason": "Afirmație interpretativă; nu poate fi verbalizată drept fapt în rezumat.",
                    "assertion_type": event.get("assertion_type"),
                    "support_score": verification.get("support_score"),
                }
            )
            continue
        if verification.get("status") != "verified_primary":
            excluded_events.append(
                {
                    "id": event_id,
                    "order": attrs.get("chapter_order"),
                    "reason": "Dovada primară nu a depășit pragul de aliniere; necesită verificare umană.",
                    "support_score": verification.get("support_score"),
                }
            )
            continue
        verified_events.append(
            {
                "id": event_id,
                "order": attrs.get("chapter_order"),
                "importance": event.get("importance"),
                "assertion_type": event.get("assertion_type"),
                "fact": attrs.get("canonical_description") or event.get("description"),
                "provenance": verification,
            }
        )

    verified_ids = [event["id"] for event in verified_events]
    excluded_ids = [event["id"] for event in excluded_events]
    packet: dict[str, Any] = {
        "metadata": {
            "packet_id": f"ION-GRAPH2-SUMMARY-{chapter['ordinal']:02d}",
            "task": "chapter_summary",
            "source_graph": "cercetare/graf2/knowledge-graph.json",
            "source_graph_version": graph["metadata"]["version"],
            "source_graph_sha256": sha256(GRAPH_PATH),
            "language": "ro",
            "compact": True,
            "chapter_id": chapter["id"],
            "chapter_title": chapter["title"],
            "source_event_count": len(chapter["event_sequence"]),
            "verified_event_count": len(verified_events),
            "excluded_event_count": len(excluded_events),
        },
        "usage_rules": {
            "canonical_scope": "Numai verified_events pot apărea în rezumat.",
            "provenance_rule": "Validatorul asociază local event_ids cu evidence_quote; modelul nu recopiază citatele.",
            "source_support_rule": "O propoziție păstrează numai detaliile compatibile cu fact și evidence_quote.",
            "exclusion_rule": "excluded_events nu se verbalizează.",
            "interpretation_rule": "Rezumatul factual nu folosește teme, simboluri sau motivații deduse.",
        },
        "chapter": {
            "id": chapter["id"],
            "ordinal": chapter["ordinal"],
            "title": chapter["title"],
            "part_id": chapter["part_id"],
            "source_event_sequence": chapter["event_sequence"],
            "verified_event_sequence": verified_ids,
            "excluded_event_sequence": excluded_ids,
        },
        "verified_events": verified_events,
        "excluded_events": excluded_events,
    }
    packet["validation"] = validate_packet(packet, graph, chapter)
    return packet


def validate_packet(
    packet: dict[str, Any], graph: dict[str, Any], canonical_chapter: dict[str, Any]
) -> dict[str, Any]:
    verified = packet["verified_events"]
    excluded = packet["excluded_events"]
    verified_ids = [event["id"] for event in verified]
    excluded_ids = [event["id"] for event in excluded]
    expected = canonical_chapter["event_sequence"]
    checks = {
        "partition_is_exact": (
            set(verified_ids).isdisjoint(excluded_ids)
            and set(verified_ids) | set(excluded_ids) == set(expected)
            and len(verified_ids) + len(excluded_ids) == len(expected)
        ),
        "verified_sequence_exact": packet["chapter"]["verified_event_sequence"] == verified_ids,
        "excluded_sequence_exact": packet["chapter"]["excluded_event_sequence"] == excluded_ids,
        "all_verified_have_primary_quotes": all(
            event.get("assertion_type") == "explicit_fact"
            and event.get("provenance", {}).get("status") == "verified_primary"
            and bool(event.get("provenance", {}).get("evidence_quote"))
            for event in verified
        ),
        "no_boundary_context": "boundary_context" not in packet,
        "no_graph_noise": "nodes" not in packet and "edges" not in packet,
    }
    passed = all(checks.values()) and bool(verified)
    return {
        "passed": passed,
        "checks": checks,
        "verified_event_count": len(verified),
        "excluded_event_count": len(excluded),
    }


def render_prompt(chapter: dict[str, Any], verified_event_count: int) -> str:
    return (
        PROMPT_TEMPLATE.replace("__CHAPTER_TITLE__", chapter["title"])
        .replace("__CHAPTER_ID__", chapter["id"])
        .replace("__EVENT_COUNT__", str(verified_event_count))
    )


def estimate_tokens(characters: int) -> int:
    return round(characters / EMPIRICAL_CHARS_PER_TOKEN)


def write_readme(rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Prompturi și GRAPH_PACKET-uri pentru rezumatele capitolelor",
        "",
        "Directorul conține câte trei fișiere pentru fiecare dintre cele 13 capitole:",
        "",
        "- `.prompt.md` — prompt reutilizabil, cu placeholderul `{{GRAPH_PACKET}}`;",
        "- `.graph-packet.json` — subgraful compact al capitolului;",
        "- `.qwen.txt` — promptul și packetul deja combinate, gata de trimis modelului.",
        "",
        "Fișierele `.qwen.txt` sunt varianta recomandată pentru rulare.",
        "",
        "Estimările folosesc raportul empiric de aproximativ 3,142 caractere/token observat pentru Qwen 3.5 Flash în Experimentul 2.",
        "",
        "| Capitol | Evenimente sursă | Verificate | Excluse | Tokenuri GRAPH_PACKET | Tokenuri fișier Qwen |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['title']} | {row['events']} | {row['verified']} | {row['excluded']} | "
            f"{row['packet_tokens']:,} | {row['combined_tokens']:,} |"
        )
    lines.extend(
        [
            "",
            f"Total estimat pentru toate cele 13 rulări: **{sum(row['combined_tokens'] for row in rows):,} tokenuri input**.",
            "",
            "## Garanții ale packeturilor",
            "",
            "- evenimentele sunt împărțite explicit în verificate și excluse;",
        "- fiecare eveniment verificat are pagină PDF sau locator de sursă și citat din textul integral;",
        "- modelul returnează numai event_ids; citatele nu sunt duplicate în output și sunt verificate local;",
            "- packetul nu conține evenimente din capitole vecine, teme sau muchii inutile;",
            "- evenimentele interpretative sau cu aliniere insuficientă sunt păstrate numai pentru audit și nu pot fi verbalizate.",
            "",
            "## Regenerare",
            "",
            "```powershell",
            "python cercetare-qwen/build_chapter_summary_packets.py",
            "```",
        ]
    )
    (OUTPUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    graph = load_graph()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for index, chapter in enumerate(graph["chapters"]):
        packet = build_packet(graph, index)
        if not packet["validation"]["passed"]:
            raise ValueError(f"Packet invalid pentru {chapter['id']}: {packet['validation']}")
        short_title = chapter["title"].split(" - ", 1)[-1]
        stem = f"{chapter['ordinal']:02d}-{slugify(short_title)}"
        prompt = render_prompt(chapter, len(packet["verified_events"]))
        packet_text = json.dumps(packet, ensure_ascii=False, separators=(",", ":"))
        prompt_path = OUTPUT_DIR / f"{stem}.prompt.md"
        packet_path = OUTPUT_DIR / f"{stem}.graph-packet.json"
        ready_path = OUTPUT_DIR / f"{stem}.qwen.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
        packet_path.write_text(packet_text, encoding="utf-8")
        ready_text = prompt.replace("{{GRAPH_PACKET}}", packet_text)
        ready_path.write_text(ready_text, encoding="utf-8")
        rows.append(
            {
                "title": chapter["title"],
                "events": len(chapter["event_sequence"]),
                "verified": len(packet["verified_events"]),
                "excluded": len(packet["excluded_events"]),
                "packet_tokens": estimate_tokens(len(packet_text)),
                "combined_tokens": estimate_tokens(len(ready_text)),
            }
        )
    write_readme(rows)
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
