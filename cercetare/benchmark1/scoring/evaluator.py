"""Evaluator deterministic pentru benchmarkul knowledge graph-ului Ion.

Fisierul nu apeleaza niciun model AI. El valideaza outputurile JSON produse de
modele si calculeaza doua scoruri independente:

* Question Generation Score (QGS), 0-100;
* Summary Reconstruction Score (SRS), 0-100.

Functiile publice sunt:

    score_question_generation(question_output, graph, manifest=None)
    score_chapter_1_summary(summary_output, graph)
    score_agent_submission(question_output, summary_output, graph, manifest=None)

Argumentele pot fi dictionare Python, texte JSON sau cai catre fisiere JSON.
Evaluatorul foloseste exclusiv biblioteca standard Python.

Limitare metodologica:
    O functie deterministica poate verifica perfect identificatori, muchii,
    trasee, ordine si afirmatii structurate. Nu poate demonstra ca textul liber
    in limba romana exprima exact aceleasi afirmatii. De aceea, textul natural
    primeste numai puncte pentru reguli formale, iar scorul factual se bazeaza
    pe query_plan, evidence si claims.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import unicodedata
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


REQUIRED_BLUEPRINTS = (
    "FACT_1HOP",
    "RELATION_1HOP",
    "TEMPORAL_ORDER",
    "DIRECT_CAUSE",
    "DIRECT_EFFECT",
    "MULTIHOP_CAUSAL",
    "STATE_TRANSITION",
    "CROSS_CHAPTER_COMPARE",
)

CAUSAL_PREDICATES = {
    "has_motivation",
    "motivates",
    "causes",
    "contributes_to",
    "enables",
    "results_in",
    "has_consequence",
}

TEMPORAL_PREDICATES = {
    "occurs_before",
    "occurs_after",
    "immediately_precedes",
    "immediately_follows",
}

STATE_PREDICATES = {
    "has_state_before",
    "has_state_after",
    "changes_state_of",
    "gains",
    "loses",
    "discovers",
    "believes",
    "desires",
    "fears",
    "decides",
    "abandons_goal",
    "adopts_goal",
}

QUESTION_MAX_POINTS = {
    "schema": 5.0,
    "blueprint": 15.0,
    "references": 15.0,
    "derivability": 25.0,
    "uniqueness": 10.0,
    "minimality": 10.0,
    "difficulty": 10.0,
    "formal_rules": 5.0,
    "non_duplication": 5.0,
}

SUMMARY_MAX_POINTS = {
    "event_coverage": 30.0,
    "claim_support": 25.0,
    "event_order": 20.0,
    "causal_retention": 10.0,
    "evidence_discipline": 5.0,
    "concision": 5.0,
    "register": 5.0,
}


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _round(value: float) -> float:
    return round(float(value), 3)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _load_json(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, Path):
        return json.loads(value.read_text(encoding="utf-8"))
    if isinstance(value, str):
        stripped = value.strip()
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            parsed = json.loads(Path(value).read_text(encoding="utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("Documentul JSON trebuie sa aiba un obiect la radacina.")
        return parsed
    raise TypeError("Inputul trebuie sa fie dictionar, text JSON sau cale catre JSON.")


def _safe_load_json(value: Any) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return _load_json(value), None
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return None, str(exc)


def _normalize_text(text: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.lower()
    return " ".join(re.findall(r"[a-z0-9]+", normalized))


def _words(text: Any) -> list[str]:
    return re.findall(r"[0-9A-Za-zĂÂÎȘȚăâîșț]+(?:[-'][0-9A-Za-zĂÂÎȘȚăâîșț]+)?", str(text or ""))


def _jaccard(left: Iterable[Any], right: Iterable[Any]) -> float:
    a, b = set(left), set(right)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _f1(predicted: Iterable[Any], expected: Iterable[Any]) -> float:
    predicted_set, expected_set = set(predicted), set(expected)
    if not predicted_set and not expected_set:
        return 1.0
    if not predicted_set or not expected_set:
        return 0.0
    intersection = len(predicted_set & expected_set)
    precision = intersection / len(predicted_set)
    recall = intersection / len(expected_set)
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


@dataclass(frozen=True)
class GraphIndex:
    graph: dict[str, Any]

    def __post_init__(self) -> None:
        nodes = {str(node.get("id")): node for node in self.graph.get("nodes", []) if node.get("id")}
        edges = {str(edge.get("id")): edge for edge in self.graph.get("edges", []) if edge.get("id")}
        outgoing: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
        edge_tuples: dict[tuple[str, str, str], list[str]] = defaultdict(list)
        adjacency: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for edge_id, edge in edges.items():
            source = str(edge.get("source", ""))
            predicate = str(edge.get("predicate", ""))
            target = str(edge.get("target", ""))
            outgoing[source][predicate].add(target)
            edge_tuples[(source, predicate, target)].append(edge_id)
            adjacency[source].append((target, predicate))
        chapters = {str(chapter.get("id")): chapter for chapter in self.graph.get("chapters", []) if chapter.get("id")}
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "edges", edges)
        object.__setattr__(self, "outgoing", outgoing)
        object.__setattr__(self, "edge_tuples", edge_tuples)
        object.__setattr__(self, "adjacency", adjacency)
        object.__setattr__(self, "chapters", chapters)

    @classmethod
    def from_value(cls, graph: Any) -> "GraphIndex":
        return cls(_load_json(graph))

    def execute_query(self, start_node_ids: Sequence[str], predicates: Sequence[str]) -> set[str]:
        current = {node_id for node_id in start_node_ids if node_id in self.nodes}
        for predicate in predicates:
            next_nodes: set[str] = set()
            for source in current:
                next_nodes.update(self.outgoing.get(source, {}).get(predicate, set()))
            current = next_nodes
            if not current:
                break
        return current

    def path_is_valid(self, node_ids: Sequence[str], edge_ids: Sequence[str]) -> bool:
        if len(node_ids) < 2 or len(edge_ids) != len(node_ids) - 1:
            return False
        for index, edge_id in enumerate(edge_ids):
            edge = self.edges.get(edge_id)
            if not edge:
                return False
            if edge.get("source") != node_ids[index] or edge.get("target") != node_ids[index + 1]:
                return False
        return True

    def shortest_path_length(
        self,
        starts: Sequence[str],
        targets: Sequence[str],
        allowed_predicates: set[str] | None = None,
    ) -> int | None:
        target_set = set(targets)
        queue: deque[tuple[str, int]] = deque((node_id, 0) for node_id in starts if node_id in self.nodes)
        visited = {node_id for node_id, _ in queue}
        while queue:
            node_id, distance = queue.popleft()
            if node_id in target_set:
                return distance
            for neighbor, predicate in self.adjacency.get(node_id, []):
                if allowed_predicates and predicate not in allowed_predicates:
                    continue
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, distance + 1))
        return None

    def chapters_for_nodes(self, node_ids: Iterable[str]) -> set[str]:
        result: set[str] = set()
        for node_id in node_ids:
            node = self.nodes.get(node_id, {})
            result.update(str(ch) for ch in _as_list(node.get("chapter_ids")) if ch)
            if node.get("type") == "Chapter":
                result.add(node_id)
            chapter_id = node.get("attributes", {}).get("chapter_id")
            if chapter_id:
                result.add(str(chapter_id))
        return result


def _manifest_slot_index(manifest: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not manifest:
        return {}
    return {
        str(slot.get("slot_id")): dict(slot)
        for slot in manifest.get("slots", [])
        if isinstance(slot, Mapping) and slot.get("slot_id")
    }


def _question_ids(question: Mapping[str, Any]) -> tuple[set[str], set[str]]:
    answer = question.get("answer", {}) if isinstance(question.get("answer"), Mapping) else {}
    query = question.get("query_plan", {}) if isinstance(question.get("query_plan"), Mapping) else {}
    evidence = question.get("evidence", {}) if isinstance(question.get("evidence"), Mapping) else {}
    scope = question.get("scope", {}) if isinstance(question.get("scope"), Mapping) else {}
    node_ids: set[str] = set()
    for field in ("node_ids", "ordered_node_ids"):
        node_ids.update(str(v) for v in _as_list(answer.get(field)) if v)
    for field in ("start_node_ids", "intermediate_node_ids", "expected_result_ids"):
        node_ids.update(str(v) for v in _as_list(query.get(field)) if v)
    for field in ("node_ids", "path_node_ids"):
        node_ids.update(str(v) for v in _as_list(evidence.get(field)) if v)
    node_ids.update(str(v) for v in _as_list(scope.get("chapter_ids")) if v)
    edge_ids = {str(v) for v in _as_list(evidence.get("edge_ids")) if v}
    return node_ids, edge_ids


def _question_schema_fraction(question: Mapping[str, Any]) -> tuple[float, list[str]]:
    errors: list[str] = []
    required = (
        "question_id",
        "slot_id",
        "blueprint_id",
        "status",
        "question_text",
        "answer",
        "query_plan",
        "evidence",
        "scope",
        "declared_difficulty",
    )
    present = sum(1 for key in required if key in question)
    for key in required:
        if key not in question:
            errors.append(f"Camp obligatoriu lipsa: {key}")
    mapping_fields = ("answer", "query_plan", "evidence", "scope", "declared_difficulty")
    type_checks = sum(1 for key in mapping_fields if isinstance(question.get(key), Mapping))
    fraction = (present + type_checks) / (len(required) + len(mapping_fields))
    return fraction, errors


def _blueprint_fraction(
    question: Mapping[str, Any],
    graph: GraphIndex,
    requested_slot: Mapping[str, Any] | None,
) -> tuple[float, list[str]]:
    blueprint = str(question.get("blueprint_id", ""))
    evidence = question.get("evidence", {}) if isinstance(question.get("evidence"), Mapping) else {}
    node_ids = [str(v) for v in _as_list(evidence.get("path_node_ids")) if v]
    edge_ids = [str(v) for v in _as_list(evidence.get("edge_ids")) if v]
    edges = [graph.edges[eid] for eid in edge_ids if eid in graph.edges]
    predicates = [str(edge.get("predicate", "")) for edge in edges]
    node_types = [graph.nodes.get(node_id, {}).get("type") for node_id in node_ids]
    chapters = graph.chapters_for_nodes(node_ids)
    requirements: list[bool] = []
    diagnostics: list[str] = []

    if requested_slot:
        requested_blueprint = str(requested_slot.get("blueprint_id", ""))
        requirements.append(blueprint == requested_blueprint)
        if blueprint != requested_blueprint:
            diagnostics.append(f"Blueprint cerut {requested_blueprint}, primit {blueprint}.")

    if blueprint in {"FACT_1HOP", "RELATION_1HOP"}:
        requirements.extend([len(edge_ids) == 1, len(node_ids) == 2, graph.path_is_valid(node_ids, edge_ids)])
    elif blueprint == "TEMPORAL_ORDER":
        event_count = sum(1 for node_type in node_types if node_type == "NarrativeEvent")
        has_explicit_temporal = any(predicate in TEMPORAL_PREDICATES for predicate in predicates)
        ordered = []
        for node_id in node_ids:
            order = graph.nodes.get(node_id, {}).get("attributes", {}).get("global_order")
            if order is not None:
                ordered.append(order)
        has_attribute_order = len(ordered) >= 3 and len(set(ordered)) == len(ordered)
        requirements.extend([event_count >= 3, has_explicit_temporal or has_attribute_order])
    elif blueprint == "DIRECT_CAUSE":
        requirements.extend([len(edge_ids) in {1, 2}, any(predicate in {"has_motivation", "motivates", "causes"} for predicate in predicates)])
    elif blueprint == "DIRECT_EFFECT":
        requirements.extend([len(edge_ids) in {1, 2}, any(predicate in {"has_consequence", "results_in"} for predicate in predicates)])
    elif blueprint == "MULTIHOP_CAUSAL":
        narrative_types = {"NarrativeEvent", "NarrativeState", "Motivation", "Consequence", "CharacterState"}
        requirements.extend([
            len(edge_ids) >= 4,
            sum(1 for node_type in node_types if node_type in narrative_types) >= 3,
            sum(1 for predicate in predicates if predicate in CAUSAL_PREDICATES) >= 2,
            graph.path_is_valid(node_ids, edge_ids),
        ])
    elif blueprint == "STATE_TRANSITION":
        requirements.extend([
            any(node_type in {"NarrativeState", "CharacterState"} for node_type in node_types),
            any(predicate in STATE_PREDICATES or predicate in {"enables", "results_in"} for predicate in predicates),
            len(edge_ids) >= 2,
        ])
    elif blueprint == "CROSS_CHAPTER_COMPARE":
        requirements.extend([len(chapters) >= 2, len(edge_ids) >= 2])
    else:
        diagnostics.append(f"Blueprint necunoscut: {blueprint or '(gol)'}.")
        return 0.0, diagnostics

    if requested_slot:
        requested_chapters = set(str(v) for v in requested_slot.get("scope", {}).get("chapter_ids", []))
        if requested_chapters:
            scope_ok = bool(chapters) and chapters.issubset(requested_chapters)
            requirements.append(scope_ok)
            if not scope_ok:
                diagnostics.append("Intrebarea foloseste capitole din afara scope-ului manifestului.")

    if not requirements:
        return 0.0, diagnostics
    return sum(bool(value) for value in requirements) / len(requirements), diagnostics


def _computed_difficulty(question: Mapping[str, Any], graph: GraphIndex) -> tuple[int, int, int]:
    evidence = question.get("evidence", {}) if isinstance(question.get("evidence"), Mapping) else {}
    path_nodes = [str(v) for v in _as_list(evidence.get("path_node_ids")) if v]
    edge_ids = [str(v) for v in _as_list(evidence.get("edge_ids")) if v]
    scope = question.get("scope", {}) if isinstance(question.get("scope"), Mapping) else {}
    chapters = graph.chapters_for_nodes(path_nodes)
    chapters.update(str(v) for v in _as_list(scope.get("chapter_ids")) if v)
    hops = len(edge_ids)
    blueprint = str(question.get("blueprint_id", ""))
    if hops >= 4 or len(chapters) >= 2 or blueprint == "CROSS_CHAPTER_COMPARE":
        level = 3
    elif hops >= 2 or blueprint in {"TEMPORAL_ORDER", "STATE_TRANSITION", "DIRECT_CAUSE", "DIRECT_EFFECT"}:
        level = 2
    else:
        level = 1
    return level, hops, len(chapters)


def _formal_rule_fraction(question: Mapping[str, Any]) -> tuple[float, list[str]]:
    text = str(question.get("question_text", "")).strip()
    answer = question.get("answer", {}) if isinstance(question.get("answer"), Mapping) else {}
    answer_text = _normalize_text(answer.get("text", ""))
    normalized_question = _normalize_text(text)
    word_count = len(_words(text))
    rules = {
        "ends_with_question_mark": text.endswith("?"),
        "word_count_5_35": 5 <= word_count <= 35,
        "no_technical_ids": re.search(r"\b(?:EV|CHAR|EDGE|CH|MOT|CON|LOC|STATE)_[A-Z0-9_]+\b", text, re.IGNORECASE) is None,
        "no_opinion_prompt": not any(phrase in normalized_question for phrase in ("ce crezi", "cum consideri", "dupa parerea ta")),
        "answer_not_copied": not answer_text or answer_text not in normalized_question,
    }
    diagnostics = [name for name, passed in rules.items() if not passed]
    return sum(rules.values()) / len(rules), diagnostics


def _score_single_question(
    question: Mapping[str, Any],
    graph: GraphIndex,
    requested_slot: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if question.get("status") != "generated":
        return {
            "question_id": question.get("question_id"),
            "slot_id": question.get("slot_id"),
            "blueprint_id": question.get("blueprint_id"),
            "question_text": question.get("question_text", ""),
            "score": 0.0,
            "breakdown": {key: 0.0 for key in QUESTION_MAX_POINTS},
            "diagnostics": [f"Statusul intrebarii este {question.get('status')!r}, nu 'generated'."],
            "duplicate_similarity": 0.0,
        }

    diagnostics: list[str] = []
    breakdown: dict[str, float] = {}

    schema_fraction, schema_errors = _question_schema_fraction(question)
    diagnostics.extend(schema_errors)
    breakdown["schema"] = QUESTION_MAX_POINTS["schema"] * schema_fraction

    blueprint_fraction, blueprint_errors = _blueprint_fraction(question, graph, requested_slot)
    diagnostics.extend(blueprint_errors)
    breakdown["blueprint"] = QUESTION_MAX_POINTS["blueprint"] * blueprint_fraction

    node_ids, edge_ids = _question_ids(question)
    node_validity = sum(node_id in graph.nodes for node_id in node_ids) / len(node_ids) if node_ids else 0.0
    edge_validity = sum(edge_id in graph.edges for edge_id in edge_ids) / len(edge_ids) if edge_ids else 0.0
    breakdown["references"] = 7.5 * node_validity + 7.5 * edge_validity
    missing_nodes = sorted(node_id for node_id in node_ids if node_id not in graph.nodes)
    missing_edges = sorted(edge_id for edge_id in edge_ids if edge_id not in graph.edges)
    if missing_nodes:
        diagnostics.append(f"Noduri inexistente: {', '.join(missing_nodes)}")
    if missing_edges:
        diagnostics.append(f"Muchii inexistente: {', '.join(missing_edges)}")

    answer = question.get("answer", {}) if isinstance(question.get("answer"), Mapping) else {}
    query = question.get("query_plan", {}) if isinstance(question.get("query_plan"), Mapping) else {}
    starts = [str(v) for v in _as_list(query.get("start_node_ids")) if v]
    predicates = [str(v) for v in _as_list(query.get("predicates")) if v]
    expected = [str(v) for v in _as_list(query.get("expected_result_ids")) if v]
    declared = [str(v) for v in _as_list(answer.get("ordered_node_ids")) if v]
    if not declared:
        declared = [str(v) for v in _as_list(answer.get("node_ids")) if v]
    derived = graph.execute_query(starts, predicates)
    derivability_f1 = _f1(derived, declared)
    expected_consistency = _f1(expected, declared)
    derivability_fraction = derivability_f1 * expected_consistency
    breakdown["derivability"] = QUESTION_MAX_POINTS["derivability"] * derivability_fraction
    if derivability_fraction < 1:
        diagnostics.append(
            f"Rezultate query_plan={sorted(derived)}, raspuns declarat={sorted(set(declared))}, "
            f"expected_result_ids={sorted(set(expected))}."
        )

    answer_type = str(answer.get("answer_type", "entity"))
    if answer_type in {"entity", "literal", "short_text"}:
        uniqueness_fraction = 1.0 if len(derived) == 1 and set(declared) == derived else 0.0
    else:
        uniqueness_fraction = 1.0 if derived and set(declared) == derived else derivability_f1
    breakdown["uniqueness"] = QUESTION_MAX_POINTS["uniqueness"] * uniqueness_fraction

    declared_hops = question.get("declared_difficulty", {}).get("required_hops") if isinstance(question.get("declared_difficulty"), Mapping) else None
    try:
        declared_hops_int = int(declared_hops)
    except (TypeError, ValueError):
        declared_hops_int = len(_as_list(question.get("evidence", {}).get("edge_ids"))) if isinstance(question.get("evidence"), Mapping) else 0
    shortest = graph.shortest_path_length(starts, declared, set(predicates) if predicates else None)
    if shortest is None or declared_hops_int <= 0:
        minimality_fraction = 0.0
    elif shortest == 0 and declared_hops_int == 0:
        minimality_fraction = 1.0
    else:
        minimality_fraction = _clamp(shortest / declared_hops_int)
    breakdown["minimality"] = QUESTION_MAX_POINTS["minimality"] * minimality_fraction
    if minimality_fraction < 1:
        diagnostics.append(f"Traseu declarat={declared_hops_int} hop-uri; traseu minim={shortest}.")

    computed_level, computed_hops, computed_chapters = _computed_difficulty(question, graph)
    declared_difficulty = question.get("declared_difficulty", {}) if isinstance(question.get("declared_difficulty"), Mapping) else {}
    requested_level = None
    if requested_slot:
        requested_level = requested_slot.get("difficulty")
        if isinstance(requested_level, Mapping):
            requested_level = requested_level.get("level")
    try:
        target_level = int(requested_level if requested_level is not None else declared_difficulty.get("level"))
    except (TypeError, ValueError):
        target_level = 0
    difference = abs(computed_level - target_level) if target_level else 99
    difficulty_fraction = 1.0 if difference == 0 else 0.5 if difference == 1 else 0.0
    if declared_difficulty.get("required_hops") not in (None, computed_hops):
        difficulty_fraction *= 0.8
    breakdown["difficulty"] = QUESTION_MAX_POINTS["difficulty"] * difficulty_fraction
    if difficulty_fraction < 1:
        diagnostics.append(
            f"Dificultate recalculata: nivel={computed_level}, hop-uri={computed_hops}, "
            f"capitole={computed_chapters}; nivel tinta={target_level or 'nedefinit'}."
        )

    formal_fraction, formal_errors = _formal_rule_fraction(question)
    diagnostics.extend(f"Regula formala incalcata: {error}" for error in formal_errors)
    breakdown["formal_rules"] = QUESTION_MAX_POINTS["formal_rules"] * formal_fraction
    breakdown["non_duplication"] = QUESTION_MAX_POINTS["non_duplication"]

    return {
        "question_id": question.get("question_id"),
        "slot_id": question.get("slot_id"),
        "blueprint_id": question.get("blueprint_id"),
        "question_text": question.get("question_text", ""),
        "score": _round(sum(breakdown.values())),
        "breakdown": {key: _round(value) for key, value in breakdown.items()},
        "diagnostics": diagnostics,
        "computed": {
            "query_results": sorted(derived),
            "difficulty_level": computed_level,
            "required_hops": computed_hops,
            "chapters_involved": computed_chapters,
            "shortest_path_hops": shortest,
        },
        "duplicate_similarity": 0.0,
    }


def _question_similarity(left: Mapping[str, Any], right: Mapping[str, Any]) -> float:
    left_nodes, left_edges = _question_ids(left)
    right_nodes, right_edges = _question_ids(right)
    left_words = _normalize_text(left.get("question_text", "")).split()
    right_words = _normalize_text(right.get("question_text", "")).split()
    return 0.4 * _jaccard(left_words, right_words) + 0.3 * _jaccard(left_nodes, right_nodes) + 0.3 * _jaccard(left_edges, right_edges)


def _set_coverage_score(questions: Sequence[Mapping[str, Any]], graph: GraphIndex) -> tuple[float, dict[str, float]]:
    generated = [question for question in questions if question.get("status") == "generated"]
    blueprints = {str(question.get("blueprint_id")) for question in generated}
    blueprint_score = 40.0 * len(blueprints & set(REQUIRED_BLUEPRINTS)) / len(REQUIRED_BLUEPRINTS)

    all_nodes: list[set[str]] = []
    all_edges: list[set[str]] = []
    all_chapters: set[str] = set()
    all_predicates: set[str] = set()
    signatures: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()
    for question in generated:
        node_ids, edge_ids = _question_ids(question)
        all_nodes.append(node_ids)
        all_edges.append(edge_ids)
        all_chapters.update(graph.chapters_for_nodes(node_ids))
        all_predicates.update(str(graph.edges[eid].get("predicate")) for eid in edge_ids if eid in graph.edges)
        answer = question.get("answer", {}) if isinstance(question.get("answer"), Mapping) else {}
        answer_ids = tuple(sorted(str(v) for v in _as_list(answer.get("node_ids")) if v))
        path_ids = tuple(str(v) for v in _as_list(question.get("evidence", {}).get("path_node_ids")) if v) if isinstance(question.get("evidence"), Mapping) else ()
        signatures.add((answer_ids, path_ids))

    chapter_score = 20.0 * _clamp(len(all_chapters) / 6.0)
    pair_overlaps: list[float] = []
    for index in range(len(all_nodes)):
        for other in range(index + 1, len(all_nodes)):
            pair_overlaps.append(_jaccard(all_nodes[index], all_nodes[other]))
    entity_diversity = 1.0 - (sum(pair_overlaps) / len(pair_overlaps) if pair_overlaps else 0.0)
    entity_score = 15.0 * _clamp(entity_diversity)
    relation_score = 15.0 * _clamp(len(all_predicates) / 8.0)
    uniqueness_score = 10.0 * (len(signatures) / len(generated) if generated else 0.0)
    breakdown = {
        "blueprint_coverage": _round(blueprint_score),
        "chapter_diversity": _round(chapter_score),
        "entity_diversity": _round(entity_score),
        "relation_diversity": _round(relation_score),
        "unique_answers_and_paths": _round(uniqueness_score),
    }
    return _round(sum(breakdown.values())), breakdown


def score_question_generation(
    question_output: Any,
    graph: Any,
    manifest: Any | None = None,
) -> dict[str, Any]:
    """Calculeaza Question Generation Score pentru un output de model."""

    output, error = _safe_load_json(question_output)
    if error or output is None:
        return {
            "task": "question_generation",
            "score": 0.0,
            "question_average": 0.0,
            "set_coverage_score": 0.0,
            "questions": [],
            "errors": [f"Output JSON invalid: {error}"],
        }
    try:
        graph_index = GraphIndex.from_value(graph)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return {"task": "question_generation", "score": 0.0, "questions": [], "errors": [f"Graf invalid: {exc}"]}

    manifest_data = _load_json(manifest) if manifest is not None else None
    slot_index = _manifest_slot_index(manifest_data)
    questions_value = output.get("questions")
    if questions_value is None and isinstance(output.get("model_response"), Mapping):
        questions_value = output["model_response"].get("questions")
    questions = [dict(item) for item in _as_list(questions_value) if isinstance(item, Mapping)]
    errors: list[str] = []
    if not questions:
        errors.append("Outputul nu contine nicio intrebare valida structural.")

    scored = [
        _score_single_question(question, graph_index, slot_index.get(str(question.get("slot_id"))))
        for question in questions
    ]

    for index, question in enumerate(questions):
        similarities = [
            _question_similarity(question, other)
            for other_index, other in enumerate(questions)
            if other_index != index
        ]
        maximum_similarity = max(similarities, default=0.0)
        duplicate_points = 5.0 if maximum_similarity < 0.50 else 3.0 if maximum_similarity <= 0.70 else 0.0
        scored[index]["duplicate_similarity"] = _round(maximum_similarity)
        previous = scored[index]["breakdown"].get("non_duplication", 0.0)
        scored[index]["breakdown"]["non_duplication"] = duplicate_points
        scored[index]["score"] = _round(scored[index]["score"] - previous + duplicate_points)
        if duplicate_points < 5:
            scored[index]["diagnostics"].append(
                f"Similaritate maxima cu alta intrebare: {maximum_similarity:.3f}."
            )

    expected_count = len(REQUIRED_BLUEPRINTS)
    question_average = sum(item["score"] for item in scored) / expected_count
    if len(questions) != expected_count:
        errors.append(f"Au fost primite {len(questions)} intrebari; erau asteptate {expected_count}.")
    set_score, set_breakdown = _set_coverage_score(questions, graph_index)
    final_score = 0.90 * question_average + 0.10 * set_score

    slot_ids = [str(question.get("slot_id")) for question in questions]
    duplicate_slots = sorted({slot_id for slot_id in slot_ids if slot_ids.count(slot_id) > 1 and slot_id})
    if duplicate_slots:
        errors.append(f"Sloturi duplicate: {', '.join(duplicate_slots)}.")

    return {
        "task": "question_generation",
        "benchmark_id": output.get("benchmark_id"),
        "graph_version": output.get("graph_version"),
        "score": _round(final_score),
        "question_average": _round(question_average),
        "set_coverage_score": set_score,
        "set_coverage_breakdown": set_breakdown,
        "expected_question_count": expected_count,
        "received_question_count": len(questions),
        "questions": scored,
        "errors": errors,
    }


def _chapter_one(graph: GraphIndex) -> tuple[dict[str, Any] | None, list[str]]:
    if "CH_01" in graph.chapters:
        chapter = graph.chapters["CH_01"]
    else:
        chapter = next((ch for ch in graph.chapters.values() if ch.get("ordinal") == 1), None)
    if not chapter:
        return None, []
    return chapter, [str(event_id) for event_id in chapter.get("event_sequence", [])]


def _event_weight(node: Mapping[str, Any]) -> float:
    return {"major": 2.0, "medium": 1.0, "supporting": 0.5}.get(str(node.get("importance")), 0.5)


def _pairwise_order_accuracy(observed: Sequence[str], canonical: Sequence[str]) -> float:
    canonical_index = {event_id: index for index, event_id in enumerate(canonical)}
    filtered = []
    for event_id in observed:
        if event_id in canonical_index and event_id not in filtered:
            filtered.append(event_id)
    if len(filtered) < 2:
        return 0.0
    correct = total = 0
    for index in range(len(filtered)):
        for other in range(index + 1, len(filtered)):
            total += 1
            if canonical_index[filtered[index]] < canonical_index[filtered[other]]:
                correct += 1
    return correct / total if total else 0.0


def _trigram_repetition(text: str) -> float:
    tokens = _normalize_text(text).split()
    if len(tokens) < 3:
        return 0.0
    trigrams = [tuple(tokens[index : index + 3]) for index in range(len(tokens) - 2)]
    return 1.0 - len(set(trigrams)) / len(trigrams)


def _score_summary_register(
    register_name: str,
    summary: Mapping[str, Any],
    graph: GraphIndex,
    canonical_events: Sequence[str],
) -> dict[str, Any]:
    diagnostics: list[str] = []
    breakdown: dict[str, float] = {}
    sentences = [dict(item) for item in _as_list(summary.get("sentences")) if isinstance(item, Mapping)]
    summary_text = str(summary.get("summary_text", "")).strip()
    used_events = [str(v) for v in _as_list(summary.get("used_event_ids")) if v]
    omitted_events = [str(v) for v in _as_list(summary.get("omitted_event_ids")) if v]

    total_weight = sum(_event_weight(graph.nodes[event_id]) for event_id in canonical_events if event_id in graph.nodes)
    covered = set(used_events) & set(canonical_events)
    covered_weight = sum(_event_weight(graph.nodes[event_id]) for event_id in covered)
    coverage_fraction = covered_weight / total_weight if total_weight else 0.0
    breakdown["event_coverage"] = SUMMARY_MAX_POINTS["event_coverage"] * coverage_fraction
    missing_major = [
        event_id for event_id in canonical_events
        if event_id not in covered and graph.nodes.get(event_id, {}).get("importance") == "major"
    ]
    if missing_major:
        diagnostics.append(f"Evenimente majore omise: {', '.join(missing_major)}.")

    all_claims: list[Mapping[str, Any]] = []
    declared_edge_ids: set[str] = set()
    for sentence in sentences:
        all_claims.extend(item for item in _as_list(sentence.get("claims")) if isinstance(item, Mapping))
        declared_edge_ids.update(str(v) for v in _as_list(sentence.get("edge_ids")) if v)
    valid_claims = 0
    for claim in all_claims:
        triple = (str(claim.get("subject", "")), str(claim.get("predicate", "")), str(claim.get("object", "")))
        if triple in graph.edge_tuples:
            valid_claims += 1
    claim_fraction = valid_claims / len(all_claims) if all_claims else 0.0
    breakdown["claim_support"] = SUMMARY_MAX_POINTS["claim_support"] * claim_fraction
    if all_claims and valid_claims != len(all_claims):
        diagnostics.append(f"Afirmatii invalide: {len(all_claims) - valid_claims} din {len(all_claims)}.")
    elif not all_claims:
        diagnostics.append("Nu au fost declarate afirmatii formale pentru rezumat.")

    first_appearance: list[str] = []
    for sentence in sentences:
        for event_id in _as_list(sentence.get("event_ids")):
            event_id = str(event_id)
            if event_id not in first_appearance:
                first_appearance.append(event_id)
    order_fraction = _pairwise_order_accuracy(first_appearance, canonical_events)
    breakdown["event_order"] = SUMMARY_MAX_POINTS["event_order"] * order_fraction
    if order_fraction < 1:
        diagnostics.append(f"Acuratetea ordinii evenimentelor: {order_fraction:.3f}.")

    expected_causal_edges = {
        edge_id
        for edge_id, edge in graph.edges.items()
        if edge.get("source") in canonical_events and edge.get("predicate") in CAUSAL_PREDICATES
    }
    causal_recall = len(expected_causal_edges & declared_edge_ids) / len(expected_causal_edges) if expected_causal_edges else 1.0
    breakdown["causal_retention"] = SUMMARY_MAX_POINTS["causal_retention"] * causal_recall
    if causal_recall < 1:
        diagnostics.append(
            f"Relatii cauzale declarate: {len(expected_causal_edges & declared_edge_ids)} "
            f"din {len(expected_causal_edges)} asteptate."
        )

    valid_sentence_count = 0
    for sentence in sentences:
        sentence_event_ids = [str(v) for v in _as_list(sentence.get("event_ids")) if v]
        supporting_ids = [str(v) for v in _as_list(sentence.get("supporting_node_ids")) if v]
        sentence_edge_ids = [str(v) for v in _as_list(sentence.get("edge_ids")) if v]
        sentence_claims = [item for item in _as_list(sentence.get("claims")) if isinstance(item, Mapping)]
        ids_valid = all(node_id in graph.nodes for node_id in sentence_event_ids + supporting_ids)
        edges_valid = all(edge_id in graph.edges for edge_id in sentence_edge_ids)
        claims_valid = all(
            (str(claim.get("subject", "")), str(claim.get("predicate", "")), str(claim.get("object", ""))) in graph.edge_tuples
            for claim in sentence_claims
        )
        has_evidence = bool(sentence_event_ids or supporting_ids) and bool(sentence_edge_ids or sentence_claims)
        if ids_valid and edges_valid and claims_valid and has_evidence:
            valid_sentence_count += 1
    evidence_fraction = valid_sentence_count / len(sentences) if sentences else 0.0
    sentence_join = " ".join(str(sentence.get("text", "")).strip() for sentence in sentences).strip()
    text_consistency = 1.0 if _normalize_text(sentence_join) == _normalize_text(summary_text) and summary_text else 0.0
    breakdown["evidence_discipline"] = SUMMARY_MAX_POINTS["evidence_discipline"] * (0.8 * evidence_fraction + 0.2 * text_consistency)
    if evidence_fraction < 1:
        diagnostics.append(f"Propozitii cu dovezi integral valide: {valid_sentence_count} din {len(sentences)}.")
    if not text_consistency:
        diagnostics.append("summary_text nu coincide cu concatenarea sentences[].text.")

    actual_word_count = len(_words(summary_text))
    expected_range = (180, 300) if register_name == "simple" else (220, 350)
    length_score = 1.0 if expected_range[0] <= actual_word_count <= expected_range[1] else _clamp(
        1.0 - min(abs(actual_word_count - expected_range[0]), abs(actual_word_count - expected_range[1])) / max(expected_range)
    )
    normalized_sentences = [_normalize_text(sentence.get("text", "")) for sentence in sentences]
    unique_sentence_fraction = len(set(normalized_sentences)) / len(normalized_sentences) if normalized_sentences else 0.0
    repetition_score = 1.0 - _clamp(_trigram_repetition(summary_text) * 4.0)
    concision_fraction = 0.6 * length_score + 0.2 * unique_sentence_fraction + 0.2 * repetition_score
    breakdown["concision"] = SUMMARY_MAX_POINTS["concision"] * concision_fraction
    declared_word_count = summary.get("word_count")
    if declared_word_count != actual_word_count:
        diagnostics.append(f"word_count declarat={declared_word_count}, recalculat={actual_word_count}.")

    sentence_lengths = [len(_words(sentence.get("text", ""))) for sentence in sentences if sentence.get("text")]
    average_sentence_length = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0.0
    tokens = [_normalize_text(word) for word in _words(summary_text)]
    type_token_ratio = len(set(tokens)) / len(tokens) if tokens else 0.0
    starts = [
        " ".join(_normalize_text(sentence.get("text", "")).split()[:3])
        for sentence in sentences if sentence.get("text")
    ]
    transition_variety = len(set(starts)) / len(starts) if starts else 0.0
    if register_name == "simple":
        length_register = 1.0 if 8 <= average_sentence_length <= 22 else 0.5 if average_sentence_length <= 28 else 0.0
        lexical_register = _clamp(type_token_ratio / 0.40)
    else:
        length_register = 1.0 if 18 <= average_sentence_length <= 30 else 0.5 if 12 <= average_sentence_length <= 36 else 0.0
        lexical_register = _clamp(type_token_ratio / 0.48)
    register_fraction = 0.4 * length_register + 0.4 * lexical_register + 0.2 * transition_variety
    breakdown["register"] = SUMMARY_MAX_POINTS["register"] * register_fraction

    overlap = set(used_events) & set(omitted_events)
    if overlap:
        diagnostics.append(f"Evenimente simultan folosite si omise: {', '.join(sorted(overlap))}.")
    invalid_used = [event_id for event_id in used_events if event_id not in canonical_events]
    if invalid_used:
        diagnostics.append(f"Evenimente din afara capitolului I: {', '.join(invalid_used)}.")

    return {
        "register": register_name,
        "score": _round(sum(breakdown.values())),
        "breakdown": {key: _round(value) for key, value in breakdown.items()},
        "metrics": {
            "event_coverage": _round(coverage_fraction),
            "valid_claim_ratio": _round(claim_fraction),
            "event_order_accuracy": _round(order_fraction),
            "causal_recall": _round(causal_recall),
            "evidence_sentence_ratio": _round(evidence_fraction),
            "actual_word_count": actual_word_count,
            "average_sentence_length": _round(average_sentence_length),
            "type_token_ratio": _round(type_token_ratio),
            "trigram_repetition": _round(_trigram_repetition(summary_text)),
        },
        "used_event_ids": used_events,
        "diagnostics": diagnostics,
    }


def score_chapter_1_summary(summary_output: Any, graph: Any) -> dict[str, Any]:
    """Calculeaza Summary Reconstruction Score pentru capitolul I."""

    output, error = _safe_load_json(summary_output)
    if error or output is None:
        return {
            "task": "chapter_summary_reconstruction",
            "chapter_id": "CH_01",
            "score": 0.0,
            "registers": {},
            "errors": [f"Output JSON invalid: {error}"],
        }
    try:
        graph_index = GraphIndex.from_value(graph)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return {
            "task": "chapter_summary_reconstruction",
            "chapter_id": "CH_01",
            "score": 0.0,
            "registers": {},
            "errors": [f"Graf invalid: {exc}"],
        }
    chapter, canonical_events = _chapter_one(graph_index)
    if not chapter:
        return {
            "task": "chapter_summary_reconstruction",
            "chapter_id": "CH_01",
            "score": 0.0,
            "registers": {},
            "errors": ["Graful nu contine capitolul CH_01."],
        }

    summaries = output.get("summaries", {}) if isinstance(output.get("summaries"), Mapping) else {}
    errors: list[str] = []
    register_results: dict[str, Any] = {}
    for register_name in ("simple", "elevated"):
        value = summaries.get(register_name)
        if not isinstance(value, Mapping):
            errors.append(f"Lipseste rezumatul {register_name}.")
            register_results[register_name] = {
                "register": register_name,
                "score": 0.0,
                "breakdown": {key: 0.0 for key in SUMMARY_MAX_POINTS},
                "metrics": {},
                "used_event_ids": [],
                "diagnostics": [f"Rezumatul {register_name} lipseste."],
            }
        else:
            register_results[register_name] = _score_summary_register(
                register_name, value, graph_index, canonical_events
            )

    simple_events = set(register_results["simple"].get("used_event_ids", []))
    elevated_events = set(register_results["elevated"].get("used_event_ids", []))
    cross_register_consistency = _jaccard(simple_events, elevated_events)
    consistency_penalty = 10.0 * (1.0 - cross_register_consistency)
    raw_average = (register_results["simple"]["score"] + register_results["elevated"]["score"]) / 2.0
    final_score = _clamp(raw_average - consistency_penalty, 0.0, 100.0)
    if consistency_penalty:
        errors.append(
            f"Penalizare consistenta intre registre: {consistency_penalty:.3f}; "
            f"Jaccard evenimente={cross_register_consistency:.3f}."
        )

    return {
        "task": "chapter_summary_reconstruction",
        "benchmark_id": output.get("benchmark_id"),
        "graph_version": output.get("graph_version"),
        "chapter_id": "CH_01",
        "score": _round(final_score),
        "raw_register_average": _round(raw_average),
        "cross_register_event_consistency": _round(cross_register_consistency),
        "cross_register_penalty": _round(consistency_penalty),
        "registers": register_results,
        "errors": errors,
    }


def score_agent_submission(
    question_output: Any,
    summary_output: Any,
    graph: Any,
    manifest: Any | None = None,
    question_weight: float = 0.5,
    summary_weight: float = 0.5,
) -> dict[str, Any]:
    """Puncteaza ambele outputuri si calculeaza un scor general optional."""

    if question_weight < 0 or summary_weight < 0 or math.isclose(question_weight + summary_weight, 0.0):
        raise ValueError("Ponderile trebuie sa fie nenegative si sa aiba suma mai mare decat zero.")
    total_weight = question_weight + summary_weight
    normalized_question_weight = question_weight / total_weight
    normalized_summary_weight = summary_weight / total_weight
    question_result = score_question_generation(question_output, graph, manifest)
    summary_result = score_chapter_1_summary(summary_output, graph)
    overall = (
        normalized_question_weight * question_result.get("score", 0.0)
        + normalized_summary_weight * summary_result.get("score", 0.0)
    )
    return {
        "overall_score": _round(overall),
        "weights": {
            "question_generation": _round(normalized_question_weight),
            "chapter_1_summary": _round(normalized_summary_weight),
        },
        "question_generation": question_result,
        "chapter_1_summary": summary_result,
    }


def _main() -> int:
    parser = argparse.ArgumentParser(description="Evaluator deterministic pentru benchmarkul Ion.")
    parser.add_argument("--graph", required=True, help="Calea catre knowledge-graph.json")
    parser.add_argument("--questions", help="Calea catre outputul JSON cu intrebarile")
    parser.add_argument("--summary", help="Calea catre outputul JSON cu rezumatele capitolului I")
    parser.add_argument("--manifest", help="Calea optionala catre manifestul experimentului")
    parser.add_argument("--output", help="Calea optionala unde se scrie raportul JSON")
    args = parser.parse_args()

    if not args.questions and not args.summary:
        parser.error("Este necesar --questions, --summary sau ambele.")

    if args.questions and args.summary:
        result = score_agent_submission(
            args.questions,
            args.summary,
            args.graph,
            manifest=args.manifest,
        )
    elif args.questions:
        result = score_question_generation(args.questions, args.graph, manifest=args.manifest)
    else:
        result = score_chapter_1_summary(args.summary, args.graph)

    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(serialized + "\n", encoding="utf-8")
    else:
        print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
