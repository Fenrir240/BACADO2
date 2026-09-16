"""Construiește integral datele UI pentru „Construiește eseul”.

Pipeline-ul primește knowledge graph-ul și eseul-model al utilizatorului. Face un
singur apel Qwen 3.7 Flash și nu regenerează niciodată un răspuns invalid. Trăsăturile
curentului sunt o listă închisă: sunt acceptate numai trăsăturile dezvoltate explicit
în eseul-model, fiecare fiind verificată printr-un fragment-sursă din acel fișier.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import importlib.util
import json
import re
import sys
import unicodedata
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

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.composition_service import infer_composition_element_ids


QWEN_DIR = ROOT_DIR / "cercetare-qwen"
DEFAULT_CONFIG_PATH = QWEN_DIR / "config.local.env"
LEGACY_CONFIG_PATH = ROOT_DIR / "cercetare" / "experiment2" / "config.local.env"
DEFAULT_MODEL = "qwen/qwen3.7-flash"
DEFAULT_REASONING = "medium"
RELEVANT_NODE_TYPES = {
    "Work", "Author", "LiteraryMovement", "LiteraryTrait", "Theme", "Motif",
    "Symbol", "Conflict", "Event", "Chapter", "Character", "NarrativeStructure",
    "NarrativePerspective", "LiteraryTechnique", "Location",
}


def _runner() -> ModuleType:
    name = "bacapp_essay_builder_qwen_runner"
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


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _slug(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_") or "sectiune"


def _normalized_source(value: object) -> str:
    return " ".join(str(value or "").split()).casefold()


def _repair_non_trait_excerpt(item: dict, model_essay: str) -> dict[str, str] | None:
    """Înlocuiește local o parafrază aproape identică prin fragmentul-sursă exact."""
    excerpt = clean_text(item.get("source_excerpt"))
    source = _normalized_source(model_essay)
    normalized_excerpt = _normalized_source(excerpt)
    if not normalized_excerpt or normalized_excerpt in source:
        return None
    candidates = [
        clean_text(value)
        for value in re.split(r"\n\s*\n|\n", model_essay)
        if clean_text(value)
    ]
    if not candidates:
        return None
    best = max(
        candidates,
        key=lambda value: difflib.SequenceMatcher(
            None, normalized_excerpt, _normalized_source(value)
        ).ratio(),
    )
    similarity = difflib.SequenceMatcher(
        None, normalized_excerpt, _normalized_source(best)
    ).ratio()
    if similarity < 0.94:
        return None
    item["source_excerpt"] = best
    return {
        "section_id": str(item.get("id") or ""),
        "reason": "near_exact_excerpt_replaced_from_model_essay",
        "similarity": round(similarity, 4),
    }


def _find_reusable_result(project_dir: Path, packet: dict) -> Path | None:
    """Reutilizează prima variantă Qwen deja plătită pentru același pachet."""
    runs_dir = project_dir / "runs"
    if not runs_dir.is_dir():
        return None
    for run_dir in sorted(runs_dir.glob("run-*"), reverse=True):
        packet_path = run_dir / "packet.json"
        result_path = run_dir / "result.json"
        if not packet_path.is_file() or not result_path.is_file():
            continue
        try:
            same_packet = read_json(packet_path) == packet
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if same_packet:
            return result_path
    return None


def _compact_node(node: dict) -> dict:
    return {
        key: node.get(key)
        for key in (
            "id", "type", "label", "description", "importance",
            "assertion_type", "attributes", "chapter_ids",
        )
        if node.get(key) not in (None, "", [], {})
    }


def build_packet(
    graph: dict,
    graph_path: Path,
    model_essay_path: Path,
    model_essay: str,
    expected_traits: int,
) -> dict:
    nodes = [node for node in graph.get("nodes", []) if isinstance(node, dict)]
    selected = [
        node for node in nodes
        if str(node.get("type") or "") in RELEVANT_NODE_TYPES
    ]
    selected.sort(
        key=lambda node: (
            0 if node.get("type") in {"Work", "Author"} else 1,
            {"major": 0, "supporting": 1, "minor": 2}.get(
                str(node.get("importance") or ""), 3
            ),
            str(node.get("id") or ""),
        )
    )
    selected = selected[:220]
    selected_ids = {str(node.get("id") or "") for node in selected}
    edges = [
        edge for edge in graph.get("edges", [])
        if isinstance(edge, dict)
        and (
            str(edge.get("source") or "") in selected_ids
            or str(edge.get("target") or "") in selected_ids
        )
    ][:900]
    return {
        "schema_version": 1,
        "task": "build_essay_ui_blueprint",
        "work": graph_work_metadata(graph),
        "source_graph": str(graph_path),
        "source_model_essay": str(model_essay_path),
        "expected_explicit_trait_count": expected_traits,
        "model_essay": model_essay,
        "graph": {
            "metadata": graph.get("metadata", {}),
            "nodes": [_compact_node(node) for node in selected],
            "edges": edges,
        },
    }


def render_prompt(packet: dict) -> str:
    expected = int(packet["expected_explicit_trait_count"])
    return f"""
Ești profesor expert de literatură română pentru Bacalaureat. Construiește blueprint-ul
UI al secțiunii „Construiește eseul” pentru opera din pachet.

SURSE ȘI PRIORITATE:
1. ESEUL-MODEL este autoritatea absolută pentru structura eseului și pentru trăsăturile
   curentului literar care sunt considerate corecte.
2. KNOWLEDGE GRAPH-ul este folosit pentru verificarea faptelor și pentru formularea
   explicațiilor despre operă.

REGULA STRICTĂ A TRĂSĂTURILOR:
- extrage exact {expected} trăsături ale curentului;
- alege NUMAI trăsăturile dezvoltate în paragrafe argumentative distincte în eseul-model;
- nu alege trăsături doar enumerate în definiția introductivă a curentului;
- nu înlocui, nu generaliza și nu adăuga trăsături din cunoștințele tale sau din graf;
- pentru fiecare trăsătură, `source_excerpt` trebuie să fie un fragment CONTIGUU,
  copiat exact din eseul-model, care dovedește că acea trăsătură este abordată;
- orice altă trăsătură va fi considerată incorectă la evaluarea elevului.

REGULI PENTRU RESTUL SCHEMEI:
- extrage tema exact așa cum este abordată în eseul-model;
- extrage exact două secvențe relevante analizate în eseul-model;
- indicațiile pentru secvențe trebuie să numească scena și capitolul, dacă apar în sursă;
- introducerea trebuie să aibă un checklist factual pentru operă și autor;
- concluzia trebuie să reflecte exact direcția eseului-model;
- nu inventa citate;
- răspunde exclusiv cu un obiect JSON valid, fără markdown.

SCHEMA JSON:
{{
  "movement": {{"name": "curentul literar"}},
  "introduction": {{
    "title": "Introducere",
    "instructions": "indicație completă pentru elev",
    "checklist": ["cerință concretă"]
  }},
  "traits": [
    {{
      "title": "denumirea exactă a trăsăturii dezvoltate",
      "source_excerpt": "fragment contiguu copiat exact din eseul-model",
      "instructions": "ce trebuie să demonstreze elevul",
      "model_fragment": "paragraful-model relevant, fără adaosuri"
    }}
  ],
  "theme": {{
    "title": "tema exactă",
    "source_excerpt": "fragment contiguu din eseul-model",
    "instructions": "indicație pentru elev"
  }},
  "sequences": [
    {{
      "title": "numele scenei",
      "chapter": "capitolul sau gol",
      "source_excerpt": "fragment contiguu din eseul-model",
      "instructions": "analiza cerută elevului"
    }}
  ],
  "conclusion": {{
    "title": "Concluzie",
    "source_excerpt": "fragment contiguu din concluzia eseului-model",
    "instructions": "indicație pentru elev"
  }}
}}

PACHET:
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


def _normalize_blueprint(
    raw_payload: dict | None,
    *,
    work: dict,
    graph_path: Path,
    model_essay_path: Path,
    model_essay: str,
    expected_traits: int,
    generation: dict,
) -> dict:
    raw = raw_payload if isinstance(raw_payload, dict) else {}
    raw_movement = raw.get("movement") if isinstance(raw.get("movement"), dict) else {}
    movement_name = clean_text(raw_movement.get("name"))

    raw_traits = raw.get("traits") if isinstance(raw.get("traits"), list) else []
    traits = []
    for index, item in enumerate(raw_traits, start=1):
        if not isinstance(item, dict):
            continue
        title = clean_text(item.get("title")) or f"Trăsătura {index}"
        traits.append(
            {
                "id": f"trasatura_{index}",
                "kind": "literary_trait",
                "title": title,
                "source_excerpt": clean_text(item.get("source_excerpt")),
                "instructions": clean_text(item.get("instructions")),
                "model_fragment": clean_text(item.get("model_fragment")),
            }
        )

    raw_intro = raw.get("introduction") if isinstance(raw.get("introduction"), dict) else {}
    introduction = {
        "id": "introducere",
        "kind": "introduction",
        "title": clean_text(raw_intro.get("title")) or "Introducere",
        "instructions": clean_text(raw_intro.get("instructions")),
        "checklist": [
            clean_text(value) for value in raw_intro.get("checklist", [])
            if clean_text(value)
        ] if isinstance(raw_intro.get("checklist"), list) else [],
    }

    raw_theme = raw.get("theme") if isinstance(raw.get("theme"), dict) else {}
    theme = {
        "id": "tema",
        "kind": "theme",
        "title": clean_text(raw_theme.get("title")) or "Tema operei",
        "source_excerpt": clean_text(raw_theme.get("source_excerpt")),
        "instructions": clean_text(raw_theme.get("instructions")),
    }

    raw_sequences = raw.get("sequences") if isinstance(raw.get("sequences"), list) else []
    sequences = []
    for index, item in enumerate(raw_sequences, start=1):
        if not isinstance(item, dict):
            continue
        title = clean_text(item.get("title")) or f"Secvența {index}"
        sequences.append(
            {
                "id": f"secventa_{index}",
                "kind": "sequence",
                "title": title,
                "chapter": clean_text(item.get("chapter")),
                "source_excerpt": clean_text(item.get("source_excerpt")),
                "instructions": clean_text(item.get("instructions")),
            }
        )

    raw_conclusion = raw.get("conclusion") if isinstance(raw.get("conclusion"), dict) else {}
    conclusion = {
        "id": "concluzie",
        "kind": "conclusion",
        "title": clean_text(raw_conclusion.get("title")) or "Concluzie",
        "source_excerpt": clean_text(raw_conclusion.get("source_excerpt")),
        "instructions": clean_text(raw_conclusion.get("instructions")),
    }

    composition_sections = [
        {
            "id": "element_incipit_final",
            "kind": "composition",
            "title": "Relația incipit–final",
            "instructions": "Prezintă relația dintre incipit și final pe baza schemei studiate.",
        },
        {
            "id": "element_conflict",
            "kind": "composition",
            "title": "Conflictul",
            "instructions": "Prezintă conflictul pe baza schemei studiate.",
        },
        {
            "id": "element_title",
            "kind": "composition",
            "title": "Titlul",
            "instructions": "Prezintă semnificația titlului pe baza schemei studiate.",
        },
    ]
    local_source_repairs = []
    for item in [theme, *sequences, conclusion]:
        repair = _repair_non_trait_excerpt(item, model_essay)
        if repair:
            local_source_repairs.append(repair)
    sections = [introduction, *traits, theme, *sequences, *composition_sections, conclusion]

    errors = []
    source = _normalized_source(model_essay)
    if len(traits) != expected_traits:
        errors.append(
            f"Au fost extrase {len(traits)} trăsături, dar sunt obligatorii exact {expected_traits}."
        )
    if len(sequences) != 2:
        errors.append(f"Au fost extrase {len(sequences)} secvențe, dar sunt obligatorii exact 2.")
    if not movement_name:
        errors.append("Curentul literar lipsește.")
    for label, item in [
        *(('trăsătura', value) for value in traits),
        ("tema", theme),
        *(('secvența', value) for value in sequences),
        ("concluzia", conclusion),
    ]:
        excerpt = _normalized_source(item.get("source_excerpt"))
        if not excerpt or excerpt not in source:
            errors.append(
                f"Fragmentul-sursă pentru {label} «{item.get('title', '')}» nu există în eseul-model."
            )
    for trait in traits:
        normalized_title = _normalized_source(trait["title"])
        normalized_excerpt = _normalized_source(trait["source_excerpt"])
        if normalized_title not in normalized_excerpt:
            errors.append(
                "Denumirea trăsăturii "
                f"«{trait['title']}» nu apare exact în fragmentul-sursă oferit."
            )
        model_fragment = _normalized_source(trait["model_fragment"])
        if not model_fragment or model_fragment not in source:
            errors.append(
                "Fragmentul-model pentru trăsătura "
                f"«{trait['title']}» nu este un fragment contiguu din eseul-model."
            )
    if not introduction["instructions"] or not introduction["checklist"]:
        errors.append("Introducerea nu are instrucțiuni și checklist complet.")
    if any(not item["instructions"] for item in [*traits, theme, *sequences, conclusion]):
        errors.append("Cel puțin o secțiune nu are instrucțiuni pentru elev.")
    trait_titles = [_normalized_source(item["title"]) for item in traits]
    if len(set(trait_titles)) != len(trait_titles):
        errors.append("Trăsăturile extrase nu sunt distincte.")

    return {
        "schema_version": 1,
        "pipeline": "construieste-eseu",
        "work": work,
        "source": {
            "knowledge_graph": str(graph_path),
            "model_essay": str(model_essay_path),
            "model_essay_sha256": hashlib.sha256(model_essay.encode("utf-8")).hexdigest(),
        },
        "generation": generation,
        "default_composition_element_ids": infer_composition_element_ids(model_essay),
        "strict_trait_policy": {
            "mode": "model_essay_only",
            "expected_count": expected_traits,
            "reject_unlisted_traits": True,
            "accepted_trait_ids": [item["id"] for item in traits],
            "accepted_trait_titles": [item["title"] for item in traits],
            "rule": (
                "Sunt corecte exclusiv trăsăturile dezvoltate explicit în eseul-model; "
                "orice altă trăsătură este evaluată ca incorectă."
            ),
        },
        "movement": {"name": movement_name},
        "mindmap": {
            "movement_name": movement_name,
            "traits": [{"id": item["id"], "title": item["title"]} for item in traits],
            "theme": {"id": theme["id"], "title": theme["title"]},
            "sequences": [
                {"id": item["id"], "title": item["title"], "chapter": item["chapter"]}
                for item in sequences
            ],
        },
        "sections": sections,
        "validation": {
            "valid": not errors,
            "errors": errors,
            "trait_count": len(traits),
            "sequence_count": len(sequences),
            "source_excerpts_verified": not any("Fragmentul-sursă" in error for error in errors),
            "trait_titles_verified": not any(
                "Denumirea trăsăturii" in error for error in errors
            ),
            "trait_model_fragments_verified": not any(
                "Fragmentul-model" in error for error in errors
            ),
            "local_source_repairs": local_source_repairs,
        },
    }


def generate_essay_blueprint(
    graph_path: Path,
    model_essay_path: Path,
    *,
    expected_traits: int = 2,
    config_path: Path = DEFAULT_CONFIG_PATH,
    model: str = DEFAULT_MODEL,
    reasoning: str = DEFAULT_REASONING,
    timeout: int = 1200,
    max_tokens: int = 9000,
    dry_run: bool = False,
    input_result: Path | None = None,
) -> tuple[dict, Path]:
    if expected_traits != 2:
        raise ValueError(
            "Schema actuală de Bac folosește exact două trăsături; "
            "--expected-traits trebuie să fie 2."
        )
    graph = read_json(graph_path)
    work = graph_work_metadata(graph)
    model_essay = model_essay_path.read_text(encoding="utf-8").strip()
    if not model_essay:
        raise ValueError("Eseul-model este gol.")
    project_dir = ROOT_DIR / "data" / "generated_works" / work["work_id"] / "construieste-eseu"
    packet = build_packet(
        graph, graph_path, model_essay_path, model_essay, expected_traits
    )
    reusable_result = (
        _find_reusable_result(project_dir, packet) if input_result is None else None
    )
    run_dir = project_dir / "runs" / f"run-{_stamp()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    prompt = render_prompt(packet)
    write_json(run_dir / "packet.json", packet)
    (run_dir / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")
    if dry_run:
        manifest = {
            "schema_version": 1,
            "pipeline": "construieste-eseu",
            "status": "planned",
            "work": work,
            "qwen_calls": 1,
            "retry_on_invalid": False,
            "run_dir": str(run_dir),
        }
        write_json(run_dir / "manifest.json", manifest)
        return manifest, run_dir / "manifest.json"

    response: dict = {}
    local_result = input_result or reusable_result
    if local_result is not None:
        parsed = read_json(local_result)
        raw_content = json.dumps(parsed, ensure_ascii=False)
        generation = {
            "model": "reused-result" if reusable_result else "offline-result",
            "reasoning_effort": "none",
            "attempts": 0,
            "retry_on_invalid": False,
            "run_dir": str(run_dir),
            "reused_from": str(local_result),
        }
    else:
        runner = _runner()
        config = runner.load_local_env(config_path)
        if not config.get("OPENROUTER_API_KEY"):
            config = {**runner.load_local_env(LEGACY_CONFIG_PATH), **config}
        api_key = str(config.get("OPENROUTER_API_KEY") or "")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY lipsește din configurație.")
        request = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "reasoning": {"effort": reasoning, "exclude": True},
            "provider": {
                "allow_fallbacks": True,
                "require_parameters": True,
                "data_collection": "deny",
            },
            "response_format": {"type": "json_object"},
        }
        write_json(run_dir / "request.json", request)
        response = runner.api_json(
            f"{runner.OPENROUTER_BASE_URL}/chat/completions",
            api_key,
            method="POST",
            payload=request,
            timeout=timeout,
        )
        write_json(run_dir / "response.openrouter.json", response)
        raw_content = runner.extract_content(response)
        parsed = _extract_json(raw_content)
        generation = {
            "model": model,
            "reasoning_effort": reasoning,
            "attempts": 1,
            "retry_on_invalid": False,
            "run_dir": str(run_dir),
            "usage": response.get("usage") or {},
        }

    (run_dir / "response.raw.txt").write_text(raw_content + "\n", encoding="utf-8")
    if isinstance(parsed, dict):
        write_json(run_dir / "result.json", parsed)
    blueprint = _normalize_blueprint(
        parsed,
        work=work,
        graph_path=graph_path,
        model_essay_path=model_essay_path,
        model_essay=model_essay,
        expected_traits=expected_traits,
        generation=generation,
    )
    if blueprint["validation"]["valid"]:
        canonical_model_essay_path = project_dir / "eseu-model.md"
        canonical_model_essay_path.write_text(model_essay + "\n", encoding="utf-8")
        blueprint["source"]["input_model_essay"] = blueprint["source"]["model_essay"]
        blueprint["source"]["model_essay"] = str(canonical_model_essay_path)
    write_json(run_dir / "validation.json", blueprint["validation"])
    write_json(run_dir / "manifest.json", blueprint)
    if blueprint["validation"]["valid"]:
        artifact_path = project_dir / "eseu.json"
        write_json(artifact_path, blueprint)
        write_json(
            project_dir / "manifest.json",
            {
                "schema_version": 1,
                "pipeline": "construieste-eseu",
                "status": "ready",
                "work": work,
                "artifact": str(artifact_path),
                "source": blueprint["source"],
                "strict_trait_policy": blueprint["strict_trait_policy"],
                "generation": generation,
                "validation": blueprint["validation"],
            },
        )
    return blueprint, project_dir / "eseu.json"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH)
    parser.add_argument("--model-essay", type=Path, required=True)
    parser.add_argument("--expected-traits", type=int, default=2)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--reasoning-effort",
        choices=("none", "minimal", "low", "medium", "high", "xhigh", "max"),
        default=DEFAULT_REASONING,
    )
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--max-tokens", type=int, default=9000)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--input-result",
        type=Path,
        help="Folosește un rezultat JSON local și nu apelează Qwen (pentru verificări).",
    )
    args = parser.parse_args(argv)
    if args.expected_traits != 2:
        parser.error("--expected-traits trebuie să fie 2 pentru schema actuală.")
    graph_path = args.graph.resolve()
    model_essay_path = args.model_essay.resolve()
    if not graph_path.is_file():
        parser.error(f"Graful nu există: {graph_path}")
    if not model_essay_path.is_file():
        parser.error(f"Eseul-model nu există: {model_essay_path}")
    if args.input_result and not args.input_result.resolve().is_file():
        parser.error(f"Rezultatul JSON local nu există: {args.input_result.resolve()}")
    try:
        blueprint, path = generate_essay_blueprint(
            graph_path,
            model_essay_path,
            expected_traits=args.expected_traits,
            config_path=args.config.resolve(),
            model=args.model,
            reasoning=args.reasoning_effort,
            timeout=args.timeout,
            max_tokens=args.max_tokens,
            dry_run=args.dry_run,
            input_result=args.input_result.resolve() if args.input_result else None,
        )
    except (ValueError, RuntimeError) as error:
        parser.error(str(error))
    if args.dry_run:
        print(f"Plan pregătit fără apel API: {path}")
        return 0
    validation = blueprint["validation"]
    if not validation["valid"]:
        print("Blueprint-ul NU a fost publicat: validarea strictă a eșuat.")
        for error in validation["errors"]:
            print(f"- {error}")
        print(f"Diagnosticul a rămas în: {blueprint['generation']['run_dir']}")
        return 2
    print(
        f"Construiește eseul finalizat pentru {blueprint['work']['title']}: "
        f"{validation['trait_count']} trăsături exacte și "
        f"{validation['sequence_count']} secvențe."
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
