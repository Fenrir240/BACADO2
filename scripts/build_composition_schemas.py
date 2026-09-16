"""Generează cu Qwen 3.7 Flash cele trei scheme compoziționale ale unei opere.

Sunt făcute exact trei apeluri: relația incipit-final, conflictul și titlul. Fiecare
apel are o singură încercare; validarea locală este doar diagnostică și nu produce
regenerări. Rezultatul final este contractul consumat direct de UI.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Sequence

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
DEFAULT_REASONING_EFFORT = "medium"
DEFAULT_MAX_TOKENS = 12_000
ELEMENTS = (
    {
        "id": "incipit_final",
        "title": "Relația incipit–final",
        "focus": (
            "Explică relația dintre începutul și finalul operei: elementele reluate, "
            "simetriile, contrastele și semnificația lor pentru ansamblul operei."
        ),
        "branch_headings": (
            "Incipitul",
            "Finalul",
            "Corespondențe și contraste",
            "Cum folosesc elementul în eseu",
        ),
    },
    {
        "id": "conflict",
        "title": "Conflictul",
        "focus": (
            "Explică principalele conflicte ale operei, personajele sau forțele implicate, "
            "evoluția tensiunilor și rolul conflictului în construcția sensului."
        ),
        "branch_headings": (
            "Conflictul central",
            "Forme și planuri ale conflictului",
            "Evoluție și consecințe",
            "Cum folosesc elementul în eseu",
        ),
    },
    {
        "id": "title",
        "title": "Titlul",
        "focus": (
            "Explică semnificația titlului, tipul său, legătura cu personajele, temele "
            "sau motivele operei și relevanța sa pentru mesajul textului."
        ),
        "branch_headings": (
            "Sens și tip de titlu",
            "Legătura cu opera",
            "Semnificație literară",
            "Cum folosesc elementul în eseu",
        ),
    },
)
IMPORTANCE_ORDER = {"major": 0, "supporting": 1, "minor": 2}


def _load_runner() -> ModuleType:
    name = "bacapp_composition_qwen_runner"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    path = QWEN_DIR / "run_qwen_packets.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Nu pot încărca runner-ul Qwen din {path}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _as_list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _nodes_by_id(graph: dict) -> dict[str, dict]:
    return {
        str(node["id"]): node
        for node in _as_list(graph.get("nodes"))
        if isinstance(node, dict) and node.get("id")
    }


def _event_order(node: dict) -> int:
    attributes = node.get("attributes") if isinstance(node.get("attributes"), dict) else {}
    try:
        return int(attributes.get("global_order") or 10**9)
    except (TypeError, ValueError):
        return 10**9


def _event_importance(node: dict) -> tuple[int, int]:
    attributes = node.get("attributes") if isinstance(node.get("attributes"), dict) else {}
    importance = str(attributes.get("importance") or node.get("importance") or "minor")
    return IMPORTANCE_ORDER.get(importance, 3), _event_order(node)


def _chapter_ordinal(node: dict) -> int:
    attributes = node.get("attributes") if isinstance(node.get("attributes"), dict) else {}
    try:
        return int(attributes.get("ordinal") or 10**9)
    except (TypeError, ValueError):
        return 10**9


def _compact_node(node: dict) -> dict:
    result = {
        "id": str(node.get("id") or ""),
        "type": str(node.get("type") or ""),
        "label": clean_text(node.get("label")),
        "description": clean_text(node.get("description")),
        "importance": str(node.get("importance") or ""),
        "assertion_type": str(node.get("assertion_type") or ""),
    }
    attributes = node.get("attributes") if isinstance(node.get("attributes"), dict) else {}
    allowed_attributes = (
        "ordinal",
        "chapter_id",
        "chapter_order",
        "global_order",
        "title",
        "participants",
        "location",
        "action",
        "simple_narration",
        "immediate_effects",
        "long_term_effects",
        "state_transitions",
        "conflicts",
        "themes",
        "importance",
    )
    compact_attributes = {
        key: attributes[key]
        for key in allowed_attributes
        if key in attributes and attributes[key] not in (None, "", [], {})
    }
    if compact_attributes:
        result["attributes"] = compact_attributes
    return result


def _edge_ids_for_nodes(graph: dict, selected_ids: set[str]) -> list[dict]:
    result = []
    for edge in _as_list(graph.get("edges")):
        if not isinstance(edge, dict):
            continue
        source, target = str(edge.get("source") or ""), str(edge.get("target") or "")
        if source not in selected_ids or target not in selected_ids:
            continue
        result.append(
            {
                "id": str(edge.get("id") or ""),
                "source": source,
                "predicate": str(edge.get("predicate") or ""),
                "target": target,
                "assertion_type": str(edge.get("assertion_type") or ""),
            }
        )
    return result


def _referenced_ids(nodes: Iterable[dict]) -> set[str]:
    result: set[str] = set()
    for node in nodes:
        attributes = node.get("attributes") if isinstance(node.get("attributes"), dict) else {}
        for key in ("participants", "conflicts", "themes"):
            result.update(str(value) for value in _as_list(attributes.get(key)) if value)
        location = attributes.get("location")
        if location:
            result.add(str(location))
        chapter = attributes.get("chapter_id")
        if chapter:
            result.add(str(chapter))
    return result


def _base_nodes(graph: dict) -> list[dict]:
    nodes = [node for node in _as_list(graph.get("nodes")) if isinstance(node, dict)]
    return [node for node in nodes if node.get("type") in {"Work", "Author"}]


def _packet_nodes(graph: dict, element_id: str) -> list[dict]:
    nodes = [node for node in _as_list(graph.get("nodes")) if isinstance(node, dict)]
    nodes_by_id = _nodes_by_id(graph)
    characters = sorted(
        (node for node in nodes if node.get("type") == "Character"),
        key=lambda node: (
            IMPORTANCE_ORDER.get(str(node.get("importance") or "minor"), 3),
            clean_text(node.get("label")).casefold(),
        ),
    )
    concepts = [
        node
        for node in nodes
        if node.get("type") in {"Theme", "Conflict", "Motif", "LiteraryTechnique", "Value"}
    ]
    events = sorted(
        (node for node in nodes if node.get("type") == "NarrativeEvent"),
        key=_event_order,
    )
    selected: list[dict] = list(_base_nodes(graph))

    if element_id == "incipit_final":
        chapters = sorted(
            (node for node in nodes if node.get("type") == "Chapter"),
            key=_chapter_ordinal,
        )
        boundary_chapters = chapters[:1] + chapters[-1:] if chapters else []
        boundary_ids = {str(node.get("id")) for node in boundary_chapters}
        boundary_events = [
            event
            for event in events
            if str((event.get("attributes") or {}).get("chapter_id") or "") in boundary_ids
        ]
        boundary_states = [
            node
            for node in nodes
            if node.get("type") == "NarrativeState"
            and any(chapter_id in str(node.get("id") or "") for chapter_id in boundary_ids)
        ]
        selected.extend(boundary_chapters + boundary_events + boundary_states + concepts)
    elif element_id == "conflict":
        conflict_ids = {str(node.get("id")) for node in concepts if node.get("type") == "Conflict"}
        conflict_events = [
            event
            for event in events
            if conflict_ids & set(map(str, _as_list((event.get("attributes") or {}).get("conflicts"))))
        ]
        conflict_events = sorted(conflict_events, key=_event_importance)[:42]
        selected.extend(concepts + characters[:12] + conflict_events)
    else:
        important_events = sorted(events, key=_event_importance)[:30]
        selected.extend(characters[:10] + concepts + important_events)

    selected_ids = {str(node.get("id")) for node in selected if node.get("id")}
    selected_ids.update(_referenced_ids(selected))
    # Include nodurile referite de evenimente, dar nu extinde recursiv packetul.
    selected.extend(nodes_by_id[node_id] for node_id in sorted(selected_ids) if node_id in nodes_by_id)
    unique: dict[str, dict] = {}
    for node in selected:
        node_id = str(node.get("id") or "")
        if node_id:
            unique[node_id] = node
    return list(unique.values())


def build_packet(graph: dict, element: dict, graph_path: Path) -> dict:
    metadata = graph_work_metadata(graph)
    selected_nodes = _packet_nodes(graph, element["id"])
    selected_ids = {str(node["id"]) for node in selected_nodes}
    return {
        "metadata": {
            "task": "composition_element_schema",
            "work_id": metadata["work_id"],
            "work_title": metadata["title"],
            "author": metadata["author"],
            "element_id": element["id"],
            "element_title": element["title"],
            "source_graph": str(graph_path),
            "source_graph_version": str((graph.get("metadata") or {}).get("version") or ""),
        },
        "element": {
            "id": element["id"],
            "title": element["title"],
            "focus": element["focus"],
            "required_branch_headings": list(element["branch_headings"]),
        },
        "source_contract": {
            "exclusive_source": "Folosește exclusiv acest packet.",
            "no_external_knowledge": True,
            "no_invented_quotes": True,
            "evidence_rule": "Fiecare ramură citează numai ID-uri prezente în nodes.",
        },
        "nodes": [_compact_node(node) for node in selected_nodes],
        "edges": _edge_ids_for_nodes(graph, selected_ids),
    }


def render_prompt(packet: dict) -> str:
    element = packet["element"]
    schema_example = {
        "task": "composition_element_schema",
        "element_id": element["id"],
        "title": element["title"],
        "central_idea": "Ideea centrală, clară și memorabilă.",
        "branches": [
            {
                "heading": heading,
                "key_idea": "Ideea-cheie.",
                "explanation": "Explicație de 2-4 propoziții.",
                "evidence_node_ids": ["ID_DIN_PACKET"],
            }
            for heading in element["required_branch_headings"]
        ],
        "essay_paragraph": "Paragraf coerent, gata de adaptat într-un eseu BAC.",
        "memory_formula": ["formulă scurtă 1", "formulă scurtă 2", "formulă scurtă 3"],
    }
    return f"""
Ești Qwen 3.7 Flash și construiești o schemă explicativă pentru un elev care pregătește
eseul de Bacalaureat. Folosește exclusiv GRAPH_PACKET. Nu completa din memorie, nu
consulta alte surse și nu inventa citate sau fapte.

SARCINĂ:
{element['focus']}

REGULI:
1. Returnează exact cele patru ramuri cerute, în ordinea dată.
2. Formulează clar, cu diacritice, fără identificatori tehnici în textul pentru elev.
3. Fiecare ramură are o idee-cheie și o explicație de 2-4 propoziții.
4. `evidence_node_ids` conține numai ID-uri existente în packet.
5. `essay_paragraph` are 130-190 de cuvinte și poate fi folosit direct în eseu.
6. `memory_formula` conține exact trei formule scurte.
7. Returnează exclusiv un obiect JSON valid, fără Markdown.

FORMAT OBLIGATORIU:
{json.dumps(schema_example, ensure_ascii=False, indent=2)}

GRAPH_PACKET:
{json.dumps(packet, ensure_ascii=False, separators=(',', ':'))}
""".strip()


def _extract_json(text: str) -> dict | None:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        first, last = text.find("{"), text.rfind("}")
        if first < 0 or last <= first:
            return None
        try:
            value = json.loads(text[first : last + 1])
        except json.JSONDecodeError:
            return None
    return value if isinstance(value, dict) else None


def validate_schema(payload: dict | None, packet: dict) -> dict:
    errors: list[str] = []
    if payload is None:
        return {"valid": False, "errors": ["Răspunsul nu este un obiect JSON interpretabil."]}
    element = packet["element"]
    if payload.get("task") != "composition_element_schema":
        errors.append("task incorect")
    if payload.get("element_id") != element["id"]:
        errors.append("element_id incorect")
    branches = payload.get("branches")
    if not isinstance(branches, list) or len(branches) != 4:
        errors.append("branches trebuie să conțină exact 4 ramuri")
        branches = []
    allowed_ids = {str(node["id"]) for node in packet["nodes"]}
    for index, branch in enumerate(branches):
        if not isinstance(branch, dict):
            errors.append(f"branches[{index}] nu este obiect")
            continue
        if not clean_text(branch.get("heading")) or not clean_text(branch.get("explanation")):
            errors.append(f"branches[{index}] nu are heading/explanation")
        unknown = sorted(set(map(str, _as_list(branch.get("evidence_node_ids")))) - allowed_ids)
        if unknown:
            errors.append(f"branches[{index}] folosește ID-uri necunoscute: {unknown}")
    if not clean_text(payload.get("central_idea")):
        errors.append("central_idea lipsește")
    if not clean_text(payload.get("essay_paragraph")):
        errors.append("essay_paragraph lipsește")
    if len(_as_list(payload.get("memory_formula"))) != 3:
        errors.append("memory_formula trebuie să aibă exact 3 elemente")
    return {"valid": not errors, "errors": errors}


def _normalized_schema(payload: dict | None, element: dict, validation: dict) -> dict:
    payload = payload or {}
    branches = payload.get("branches") if isinstance(payload.get("branches"), list) else []
    normalized_branches = []
    for index, heading in enumerate(element["branch_headings"]):
        source = branches[index] if index < len(branches) and isinstance(branches[index], dict) else {}
        normalized_branches.append(
            {
                "heading": clean_text(source.get("heading")) or heading,
                "key_idea": clean_text(source.get("key_idea")) or "Schema nu a furnizat ideea-cheie.",
                "explanation": clean_text(source.get("explanation")) or "Prima variantă Qwen nu a furnizat această explicație.",
                "evidence_node_ids": [str(value) for value in _as_list(source.get("evidence_node_ids"))],
            }
        )
    return {
        "id": element["id"],
        "title": clean_text(payload.get("title")) or element["title"],
        "central_idea": clean_text(payload.get("central_idea")) or "Prima variantă Qwen nu a furnizat ideea centrală.",
        "branches": normalized_branches,
        "essay_paragraph": clean_text(payload.get("essay_paragraph")),
        "memory_formula": [clean_text(value) for value in _as_list(payload.get("memory_formula")) if clean_text(value)],
        "validation": validation,
    }


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def output_path_for(work_id: str) -> Path:
    return (
        ROOT_DIR
        / "data"
        / "generated_works"
        / work_id
        / "intelegere-opera"
        / "elemente-compozitionale.json"
    )


def _find_cached_element(
    output_dir: Path,
    element: dict,
    packet: dict,
    prompt: str,
    *,
    model: str,
    reasoning: str,
) -> dict[str, Any] | None:
    runs_dir = output_dir / "qwen-composition-runs"
    if not runs_dir.is_dir():
        return None
    for previous_run in sorted(runs_dir.glob("run-*"), reverse=True):
        previous_dir = previous_run / element["id"]
        packet_path = previous_dir / "packet.json"
        prompt_path = previous_dir / "prompt.txt"
        request_path = previous_dir / "request.json"
        response_path = previous_dir / "response.openrouter.json"
        raw_path = previous_dir / "response.raw.txt"
        if not all(
            path.is_file()
            for path in (packet_path, prompt_path, request_path, response_path, raw_path)
        ):
            continue
        try:
            cached_packet = read_json(packet_path)
            cached_prompt = prompt_path.read_text(encoding="utf-8").rstrip("\n")
            request = read_json(request_path)
            content = raw_path.read_text(encoding="utf-8").strip()
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        request_reasoning = request.get("reasoning") if isinstance(request.get("reasoning"), dict) else {}
        if (
            cached_packet != packet
            or cached_prompt != prompt
            or str(request.get("model") or "") != model
            or str(request_reasoning.get("effort") or "none") != reasoning
        ):
            continue
        parsed = _extract_json(content)
        validation = validate_schema(parsed, packet)
        return {
            "source_element_dir": previous_dir,
            "source_response": response_path,
            "content": content,
            "parsed": parsed,
            "validation": validation,
            "normalized": _normalized_schema(parsed, element, validation),
        }
    return None


def generate_composition_schemas(
    graph_path: Path,
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
    model_id: str = DEFAULT_MODEL,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
    timeout: int = 1200,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    dry_run: bool = False,
) -> tuple[dict, Path]:
    graph = read_json(graph_path)
    work = graph_work_metadata(graph)
    output_path = output_path_for(work["work_id"])
    run_dir = output_path.parent / "qwen-composition-runs" / f"run-{_utc_stamp()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    packets = [(element, build_packet(graph, element, graph_path)) for element in ELEMENTS]
    for element, packet in packets:
        element_dir = run_dir / element["id"]
        element_dir.mkdir(parents=True, exist_ok=False)
        write_json(element_dir / "packet.json", packet)
        (element_dir / "prompt.txt").write_text(render_prompt(packet) + "\n", encoding="utf-8")

    if dry_run:
        manifest = {
            "schema_version": 1,
            "work": work,
            "model": model_id,
            "reasoning_effort": reasoning_effort,
            "dry_run": True,
            "run_dir": str(run_dir),
            "elements": [],
        }
        write_json(run_dir / "manifest.json", manifest)
        return manifest, run_dir / "manifest.json"

    runner = _load_runner()
    config = runner.load_local_env(config_path)
    config_used = config_path
    if not config.get("OPENROUTER_API_KEY") and config_path == DEFAULT_CONFIG_PATH:
        legacy = runner.load_local_env(LEGACY_CONFIG_PATH)
        if legacy.get("OPENROUTER_API_KEY"):
            config = {**legacy, **config}
            config_used = LEGACY_CONFIG_PATH
    api_key = config.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError(f"OPENROUTER_API_KEY lipsește din {config_used}.")
    configured_model = model_id
    model_info = runner.get_model_info(api_key, configured_model, timeout)
    results = []
    raw_results = []
    reused_elements = []
    for position, (element, packet) in enumerate(packets, start=1):
        element_dir = run_dir / element["id"]
        prompt = render_prompt(packet)
        cached = _find_cached_element(
            output_path.parent,
            element,
            packet,
            prompt,
            model=configured_model,
            reasoning=reasoning_effort,
        )
        if cached is not None:
            print(f"[{position}/3] {element['title']} - reutilizat local")
            reuse_record = {
                "reused": True,
                "source_element_dir": str(cached["source_element_dir"]),
                "source_response": str(cached["source_response"]),
                "new_api_call": False,
            }
            write_json(element_dir / "reuse.json", reuse_record)
            (element_dir / "response.raw.reused.txt").write_text(
                str(cached["content"]) + "\n", encoding="utf-8"
            )
            if cached["parsed"] is not None:
                write_json(element_dir / "result.json", cached["parsed"])
            write_json(element_dir / "validation.json", cached["validation"])
            results.append(cached["normalized"])
            raw_results.append(
                {
                    "element_id": element["id"],
                    "validation": cached["validation"],
                    "applied_parameters": {},
                    "usage": {},
                    **reuse_record,
                }
            )
            reused_elements.append(element["id"])
            continue
        request, applied = runner.build_request(
            configured_model,
            model_info,
            prompt,
            max_tokens=max_tokens,
            reasoning_effort=reasoning_effort,
            allow_provider_fallbacks=True,
            provider_order=None,
        )
        write_json(element_dir / "request.json", request)
        print(f"[{position}/3] Generez {element['title']} cu {configured_model}, reasoning={reasoning_effort}...")
        response = runner.api_json(
            f"{runner.OPENROUTER_BASE_URL}/chat/completions",
            api_key,
            method="POST",
            payload=request,
            timeout=timeout,
        )
        write_json(element_dir / "response.openrouter.json", response)
        runner.verify_returned_model(configured_model, model_info, response)
        try:
            content = runner.extract_content(response)
        except ValueError:
            choices = response.get("choices") or []
            first_choice = choices[0] if choices and isinstance(choices[0], dict) else {}
            finish_reason = first_choice.get("finish_reason") or first_choice.get(
                "native_finish_reason"
            )
            if finish_reason != "length":
                raise
            content = ""
        (element_dir / "response.raw.txt").write_text(content + "\n", encoding="utf-8")
        parsed = _extract_json(content)
        if parsed is not None:
            write_json(element_dir / "result.json", parsed)
        validation = validate_schema(parsed, packet)
        write_json(element_dir / "validation.json", validation)
        normalized = _normalized_schema(parsed, element, validation)
        results.append(normalized)
        raw_results.append(
            {
                "element_id": element["id"],
                "validation": validation,
                "applied_parameters": applied,
                "usage": response.get("usage") or {},
            }
        )

    payload = {
        "schema_version": 1,
        "work": work,
        "generation": {
            "model": configured_model,
            "reasoning_effort": reasoning_effort,
            "attempts_per_element": 1,
            "retry_on_invalid": False,
            "api_calls": sum(bool(item.get("usage")) for item in raw_results),
            "reused_element_count": len(reused_elements),
            "reused_element_ids": reused_elements,
            "source_graph": str(graph_path),
            "run_dir": str(run_dir),
        },
        "elements": results,
        "diagnostics": raw_results,
    }
    write_json(output_path, payload)
    write_json(run_dir / "manifest.json", payload)
    return payload, output_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--reasoning-effort",
        choices=("none", "minimal", "low", "medium", "high", "xhigh", "max"),
        default=DEFAULT_REASONING_EFFORT,
    )
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    payload, path = generate_composition_schemas(
        args.graph.resolve(),
        config_path=args.config.resolve(),
        model_id=args.model,
        reasoning_effort=args.reasoning_effort,
        timeout=args.timeout,
        max_tokens=args.max_tokens,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        print(f"Packeturile au fost pregătite fără apeluri API: {path}")
    else:
        valid = sum(bool(element["validation"]["valid"]) for element in payload["elements"])
        print(f"Scheme generate: {len(payload['elements'])}; validate local: {valid}/3.")
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
