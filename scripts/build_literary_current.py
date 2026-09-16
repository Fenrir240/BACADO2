"""Generează cu Qwen materialul despre curentul literar fără să modifice graful.

Se face o singură generare, fără retry dacă validarea locală eșuează. Curentul nu
este primit ca argument: Qwen îl determină din knowledge graph-ul operei. Cele două
trăsături dezvoltate sunt însă strict cele argumentate în eseul-model. O eventuală
îmbogățire a grafului se face numai dacă este cerută explicit.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from exercise_builder_common import (
    DEFAULT_GRAPH_PATH,
    ROOT_DIR,
    clean_text,
    graph_work_metadata,
    read_json,
    write_json,
)


QWEN_DIR = ROOT_DIR / "cercetare-qwen"
DEFAULT_CONFIG_PATH = QWEN_DIR / "config.local.env"
LEGACY_CONFIG_PATH = ROOT_DIR / "cercetare" / "experiment2" / "config.local.env"
DEFAULT_MODEL = "qwen/qwen3.7-flash"
DEFAULT_REASONING = "medium"
RELEVANT_TYPES = {
    "Work", "Author", "NarrativePerspective", "LiteraryTechnique", "Theme",
    "Motif", "Symbol", "Conflict", "SocialGroup", "Location", "Value",
    "NarrativeStructure", "LiteraryMovement", "LiteraryTrait",
}


def _load_runner() -> ModuleType:
    name = "bacapp_literary_current_qwen_runner"
    path = QWEN_DIR / "run_qwen_packets.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Nu pot încărca runner-ul Qwen din {path}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _slug(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_") or "curent"


def _compact_node(node: dict) -> dict:
    return {
        key: node.get(key)
        for key in (
            "id", "type", "label", "description", "importance",
            "assertion_type", "attributes", "chapter_ids",
        )
        if node.get(key) not in (None, "", [], {})
    }


def build_packet(graph: dict, graph_path: Path, model_essay_path: Path) -> dict:
    nodes = [node for node in graph.get("nodes", []) if isinstance(node, dict)]
    selected = [
        node for node in nodes
        if str(node.get("type") or "") in RELEVANT_TYPES
        or any(
            token in (str(node.get("label") or "") + " " + str(node.get("description") or "")).casefold()
            for token in ("realism", "realist", "romant", "modern", "simbol", "clasic")
        )
    ]
    selected.sort(
        key=lambda node: (
            0 if node.get("type") in {"Work", "Author"} else 1,
            {"major": 0, "supporting": 1, "minor": 2}.get(str(node.get("importance")), 3),
            str(node.get("id") or ""),
        )
    )
    selected = selected[:120]
    selected_ids = {str(node.get("id")) for node in selected}
    edges = [
        edge for edge in graph.get("edges", [])
        if isinstance(edge, dict)
        and (
            str(edge.get("source")) in selected_ids
            or str(edge.get("target")) in selected_ids
        )
    ][:650]
    model_essay = model_essay_path.read_text(encoding="utf-8").strip()
    if not model_essay:
        raise ValueError("Eseul-model este gol.")
    return {
        "schema_version": 1,
        "task": "determine_and_explain_literary_current",
        "source_graph": str(graph_path),
        "model_essay_source": str(model_essay_path),
        "model_essay": model_essay,
        "work": graph_work_metadata(graph),
        "graph_metadata": graph.get("metadata", {}),
        "nodes": [_compact_node(node) for node in selected],
        "edges": edges,
    }


def render_prompt(packet: dict) -> str:
    return f"""
Ești profesor expert de literatură română pentru Bacalaureat. Folosește knowledge
graph-ul pentru datele despre operă și eseul-model pentru a stabili trăsăturile
curentului care trebuie predate. Determină implicit curentul literar principal și
construiește un material didactic clar.

REGULI:
- identifică exact cele DOUĂ trăsături ale curentului argumentate efectiv în
  eseul-model; nu selecta alte trăsături, chiar dacă apar în knowledge graph;
- simpla menționare a unei trăsături în eseu nu este suficientă: ea trebuie să fie
  dezvoltată și aplicată operei;
- pentru fiecare trăsătură explică noțiunea și indică 1-3 dovezi concrete din operă;
- pentru fiecare trăsătură copiază în `model_essay_excerpt` un fragment textual exact
  din eseul-model care dovedește că acea trăsătură este argumentată;
- nu inventa citate și nu pretinde că o interpretare este citat;
- conținutul va fi afișat direct elevului, deci scrie natural și corect în română;
- produce o singură variantă;
- răspunde EXCLUSIV cu un obiect JSON valid, fără markdown.

SCHEMA JSON:
{{
  "movement": {{
    "id": "slug_stabil",
    "name": "numele curentului",
    "definition": "definiție clară",
    "work_classification": "argumentarea încadrării operei",
    "historical_context": "context literar concis"
  }},
  "traits": [
    {{
      "id": "trait_slug",
      "title": "denumirea trăsăturii",
      "explanation": "explicație",
      "evidence_from_work": ["dovadă concretă"],
      "essay_use": "cum poate fi formulată în eseu",
      "model_essay_excerpt": "fragment exact din eseul-model"
    }}
  ],
  "bac_synthesis": "sinteză finală pentru elev"
}}

KNOWLEDGE GRAPH SELECTAT:
{json.dumps(packet, ensure_ascii=False, separators=(',', ':'))}
""".strip()


def _extract_json(text: str) -> dict | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        value = json.loads(cleaned)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            return None
        try:
            value = json.loads(match.group(0))
            return value if isinstance(value, dict) else None
        except json.JSONDecodeError:
            return None


def _normalize(payload: dict | None, model_essay: str = "") -> tuple[dict, dict]:
    raw = payload if isinstance(payload, dict) else {}
    movement = raw.get("movement") if isinstance(raw.get("movement"), dict) else {}
    raw_traits = raw.get("traits") if isinstance(raw.get("traits"), list) else []
    traits = []
    for index, trait in enumerate(raw_traits, start=1):
        if not isinstance(trait, dict):
            continue
        title = clean_text(trait.get("title")) or f"Trăsătura {index}"
        traits.append(
            {
                "id": clean_text(trait.get("id")) or _slug(title),
                "title": title,
                "explanation": clean_text(trait.get("explanation")),
                "evidence_from_work": [
                    clean_text(value) for value in trait.get("evidence_from_work", [])
                    if clean_text(value)
                ] if isinstance(trait.get("evidence_from_work"), list) else [],
                "essay_use": clean_text(trait.get("essay_use")),
                "model_essay_excerpt": clean_text(trait.get("model_essay_excerpt")),
            }
        )
    name = clean_text(movement.get("name")) or "Curent literar neprecizat"
    result = {
        "movement": {
            "id": clean_text(movement.get("id")) or _slug(name),
            "name": name,
            "definition": clean_text(movement.get("definition")),
            "work_classification": clean_text(movement.get("work_classification")),
            "historical_context": clean_text(movement.get("historical_context")),
        },
        "traits": traits,
        "bac_synthesis": clean_text(raw.get("bac_synthesis")),
    }
    normalized_essay = " ".join(model_essay.split())
    excerpts_verified = bool(traits) and all(
        trait["model_essay_excerpt"]
        and " ".join(trait["model_essay_excerpt"].split()) in normalized_essay
        for trait in traits
    )
    validation = {
        "valid": bool(
            result["movement"]["name"]
            and result["movement"]["definition"]
            and result["movement"]["work_classification"]
            and len(traits) == 2
            and all(trait["explanation"] and trait["evidence_from_work"] for trait in traits)
            and excerpts_verified
        ),
        "trait_count": len(traits),
        "expected_trait_count": 2,
        "traits_from_model_essay_verified": excerpts_verified,
    }
    return result, validation


def _upsert(items: list[dict], value: dict) -> None:
    for index, item in enumerate(items):
        if isinstance(item, dict) and item.get("id") == value["id"]:
            items[index] = value
            return
    items.append(value)


def enrich_graph(graph: dict, artifact: dict, artifact_path: Path) -> None:
    material = artifact["literary_current"]
    movement = material["movement"]
    movement_slug = _slug(movement["id"] or movement["name"])
    movement_id = f"LITERARY_MOVEMENT_{movement_slug.upper()}"
    source_id = "SRC_QWEN_LITERARY_CURRENT"
    work_node = next(
        (node for node in graph.get("nodes", []) if isinstance(node, dict) and node.get("type") == "Work"),
        None,
    )
    if work_node is None:
        raise ValueError("Graful nu conține un nod Work pentru îmbogățire.")
    sources = graph.setdefault("sources", [])
    nodes = graph.setdefault("nodes", [])
    edges = graph.setdefault("edges", [])
    _upsert(
        sources,
        {
            "id": source_id,
            "source_type": "ai_derived_analysis",
            "title": "Curent literar determinat din knowledge graph",
            "model": artifact["generation"]["model"],
            "path": str(artifact_path),
            "confidence": 0.9,
        },
    )
    _upsert(
        nodes,
        {
            "aliases": [], "chapter_ids": [], "importance": "major", "confidence": 0.9,
            "assertion_type": "literary_interpretation", "source_refs": [source_id],
            "attributes": {"generated_by": artifact["generation"]["model"]},
            "id": movement_id, "type": "LiteraryMovement", "label": movement["name"],
            "description": movement["definition"],
        },
    )
    _upsert(
        edges,
        {
            "id": f"EDGE_{work_node['id']}_BELONGS_TO_{movement_id}",
            "source": work_node["id"], "predicate": "belongs_to_literary_movement",
            "target": movement_id, "qualifiers": {},
            "assertion_type": "literary_interpretation", "source_refs": [source_id],
        },
    )
    for index, trait in enumerate(material["traits"], start=1):
        trait_id = f"LITERARY_TRAIT_{movement_slug.upper()}_{index:02d}"
        _upsert(
            nodes,
            {
                "aliases": [], "chapter_ids": [], "importance": "supporting", "confidence": 0.9,
                "assertion_type": "literary_interpretation", "source_refs": [source_id],
                "attributes": {
                    "essay_use": trait["essay_use"],
                    "evidence_from_work": trait["evidence_from_work"],
                },
                "id": trait_id, "type": "LiteraryTrait", "label": trait["title"],
                "description": trait["explanation"],
            },
        )
        _upsert(
            edges,
            {
                "id": f"EDGE_{movement_id}_HAS_{trait_id}",
                "source": movement_id, "predicate": "has_characteristic", "target": trait_id,
                "qualifiers": {"order": index}, "assertion_type": "literary_interpretation",
                "source_refs": [source_id],
            },
        )
        _upsert(
            edges,
            {
                "id": f"EDGE_{work_node['id']}_EXEMPLIFIES_{trait_id}",
                "source": work_node["id"], "predicate": "exemplifies_characteristic", "target": trait_id,
                "qualifiers": {}, "assertion_type": "literary_interpretation",
                "source_refs": [source_id],
            },
        )
    ontology = graph.setdefault("ontology", {})
    for node_type in ("LiteraryMovement", "LiteraryTrait"):
        if node_type not in ontology.setdefault("node_types", []):
            ontology["node_types"].append(node_type)
    for relation in ("belongs_to_literary_movement", "has_characteristic", "exemplifies_characteristic"):
        if relation not in ontology.setdefault("relationship_types", []):
            ontology["relationship_types"].append(relation)
    validation = graph.setdefault("validation", {})
    validation["node_count"] = len(nodes)
    validation["edge_count"] = len(edges)
    validation["connected_to_main_count"] = len(nodes)
    validation["connected_to_main_ratio"] = 1.0
    validation["sourced_assertion_count"] = len(nodes) + len(edges)
    validation["type_distribution"] = dict(
        sorted(Counter(str(node.get("type")) for node in nodes).items())
    )
    validation["relation_distribution"] = dict(
        sorted(Counter(str(edge.get("predicate")) for edge in edges).items())
    )


def enrich_adjacent_schema(graph_path: Path) -> None:
    schema_path = graph_path.with_name("knowledge-graph.schema.json")
    if not schema_path.is_file():
        return
    schema = read_json(schema_path)
    definitions = schema.get("$defs", {})
    node_enum = (
        definitions.get("node", {}).get("properties", {}).get("type", {}).get("enum")
    )
    edge_enum = (
        definitions.get("edge", {}).get("properties", {}).get("predicate", {}).get("enum")
    )
    if isinstance(node_enum, list):
        for value in ("LiteraryMovement", "LiteraryTrait"):
            if value not in node_enum:
                node_enum.append(value)
    if isinstance(edge_enum, list):
        for value in (
            "belongs_to_literary_movement",
            "has_characteristic",
            "exemplifies_characteristic",
        ):
            if value not in edge_enum:
                edge_enum.append(value)
    write_json(schema_path, schema)


def generate_literary_current(
    graph_path: Path,
    *,
    model_essay_path: Path,
    config_path: Path = DEFAULT_CONFIG_PATH,
    model: str = DEFAULT_MODEL,
    reasoning: str = DEFAULT_REASONING,
    timeout: int = 1200,
    max_tokens: int = 6000,
    dry_run: bool = False,
    enrich: bool = False,
) -> tuple[dict, Path]:
    graph = read_json(graph_path)
    work = graph_work_metadata(graph)
    output_path = ROOT_DIR / "data" / "generated_works" / work["work_id"] / "intelegere-opera" / "curent-literar.json"
    run_dir = output_path.parent / "qwen-literary-current-runs" / f"run-{_stamp()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    resolved_model_essay_path = model_essay_path.resolve()
    if not resolved_model_essay_path.is_file():
        raise ValueError(f"Eseul-model nu există: {resolved_model_essay_path}")
    packet = build_packet(graph, graph_path, resolved_model_essay_path)
    prompt = render_prompt(packet)
    write_json(run_dir / "packet.json", packet)
    (run_dir / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")
    if dry_run:
        result = {"dry_run": True, "work": work, "model": model, "run_dir": str(run_dir)}
        write_json(run_dir / "manifest.json", result)
        return result, run_dir / "manifest.json"

    runner = _load_runner()
    config = runner.load_local_env(config_path)
    if not config.get("OPENROUTER_API_KEY"):
        config = {**runner.load_local_env(LEGACY_CONFIG_PATH), **config}
    api_key = config.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY lipsește din configurație.")
    request = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "reasoning": {"effort": reasoning, "exclude": True},
        "provider": {"allow_fallbacks": True, "require_parameters": True, "data_collection": "deny"},
        "response_format": {"type": "json_object"},
    }
    write_json(run_dir / "request.json", request)
    response = runner.api_json(
        f"{runner.OPENROUTER_BASE_URL}/chat/completions", api_key,
        method="POST", payload=request, timeout=timeout,
    )
    write_json(run_dir / "response.openrouter.json", response)
    content = runner.extract_content(response)
    (run_dir / "response.raw.txt").write_text(content + "\n", encoding="utf-8")
    parsed = _extract_json(content)
    if parsed is not None:
        write_json(run_dir / "result.json", parsed)
    material, validation = _normalize(parsed, packet["model_essay"])
    artifact = {
        "schema_version": 1,
        "work": work,
        "generation": {
            "model": model, "reasoning_effort": reasoning, "attempts": 1,
            "retry_on_invalid": False, "source_graph": str(graph_path), "run_dir": str(run_dir),
            "model_essay": str(resolved_model_essay_path),
            "usage": response.get("usage") or {},
        },
        "literary_current": material,
        "validation": validation,
    }
    write_json(output_path, artifact)
    if enrich:
        enrich_graph(graph, artifact, output_path)
        enrich_adjacent_schema(graph_path)
        write_json(graph_path, graph)
    write_json(run_dir / "manifest.json", artifact)
    return artifact, output_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH)
    parser.add_argument("--model-essay", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--reasoning-effort", default=DEFAULT_REASONING)
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--max-tokens", type=int, default=6000)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--enrich-graph",
        action="store_true",
        help="Adaugă explicit în graf nodurile și muchiile despre curent.",
    )
    args = parser.parse_args(argv)
    artifact, path = generate_literary_current(
        args.graph.resolve(), model_essay_path=args.model_essay.resolve(),
        config_path=args.config.resolve(), model=args.model,
        reasoning=args.reasoning_effort, timeout=args.timeout, max_tokens=args.max_tokens,
        dry_run=args.dry_run, enrich=args.enrich_graph,
    )
    if args.dry_run:
        print(f"Packet pregătit fără apel API: {path}")
    else:
        print(f"Curent determinat: {artifact['literary_current']['movement']['name']}")
        print(f"Trăsături: {len(artifact['literary_current']['traits'])}")
        print(f"Validare locală: {artifact['validation']['valid']}")
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
