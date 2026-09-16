"""Construiește integral o operă în aplicație pornind de la un singur knowledge graph.

Graful poate avea un nume precum „graf-opera curenta.json”. Titlul, autorul, ID-ul
operei și calea eseului-model sunt citite din conținutul grafului, nu din numele
fișierului. Sunt rulate, în ordine, cele trei pipeline-uri: Înțelege opera, Testare
rapidă și Construiește eseul. Opera este înregistrată în aplicație numai după ce toate
cele trei secțiuni sunt pregătite.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_essay_builder import generate_essay_blueprint
from build_quick_testing import main as quick_testing_main
from build_understanding import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_MODEL,
    DEFAULT_REASONING,
    _chapters,
    build_understanding_project,
)
from cost_reporting import (
    build_cost_report,
    combine_cost_summaries,
    empty_cost_summary,
    response_paths_by_section,
    section_costs_from_responses,
    summarize_openrouter_responses,
    summarize_usages,
)
from exercise_builder_common import ROOT_DIR, graph_work_metadata, read_json, write_json


DEFAULT_BATCHES = 4


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_declared_source(
    graph: dict,
    graph_path: Path,
    source_type: str,
) -> Path | None:
    for source in graph.get("sources", []):
        if not isinstance(source, dict) or str(source.get("source_type") or "") != source_type:
            continue
        raw = Path(str(source.get("path") or ""))
        if not str(raw):
            continue
        candidates = [raw] if raw.is_absolute() else [ROOT_DIR / raw, graph_path.parent / raw]
        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve()
    return None


def resolve_model_essay(
    graph: dict,
    graph_path: Path,
    explicit_path: Path | None = None,
) -> Path:
    if explicit_path is not None:
        resolved = explicit_path.resolve()
        if not resolved.is_file():
            raise ValueError(f"Eseul-model nu există: {resolved}")
        return resolved
    resolved = _resolve_declared_source(graph, graph_path, "model_essay")
    if resolved is None:
        raise ValueError(
            "Graful trebuie să conțină în sources o intrare cu "
            "source_type='model_essay' și o cale validă."
        )
    return resolved


def _infer_work_type(graph: dict) -> str:
    metadata = graph.get("metadata") if isinstance(graph.get("metadata"), dict) else {}
    for key in ("work_type", "literary_form", "genre", "species", "type"):
        value = str(metadata.get(key) or "").strip()
        if value:
            return value.casefold()
    work_node = next(
        (
            node
            for node in graph.get("nodes", [])
            if isinstance(node, dict) and node.get("type") == "Work"
        ),
        {},
    )
    attributes = work_node.get("attributes") if isinstance(work_node.get("attributes"), dict) else {}
    for key in ("work_type", "literary_form", "genre", "species"):
        value = str(attributes.get(key) or "").strip()
        if value:
            return value.casefold()
    return "operă literară"


def _default_icon(work_type: str) -> str:
    normalized = work_type.casefold()
    if any(value in normalized for value in ("poe", "liric", "poem")):
        return "📜"
    if any(value in normalized for value in ("dram", "comed", "traged")):
        return "🎭"
    if "roman" in normalized:
        return "📖"
    if any(value in normalized for value in ("nuvel", "basm", "povest")):
        return "📘"
    return "📚"


def register_work(
    graph: dict,
    *,
    category: str = "my",
    icon: str | None = None,
    works_path: Path | None = None,
) -> tuple[dict, bool]:
    works_path = works_path or ROOT_DIR / "data" / "works.json"
    work = graph_work_metadata(graph)
    work_type = _infer_work_type(graph)
    works = []
    if works_path.is_file():
        loaded = json.loads(works_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, list):
            raise ValueError(f"Registrul {works_path} nu conține o listă.")
        works = [dict(item) for item in loaded if isinstance(item, dict)]
    existing = next((item for item in works if str(item.get("id")) == work["work_id"]), None)
    registered_type = (
        str(existing.get("type"))
        if existing and existing.get("type") and work_type == "operă literară"
        else work_type
    )
    if any(token in registered_type.casefold() for token in ("poezie", "poem", "liric")):
        registered_type = "poezie"
    entry = {
        "id": work["work_id"],
        "title": work["title"],
        "author": work["author"],
        "type": registered_type,
        "icon": icon or (str(existing.get("icon")) if existing and existing.get("icon") else _default_icon(registered_type)),
        "category": str(existing.get("category")) if existing and existing.get("category") else category,
    }
    changed = existing != entry
    if existing is None:
        works.append(entry)
    else:
        works[works.index(existing)] = entry
    if changed:
        write_json(works_path, works)
    return entry, changed


def _manifest_status(path: Path, expected: set[str]) -> bool:
    if not path.is_file():
        return False
    try:
        payload = read_json(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    return str(payload.get("status") or "") in expected


def _copy_canonical_graph(
    source_path: Path,
    canonical_path: Path,
    *,
    force: bool,
) -> None:
    if canonical_path.is_file() and _sha256(canonical_path) != _sha256(source_path) and not force:
        raise ValueError(
            "Proiectul conține deja un alt knowledge graph pentru aceeași operă. "
            "Folosește --force numai dacă vrei să regenerezi proiectul cu noul graf."
        )
    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    if not canonical_path.is_file() or _sha256(canonical_path) != _sha256(source_path):
        shutil.copyfile(source_path, canonical_path)


def _promote_poetry_staging(staging_root: Path, work_id: str) -> None:
    """Publică numai bundle-ul liric deja validat din zona de staging."""
    directory_pairs = [
        (
            staging_root / "data" / "generated_works" / work_id / "intelegere-opera",
            ROOT_DIR / "data" / "generated_works" / work_id / "intelegere-opera",
        ),
        (
            staging_root / "data" / "generated_works" / work_id / "construieste-eseu",
            ROOT_DIR / "data" / "generated_works" / work_id / "construieste-eseu",
        ),
        (
            staging_root / "data" / "exercises" / work_id,
            ROOT_DIR / "data" / "exercises" / work_id,
        ),
        (
            staging_root / "data" / "sources" / work_id,
            ROOT_DIR / "data" / "sources" / work_id,
        ),
    ]
    for source, target in directory_pairs:
        if not source.is_dir():
            raise ValueError(f"Directorul validat lipsește din staging: {source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target, dirs_exist_ok=True)
    flashcard_source = staging_root / "data" / "flashcards" / f"{work_id}.json"
    flashcard_target = ROOT_DIR / "data" / "flashcards" / f"{work_id}.json"
    if not flashcard_source.is_file():
        raise ValueError(f"Banca validată de flashcarduri lipsește: {flashcard_source}")
    flashcard_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(flashcard_source, flashcard_target)


def _run_quick_testing(
    graph_path: Path,
    *,
    config_path: Path,
    model: str,
    reasoning: str,
    batches: int,
    timeout: int,
) -> dict[str, int | float]:
    graph = read_json(graph_path)
    work = graph_work_metadata(graph)
    runs_dir = (
        ROOT_DIR
        / "data"
        / "generated_works"
        / work["work_id"]
        / "testare-rapida"
        / "runs"
    )
    before = {
        path.resolve()
        for path in runs_dir.glob("**/response.openrouter.json")
        if path.is_file()
    }
    argv = [
        "--graph", str(graph_path),
        "--config", str(config_path),
        "--model", model,
        "--batches", str(batches),
        "--reasoning-effort", reasoning,
        "--timeout", str(timeout),
    ]
    try:
        exit_code = quick_testing_main(argv)
    except SystemExit as error:
        raise RuntimeError(f"Pipeline-ul Testare rapidă s-a oprit cu codul {error.code}.") from error
    if exit_code != 0:
        raise RuntimeError(f"Pipeline-ul Testare rapidă a returnat codul {exit_code}.")
    after = {
        path.resolve()
        for path in runs_dir.glob("**/response.openrouter.json")
        if path.is_file()
    }
    return summarize_openrouter_responses(after - before)


def build_complete_work(
    graph_path: Path,
    *,
    model_essay_path: Path | None = None,
    config_path: Path = DEFAULT_CONFIG_PATH,
    model: str = DEFAULT_MODEL,
    reasoning: str = DEFAULT_REASONING,
    batches: int = DEFAULT_BATCHES,
    timeout: int = 1200,
    category: str = "my",
    icon: str | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> tuple[dict, Path]:
    source_graph_path = graph_path.resolve()
    graph = read_json(source_graph_path)
    work = graph_work_metadata(graph)
    model_essay = resolve_model_essay(graph, source_graph_path, model_essay_path)
    work_type = _infer_work_type(graph)
    work_dir = ROOT_DIR / "data" / "generated_works" / work["work_id"]
    output_path = work_dir / "manifest.json"

    if any(token in work_type.casefold() for token in ("poezie", "poem", "liric")):
        run_dir = work_dir / "pipeline-total" / "runs" / f"run-{_stamp()}"
        run_dir.mkdir(parents=True, exist_ok=False)
        canonical_graph_path = work_dir / "knowledge-graph.json"
        cost_report_path = work_dir / "cost-report.json"
        manifest: dict[str, Any] = {
            "schema_version": 1,
            "generator_schema_version": 2,
            "pipeline": "opera-completa",
            "status": "planned" if dry_run else "running",
            "work": work,
            "work_type": "poezie",
            "input": {
                "knowledge_graph": str(source_graph_path),
                "knowledge_graph_sha256": _sha256(source_graph_path),
                "model_essay": str(model_essay),
                "model_essay_sha256": _sha256(model_essay),
            },
            "canonical_graph": str(canonical_graph_path),
            "model": model,
            "reasoning_effort": reasoning,
            "qwen_calls": 6,
            "executed_qwen_calls": 0,
            "force": force,
            "registered_in_app": False,
            "steps": [
                {"id": "intelegere-opera", "status": "planned", "qwen_calls": 1},
                {"id": "testare-rapida", "status": "planned", "qwen_calls": 5},
                {"id": "construieste-eseu", "status": "planned", "qwen_calls": 0},
                {"id": "validate-and-publish", "status": "planned", "qwen_calls": 0},
                {"id": "register-work", "status": "planned", "qwen_calls": 0},
            ],
            "run_dir": str(run_dir),
            "cost_report": str(cost_report_path),
        }
        if dry_run:
            write_json(run_dir / "manifest.json", manifest)
            return manifest, run_dir / "manifest.json"
        from services.work_artifact_validation_service import validate_poetry_artifacts

        if output_path.is_file() and not force:
            previous_manifest = read_json(output_path)
            if (
                previous_manifest.get("status") == "ready"
                and previous_manifest.get("generator_schema_version") == 2
                and str((previous_manifest.get("input") or {}).get("knowledge_graph_sha256") or "")
                == _sha256(source_graph_path)
                and str((previous_manifest.get("input") or {}).get("model_essay_sha256") or "")
                == _sha256(model_essay)
            ):
                previous_manifest["latest_invocation"] = {
                    "status": "skipped_already_ready",
                    "run_dir": str(run_dir),
                }
                write_json(run_dir / "manifest.json", previous_manifest)
                return previous_manifest, output_path

        if not output_path.is_file() and not force:
            try:
                validation_report = validate_poetry_artifacts(ROOT_DIR, work["work_id"], graph)
            except (OSError, ValueError, json.JSONDecodeError):
                validation_report = None
            if validation_report is not None:
                _copy_canonical_graph(source_graph_path, canonical_graph_path, force=False)
                write_json(run_dir / "validation-report.json", validation_report)
                registry_entry, registry_changed = register_work(
                    graph,
                    category=category,
                    icon=icon,
                    works_path=ROOT_DIR / "data" / "works.json",
                )
                zero_costs = {
                    section_id: empty_cost_summary()
                    for section_id in ("intelegere-opera", "testare-rapida", "construieste-eseu")
                }
                cost_report = build_cost_report(
                    work=work,
                    total_run_dir=run_dir,
                    current_by_section=zero_costs,
                    previous_report=(read_json(cost_report_path) if cost_report_path.is_file() else None),
                )
                write_json(cost_report_path, cost_report)
                manifest.update(
                    {
                        "status": "ready",
                        "registered_in_app": True,
                        "registry_entry": registry_entry,
                        "adopted_existing_artifacts": True,
                        "steps": [
                            {"id": section_id, "status": "adopted_existing_validated"}
                            for section_id in ("intelegere-opera", "testare-rapida", "construieste-eseu")
                        ]
                        + [
                            {"id": "validate-and-publish", "status": "complete", "report": str(run_dir / "validation-report.json")},
                            {"id": "register-work", "status": "complete", "changed": registry_changed},
                        ],
                        "costs": {
                            "currency": "USD",
                            "latest_run": cost_report["latest_total_run"]["total"],
                            "work_lifetime": cost_report["lifetime"]["total"],
                            "report": str(cost_report_path),
                        },
                    }
                )
                write_json(output_path, manifest)
                write_json(run_dir / "manifest.json", manifest)
                return manifest, output_path

        from creeaza_opera_poezie import generate_poetic_work_complete

        staging_root = run_dir / "staging"
        previous_cost_report = read_json(cost_report_path) if cost_report_path.is_file() else None
        try:
            _copy_canonical_graph(source_graph_path, canonical_graph_path, force=force)
            result = generate_poetic_work_complete(
                canonical_graph_path,
                model_essay,
                config_path=config_path,
                model=model,
                reasoning_effort=reasoning,
                category=category,
                icon=icon or "🌸",
                output_root=staging_root,
                register_work_entry=False,
            )
            validation_report = validate_poetry_artifacts(staging_root, work["work_id"], graph)
            write_json(run_dir / "validation-report.json", validation_report)
            _promote_poetry_staging(staging_root, work["work_id"])
            registry_entry, registry_changed = register_work(
                graph,
                category=category,
                icon=icon,
                works_path=ROOT_DIR / "data" / "works.json",
            )
            current_by_section = result.get("usage_by_section") or {}
            cost_report = build_cost_report(
                work=work,
                total_run_dir=run_dir,
                current_by_section=current_by_section,
                previous_report=previous_cost_report,
            )
            write_json(cost_report_path, cost_report)
            manifest.update(
                {
                    "status": "ready",
                    "registered_in_app": True,
                    "registry_entry": registry_entry,
                    "executed_qwen_calls": int((result.get("usage") or {}).get("api_calls") or 0),
                    "steps": [
                        {"id": section_id, "status": "complete", "usage": usage}
                        for section_id, usage in current_by_section.items()
                    ]
                    + [
                        {"id": "validate-and-publish", "status": "complete", "report": str(run_dir / "validation-report.json")},
                        {"id": "register-work", "status": "complete", "changed": registry_changed},
                    ],
                    "costs": {
                        "currency": "USD",
                        "latest_run": cost_report["latest_total_run"]["total"],
                        "work_lifetime": cost_report["lifetime"]["total"],
                        "report": str(cost_report_path),
                    },
                }
            )
        except Exception as error:
            manifest.update({"status": "failed", "error": str(error)})
            write_json(run_dir / "manifest.json", manifest)
            raise
        write_json(output_path, manifest)
        write_json(run_dir / "manifest.json", manifest)
        return manifest, output_path

    chapter_count = len(_chapters(graph))
    if output_path.is_file() and not force:
        previous_manifest = read_json(output_path)
        previous_input = previous_manifest.get("input") if isinstance(previous_manifest.get("input"), dict) else {}
        previous_model_hash = str(previous_input.get("model_essay_sha256") or "")
        if previous_model_hash and previous_model_hash != _sha256(model_essay):
            raise ValueError(
                "Eseul-model s-a schimbat față de proiectul deja construit. "
                "Folosește --force pentru regenerare."
            )
    run_dir = work_dir / "pipeline-total" / "runs" / f"run-{_stamp()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    canonical_graph_path = work_dir / "knowledge-graph.json"
    cost_report_path = work_dir / "cost-report.json"
    previous_cost_report = read_json(cost_report_path) if cost_report_path.is_file() else None
    response_paths_before = response_paths_by_section(work_dir)
    total_qwen_calls = chapter_count + 5 + (batches * 8) + 1
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "pipeline": "opera-completa",
        "status": "planned" if dry_run else "running",
        "work": work,
        "input": {
            "knowledge_graph": str(source_graph_path),
            "knowledge_graph_sha256": _sha256(source_graph_path),
            "model_essay": str(model_essay),
            "model_essay_sha256": _sha256(model_essay),
        },
        "canonical_graph": str(canonical_graph_path),
        "model": model,
        "reasoning_effort": reasoning,
        "quick_testing_batches": batches,
        "planned_questions": batches * 24,
        "qwen_calls": total_qwen_calls,
        "executed_qwen_calls": 0,
        "retry_on_invalid": False,
        "force": force,
        "registered_in_app": False,
        "steps": [],
        "run_dir": str(run_dir),
        "cost_report": str(cost_report_path),
    }
    if dry_run:
        manifest["steps"] = [
            {"id": "intelegere-opera", "status": "planned", "qwen_calls": chapter_count + 5},
            {"id": "testare-rapida", "status": "planned", "qwen_calls": batches * 8},
            {"id": "construieste-eseu", "status": "planned", "qwen_calls": 1},
            {"id": "register-work", "status": "planned", "qwen_calls": 0},
        ]
        write_json(run_dir / "manifest.json", manifest)
        return manifest, run_dir / "manifest.json"

    _copy_canonical_graph(source_graph_path, canonical_graph_path, force=force)
    step_specs = [
        (
            "intelegere-opera",
            work_dir / "intelegere-opera" / "manifest.json",
            {"ready"},
        ),
        (
            "testare-rapida",
            work_dir / "testare-rapida" / "manifest.json",
            {"complete"},
        ),
        (
            "construieste-eseu",
            work_dir / "construieste-eseu" / "manifest.json",
            {"ready"},
        ),
    ]
    step_qwen_calls = {
        "intelegere-opera": chapter_count + 5,
        "testare-rapida": batches * 8,
        "construieste-eseu": 1,
    }
    current_costs: dict[str, dict[str, int | float]] = {
        step_id: empty_cost_summary() for step_id in step_qwen_calls
    }
    try:
        for step_id, step_manifest, ready_statuses in step_specs:
            if not force and _manifest_status(step_manifest, ready_statuses):
                manifest["steps"].append(
                    {"id": step_id, "status": "skipped_already_ready", "manifest": str(step_manifest)}
                )
                continue
            if step_id == "intelegere-opera":
                understanding_manifest, produced_path = build_understanding_project(
                    canonical_graph_path,
                    model_essay_path=model_essay,
                    config_path=config_path,
                    model=model,
                    reasoning=reasoning,
                    timeout=timeout,
                )
                current_costs[step_id] = dict(
                    understanding_manifest.get("cost_summary") or empty_cost_summary()
                )
            elif step_id == "testare-rapida":
                quick_cost = _run_quick_testing(
                    canonical_graph_path,
                    config_path=config_path,
                    model=model,
                    reasoning=reasoning,
                    batches=batches,
                    timeout=timeout,
                )
                current_costs[step_id] = dict(quick_cost or empty_cost_summary())
                produced_path = step_manifest
            else:
                blueprint, produced_path = generate_essay_blueprint(
                    canonical_graph_path,
                    model_essay,
                    config_path=config_path,
                    model=model,
                    reasoning=reasoning,
                    timeout=timeout,
                )
                essay_generation = blueprint.get("generation", {})
                essay_usage = essay_generation.get("usage", {})
                current_costs[step_id] = (
                    summarize_usages([essay_usage])
                    if isinstance(essay_usage, dict) and bool(essay_usage)
                    else empty_cost_summary()
                )
                if not blueprint.get("validation", {}).get("valid"):
                    raise RuntimeError(
                        "Construiește eseul nu a fost publicat deoarece prima variantă "
                        "nu respectă regula strictă a trăsăturilor din eseul-model."
                    )
            manifest["steps"].append(
                {
                    "id": step_id,
                    "status": "complete",
                    "manifest": str(produced_path),
                    "executed_qwen_calls": int(current_costs[step_id].get("api_calls") or 0),
                }
            )
            manifest["executed_qwen_calls"] += int(
                current_costs[step_id].get("api_calls") or 0
            )

        works_path = ROOT_DIR / "data" / "works.json"
        registry_entry, registry_changed = register_work(
            graph,
            category=category,
            icon=icon,
            works_path=works_path,
        )
        manifest["steps"].append(
            {
                "id": "register-work",
                "status": "complete",
                "registry": str(works_path),
                "changed": registry_changed,
            }
        )
        manifest.update(
            {
                "status": "ready",
                "registered_in_app": True,
                "registry_entry": registry_entry,
                "canonical_graph_sha256": _sha256(canonical_graph_path),
                "source_graph_modified": _sha256(source_graph_path) != manifest["input"]["knowledge_graph_sha256"],
            }
        )
        response_paths_after = response_paths_by_section(work_dir)
        scanned_current_costs = section_costs_from_responses(
            {
                section_id: response_paths_after[section_id] - response_paths_before[section_id]
                for section_id in response_paths_after
            }
        )
        for section_id, scanned in scanned_current_costs.items():
            if int(scanned["api_calls"]) > 0:
                current_costs[section_id] = scanned
        scanned_lifetime_costs = section_costs_from_responses(response_paths_after)
        scanned_lifetime_total = combine_cost_summaries(scanned_lifetime_costs.values())
        cost_report = build_cost_report(
            work=work,
            total_run_dir=run_dir,
            current_by_section=current_costs,
            previous_report=previous_cost_report,
            lifetime_by_section=(
                scanned_lifetime_costs
                if int(scanned_lifetime_total["api_calls"]) > 0
                else None
            ),
        )
        write_json(cost_report_path, cost_report)
        manifest["costs"] = {
            "currency": "USD",
            "latest_run": cost_report["latest_total_run"]["total"],
            "work_lifetime": cost_report["lifetime"]["total"],
            "report": str(cost_report_path),
        }
    except Exception as error:
        manifest.update({"status": "failed", "error": str(error)})
        write_json(run_dir / "manifest.json", manifest)
        raise

    write_json(output_path, manifest)
    write_json(run_dir / "manifest.json", manifest)
    return manifest, output_path


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "graph",
        type=Path,
        help="Calea către graf, de exemplu «graf-opera curenta.json».",
    )
    parser.add_argument(
        "--model-essay",
        type=Path,
        default=None,
        help="Opțional; implicit este citit din sources[source_type=model_essay].",
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--reasoning-effort",
        choices=("none", "minimal", "low", "medium", "high", "xhigh", "max"),
        default=DEFAULT_REASONING,
    )
    parser.add_argument("--batches", type=int, default=DEFAULT_BATCHES)
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--category", choices=("my", "other"), default="my")
    parser.add_argument("--icon", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    graph_path = args.graph.resolve()
    if not graph_path.is_file():
        parser.error(f"Knowledge graph-ul nu există: {graph_path}")
    if args.batches < 1:
        parser.error("--batches trebuie să fie cel puțin 1.")
    try:
        manifest, path = build_complete_work(
            graph_path,
            model_essay_path=args.model_essay,
            config_path=args.config.resolve(),
            model=args.model,
            reasoning=args.reasoning_effort,
            batches=args.batches,
            timeout=args.timeout,
            category=args.category,
            icon=args.icon,
            force=args.force,
            dry_run=args.dry_run,
        )
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        parser.error(str(error))
    if args.dry_run:
        print(f"Plan pregătit fără apeluri API: {path}")
        print(f"Apeluri Qwen planificate: {manifest['qwen_calls']}")
        if "planned_questions" in manifest:
            print(f"Întrebări planificate: {manifest['planned_questions']}")
        return 0
    print(f"Opera „{manifest['work']['title']}” a fost construită integral și adăugată în aplicație.")
    print(
        f"Apeluri Qwen executate: {manifest['executed_qwen_calls']} "
        f"din {manifest['qwen_calls']} planificate; regenerări: 0."
    )
    costs = manifest["costs"]
    print(f"Cost rulare curentă: ${costs['latest_run']['cost_usd']:.6f} USD")
    print(f"Cost total acumulat pentru operă: ${costs['work_lifetime']['cost_usd']:.6f} USD")
    print(
        f"Tokenuri totale acumulate: {costs['work_lifetime']['total_tokens']} "
        f"(prompt: {costs['work_lifetime']['prompt_tokens']}, "
        f"răspuns: {costs['work_lifetime']['completion_tokens']}, "
        f"reasoning: {costs['work_lifetime']['reasoning_tokens']})."
    )
    print(f"Raport costuri: {costs['report']}")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
