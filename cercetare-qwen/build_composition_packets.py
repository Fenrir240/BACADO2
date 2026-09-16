"""Construiește pachete compacte pentru elementele compoziționale ale romanului Ion."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
GRAPH_PATH = BASE_DIR.parent / "cercetare" / "graf2" / "knowledge-graph.json"
OUTPUT_DIR = BASE_DIR / "prompturi elemente compozitionale"
PLACEHOLDER = "{{GRAPH_PACKET}}"
QWEN_CHARS_PER_TOKEN = 3.142

EVENT_ATTRIBUTES = (
    "chapter_id",
    "chapter_order",
    "global_order",
    "title",
    "canonical_description",
    "participants",
    "location",
    "causes",
    "action",
    "immediate_effects",
    "long_term_effects",
    "state_transitions",
    "motivations",
    "conflicts",
    "themes",
    "importance",
)


@dataclass(frozen=True)
class PacketDefinition:
    number: int
    slug: str
    element_id: str
    element_name: str
    objective: str
    required_sections: tuple[str, ...]
    seed_ids: tuple[str, ...]
    researcher_brief: tuple[dict[str, Any], ...]


DEFINITIONS = (
    PacketDefinition(
        number=1,
        slug="titlul",
        element_id="TITLE",
        element_name="Titlul",
        objective=(
            "Explică valoarea titlului eponim «Ion», cu accent pe simbolistica "
            "prenumelui și pe caracterul tipologic al protagonistului."
        ),
        required_sections=(
            "sensul denotativ și caracterul eponim",
            "frecvența prenumelui și valoarea tipologică",
            "legătura dintre tipologia țăranului, pământ, iubire și statut social",
            "concluzia despre relevanța titlului pentru roman",
        ),
        seed_ids=(
            "WORK_ION",
            "AUTHOR_REBREANU",
            "CHAR_001",
            "CHAR_002",
            "CHAR_003",
            "CHAR_005",
            "CH_01",
            "CH_02",
            "CH_09",
            "CH_13",
            "EV_003",
            "EV_005",
            "EV_011",
            "EV_013",
            "EV_014",
            "EV_017",
            "EV_018",
            "EV_070",
            "EV_080",
            "EV_081",
            "EV_082",
            "EV_084",
            "EV_086",
            "EV_114",
            "EV_122",
            "EV_124",
            "CONCEPT_001",
            "CONCEPT_002",
            "CONCEPT_004",
            "CONCEPT_005",
            "CONCEPT_011",
            "CONCEPT_020",
        ),
        researcher_brief=(
            {
                "brief_id": "RB_TITLE_001",
                "claim": "Titlul este eponim: prenumele protagonistului devine titlul romanului.",
                "basis": "researcher_provided_interpretation",
                "graph_support": "partial",
                "graph_anchor_ids": ["WORK_ION", "CHAR_001"],
            },
            {
                "brief_id": "RB_TITLE_002",
                "claim": (
                    "Ion este un prenume foarte frecvent în mediul rural tradițional, "
                    "iar alegerea lui reduce impresia de excepționalitate individuală."
                ),
                "basis": "researcher_provided_interpretation",
                "graph_support": "not_explicit",
                "graph_anchor_ids": [],
            },
            {
                "brief_id": "RB_TITLE_003",
                "claim": (
                    "Numele susține caracterul tipologic al personajului: Ion întruchipează "
                    "țăranul român tradițional legat de muncă, pământ, statut și demnitate."
                ),
                "basis": "researcher_provided_interpretation",
                "graph_support": "partial",
                "graph_anchor_ids": ["CHAR_001", "EV_011", "EV_014", "CONCEPT_001", "CONCEPT_004"],
            },
        ),
    ),
    PacketDefinition(
        number=2,
        slug="relatia-incipit-final",
        element_id="INCIPIT_FINAL",
        element_name="Relația incipit–final",
        objective=(
            "Explică simetria compozițională dintre început și final, cu accent pe "
            "motivul drumului, cele două hore și continuitatea comunității."
        ),
        required_sections=(
            "incipitul: drumul, intrarea în Pripas și hora inițială",
            "finalul: noua adunare a satului, reluarea horei și continuitatea vieții",
            "corespondențele început–final și structura circulară",
            "contrastul dintre destinul individual și durata colectivă",
        ),
        seed_ids=(
            "WORK_ION",
            "CH_01",
            "CH_13",
            "STATE_CH_01_OPEN",
            "STATE_CH_01_CLOSE",
            "STATE_CH_13_OPEN",
            "STATE_CH_13_CLOSE",
            "EV_001",
            "EV_002",
            "EV_003",
            "EV_113",
            "EV_114",
            "EV_117",
            "EV_118",
            "EV_119",
            "EV_120",
            "EV_121",
            "EV_122",
            "LOC_001",
            "LOC_002",
            "LOC_013",
            "CONCEPT_003",
            "CONCEPT_011",
            "CONCEPT_012",
            "CONCEPT_013",
            "CONCEPT_014",
            "CONCEPT_018",
            "CONCEPT_020",
        ),
        researcher_brief=(
            {
                "brief_id": "RB_FRAME_001",
                "claim": (
                    "Motivul drumului funcționează ca ramă a romanului: drumul conduce "
                    "privirea spre Pripas în incipit și o îndepărtează de sat în final."
                ),
                "basis": "researcher_provided_interpretation_grounded_in_primary_text",
                "graph_support": "explicit_and_interpretive",
                "graph_anchor_ids": ["EV_001", "EV_124", "CONCEPT_018", "STATE_CH_13_CLOSE"],
            },
            {
                "brief_id": "RB_FRAME_002",
                "claim": (
                    "Hora de la început și hora reluată în final formează o simetrie "
                    "compozițională și arată permanența comunității."
                ),
                "basis": "researcher_provided_interpretation",
                "graph_support": "explicit_and_interpretive",
                "graph_anchor_ids": ["EV_002", "EV_003", "EV_121", "EV_122", "CONCEPT_018"],
            },
        ),
    ),
    PacketDefinition(
        number=3,
        slug="conflictul",
        element_id="CONFLICT",
        element_name="Conflictul",
        objective=(
            "Explică organizarea conflictelor romanului prin conflictul interior al lui Ion, "
            "conflictul social Ion–Vasile Baciu și conflictul secundar Belciug–Herdelea."
        ),
        required_sections=(
            "conflictul interior al lui Ion: glasul pământului versus glasul iubirii",
            "conflictul social Ion–Vasile Baciu: sărăcie, pământ, zestre și prestigiu",
            "conflictul Belciug–Herdelea: autoritate, prestigiu și consecințe publice",
            "legătura dintre conflicte și evoluția acțiunii",
        ),
        seed_ids=(
            "WORK_ION",
            "CHAR_001",
            "CHAR_002",
            "CHAR_003",
            "CHAR_005",
            "CHAR_008",
            "CHAR_009",
            "CHAR_013",
            "CHAR_016",
            "EV_004",
            "EV_005",
            "EV_006",
            "EV_008",
            "EV_011",
            "EV_013",
            "EV_016",
            "EV_017",
            "EV_018",
            "EV_019",
            "EV_022",
            "EV_023",
            "EV_025",
            "EV_035",
            "EV_037",
            "EV_045",
            "EV_049",
            "EV_050",
            "EV_052",
            "EV_053",
            "EV_054",
            "EV_055",
            "EV_056",
            "EV_057",
            "EV_059",
            "EV_060",
            "EV_061",
            "EV_064",
            "EV_065",
            "EV_067",
            "EV_068",
            "EV_069",
            "EV_080",
            "EV_084",
            "EV_086",
            "EV_089",
            "EV_102",
            "EV_103",
            "EV_104",
            "CONCEPT_001",
            "CONCEPT_002",
            "CONCEPT_004",
            "CONCEPT_005",
            "CONCEPT_013",
            "CONCEPT_014",
        ),
        researcher_brief=(
            {
                "brief_id": "RB_CONFLICT_001",
                "claim": (
                    "Conflictul interior central al lui Ion opune dorința de pământ "
                    "iubirii pentru Florica."
                ),
                "basis": "researcher_provided_focus",
                "graph_support": "explicit_and_interpretive",
                "graph_anchor_ids": ["EV_017", "EV_018", "CONCEPT_002", "CONCEPT_005"],
            },
            {
                "brief_id": "RB_CONFLICT_002",
                "claim": (
                    "Conflictul social Ion–Vasile Baciu pornește din diferența de avere și "
                    "se dezvoltă în jurul Anei, zestrei, pământurilor și prestigiului."
                ),
                "basis": "researcher_provided_focus",
                "graph_support": "explicit_and_interpretive",
                "graph_anchor_ids": ["EV_006", "EV_008", "EV_056", "EV_057", "EV_064", "EV_069"],
            },
            {
                "brief_id": "RB_CONFLICT_003",
                "claim": (
                    "Conflictul secundar Belciug–Herdelea exprimă rivalitatea dintre "
                    "autoritatea religioasă și intelectualitatea rurală vulnerabilă."
                ),
                "basis": "researcher_provided_focus",
                "graph_support": "explicit_and_interpretive",
                "graph_anchor_ids": ["EV_022", "EV_052", "EV_054", "CONCEPT_013", "CONCEPT_014"],
            },
        ),
    ),
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact_node(node: dict[str, Any]) -> dict[str, Any]:
    result = {
        key: node[key]
        for key in (
            "id",
            "type",
            "label",
            "description",
            "chapter_ids",
            "importance",
            "confidence",
            "assertion_type",
        )
        if key in node
    }
    attributes = node.get("attributes") or {}
    if node.get("type") == "NarrativeEvent":
        selected = {key: attributes[key] for key in EVENT_ATTRIBUTES if key in attributes}
        if selected:
            result["attributes"] = selected
    elif attributes:
        result["attributes"] = attributes
    return result


def compact_edge(edge: dict[str, Any]) -> dict[str, Any]:
    result = {
        key: edge[key]
        for key in ("id", "source", "predicate", "target", "assertion_type")
        if key in edge
    }
    if edge.get("qualifiers"):
        result["qualifiers"] = edge["qualifiers"]
    return result


def referenced_node_ids(node: dict[str, Any], canonical_ids: set[str]) -> set[str]:
    values: set[str] = set(node.get("chapter_ids") or [])
    attributes = node.get("attributes") or {}
    for key in ("chapter_id", "location"):
        value = attributes.get(key)
        if isinstance(value, str):
            values.add(value)
    for key in ("participants", "conflicts", "themes"):
        values.update(str(value) for value in attributes.get(key) or [])
    return values & canonical_ids


def build_packet(definition: PacketDefinition, graph: dict[str, Any]) -> dict[str, Any]:
    nodes_by_id = {node["id"]: node for node in graph["nodes"]}
    canonical_ids = set(nodes_by_id)
    missing = sorted(set(definition.seed_ids) - canonical_ids)
    if missing:
        raise ValueError(f"{definition.element_id}: seed IDs inexistente: {missing}")
    selected_ids = set(definition.seed_ids)
    for node_id in tuple(selected_ids):
        selected_ids.update(referenced_node_ids(nodes_by_id[node_id], canonical_ids))
    nodes = [compact_node(node) for node in graph["nodes"] if node["id"] in selected_ids]
    edges = [
        compact_edge(edge)
        for edge in graph["edges"]
        if edge["source"] in selected_ids and edge["target"] in selected_ids
    ]
    chapter_ids = sorted(
        {chapter_id for node in nodes for chapter_id in node.get("chapter_ids") or []}
    )
    return {
        "metadata": {
            "packet_id": f"ION-GRAPH2-COMPOSITION-{definition.number:02d}",
            "task": "composition_element_schema",
            "element_id": definition.element_id,
            "element_name": definition.element_name,
            "source_graph": "cercetare/graf2/knowledge-graph.json",
            "source_graph_version": graph["metadata"]["version"],
            "source_graph_sha256": sha256_file(GRAPH_PATH),
            "language": "ro",
            "compact": True,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "chapter_count": len(chapter_ids),
        },
        "source_policy": {
            "graph_evidence": (
                "Nodurile, muchiile și atributele sunt extrase din graful canonic și pot "
                "fi citate prin ID."
            ),
            "researcher_brief": (
                "Direcțiile interpretative furnizate de cercetător sunt permise, dar se "
                "citează separat prin brief_id și nu se prezintă ca muchii explicite ale grafului."
            ),
            "forbidden": (
                "Memoria modelului, internetul, textul integral al romanului și alte surse externe."
            ),
        },
        "assignment": {
            "objective": definition.objective,
            "required_sections": list(definition.required_sections),
        },
        "researcher_brief": list(definition.researcher_brief),
        "ontology": {
            "node_types": sorted({node["type"] for node in nodes}),
            "relationship_types": sorted({edge["predicate"] for edge in edges}),
            "assertion_types": sorted(
                {node.get("assertion_type") for node in nodes if node.get("assertion_type")}
                | {edge.get("assertion_type") for edge in edges if edge.get("assertion_type")}
            ),
        },
        "nodes": nodes,
        "edges": edges,
        "validation": {
            "all_ids_canonical": True,
            "all_edge_endpoints_included": True,
            "required_seed_ids": list(definition.seed_ids),
            "chapter_ids": chapter_ids,
        },
    }


def prompt_text(definition: PacketDefinition) -> str:
    required = "\n".join(
        f"{index}. {section}" for index, section in enumerate(definition.required_sections, start=1)
    )
    return f"""# Prompt Qwen — schemă pentru elementul compozițional: {definition.element_name}

Ești un redactor educațional care construiește scheme de analiză literară pentru
pregătirea examenului de Bacalaureat. Lucrează exclusiv cu cele două categorii de
surse din `GRAPH_PACKET`:

1. dovezi canonice din `nodes`, `edges` și atribute;
2. direcții interpretative declarate separat în `researcher_brief`.

Nu folosi memoria proprie, internetul, textul romanului sau alte comentarii. Nu
transforma o direcție din `researcher_brief` într-un fapt despre structura grafului.

## Sarcina

{definition.objective}

Construiește o explicație schematizată clară, logică și ușor de memorat. Schema
trebuie să fie utilă unui elev de liceu: suficient de riguroasă pentru un eseu BAC,
dar fără fraze greoaie, jargon inutil ori repetiții.

## Secțiuni obligatorii

{required}

Pentru fiecare idee:

- formulează mai întâi ideea-cheie într-o propoziție scurtă;
- explică apoi legătura logică în 1-3 propoziții;
- indică precis baza: `graph`, `researcher_brief` sau ambele;
- citează toate ID-urile folosite;
- distinge faptele narative de interpretările literare;
- nu inventa citate și nu atribui grafului informații care apar numai în brief.

## Dimensiune și stil

- 4 secțiuni, în ordinea cerută;
- 2-4 idei pentru fiecare secțiune;
- o sinteză finală de 120-180 de cuvinte;
- 3-5 formule foarte scurte în `memory_formula`;
- limba română cu diacritice, registru clar și îngrijit;
- fără identificatori tehnici în textele destinate elevului.

## Format JSON obligatoriu

Returnează exclusiv JSON valid:

```json
{{
  "task": "composition_element_schema",
  "element_id": "{definition.element_id}",
  "element_name": "{definition.element_name}",
  "status": "generated",
  "central_thesis": "Ideea centrală în 1-2 propoziții.",
  "schema": [
    {{
      "section_id": "SECTION_01",
      "heading": "Titlul secțiunii",
      "ideas": [
        {{
          "key_idea": "Ideea-cheie.",
          "explanation": "Explicația clară.",
          "basis": ["graph", "researcher_brief"],
          "node_ids": ["..."],
          "edge_ids": ["..."],
          "attribute_paths": [
            {{"node_id": "EV_...", "json_path": "attributes.action"}}
          ],
          "brief_ids": ["RB_..."]
        }}
      ]
    }}
  ],
  "bac_synthesis": "Sinteza coerentă de 120-180 de cuvinte.",
  "memory_formula": ["formulă scurtă"],
  "validation": {{
    "used_node_ids": ["..."],
    "used_edge_ids": ["..."],
    "used_brief_ids": ["..."],
    "unsupported_claims": []
  }}
}}
```

`basis` trebuie să reflecte baza reală a fiecărei idei. Dacă ideea folosește o
afirmație din brief care are doar suport parțial în graf, include ambele valori și
citează `brief_id`. `validation.unsupported_claims` trebuie să rămână gol; elimină
orice idee care nu poate fi susținută de packet.

## Verificare internă

Înainte de răspuns, verifică: cele patru secțiuni, toate ID-urile, diferența dintre
fapt și interpretare, folosirea tuturor direcțiilor obligatorii din brief, coerența
sintezei și validitatea JSON-ului.

## GRAPH_PACKET

{PLACEHOLDER}
"""


def validate_packet(packet: dict[str, Any], definition: PacketDefinition, graph: dict[str, Any]) -> None:
    canonical_nodes = {node["id"] for node in graph["nodes"]}
    canonical_edges = {edge["id"]: edge for edge in graph["edges"]}
    packet_nodes = {node["id"] for node in packet["nodes"]}
    if not set(definition.seed_ids) <= packet_nodes:
        raise AssertionError(f"{definition.element_id}: lipsesc seed IDs.")
    if not packet_nodes <= canonical_nodes:
        raise AssertionError(f"{definition.element_id}: există noduri necanonice.")
    for edge in packet["edges"]:
        canonical = canonical_edges.get(edge["id"])
        if canonical is None:
            raise AssertionError(f"Muchie necanonică: {edge['id']}")
        if edge["source"] not in packet_nodes or edge["target"] not in packet_nodes:
            raise AssertionError(f"Capăt neinclus pentru {edge['id']}.")
        if (edge["source"], edge["predicate"], edge["target"]) != (
            canonical["source"],
            canonical["predicate"],
            canonical["target"],
        ):
            raise AssertionError(f"Muchie modificată: {edge['id']}")
    brief_ids = [item["brief_id"] for item in packet["researcher_brief"]]
    if len(brief_ids) != len(set(brief_ids)):
        raise AssertionError(f"{definition.element_id}: brief IDs duplicate.")


def build_readme(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Pachete Qwen pentru elementele compoziționale",
        "",
        "Fiecare element are un prompt, un GRAPH_PACKET compact și un fișier `.qwen.txt` gata de trimis.",
        "",
        "Interpretările solicitate de cercetător care nu sunt complet explicite în graful 2 sunt păstrate separat în `researcher_brief`. Qwen trebuie să le citeze prin `brief_id`, fără să le prezinte drept muchii canonice.",
        "",
        "| # | Element | Noduri | Muchii | Tokenuri packet | Tokenuri prompt + packet |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['number']} | {row['element_name']} | {row['node_count']} | "
            f"{row['edge_count']} | {row['packet_tokens']:,} | {row['qwen_tokens']:,} |"
        )
    lines.extend(
        [
            "",
            f"Total estimat pentru cele trei apeluri: **{sum(row['qwen_tokens'] for row in rows):,} tokenuri input**.",
            "",
            "Estimarea folosește raportul empiric de aproximativ 3,142 caractere/token pentru Qwen 3.5 Flash.",
            "",
            "## Fișiere",
            "",
            "- `.prompt.md` — prompt reutilizabil cu `{{GRAPH_PACKET}}`;",
            "- `.graph-packet.json` — subgraful și brief-ul cercetătorului;",
            "- `.qwen.txt` — promptul și packetul deja combinate.",
            "",
            "## Regenerare",
            "",
            "```powershell",
            "python cercetare-qwen/build_composition_packets.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    graph = read_json(GRAPH_PATH)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for definition in DEFINITIONS:
        packet = build_packet(definition, graph)
        validate_packet(packet, definition, graph)
        prefix = f"{definition.number:02d}-{definition.slug}"
        packet_text = compact_json(packet)
        prompt = prompt_text(definition)
        if prompt.count(PLACEHOLDER) != 1:
            raise AssertionError(f"{prefix}: placeholder invalid.")
        qwen = prompt.replace(PLACEHOLDER, packet_text)
        (OUTPUT_DIR / f"{prefix}.graph-packet.json").write_text(packet_text + "\n", encoding="utf-8")
        (OUTPUT_DIR / f"{prefix}.prompt.md").write_text(prompt, encoding="utf-8")
        (OUTPUT_DIR / f"{prefix}.qwen.txt").write_text(qwen, encoding="utf-8")
        rows.append(
            {
                "number": definition.number,
                "element_name": definition.element_name,
                "node_count": len(packet["nodes"]),
                "edge_count": len(packet["edges"]),
                "packet_tokens": math.ceil(len(packet_text) / QWEN_CHARS_PER_TOKEN),
                "qwen_tokens": math.ceil(len(qwen) / QWEN_CHARS_PER_TOKEN),
            }
        )
    (OUTPUT_DIR / "README.md").write_text(build_readme(rows), encoding="utf-8")
    print(f"Generate și validate {len(rows)} pachete în {OUTPUT_DIR}")
    for row in rows:
        print(
            f"{row['number']:02d}. {row['element_name']}: {row['node_count']} noduri, "
            f"{row['edge_count']} muchii, ~{row['qwen_tokens']:,} tokenuri input"
        )
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
