"""Generează determinist pachetul de graf folosit pentru rezumatul capitolului I."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


EXPERIMENT_DIR = Path(__file__).resolve().parent
RESEARCH_DIR = EXPERIMENT_DIR.parent
GRAPH_PATH = RESEARCH_DIR / "graf1" / "knowledge-graph.json"
OUTPUT_PATH = EXPERIMENT_DIR / "inputs" / "chapter-01-graph.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_chapter_packet(
    graph_path: Path = GRAPH_PATH,
    output_path: Path = OUTPUT_PATH,
) -> dict[str, Any]:
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    node_by_id = {node["id"]: node for node in graph["nodes"]}

    chapter = next(
        (item for item in graph.get("chapters", []) if item.get("id") == "CH_01"),
        None,
    )
    if chapter is None:
        raise ValueError("Graful canonic nu conține capitolul CH_01.")

    seed_ids = {
        node["id"]
        for node in graph["nodes"]
        if "CH_01" in node.get("chapter_ids", [])
    }
    seed_ids.add("CH_01")
    seed_ids.update(chapter.get("event_sequence", []))
    seed_ids.update(
        value
        for value in (chapter.get("opening_state"), chapter.get("closing_state"))
        if value
    )

    included_ids = set(seed_ids)
    candidate_edges: list[dict[str, Any]] = []
    for edge in graph["edges"]:
        if edge.get("source") not in seed_ids and edge.get("target") not in seed_ids:
            continue
        other_ids = {edge.get("source"), edge.get("target")} - seed_ids
        if any(
            node_by_id.get(node_id, {}).get("type") == "NarrativeEvent"
            for node_id in other_ids
        ):
            # Nu introducem evenimente din alte capitole în pachetul capitolului I.
            continue
        candidate_edges.append(edge)
        included_ids.update(
            node_id
            for node_id in (edge.get("source"), edge.get("target"))
            if node_id in node_by_id
        )

    packet_edges = [
        edge
        for edge in candidate_edges
        if edge.get("source") in included_ids and edge.get("target") in included_ids
    ]
    packet_nodes = [node for node in graph["nodes"] if node["id"] in included_ids]

    missing_endpoints = sorted(
        {
            endpoint
            for edge in packet_edges
            for endpoint in (edge.get("source"), edge.get("target"))
            if endpoint not in included_ids
        }
    )
    if missing_endpoints:
        raise ValueError(f"Muchii cu endpointuri lipsă: {missing_endpoints}")

    packet = {
        "metadata": {
            **graph.get("metadata", {}),
            "packet_type": "chapter_subgraph",
            "chapter_id": "CH_01",
            "source_graph_sha256": _sha256(graph_path),
            "extraction_rule": (
                "Toate nodurile asociate CH_01 și endpointurile nenarative ale "
                "muchiilor incidente; evenimentele din alte capitole sunt excluse."
            ),
        },
        "sources": graph.get("sources", []),
        "ontology": graph.get("ontology", {}),
        "nodes": packet_nodes,
        "edges": packet_edges,
        "chapters": [chapter],
        "reconstruction_profiles": graph.get("reconstruction_profiles", {}),
        "validation": {
            "node_count": len(packet_nodes),
            "edge_count": len(packet_edges),
            "chapter_count": 1,
            "event_count": len(chapter.get("event_sequence", [])),
            "missing_edge_endpoints": missing_endpoints,
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(packet, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return packet


def main() -> int:
    packet = build_chapter_packet()
    print(f"Creat: {OUTPUT_PATH}")
    print(f"Noduri: {len(packet['nodes'])}")
    print(f"Muchii: {len(packet['edges'])}")
    print(f"Evenimente: {packet['validation']['event_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
