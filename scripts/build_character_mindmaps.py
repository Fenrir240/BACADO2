"""Generează datele celor două mind-mapuri de personaje din knowledge graph.

Transformarea este complet deterministă și nu face apeluri AI. Graful rămâne sursa
unică pentru personajele afișate, descrieri, relații și evenimentele folosite drept
context în tooltip-uri.
"""

from __future__ import annotations

import argparse
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

from exercise_builder_common import (
    DEFAULT_GRAPH_PATH,
    ROOT_DIR,
    clean_text,
    graph_work_metadata,
    read_json,
    slugify,
    write_json,
)


DEFAULT_MAX_TREE_CHARACTERS = 16
DEFAULT_MAX_RELATION_CHARACTERS = 14

IMPORTANCE_SCORE = {"major": 1_000, "supporting": 300, "minor": 100}
IMPORTANCE_LABEL = {
    "major": "principal",
    "supporting": "secundar",
    "minor": "episodic",
}
RELATION_LABELS = {
    "loves": "iubește",
    "is_married_to": "este căsătorit(ă) cu",
    "is_parent_of": "este părintele lui/ei",
    "is_rival_of": "este rival(ă) cu",
    "co_occurs_with": "interacționează în acțiune cu",
}
DIRECT_RELATION_PREDICATES = {
    "loves",
    "is_married_to",
    "is_parent_of",
    "is_child_of",
    "is_rival_of",
}
GROUP_CAPTIONS = {
    "Personaje principale": "Au cea mai mare importanță în desfășurarea operei.",
    "Familie și legături apropiate": "Sunt legate direct de personajele principale prin familie, iubire sau căsătorie.",
    "Rivali și conflicte": "Participă la opoziții sau la momente tensionate ale acțiunii.",
    "Personaje secundare": "Completează lumea operei și susțin firele narative importante.",
}
TREE_GROUP_LABELS = {
    "Personaje principale": "Principale",
    "Familie și legături apropiate": "Familie / apropiați",
    "Rivali și conflicte": "Rivali / conflicte",
    "Personaje secundare": "Secundare",
}
GROUP_PALETTE = {
    "Personaje principale": "central",
    "Familie și legături apropiate": "victim",
    "Rivali și conflicte": "rich",
    "Personaje secundare": "intellectual",
}
PALETTE_LABELS = {
    "central": "personaje principale",
    "victim": "familie / apropiați",
    "rich": "rivali / conflicte",
    "intellectual": "personaje secundare",
}


def _as_list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _nodes_by_id(graph: dict) -> dict[str, dict]:
    return {
        str(node["id"]): node
        for node in _as_list(graph.get("nodes"))
        if isinstance(node, dict) and node.get("id")
    }


def _events(graph: dict) -> list[dict]:
    return [
        node
        for node in _as_list(graph.get("nodes"))
        if isinstance(node, dict) and node.get("type") == "NarrativeEvent"
    ]


def _characters(graph: dict) -> list[dict]:
    return [
        node
        for node in _as_list(graph.get("nodes"))
        if isinstance(node, dict) and node.get("type") == "Character" and node.get("id")
    ]


def _event_participants(event: dict) -> list[str]:
    attributes = event.get("attributes") if isinstance(event.get("attributes"), dict) else {}
    values = attributes.get("participants") or []
    return [str(value) for value in values if value]


def _event_text(event: dict) -> str:
    attributes = event.get("attributes") if isinstance(event.get("attributes"), dict) else {}
    return clean_text(
        attributes.get("simple_narration")
        or attributes.get("action")
        or event.get("description")
        or event.get("label")
    )


def _attribute_text(node: dict, *names: str) -> str:
    attributes = node.get("attributes") if isinstance(node.get("attributes"), dict) else {}
    for name in names:
        value = attributes.get(name)
        if isinstance(value, list):
            text = ", ".join(clean_text(item) for item in value if clean_text(item))
        else:
            text = clean_text(value)
        if text:
            return text
    return ""


def _first_clause(text: str, limit: int = 90) -> str:
    text = clean_text(text)
    for separator in (".", ";"):
        if separator in text:
            text = text.split(separator, 1)[0]
            break
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _normalize_direct_relation(edge: dict) -> tuple[str, str, str] | None:
    predicate = str(edge.get("predicate") or "")
    source = str(edge.get("source") or "")
    target = str(edge.get("target") or "")
    if predicate not in DIRECT_RELATION_PREDICATES or not source or not target or source == target:
        return None
    if predicate == "is_child_of":
        source, target, predicate = target, source, "is_parent_of"
    if predicate in {"is_married_to", "is_rival_of"} and source > target:
        source, target = target, source
    return source, predicate, target


def _direct_relations(graph: dict, character_ids: set[str]) -> list[dict]:
    seen: set[tuple[str, str, str]] = set()
    result: list[dict] = []
    for edge in _as_list(graph.get("edges")):
        if not isinstance(edge, dict):
            continue
        normalized = _normalize_direct_relation(edge)
        if normalized is None:
            continue
        source, predicate, target = normalized
        if source not in character_ids or target not in character_ids:
            continue
        key = (source, predicate, target)
        if key in seen:
            continue
        seen.add(key)
        result.append({"source": source, "predicate": predicate, "target": target})
    return result


def _co_occurrence_data(events: Iterable[dict], character_ids: set[str]) -> tuple[Counter, dict]:
    counts: Counter[tuple[str, str]] = Counter()
    evidence: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for event in events:
        participants = sorted(set(_event_participants(event)) & character_ids)
        for index, source in enumerate(participants):
            for target in participants[index + 1 :]:
                pair = (source, target)
                counts[pair] += 1
                evidence[pair].append(event)
    return counts, evidence


def _character_ranking(graph: dict) -> tuple[list[dict], dict[str, int], list[dict], dict]:
    characters = _characters(graph)
    character_ids = {str(node["id"]) for node in characters}
    events = _events(graph)
    participation = Counter(
        participant
        for event in events
        for participant in set(_event_participants(event))
        if participant in character_ids
    )
    direct = _direct_relations(graph, character_ids)
    degree = Counter(
        endpoint
        for relation in direct
        for endpoint in (relation["source"], relation["target"])
    )

    def score(node: dict) -> tuple[int, int, int, str]:
        node_id = str(node["id"])
        importance = str(node.get("importance") or "minor")
        return (
            IMPORTANCE_SCORE.get(importance, 0) + participation[node_id] * 10 + degree[node_id] * 7,
            participation[node_id],
            degree[node_id],
            clean_text(node.get("label")).casefold(),
        )

    ranked = sorted(characters, key=score, reverse=True)
    return ranked, dict(participation), direct, _co_occurrence_data(events, character_ids)


def _short_label(name: str) -> str:
    name = clean_text(name)
    if len(name) <= 13:
        return name
    parts = name.split()
    if len(parts) >= 2:
        compact = f"{parts[0][0]}. {parts[-1]}"
        if len(compact) <= 15:
            return compact
        return parts[0]
    return name[:12] + "…"


def _character_card(node: dict, participation_count: int) -> dict[str, str]:
    node_id = str(node["id"])
    name = clean_text(node.get("label")) or node_id
    description = clean_text(node.get("description")) or "Personaj prezent în knowledge graph."
    importance = str(node.get("importance") or "supporting")
    role = _attribute_text(node, "role", "narrative_role", "social_role") or description
    traits = _attribute_text(node, "traits", "qualities", "character_traits") or description
    physical = _attribute_text(node, "physical", "physical_portrait", "appearance")
    if not physical:
        physical = "Knowledge graph-ul nu oferă un portret fizic explicit pentru acest personaj."
    human_type = _attribute_text(node, "human_type", "character_type")
    if not human_type:
        importance_label = IMPORTANCE_LABEL.get(importance, "secundar")
        human_type = (
            f"Personaj {importance_label}, documentat în {participation_count} "
            f"eveniment{'e' if participation_count != 1 else ''} narativ{'e' if participation_count != 1 else ''}."
        )
    return {
        "id": node_id,
        "name": name,
        "tree_label": _short_label(name),
        "short_role": _first_clause(role),
        "physical": physical,
        "traits": traits,
        "village_role": role,
        "human_type": human_type,
    }


def _group_characters(
    selected: list[dict],
    main_ids: set[str],
    direct: list[dict],
    co_counts: Counter,
) -> list[dict]:
    close_ids: set[str] = set()
    conflict_ids: set[str] = set()
    for relation in direct:
        source, target, predicate = relation["source"], relation["target"], relation["predicate"]
        if source not in main_ids and target not in main_ids:
            continue
        other = target if source in main_ids else source
        if predicate in {"is_parent_of", "is_married_to", "loves"}:
            close_ids.add(other)
        if predicate == "is_rival_of":
            conflict_ids.add(other)
    for (source, target), count in co_counts.items():
        if count < 2:
            continue
        if source in main_ids and target not in main_ids:
            conflict_ids.add(target)
        elif target in main_ids and source not in main_ids:
            conflict_ids.add(source)
    close_ids -= main_ids
    conflict_ids -= main_ids | close_ids

    buckets: list[tuple[str, list[dict]]] = [
        ("Personaje principale", [node for node in selected if str(node["id"]) in main_ids]),
        ("Familie și legături apropiate", [node for node in selected if str(node["id"]) in close_ids]),
        ("Rivali și conflicte", [node for node in selected if str(node["id"]) in conflict_ids]),
    ]
    already = main_ids | close_ids | conflict_ids
    buckets.append(("Personaje secundare", [node for node in selected if str(node["id"]) not in already]))

    groups: list[dict] = []
    for title, nodes in buckets:
        for chunk_index in range(0, len(nodes), 4):
            chunk = nodes[chunk_index : chunk_index + 4]
            if not chunk:
                continue
            suffix = "" if len(nodes) <= 4 else f" {chunk_index // 4 + 1}"
            groups.append(
                {
                    "title": title + suffix,
                    "caption": GROUP_CAPTIONS[title],
                    "character_ids": [str(node["id"]) for node in chunk],
                }
            )
    return groups


def _tree_layout(work_title: str, groups: list[dict]) -> dict:
    width, height = 980, 540
    group_count = max(1, len(groups))
    step = (width - 100) / group_count
    group_y = 145
    character_y = 270
    positions: dict[str, dict[str, float]] = {}
    layout_groups: list[dict] = []
    for group_index, group in enumerate(groups):
        center_x = 50 + step * (group_index + 0.5)
        ids = group["character_ids"]
        local_positions: list[float]
        if len(ids) == 1:
            local_positions = [center_x]
        elif len(ids) == 2:
            local_positions = [center_x - min(40, step * 0.23), center_x + min(40, step * 0.23)]
        else:
            offset = min(48, step * 0.25)
            local_positions = [center_x - offset, center_x + offset, center_x - offset, center_x + offset]
        for index, character_id in enumerate(ids):
            positions[character_id] = {
                "x": round(local_positions[index], 2),
                "y": character_y + (105 if index >= 2 else 0),
            }
        layout_groups.append(
            {
                "label": next(
                    (
                        compact + group["title"][len(title) :]
                        for title, compact in TREE_GROUP_LABELS.items()
                        if group["title"].startswith(title)
                    ),
                    group["title"],
                ),
                "x": round(center_x, 2),
                "y": group_y,
                "character_ids": ids,
            }
        )
    return {
        "width": width,
        "height": height,
        "root": {"label": work_title, "x": width / 2, "y": 46},
        "groups": layout_groups,
        "characters": positions,
    }


def _relation_text(
    relation: dict,
    nodes_by_id: dict[str, dict],
    evidence: dict[tuple[str, str], list[dict]],
) -> tuple[str, str]:
    source_id, target_id = relation["source"], relation["target"]
    source = clean_text(nodes_by_id[source_id].get("label"))
    target = clean_text(nodes_by_id[target_id].get("label"))
    predicate = relation["predicate"]
    title = f"{source} – {target}"
    base = f"{source} {RELATION_LABELS.get(predicate, predicate.replace('_', ' '))} {target}."
    pair = tuple(sorted((source_id, target_id)))
    event_texts = [_event_text(event) for event in evidence.get(pair, [])]
    event_texts = list(dict.fromkeys(text for text in event_texts if text))[:2]
    if event_texts:
        base += " Momente comune din graf: " + " ".join(event_texts)
    return title, base


def _relation_graph(
    selected: list[dict],
    main_id: str,
    direct: list[dict],
    co_counts: Counter,
    evidence: dict,
    nodes_by_id: dict[str, dict],
    palette_by_id: dict[str, str],
) -> dict:
    selected_ids = {str(node["id"]) for node in selected}
    relations = [
        relation
        for relation in direct
        if relation["source"] in selected_ids and relation["target"] in selected_ids
    ]
    existing_pairs = {tuple(sorted((item["source"], item["target"]))) for item in relations}
    for pair, count in co_counts.most_common():
        if count < 2 or pair[0] not in selected_ids or pair[1] not in selected_ids or pair in existing_pairs:
            continue
        relations.append({"source": pair[0], "predicate": "co_occurs_with", "target": pair[1]})
        existing_pairs.add(pair)
        if len(relations) >= 22:
            break

    connected_ids = {main_id}
    for relation in relations:
        connected_ids.update((relation["source"], relation["target"]))
    relation_nodes = [node for node in selected if str(node["id"]) in connected_ids]
    others = [node for node in relation_nodes if str(node["id"]) != main_id]
    nodes_payload: dict[str, dict] = {
        main_id: {
            "label": _short_label(clean_text(nodes_by_id[main_id].get("label"))),
            "x": 490,
            "y": 280,
            "group": "central",
        }
    }
    for index, node in enumerate(others):
        angle = -math.pi / 2 + (2 * math.pi * index / max(1, len(others)))
        node_id = str(node["id"])
        nodes_payload[node_id] = {
            "label": _short_label(clean_text(node.get("label"))),
            "x": round(490 + 390 * math.cos(angle), 2),
            "y": round(280 + 220 * math.sin(angle), 2),
            "group": palette_by_id.get(node_id, "intellectual"),
        }
    edges_payload = []
    for relation in relations:
        if relation["source"] not in nodes_payload or relation["target"] not in nodes_payload:
            continue
        title, text = _relation_text(relation, nodes_by_id, evidence)
        edges_payload.append(
            {
                "source": relation["source"],
                "target": relation["target"],
                "predicate": relation["predicate"],
                "title": title,
                "text": text,
            }
        )
    used_groups = list(
        dict.fromkeys(node["group"] for node in nodes_payload.values())
    )
    return {
        "central_node_id": main_id,
        "legend": [
            {"group": group, "label": PALETTE_LABELS.get(group, group)}
            for group in used_groups
        ],
        "nodes": nodes_payload,
        "edges": edges_payload,
    }


def build_character_mindmaps(
    graph: dict,
    *,
    work_id: str | None = None,
    max_tree_characters: int = DEFAULT_MAX_TREE_CHARACTERS,
    max_relation_characters: int = DEFAULT_MAX_RELATION_CHARACTERS,
) -> dict:
    metadata = graph_work_metadata(graph, work_id)
    ranked, participation, direct, co_data = _character_ranking(graph)
    if not ranked:
        raise ValueError("Knowledge graph-ul nu conține noduri Character.")
    co_counts, evidence = co_data
    selected = ranked[: max(1, max_tree_characters)]
    main_nodes = [node for node in selected if str(node.get("importance")) == "major"]
    if not main_nodes:
        main_nodes = selected[:1]
    main_ids = {str(node["id"]) for node in main_nodes}
    main_id = str(main_nodes[0]["id"])
    groups = _group_characters(selected, main_ids, direct, co_counts)
    palette_by_id = {
        character_id: next(
            (
                palette
                for title, palette in GROUP_PALETTE.items()
                if group["title"].startswith(title)
            ),
            "intellectual",
        )
        for group in groups
        for character_id in group["character_ids"]
    }
    cards = {
        str(node["id"]): _character_card(node, participation.get(str(node["id"]), 0))
        for node in selected
    }
    relation_selected = ranked[: max(1, max_relation_characters)]
    return {
        "schema_version": 1,
        "work": metadata,
        "source": {
            "kind": "knowledge_graph",
            "generator": "scripts/build_character_mindmaps.py",
            "deterministic": True,
            "uses_ai": False,
        },
        "characters": cards,
        "groups": [
            {
                "title": group["title"],
                "caption": group["caption"],
                "characters": [cards[character_id] for character_id in group["character_ids"]],
            }
            for group in groups
        ],
        "tree_layout": _tree_layout(metadata["title"], groups),
        "relation_graph": _relation_graph(
            relation_selected,
            main_id,
            direct,
            co_counts,
            evidence,
            _nodes_by_id(graph),
            palette_by_id,
        ),
    }


def output_path_for(work_id: str, data_dir: Path | None = None) -> Path:
    base = data_dir or ROOT_DIR / "data"
    return base / "generated_works" / work_id / "intelegere-opera" / "personaje-mindmaps.json"


def build_and_write(
    graph_path: Path,
    *,
    work_id: str | None = None,
    output_path: Path | None = None,
) -> tuple[dict, Path]:
    graph = read_json(graph_path)
    payload = build_character_mindmaps(graph, work_id=work_id)
    resolved_path = output_path or output_path_for(payload["work"]["work_id"])
    write_json(resolved_path, payload)
    return payload, resolved_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH)
    parser.add_argument("--work-id", default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    payload, output_path = build_and_write(
        args.graph.resolve(),
        work_id=args.work_id,
        output_path=args.output.resolve() if args.output else None,
    )
    print(
        f"Mind-mapuri personaje generate pentru {payload['work']['title']}: "
        f"{len(payload['characters'])} personaje, "
        f"{len(payload['relation_graph']['edges'])} relații."
    )
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
