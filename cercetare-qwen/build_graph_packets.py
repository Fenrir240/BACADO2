from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = ROOT / "cercetare" / "graf2" / "knowledge-graph.json"
PROMPTS_DIR = ROOT / "cercetare-qwen" / "prompturi intrebari"
OUTPUT_DIR = ROOT / "cercetare-qwen" / "graph-packets"

# Raport observat în rularea Qwen 3.5 Flash din Experimentul 2.
EMPIRICAL_CHARS_PER_TOKEN = 900_220 / 286_471


@dataclass(frozen=True)
class PacketSpec:
    number: int
    category_id: str
    filename: str
    prompt_filename: str
    description: str
    node_types: frozenset[str]
    predicates: frozenset[str]
    event_attributes: tuple[str, ...]
    selector: Callable[[dict[str, Any]], set[str]] | None = None


EVENT_BASE_ATTRIBUTES = (
    "chapter_id",
    "chapter_order",
    "global_order",
    "title",
    "participants",
    "location",
    "time_context",
    "importance",
    "verification",
)

SELECTION_ALGORITHM_VERSION = "question-packet-selection-v3-history"
EXCLUDED_EVENT_IDS_KEY = "_question_selection_excluded_event_ids"
IMPORTANCE_WEIGHT = {"major": 3, "medium": 2, "supporting": 1}
RELATION_PREDICATES = {
    "is_married_to",
    "is_parent_of",
    "is_child_of",
    "is_rival_of",
    "loves",
}
CAUSAL_PREDICATES = {"causes", "contributes_to", "enables"}
INTERPRETIVE_TYPES = {"Theme", "Conflict", "Symbol", "Motif", "LiteraryTechnique", "Value"}

SIMPLE_ATTRIBUTES = EVENT_BASE_ATTRIBUTES + (
    "action",
    "simple_narration",
)

ACTION_ATTRIBUTES = EVENT_BASE_ATTRIBUTES + (
    "action",
    "canonical_description",
    "simple_narration",
)

TEMPORAL_ATTRIBUTES = EVENT_BASE_ATTRIBUTES + (
    "action",
    "simple_narration",
)

CAUSAL_ATTRIBUTES = EVENT_BASE_ATTRIBUTES + (
    "preconditions",
    "causes",
    "motivations",
    "action",
    "immediate_effects",
    "long_term_effects",
    "state_transitions",
    "simple_narration",
)

EVOLUTION_ATTRIBUTES = EVENT_BASE_ATTRIBUTES + (
    "action",
    "immediate_effects",
    "long_term_effects",
    "state_transitions",
    "motivations",
    "simple_narration",
)

LITERARY_ATTRIBUTES = EVENT_BASE_ATTRIBUTES + (
    "action",
    "conflicts",
    "themes",
    "simple_narration",
    "elevated_narration",
)

COMPARISON_ATTRIBUTES = EVENT_BASE_ATTRIBUTES + (
    "causes",
    "action",
    "immediate_effects",
    "long_term_effects",
    "state_transitions",
    "conflicts",
    "themes",
    "simple_narration",
    "elevated_narration",
)


def load_graph(path: Path = GRAPH_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def node_ids_for_types(graph: dict[str, Any], types: frozenset[str]) -> set[str]:
    return {node["id"] for node in graph["nodes"] if node["type"] in types}


def relation_context_selector(graph: dict[str, Any]) -> set[str]:
    node_by_id = {node["id"]: node for node in graph["nodes"]}
    character_ids = {node_id for node_id, node in node_by_id.items() if node["type"] == "Character"}
    relation_predicates = {
        "is_married_to",
        "is_parent_of",
        "is_child_of",
        "is_rival_of",
        "loves",
        "opposes",
        "helps",
        "harms",
        "protects",
        "manipulates",
    }
    pairs = {
        frozenset((edge["source"], edge["target"]))
        for edge in graph["edges"]
        if edge["predicate"] in relation_predicates
        and edge["source"] in character_ids
        and edge["target"] in character_ids
    }
    selected = set(character_ids)
    for node in graph["nodes"]:
        if node["type"] != "NarrativeEvent":
            continue
        participants = set(node.get("attributes", {}).get("participants", []))
        if any(pair <= participants for pair in pairs):
            selected.add(node["id"])
            selected.update(participants & character_ids)
    selected.update(
        node["id"]
        for node in graph["nodes"]
        if node["type"] == "Chapter"
        and any(node["id"] in event.get("chapter_ids", []) for event in graph["nodes"] if event["id"] in selected)
    )
    return selected


SPECS = (
    PacketSpec(
        1,
        "SIMPLE_FACT_LOWHOP",
        "01-simple-facts.packet.json",
        "01-intrebari-simple-lowhop.md",
        "Fapte directe despre personaje, locuri, capitole și evenimente.",
        frozenset({"Character", "Location", "Chapter", "NarrativeEvent"}),
        frozenset({"has_participant", "occurs_in_chapter", "occurs_at"}),
        SIMPLE_ATTRIBUTES,
    ),
    PacketSpec(
        2,
        "CHARACTER_RELATION",
        "02-character-relations.packet.json",
        "02-relatii-dintre-personaje-lowhop.md",
        "Relații directe și contexte narative comune între personaje.",
        frozenset({"Character", "Chapter", "NarrativeEvent"}),
        frozenset(
            {
                "is_married_to",
                "is_parent_of",
                "is_child_of",
                "is_rival_of",
                "loves",
                "opposes",
                "helps",
                "harms",
                "protects",
                "manipulates",
                "has_participant",
                "occurs_in_chapter",
            }
        ),
        ACTION_ATTRIBUTES,
        relation_context_selector,
    ),
    PacketSpec(
        3,
        "NARRATIVE_ACTION",
        "03-narrative-actions.packet.json",
        "03-actiune-narativa-lowhop.md",
        "Acțiuni, participanți, locuri și capitole.",
        frozenset({"Character", "Location", "Chapter", "NarrativeEvent"}),
        frozenset({"has_participant", "occurs_in_chapter", "occurs_at"}),
        ACTION_ATTRIBUTES,
    ),
    PacketSpec(
        4,
        "TEMPORAL_ORDER",
        "04-temporal-order.packet.json",
        "04-ordine-narativa-midhop.md",
        "Evenimente și relații explicite de ordine narativă.",
        frozenset({"Chapter", "NarrativeEvent"}),
        frozenset({"occurs_in_chapter", "occurs_before", "immediately_precedes"}),
        TEMPORAL_ATTRIBUTES,
    ),
    PacketSpec(
        5,
        "CAUSE_EFFECT",
        "05-cause-effect.packet.json",
        "05-cauza-si-consecinta-midhop.md",
        "Cauze, motivații, efecte, stări și lanțuri cauzale.",
        frozenset({"Chapter", "NarrativeEvent", "NarrativeState", "Character"}),
        frozenset(
            {
                "causes",
                "contributes_to",
                "enables",
                "results_in",
                "changes_state_of",
                "has_participant",
                "occurs_in_chapter",
                "immediately_precedes",
            }
        ),
        CAUSAL_ATTRIBUTES,
    ),
    PacketSpec(
        6,
        "CHARACTER_EVOLUTION",
        "06-character-evolution.packet.json",
        "06-evolutia-personajelor-highhop.md",
        "Evoluția personajelor prin evenimente și schimbări de stare.",
        frozenset({"Character", "Chapter", "NarrativeEvent", "NarrativeState"}),
        frozenset(
            {
                "has_participant",
                "changes_state_of",
                "occurs_in_chapter",
                "occurs_before",
                "immediately_precedes",
                "results_in",
                "loves",
                "is_married_to",
                "is_rival_of",
            }
        ),
        EVOLUTION_ATTRIBUTES,
    ),
    PacketSpec(
        7,
        "LITERARY_INTERPRETATION",
        "07-literary-concepts.packet.json",
        "07-teme-conflicte-si-simboluri-highhop.md",
        "Teme, conflicte, motive, simboluri și tehnici susținute de evenimente.",
        frozenset(
            {
                "Chapter",
                "NarrativeEvent",
                "Theme",
                "Conflict",
                "Symbol",
                "Motif",
                "LiteraryTechnique",
                "Value",
            }
        ),
        frozenset(
            {
                "expresses_theme",
                "expresses_motif",
                "symbolizes",
                "contrasts_with",
                "parallels",
                "occurs_in_chapter",
                "occurs_before",
                "immediately_precedes",
            }
        ),
        LITERARY_ATTRIBUTES,
    ),
    PacketSpec(
        8,
        "CROSS_CHAPTER_COMPARE",
        "08-cross-chapter-comparison.packet.json",
        "08-comparatii-intre-capitole-highhop.md",
        "Comparații ramificate între evenimente, personaje, stări și concepte din capitole diferite.",
        frozenset(
            {
                "Character",
                "Location",
                "Chapter",
                "NarrativeEvent",
                "NarrativeState",
                "Theme",
                "Conflict",
                "Symbol",
                "Motif",
                "LiteraryTechnique",
                "Value",
            }
        ),
        frozenset(
            {
                "has_participant",
                "changes_state_of",
                "occurs_in_chapter",
                "occurs_at",
                "occurs_before",
                "immediately_precedes",
                "results_in",
                "expresses_theme",
                "expresses_motif",
                "contrasts_with",
                "parallels",
                "loves",
                "is_married_to",
                "is_rival_of",
            }
        ),
        COMPARISON_ATTRIBUTES,
    ),
)


def compact_node(node: dict[str, Any], event_fields: tuple[str, ...]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": node["id"],
        "type": node["type"],
        "label": node["label"],
        "description": node["description"],
        "chapter_ids": node.get("chapter_ids", []),
        "importance": node.get("importance"),
        "assertion_type": node.get("assertion_type"),
    }
    if node["type"] == "NarrativeEvent":
        attrs = node.get("attributes", {})
        result["attributes"] = {field: attrs[field] for field in event_fields if field in attrs}
    elif node.get("attributes"):
        # Atributele compacte ale personajelor/conceptelor pot conține informație utilă.
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


def normalized(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold().replace("ş", "ș").replace("ţ", "ț"))
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", normalized(text)).strip("-")


def graph_work_title(graph: dict[str, Any]) -> str:
    metadata = graph.get("metadata") or {}
    title = str(metadata.get("work") or "")
    if not title:
        title = str(
            next(
                (node.get("label") for node in graph.get("nodes", []) if node.get("type") == "Work"),
                "opera",
            )
        )
    return title


def graph_work_id(graph: dict[str, Any]) -> str:
    return slugify(graph_work_title(graph)) or "opera"


def semantic_graph_sha256(graph: dict[str, Any]) -> str:
    canonical = {
        key: value
        for key, value in graph.items()
        if not str(key).startswith("_question_selection_")
    }
    content = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def source_graph_sha256(graph: dict[str, Any], graph_path: Path | None) -> str:
    if graph_path and graph_path.is_file():
        return sha256(graph_path)
    if GRAPH_PATH.is_file():
        default_graph = load_graph(GRAPH_PATH)
        if semantic_graph_sha256(default_graph) == semantic_graph_sha256(graph):
            return sha256(GRAPH_PATH)
    return semantic_graph_sha256(graph)


def chapter_ordinal_by_id(graph: dict[str, Any]) -> dict[str, int]:
    result: dict[str, int] = {}
    for index, chapter in enumerate(graph.get("chapters", []), start=1):
        chapter_id = str(chapter.get("id") or "")
        if chapter_id:
            result[chapter_id] = int(chapter.get("ordinal") or index)
    for node in graph.get("nodes", []):
        if node.get("type") != "Chapter" or not node.get("id"):
            continue
        attributes = node.get("attributes") or {}
        result.setdefault(str(node["id"]), int(attributes.get("ordinal") or len(result) + 1))
    return result


def chronological_segments(events: list[dict[str, Any]], count: int = 3) -> list[list[dict[str, Any]]]:
    ordered = sorted(
        events,
        key=lambda event: (
            int((event.get("attributes") or {}).get("global_order") or 10_000),
            str(event.get("id") or ""),
        ),
    )
    if len(ordered) < count:
        raise ValueError(f"Graful are doar {len(ordered)} evenimente eligibile; sunt necesare {count}.")
    return [
        ordered[(index * len(ordered)) // count : ((index + 1) * len(ordered)) // count]
        for index in range(count)
    ]


def spread_events_matching(
    events: list[dict[str, Any]],
    requirements: tuple[Callable[[dict[str, Any]], bool], ...],
    *,
    excluded: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Alege stabil câte un eveniment din fiecare treime a operei."""
    excluded = set(excluded or set())
    segments = chronological_segments(events, len(requirements))
    chosen: list[dict[str, Any]] = []
    for segment, requirement in zip(segments, requirements):
        candidates = [
            event for event in segment
            if event["id"] not in excluded and requirement(event)
        ]
        if not candidates:
            candidates = [
                event for event in events
                if event["id"] not in excluded and requirement(event)
            ]
        if not candidates:
            raise ValueError("Graful nu conține suficiente evenimente pentru sloturile cerute.")
        event = min(candidates, key=event_rank)
        chosen.append(event)
        excluded.add(event["id"])
    return chosen


def is_verified_event(node: dict[str, Any]) -> bool:
    return (
        node.get("type") == "NarrativeEvent"
        and node.get("assertion_type") == "explicit_fact"
        and node.get("attributes", {}).get("verification", {}).get("status") == "verified_primary"
    )


def event_rank(node: dict[str, Any]) -> tuple[Any, ...]:
    attrs = node.get("attributes", {})
    verification = attrs.get("verification", {})
    method = str(verification.get("method") or "")
    method_weight = 3 if "manual_fact_correction" in method else 2 if "manual_primary_review" in method else 1
    return (
        -IMPORTANCE_WEIGHT.get(str(node.get("importance")), 0),
        -method_weight,
        -float(verification.get("support_score") or 0),
        int(attrs.get("global_order") or 10_000),
        node["id"],
    )


def verified_events(graph: dict[str, Any]) -> list[dict[str, Any]]:
    excluded = set(graph.get(EXCLUDED_EVENT_IDS_KEY) or [])
    return sorted(
        (
            node for node in graph["nodes"]
            if is_verified_event(node) and node["id"] not in excluded
        ),
        key=event_rank,
    )


def event_ids_spread(events: list[dict[str, Any]], count: int) -> list[str]:
    if not events or count <= 0:
        return []
    best_by_chapter: dict[str, dict[str, Any]] = {}
    for event in sorted(events, key=event_rank):
        chapter_id = str(event.get("attributes", {}).get("chapter_id") or "")
        best_by_chapter.setdefault(chapter_id, event)
    chronological = sorted(
        best_by_chapter.values(),
        key=lambda event: (int(event.get("attributes", {}).get("global_order") or 10_000), event["id"]),
    )
    if len(chronological) <= count:
        chosen = chronological
    elif count == 1:
        chosen = [min(chronological, key=event_rank)]
    else:
        indexes = [(index * (len(chronological) - 1)) // (count - 1) for index in range(count)]
        chosen = [chronological[index] for index in indexes]
    if len(chosen) < count:
        used = {event["id"] for event in chosen}
        chosen.extend(event for event in sorted(events, key=event_rank) if event["id"] not in used)
    return [event["id"] for event in sorted(chosen[:count], key=lambda item: item["attributes"]["global_order"])]


def raw_slot(
    slot_id: str,
    purpose: str,
    *,
    event_ids: list[str],
    anchor_node_ids: list[str] | None = None,
    required_edge_ids: list[str] | None = None,
    min_hops: int = 0,
    max_hops: int = 6,
    selection_rule: str,
) -> dict[str, Any]:
    return {
        "slot_id": slot_id,
        "purpose": purpose,
        "event_ids": list(dict.fromkeys(event_ids)),
        "anchor_node_ids": list(dict.fromkeys(anchor_node_ids or [])),
        "required_edge_ids": list(dict.fromkeys(required_edge_ids or [])),
        "hop_bounds": {"minimum": min_hops, "maximum": max_hops},
        "selection_rule": selection_rule,
    }


def select_simple_slots(graph: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    events = verified_events(graph)
    purposes = (
        "identificarea unui loc sau capitol printr-un eveniment explicit",
        "identificarea participantului la un eveniment",
        "identificarea unei informații factuale directe despre un eveniment",
    )
    requirements = (
        lambda event: bool(event["attributes"].get("location")),
        lambda event: bool(event["attributes"].get("participants")),
        lambda event: bool(event["attributes"].get("action")),
    )
    chosen_events = spread_events_matching(events, requirements)
    slots = []
    for index, (purpose, chosen) in enumerate(zip(purposes, chosen_events), 1):
        slots.append(
            raw_slot(
                f"SIMPLE_{index:02d}", purpose, event_ids=[chosen["id"]], min_hops=0, max_hops=2,
                selection_rule="cel mai bine clasat eveniment verificat din treimea cronologică alocată",
            )
        )
    return slots, len(events)


def select_relation_slots(graph: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    node_by_id = {node["id"]: node for node in graph["nodes"]}
    events = verified_events(graph)
    definitions = (
        ("REL_01", "relație familială sau matrimonială", ("is_parent_of", "is_child_of", "is_married_to")),
        ("REL_02", "relație afectivă explicită", ("loves",)),
        ("REL_03", "relație de rivalitate explicită", ("is_rival_of",)),
    )
    slots: list[dict[str, Any]] = []
    candidate_count = 0
    used_events: set[str] = set()
    used_chapters: set[str] = set()
    for slot_id, purpose, predicates in definitions:
        relation_edges = [
            edge for edge in graph["edges"]
            if edge["predicate"] in predicates
            and node_by_id.get(edge["source"], {}).get("type") == "Character"
            and node_by_id.get(edge["target"], {}).get("type") == "Character"
        ]
        candidates = []
        seen_pairs: set[frozenset[str]] = set()
        for edge in sorted(relation_edges, key=lambda item: (predicates.index(item["predicate"]), item["id"])):
            pair = frozenset((edge["source"], edge["target"]))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            character_terms = {
                character_id: normalized(str(node_by_id[character_id].get("label") or "")).split()[0]
                for character_id in pair
            }
            support = [
                event for event in events
                if pair <= set(event.get("attributes", {}).get("participants", []))
                and all(
                    term in normalized(str(event.get("description") or ""))
                    for term in character_terms.values()
                )
            ]
            candidates.append((edge, support))
        candidate_count += len(candidates)
        edge, support = min(
            candidates,
            key=lambda item: (
                -len({event["attributes"]["chapter_id"] for event in item[1]}),
                -sum(IMPORTANCE_WEIGHT.get(str(event.get("importance")), 0) for event in item[1]),
                predicates.index(item[0]["predicate"]),
                item[0]["id"],
            ),
        )
        supporting_ids: list[str] = []
        if support:
            supporting_event = min(
                support,
                key=lambda event: (
                    event["attributes"]["chapter_id"] in used_chapters,
                    event["id"] in used_events,
                    event_rank(event),
                ),
            )
            supporting_ids = [supporting_event["id"]]
            used_events.add(supporting_event["id"])
            used_chapters.add(supporting_event["attributes"]["chapter_id"])
        slots.append(
            raw_slot(
                slot_id, purpose, event_ids=supporting_ids,
                anchor_node_ids=[edge["source"], edge["target"]], required_edge_ids=[edge["id"]],
                min_hops=1, max_hops=3,
                selection_rule="relația cu cea mai mare acoperire verificată; egalitățile se rup după predicat și ID",
            )
        )
    return slots, candidate_count


def select_action_slots(graph: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    events = verified_events(graph)
    simple_slots, _ = select_simple_slots(graph)
    reserved = {event_id for slot in simple_slots for event_id in slot["event_ids"]}
    purposes = (
        "cine realizează acțiunea",
        "ce face personajul într-un context precis",
        "ce eveniment se produce într-un loc sau capitol precis",
    )
    requirements = (
        lambda event: bool(event["attributes"].get("participants") and event["attributes"].get("action")),
        lambda event: bool(event["attributes"].get("participants") and event["attributes"].get("action")),
        lambda event: bool(
            event["attributes"].get("participants")
            and event["attributes"].get("action")
            and event["attributes"].get("location")
        ),
    )
    chosen_events = spread_events_matching(events, requirements, excluded=reserved)
    slots = []
    for index, (purpose, chosen) in enumerate(zip(purposes, chosen_events), 1):
        slots.append(
            raw_slot(
                f"ACTION_{index:02d}", purpose, event_ids=[chosen["id"]], min_hops=1, max_hops=3,
                selection_rule="cel mai bine clasat eveniment verificat din treimea cronologică alocată",
            )
        )
    return slots, len(events)


def temporal_windows(graph: dict[str, Any]) -> tuple[list[list[str]], list[list[str]], list[list[str]]]:
    verified = {event["id"] for event in verified_events(graph)}
    within: list[list[str]] = []
    cross: list[list[str]] = []
    global_windows: list[list[str]] = []
    for chapter in graph["chapters"]:
        sequence = chapter["event_sequence"]
        for start in range(max(0, len(sequence) - 3)):
            window = sequence[start : start + 4]
            if len(window) == 4 and all(event_id in verified for event_id in window):
                within.append(window)
    for left, right in zip(graph["chapters"], graph["chapters"][1:]):
        window = left["event_sequence"][-2:] + right["event_sequence"][:2]
        if len(window) == 4 and all(event_id in verified for event_id in window):
            cross.append(window)
    global_sequence = [event_id for chapter in graph["chapters"] for event_id in chapter["event_sequence"]]
    for start in range(max(0, len(global_sequence) - 5)):
        window = global_sequence[start : start + 6]
        chapters = {next(node for node in graph["nodes"] if node["id"] == event_id)["attributes"]["chapter_id"] for event_id in window}
        if len(chapters) >= 2 and all(event_id in verified for event_id in window):
            global_windows.append(window)

    return within, cross, global_windows


def select_temporal_slots(graph: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    node_by_id = {node["id"]: node for node in graph["nodes"]}
    within, cross, wide = temporal_windows(graph)

    def window_rank(window: list[str]) -> tuple[Any, ...]:
        events = [node_by_id[event_id] for event_id in window]
        shared = set(events[0]["attributes"].get("participants", []))
        for event in events[1:]:
            shared &= set(event["attributes"].get("participants", []))
        return (
            -len(shared),
            -sum(IMPORTANCE_WEIGHT.get(str(event.get("importance")), 0) for event in events),
            int(events[0]["attributes"]["global_order"]),
            tuple(window),
        )

    chosen_within = min(within, key=window_rank)
    chosen_cross = min(cross, key=window_rank)
    remaining_wide = [window for window in wide if not set(window) & set(chosen_cross)] or wide
    chosen_wide = min(remaining_wide, key=window_rank)
    definitions = (
        ("TEMPORAL_01", "ordonare în interiorul aceluiași capitol", chosen_within),
        ("TEMPORAL_02", "ordonare care traversează două capitole apropiate", chosen_cross),
        ("TEMPORAL_03", "ordonarea unui arc narativ mai larg", chosen_wide),
    )
    slots = [
        raw_slot(
            slot_id, purpose, event_ids=window, min_hops=max(0, len(window) - 1), max_hops=len(window) - 1,
            selection_rule="fereastră temporală verificată cu maxim de participanți comuni și evenimente importante",
        )
        for slot_id, purpose, window in definitions
    ]
    return slots, len(within) + len(cross) + len(wide)


def select_causal_slots(graph: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    node_by_id = {node["id"]: node for node in graph["nodes"]}
    verified_ids = {event["id"] for event in verified_events(graph)}
    causal_edges = [
        edge for edge in graph["edges"]
        if edge["predicate"] in CAUSAL_PREDICATES
        and edge["source"] in verified_ids and edge["target"] in verified_ids
    ]

    def edge_rank(edge: dict[str, Any]) -> tuple[Any, ...]:
        return event_rank(node_by_id[edge["source"]]) + event_rank(node_by_id[edge["target"]]) + (edge["id"],)

    chains = [
        (first, second) for first in causal_edges for second in causal_edges
        if first["target"] == second["source"] and first["source"] != second["target"]
    ]
    best_chain = min(
        chains,
        key=lambda pair: (
            -sum(
                bool(node_by_id[event_id]["attributes"].get("causes"))
                for event_id in (pair[0]["source"], pair[0]["target"], pair[1]["target"])
            ),
            edge_rank(pair[0]) + edge_rank(pair[1]),
        ),
    )
    direct = min(
        (edge for edge in causal_edges if edge["id"] not in {item["id"] for item in best_chain}),
        key=lambda edge: (
            -sum(
                bool(node_by_id[event_id]["attributes"].get("causes"))
                for event_id in (edge["source"], edge["target"])
            ),
            edge_rank(edge),
        ),
    )
    effect_events = [
        event for event in verified_events(graph)
        if event["id"] not in {direct["source"], direct["target"]}
        and (event["attributes"].get("immediate_effects") or event["attributes"].get("long_term_effects"))
    ]
    effect = min(effect_events, key=event_rank)
    result_edge = next(
        (edge for edge in graph["edges"] if edge["source"] == effect["id"] and edge["predicate"] == "results_in"),
        None,
    )
    slots = [
        raw_slot(
            "CAUSE_01", "cauza sau motivația directă a unui eveniment",
            event_ids=[direct["source"], direct["target"]], required_edge_ids=[direct["id"]],
            min_hops=1, max_hops=2,
            selection_rule="cea mai bine clasată muchie cauzală explicită din afara lanțului rezervat slotului 3",
        ),
        raw_slot(
            "CAUSE_02", "consecința directă sau pe termen lung",
            event_ids=[effect["id"]],
            anchor_node_ids=[result_edge["target"]] if result_edge else [],
            required_edge_ids=[result_edge["id"]] if result_edge else [],
            min_hops=0, max_hops=2,
            selection_rule="cel mai bine clasat eveniment verificat cu efecte explicite",
        ),
        raw_slot(
            "CAUSE_03", "lanț cauzal explicit cu două etape",
            event_ids=[best_chain[0]["source"], best_chain[0]["target"], best_chain[1]["target"]],
            required_edge_ids=[best_chain[0]["id"], best_chain[1]["id"]], min_hops=2, max_hops=2,
            selection_rule="cel mai bine clasat traseu simplu format din două muchii cauzale explicite",
        ),
    ]
    return slots, len(causal_edges) + len(effect_events) + len(chains)


def event_text(event: dict[str, Any]) -> str:
    attrs = event.get("attributes", {})
    values = [
        event.get("description", ""), attrs.get("action", ""),
        " ".join(attrs.get("state_transitions", [])), " ".join(attrs.get("immediate_effects", [])),
        " ".join(attrs.get("long_term_effects", [])), " ".join(attrs.get("motivations", [])),
    ]
    return normalized(" ".join(str(value) for value in values))


def explicitly_mentions_character(event: dict[str, Any], character: dict[str, Any]) -> bool:
    label_words = normalized(str(character.get("label") or "")).split()
    return bool(label_words) and label_words[0] in normalized(str(event.get("description") or ""))


def select_evolution_slots(graph: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    node_by_id = {node["id"]: node for node in graph["nodes"]}
    events = verified_events(graph)
    characters = [node for node in graph["nodes"] if node["type"] == "Character"]
    focuses = (
        ("EVOLUTION_01", "evoluție socială sau materială", ("pamant", "avere", "propriet", "statut", "bogat", "sarac")),
        ("EVOLUTION_02", "evoluție afectivă sau relațională", ("iubir", "dorint", "teama", "sufer", "casator", "relat")),
        ("EVOLUTION_03", "degradare, pierdere sau schimbarea obiectivului", ("moarte", "pierde", "durere", "violent", "inchiso", "blestem", "alung")),
    )
    used_characters: set[str] = set()
    slots = []
    pool_size = 0
    for slot_id, purpose, keywords in focuses:
        candidates = []
        for character in characters:
            if character["id"] in used_characters:
                continue
            relevant = [
                event for event in events
                if character["id"] in event["attributes"].get("participants", [])
                and explicitly_mentions_character(event, character)
                and any(keyword in event_text(event) for keyword in keywords)
            ]
            chapters = {event["attributes"]["chapter_id"] for event in relevant}
            if len(relevant) >= 2 and len(chapters) >= 2:
                candidates.append((character, relevant))
        if not candidates:
            for character in characters:
                if character["id"] in used_characters:
                    continue
                relevant = [
                    event for event in events
                    if character["id"] in event["attributes"].get("participants", [])
                    and explicitly_mentions_character(event, character)
                ]
                if len(relevant) >= 3 and len({event["attributes"]["chapter_id"] for event in relevant}) >= 2:
                    candidates.append((character, relevant))
        pool_size += len(candidates)
        character, relevant = min(
            candidates,
            key=lambda item: (
                -len({event["attributes"]["chapter_id"] for event in item[1]}),
                -len(item[1]),
                -IMPORTANCE_WEIGHT.get(str(item[0].get("importance")), 0),
                item[0]["id"],
            ),
        )
        used_characters.add(character["id"])
        if len(relevant) < 3:
            relevant_ids = {event["id"] for event in relevant}
            relevant.extend(
                event for event in events
                if event["id"] not in relevant_ids
                and character["id"] in event["attributes"].get("participants", [])
                and explicitly_mentions_character(event, character)
            )
        slots.append(
            raw_slot(
                slot_id, purpose, event_ids=event_ids_spread(relevant, 3), anchor_node_ids=[character["id"]],
                min_hops=3, max_hops=8,
                selection_rule="personajul cu cele mai multe capitole relevante; trei evenimente distribuite cronologic",
            )
        )
    return slots, pool_size


def connected_events_for_concept(graph: dict[str, Any], concept_id: str) -> list[dict[str, Any]]:
    node_by_id = {node["id"]: node for node in graph["nodes"]}
    excluded = set(graph.get(EXCLUDED_EVENT_IDS_KEY) or [])
    event_ids = {
        edge["source"] for edge in graph["edges"]
        if edge["target"] == concept_id
        and edge["predicate"] in {
            "expresses_theme",
            "intensifies",
            "expresses_motif",
            "evokes_symbol",
            "uses_technique",
            "expresses_value",
        }
    }
    return [
        node_by_id[event_id] for event_id in event_ids
        if event_id not in excluded and is_verified_event(node_by_id.get(event_id, {}))
    ]


def choose_concept(
    graph: dict[str, Any], allowed_types: set[str], excluded: set[str] | None = None
) -> tuple[dict[str, Any], list[dict[str, Any]], int]:
    excluded = excluded or set()
    candidates = []
    for concept in graph["nodes"]:
        if concept["type"] not in allowed_types or concept["id"] in excluded:
            continue
        events = connected_events_for_concept(graph, concept["id"])
        if len(events) >= 2:
            candidates.append((concept, events))
    chosen = min(
        candidates,
        key=lambda item: (
            -len({event["attributes"]["chapter_id"] for event in item[1]}),
            -sum(IMPORTANCE_WEIGHT.get(str(event.get("importance")), 0) for event in item[1]),
            -len(item[1]),
            item[0]["id"],
        ),
    )
    return chosen[0], chosen[1], len(candidates)


def select_literary_slots(graph: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    definitions = (
        ("LITERARY_01", "o temă susținută de evenimente", {"Theme"}),
        ("LITERARY_02", "un conflict susținut de evenimente", {"Conflict"}),
        ("LITERARY_03", "un simbol, motiv sau procedeu literar", {"Symbol", "Motif", "LiteraryTechnique"}),
    )
    slots = []
    pool_size = 0
    used: set[str] = set()
    for slot_id, purpose, types in definitions:
        concept, events, candidates = choose_concept(graph, types, used)
        used.add(concept["id"])
        pool_size += candidates
        slots.append(
            raw_slot(
                slot_id, purpose, event_ids=event_ids_spread(events, 3), anchor_node_ids=[concept["id"]],
                min_hops=3, max_hops=8,
                selection_rule="conceptul cu cea mai mare acoperire pe capitole; trei dovezi distribuite cronologic",
            )
        )
    return slots, pool_size


def select_compare_slots(graph: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    events = verified_events(graph)
    characters = [node for node in graph["nodes"] if node["type"] == "Character"]
    character_candidates = []
    for character in characters:
        relevant = [
            event for event in events
            if character["id"] in event["attributes"].get("participants", [])
            and explicitly_mentions_character(event, character)
        ]
        if len({event["attributes"]["chapter_id"] for event in relevant}) >= 2:
            character_candidates.append((character, relevant))
    character, character_events = min(
        character_candidates,
        key=lambda item: (-len({event["attributes"]["chapter_id"] for event in item[1]}), -len(item[1]), item[0]["id"]),
    )
    literary_slots, _ = select_literary_slots(graph)
    literary_anchors = {anchor for slot in literary_slots for anchor in slot["anchor_node_ids"]}
    conflict, conflict_events, conflict_pool = choose_concept(graph, {"Conflict"}, literary_anchors)
    theme, theme_events, theme_pool = choose_concept(graph, {"Theme"}, literary_anchors)
    slots = [
        raw_slot(
            "COMPARE_01", "compararea acțiunilor sau evoluției aceluiași personaj",
            event_ids=event_ids_spread(character_events, 2), anchor_node_ids=[character["id"]], min_hops=2, max_hops=6,
            selection_rule="personajul prezent în cele mai multe capitole; prima și ultima dovadă distribuită",
        ),
        raw_slot(
            "COMPARE_02", "compararea manifestării unui conflict în capitole diferite",
            event_ids=event_ids_spread(conflict_events, 2), anchor_node_ids=[conflict["id"]], min_hops=2, max_hops=6,
            selection_rule="conflictul cu cea mai mare acoperire; două dovezi din zone cronologice diferite",
        ),
        raw_slot(
            "COMPARE_03", "compararea manifestării unei teme în capitole diferite",
            event_ids=event_ids_spread(theme_events, 2), anchor_node_ids=[theme["id"]], min_hops=2, max_hops=6,
            selection_rule="tema cu cea mai mare acoperire; două dovezi din zone cronologice diferite",
        ),
    ]
    return slots, len(character_candidates) + conflict_pool + theme_pool


SLOT_SELECTORS: dict[str, Callable[[dict[str, Any]], tuple[list[dict[str, Any]], int]]] = {
    "SIMPLE_FACT_LOWHOP": select_simple_slots,
    "CHARACTER_RELATION": select_relation_slots,
    "NARRATIVE_ACTION": select_action_slots,
    "TEMPORAL_ORDER": select_temporal_slots,
    "CAUSE_EFFECT": select_causal_slots,
    "CHARACTER_EVOLUTION": select_evolution_slots,
    "LITERARY_INTERPRETATION": select_literary_slots,
    "CROSS_CHAPTER_COMPARE": select_compare_slots,
}


def event_closure(event: dict[str, Any]) -> set[str]:
    attrs = event.get("attributes", {})
    result = {event["id"]}
    result.update(str(item) for item in attrs.get("participants", []))
    for key in ("location", "chapter_id"):
        if attrs.get(key):
            result.add(str(attrs[key]))
    return result


def finalize_slots(
    graph: dict[str, Any], spec: PacketSpec, raw_slots: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], set[str], set[str]]:
    node_by_id = {node["id"]: node for node in graph["nodes"]}
    edge_by_id = {edge["id"]: edge for edge in graph["edges"]}
    node_order = {node["id"]: index for index, node in enumerate(graph["nodes"])}
    edge_order = {edge["id"]: index for index, edge in enumerate(graph["edges"])}
    finalized = []
    all_nodes: set[str] = set()
    all_edges: set[str] = set()
    for raw in raw_slots:
        slot_nodes = set(raw["anchor_node_ids"])
        for event_id in raw["event_ids"]:
            slot_nodes.update(event_closure(node_by_id[event_id]))
            for edge in graph["edges"]:
                if edge["predicate"] not in spec.predicates:
                    continue
                neighbor_id = None
                if edge["source"] == event_id:
                    neighbor_id = edge["target"]
                elif edge["target"] == event_id:
                    neighbor_id = edge["source"]
                if (
                    neighbor_id in node_by_id
                    and node_by_id[neighbor_id]["type"] != "NarrativeEvent"
                    and node_by_id[neighbor_id]["type"] in spec.node_types
                ):
                    slot_nodes.add(neighbor_id)
        for edge_id in raw["required_edge_ids"]:
            edge = edge_by_id[edge_id]
            slot_nodes.update((edge["source"], edge["target"]))
        slot_nodes = {
            node_id for node_id in slot_nodes
            if node_id in node_by_id and node_by_id[node_id]["type"] in spec.node_types
        }
        slot_edges = {
            edge["id"] for edge in graph["edges"]
            if edge["predicate"] in spec.predicates
            and edge["source"] in slot_nodes and edge["target"] in slot_nodes
        }
        slot_edges.update(
            edge_id for edge_id in raw["required_edge_ids"]
            if edge_id in edge_by_id and edge_by_id[edge_id]["predicate"] in spec.predicates
        )
        chapter_ordinals = chapter_ordinal_by_id(graph)
        chapter_ids = sorted(
            {
                str(node_by_id[event_id]["attributes"]["chapter_id"])
                for event_id in raw["event_ids"]
            },
            key=lambda chapter_id: (chapter_ordinals.get(chapter_id, 10_000), chapter_id),
        )
        finalized.append(
            {
                "slot_id": raw["slot_id"],
                "purpose": raw["purpose"],
                "selection_rule": raw["selection_rule"],
                "event_ids": raw["event_ids"],
                "anchor_node_ids": raw["anchor_node_ids"],
                "allowed_node_ids": sorted(slot_nodes, key=node_order.__getitem__),
                "allowed_edge_ids": sorted(slot_edges, key=edge_order.__getitem__),
                "chapter_ids": chapter_ids,
                "hop_bounds": raw["hop_bounds"],
            }
        )
        all_nodes.update(slot_nodes)
        all_edges.update(slot_edges)
    return finalized, all_nodes, all_edges


def assign_focus_events(slots: list[dict[str, Any]]) -> None:
    """Marchează evenimentul-subiect al fiecărei întrebări, distinct în packet."""
    used: set[str] = set()
    for slot in slots:
        event_ids = [str(value) for value in slot.get("event_ids") or []]
        center = len(event_ids) // 2
        preference = sorted(
            range(len(event_ids)),
            key=lambda index: (abs(index - center), index),
        )
        focus = next((event_ids[index] for index in preference if event_ids[index] not in used), "")
        if not focus and event_ids:
            focus = event_ids[center]
        slot["focus_event_id"] = focus or None
        if focus:
            used.add(focus)


def build_packet(
    graph: dict[str, Any],
    spec: PacketSpec,
    graph_path: Path | None = None,
) -> dict[str, Any]:
    raw_slots, candidate_pool_size = SLOT_SELECTORS[spec.category_id](graph)
    slots, selected_ids, selected_edge_ids = finalize_slots(graph, spec, raw_slots)
    assign_focus_events(slots)
    nodes = [
        compact_node(node, spec.event_attributes)
        for node in graph["nodes"]
        if node["id"] in selected_ids
    ]
    edges = [
        compact_edge(edge) for edge in graph["edges"] if edge["id"] in selected_edge_ids
    ]
    included_event_ids = {node["id"] for node in nodes if node["type"] == "NarrativeEvent"}
    chapters = []
    for chapter in graph["chapters"]:
        sequence = [event_id for event_id in chapter["event_sequence"] if event_id in included_event_ids]
        if sequence:
            chapters.append(
                {
                    "id": chapter["id"], "ordinal": chapter["ordinal"], "title": chapter["title"],
                    "event_sequence": sequence,
                }
            )
    actual_predicates = sorted({edge["predicate"] for edge in edges})
    packet = {
        "metadata": {
            "packet_id": f"{graph_work_id(graph).upper()}-QUESTIONS-{spec.number:02d}",
            "category_id": spec.category_id,
            "description": spec.description,
            "version": graph["metadata"]["version"],
            "work_id": graph_work_id(graph),
            "work_title": graph_work_title(graph),
            "source_graph": graph_path.name if graph_path else "knowledge-graph.json",
            "source_graph_version": graph["metadata"]["version"],
            "source_graph_sha256": source_graph_sha256(graph, graph_path),
            "language": "ro", "compact": True,
            "node_count": len(nodes), "edge_count": len(edges), "chapter_count": len(chapters),
        },
        "selection": {
            "algorithm_version": SELECTION_ALGORITHM_VERSION,
            "batch_number": int(graph.get("_question_selection_batch_number") or 1),
            "deterministic": True,
            "randomness": "none",
            "excluded_previous_event_count": len(set(graph.get(EXCLUDED_EVENT_IDS_KEY) or [])),
            "eligibility_rule": "Numai NarrativeEvent explicit_fact cu verification.status=verified_primary.",
            "stable_tie_break": "importance desc, verification method desc, support_score desc, global_order asc, ID asc",
            "candidate_pool_size": candidate_pool_size,
            "selected_event_count": len(included_event_ids),
            "question_slots": slots,
        },
        "evidence_contract": {
            "slot_rule": "Întrebarea dintr-un slot poate folosi numai allowed_node_ids și allowed_edge_ids din acel slot.",
            "edge_hop_definition": "Un hop este traversarea unei muchii din edges.",
            "attribute_access_definition": "Citirea unui atribut nu este hop și se declară în evidence.attribute_paths.",
            "forbidden_padding": [
                "traversarea unei muchii și revenirea pe inversa ei", "repetarea unui nod în același traseu",
                "folosirea unei muchii fără contribuție la răspuns",
            ],
            "available_event_attribute_paths": [f"attributes.{field}" for field in spec.event_attributes],
        },
        "ontology": {
            "node_types": sorted({node["type"] for node in nodes}),
            "relationship_types": actual_predicates,
            "assertion_types": graph["ontology"]["assertion_types"],
        },
        "nodes": nodes, "edges": edges, "chapters": chapters,
    }
    packet["validation"] = validate_packet(packet, graph, spec)
    return packet


def selected_event_ids(packet: dict[str, Any]) -> set[str]:
    """Returnează evenimentele centrale rezervate de sloturile unui packet."""
    return {
        str(event_id)
        for slot in ((packet.get("selection") or {}).get("question_slots") or [])
        for event_id in slot.get("event_ids") or []
    }


def focus_event_ids(packet: dict[str, Any]) -> set[str]:
    return {
        str(slot["focus_event_id"])
        for slot in ((packet.get("selection") or {}).get("question_slots") or [])
        if slot.get("focus_event_id")
    }


def build_packet_set(
    graph: dict[str, Any],
    output_dir: Path,
    *,
    excluded_event_ids: set[str] | None = None,
    batch_number: int = 1,
    graph_path: Path | None = None,
    excluded_event_ids_by_category: dict[str, set[str]] | None = None,
) -> tuple[list[dict[str, Any]], set[str]]:
    """Construiește un lot reproductibil, excluzând evenimentele loturilor anterioare."""
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    selected: set[str] = set()
    for spec in SPECS:
        category_excluded = set(
            (excluded_event_ids_by_category or {}).get(spec.category_id, excluded_event_ids or set())
        )
        selection_graph = dict(graph)
        selection_graph[EXCLUDED_EVENT_IDS_KEY] = sorted(category_excluded)
        selection_graph["_question_selection_batch_number"] = batch_number
        try:
            packet = build_packet(selection_graph, spec, graph_path)
        except (ValueError, StopIteration) as exc:
            raise ValueError(
                f"Nu mai există suficienți candidați nefolosiți pentru {spec.category_id} "
                f"în lotul {batch_number}. Au fost excluse {len(category_excluded)} "
                "evenimente din loturile anterioare."
            ) from exc
        if not packet["validation"]["passed"]:
            raise ValueError(f"Packet invalid pentru {spec.category_id}: {packet['validation']}")
        packet_path = output_dir / spec.filename
        packet_chars = write_packet(packet_path, packet)
        prompt_chars = len((PROMPTS_DIR / spec.prompt_filename).read_text(encoding="utf-8"))
        packet_events = selected_event_ids(packet)
        if packet_events & category_excluded:
            raise ValueError(
                f"Selecția {spec.category_id} a reutilizat evenimente istorice: "
                f"{sorted(packet_events & category_excluded)}"
            )
        selected.update(packet_events)
        rows.append(
            {
                "number": spec.number,
                "category_id": spec.category_id,
                "filename": spec.filename,
                "prompt_filename": spec.prompt_filename,
                "nodes": len(packet["nodes"]),
                "edges": len(packet["edges"]),
                "packet_chars": packet_chars,
                "packet_tokens": estimate_tokens(packet_chars),
                "combined_tokens": estimate_tokens(packet_chars + prompt_chars),
                "selected_event_ids": sorted(packet_events),
                "focus_event_ids": sorted(focus_event_ids(packet)),
            }
        )
    return rows, selected


def validate_packet(
    packet: dict[str, Any], graph: dict[str, Any], spec: PacketSpec
) -> dict[str, Any]:
    canonical_nodes = {node["id"]: node for node in graph["nodes"]}
    canonical_edges = {edge["id"]: edge for edge in graph["edges"]}
    nodes = packet["nodes"]
    edges = packet["edges"]
    node_ids = [node["id"] for node in nodes]
    node_set = set(node_ids)
    edge_ids = [edge["id"] for edge in edges]
    invalid_nodes = [node_id for node_id in node_ids if node_id not in canonical_nodes]
    invalid_edges = []
    mismatched_edges = []
    for edge in edges:
        canonical = canonical_edges.get(edge["id"])
        if canonical is None or edge["source"] not in node_set or edge["target"] not in node_set:
            invalid_edges.append(edge["id"])
            continue
        if any(edge[key] != canonical[key] for key in ("source", "predicate", "target")):
            mismatched_edges.append(edge["id"])

    event_count = sum(node["type"] == "NarrativeEvent" for node in nodes)
    character_count = sum(node["type"] == "Character" for node in nodes)
    concept_count = sum(
        node["type"] in {"Theme", "Conflict", "Symbol", "Motif", "LiteraryTechnique", "Value"}
        for node in nodes
    )
    predicate_counts: dict[str, int] = {}
    for edge in edges:
        predicate_counts[edge["predicate"]] = predicate_counts.get(edge["predicate"], 0) + 1

    selection = packet.get("selection") or {}
    slots = selection.get("question_slots") or []
    selected_by_slots = {
        event_id for slot in slots for event_id in slot.get("event_ids", [])
    }
    slot_ids = [str(slot.get("slot_id") or "") for slot in slots]
    selection_checks = {
        "algorithm_version_exact": selection.get("algorithm_version") == SELECTION_ALGORITHM_VERSION,
        "declared_deterministic": selection.get("deterministic") is True,
        "exactly_three_unique_slots": len(slots) == 3 and len(set(slot_ids)) == 3 and all(slot_ids),
        "focus_events_are_scoped": all(
            not slot.get("focus_event_id")
            or slot.get("focus_event_id") in set(slot.get("event_ids") or [])
            for slot in slots
        ),
        "all_packet_events_selected_by_slots": selected_by_slots
        == {node["id"] for node in nodes if node["type"] == "NarrativeEvent"},
        "all_events_primary_verified": all(
            node.get("assertion_type") == "explicit_fact"
            and node.get("attributes", {}).get("verification", {}).get("status") == "verified_primary"
            and bool(node.get("attributes", {}).get("verification", {}).get("evidence_quote"))
            for node in nodes if node["type"] == "NarrativeEvent"
        ),
        "slot_ids_are_scoped": all(
            set(slot.get("allowed_node_ids", [])) <= node_set
            and set(slot.get("allowed_edge_ids", [])) <= set(edge_ids)
            and set(slot.get("event_ids", [])) <= set(slot.get("allowed_node_ids", []))
            for slot in slots
        ),
        "packet_budget_respected": len(nodes) <= 40 and len(edges) <= 100,
    }

    category_checks = {
        "minimum_three_candidate_events": event_count >= 3,
        "has_multiple_chapters": len(packet["chapters"]) >= 2,
    }
    if spec.category_id == "CHARACTER_RELATION":
        relation_predicates = {
            "is_married_to",
            "is_parent_of",
            "is_child_of",
            "is_rival_of",
            "loves",
            "opposes",
            "helps",
            "harms",
            "protects",
            "manipulates",
        }
        category_checks["minimum_three_relation_types"] = len(
            relation_predicates & set(predicate_counts)
        ) >= 3
    elif spec.category_id == "TEMPORAL_ORDER":
        category_checks["has_temporal_chain_edges"] = sum(
            predicate_counts.get(predicate, 0)
            for predicate in ("occurs_before", "immediately_precedes")
        ) >= 5
    elif spec.category_id == "CAUSE_EFFECT":
        category_checks["has_causal_attributes"] = sum(
            bool(node.get("attributes", {}).get("causes"))
            for node in nodes
            if node["type"] == "NarrativeEvent"
        ) >= 3
        category_checks["has_causal_edges"] = sum(
            predicate_counts.get(predicate, 0)
            for predicate in ("causes", "contributes_to", "enables", "results_in")
        ) >= 3
    elif spec.category_id == "CHARACTER_EVOLUTION":
        category_checks["minimum_three_characters"] = character_count >= 3
        category_checks["has_state_changes"] = predicate_counts.get("changes_state_of", 0) >= 2
    elif spec.category_id == "LITERARY_INTERPRETATION":
        category_checks["minimum_three_literary_concepts"] = concept_count >= 3
        category_checks["has_interpretive_edges"] = sum(
            predicate_counts.get(predicate, 0)
            for predicate in ("expresses_theme", "expresses_motif", "symbolizes", "contrasts_with", "parallels")
        ) >= 3
    elif spec.category_id == "CROSS_CHAPTER_COMPARE":
        category_checks["minimum_two_chapters"] = len(packet["chapters"]) >= 2
        category_checks["enough_nodes_for_branches"] = len(nodes) >= 6

    passed = not any(
        (
            len(node_ids) != len(node_set),
            len(edge_ids) != len(set(edge_ids)),
            bool(invalid_nodes),
            bool(invalid_edges),
            bool(mismatched_edges),
            not all(category_checks.values()),
            not all(selection_checks.values()),
        )
    )
    return {
        "passed": passed,
        "duplicate_node_ids": sorted(node_id for node_id in node_set if node_ids.count(node_id) > 1),
        "duplicate_edge_ids": sorted(edge_id for edge_id in set(edge_ids) if edge_ids.count(edge_id) > 1),
        "invalid_nodes": invalid_nodes,
        "invalid_edges": invalid_edges,
        "mismatched_edges": mismatched_edges,
        "event_count": event_count,
        "character_count": character_count,
        "literary_concept_count": concept_count,
        "predicate_counts": predicate_counts,
        "category_checks": category_checks,
        "selection_checks": selection_checks,
    }


def write_packet(path: Path, packet: dict[str, Any]) -> int:
    content = json.dumps(packet, ensure_ascii=False, separators=(",", ":"))
    path.write_text(content, encoding="utf-8")
    return len(content)


def estimate_tokens(characters: int) -> int:
    return round(characters / EMPIRICAL_CHARS_PER_TOKEN)


def write_readme(
    rows: list[dict[str, Any]],
    full_graph_chars: int,
    output_dir: Path = OUTPUT_DIR,
    graph_path: Path = GRAPH_PATH,
) -> None:
    lines = [
        "# GRAPH_PACKET-uri compacte pentru Qwen",
        "",
        f"Fiecare fișier este derivat automat din `{graph_path}` și păstrează ID-urile canonice ale nodurilor și muchiilor. Fișierele sunt minificate intenționat pentru reducerea numărului de tokenuri.",
        "",
        "Estimările folosesc raportul empiric de aproximativ 3,142 caractere/token observat pentru Qwen 3.5 Flash în Experimentul 2. Tokenizarea exactă depinde de model și provider.",
        "",
        "| # | Categorie | Prompt | GRAPH_PACKET | Noduri | Muchii | Tokenuri packet | Tokenuri prompt + packet | Reducere față de graful complet |",
        "|---:|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        reduction = 1 - row["packet_chars"] / full_graph_chars
        lines.append(
            f"| {row['number']} | `{row['category_id']}` | `../prompturi intrebari/{row['prompt_filename']}` | "
            f"`{row['filename']}` | {row['nodes']} | {row['edges']} | {row['packet_tokens']:,} | "
            f"{row['combined_tokens']:,} | {reduction:.1%} |"
        )
    total_separate = sum(row["combined_tokens"] for row in rows)
    lines.extend(
        [
            "",
            f"Total estimat pentru cele opt rulări separate: **{total_separate:,} tokenuri input**.",
            "",
            "## Algoritmul determinist de selecție",
            "",
            f"Versiune: `{SELECTION_ALGORITHM_VERSION}`.",
            "",
            "1. Sunt eligibile numai evenimentele `explicit_fact` cu `verification.status=verified_primary`.",
            "2. Fiecare categorie are exact trei sloturi semantice fixe.",
            "3. Evenimentele rezervate de loturile anterioare sunt excluse înaintea clasării.",
            "4. Candidații rămași sunt clasați stabil după importanță, metoda verificării, scorul dovezii, ordinea globală și ID.",
            "5. Regulile categoriei aleg evenimente, relații, lanțuri sau concepte; egalitățile sunt rupte exclusiv prin cheia stabilă.",
            "6. Pentru fiecare slot se adaugă numai închiderea de o muchie către personaje, capitole, locuri, stări sau concepte permise.",
            "7. Packetul este reuniunea celor trei sloturi și are buget maxim de 40 de noduri și 100 de muchii.",
            "8. Qwen poate folosi numai ID-urile declarate în slotul curent; validatorul verifică separat respectarea contractului.",
            "",
            "Nu se folosește randomizare, seed, eșantionare LLM sau selecție manuală de ID-uri. Același graf și aceeași versiune a algoritmului produc JSON identic.",
            "",
            "## Utilizare",
            "",
            "În promptul categoriei, înlocuiește exact `{{GRAPH_PACKET}}` cu întregul conținut al fișierului `.packet.json` asociat. Nu reformata JSON-ul înainte de trimitere, deoarece indentarea mărește contextul fără beneficiu semantic.",
            "",
            "## Regenerare",
            "",
            "Rulează din rădăcina proiectului:",
            "",
            "```powershell",
            "python cercetare-qwen/build_graph_packets.py",
            "```",
            "",
            "Generatorul verifică faptul că toate ID-urile provin din graful canonic, toate muchiile au capete incluse și fiecare packet conține suficient material pentru categoria sa.",
        ]
    )
    (output_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Construiește packeturile deterministe pentru întrebări.")
    parser.add_argument("--graph", type=Path, default=GRAPH_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--batch-number", type=int, default=1)
    args = parser.parse_args()
    graph = load_graph(args.graph)
    args.output.mkdir(parents=True, exist_ok=True)
    full_graph_compact = json.dumps(graph, ensure_ascii=False, separators=(",", ":"))
    rows, _ = build_packet_set(
        graph,
        args.output,
        batch_number=args.batch_number,
        graph_path=args.graph,
    )
    write_readme(rows, len(full_graph_compact), args.output, args.graph)
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
