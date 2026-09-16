"""Generează în Experimentul 2 același subgraf determinist al capitolului I."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


EXPERIMENT_DIR = Path(__file__).resolve().parent
RESEARCH_DIR = EXPERIMENT_DIR.parent
GRAPH_PATH = RESEARCH_DIR / "graf1" / "knowledge-graph.json"
OUTPUT_PATH = EXPERIMENT_DIR / "inputs" / "chapter-01-graph.json"
BASE_PREPARER_PATH = RESEARCH_DIR / "experiment1" / "prepare_inputs.py"


def _base_module() -> Any:
    spec = importlib.util.spec_from_file_location("experiment2_base_preparer", BASE_PREPARER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Nu pot încărca {BASE_PREPARER_PATH}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_chapter_packet(
    graph_path: Path = GRAPH_PATH,
    output_path: Path = OUTPUT_PATH,
) -> dict[str, Any]:
    return _base_module().build_chapter_packet(graph_path, output_path)


def main() -> int:
    packet = build_chapter_packet()
    print(f"Creat: {OUTPUT_PATH}")
    print(f"Noduri: {len(packet['nodes'])}")
    print(f"Muchii: {len(packet['edges'])}")
    print(f"Evenimente: {packet['validation']['event_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
