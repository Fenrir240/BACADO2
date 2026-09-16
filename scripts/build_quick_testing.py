"""Construiește integral „Testare rapidă” pentru o operă, pornind de la knowledge graph.

Fluxul standard face patru loturi a câte opt apeluri Qwen (96 de întrebări), păstrează
istoricul evenimentelor între rulări și materializează toate contractele consumate de UI:
flashcarduri, grile, ordine cronologică, completare și asociere. Fiecare sarcină este
trimisă exact o dată; validarea locală nu declanșează niciodată regenerarea.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Sequence


ROOT_DIR = Path(__file__).resolve().parents[1]
QWEN_DIR = ROOT_DIR / "cercetare-qwen"
DEFAULT_GRAPH_PATH = ROOT_DIR / "cercetare" / "graf2" / "knowledge-graph.json"
DEFAULT_CONFIG_PATH = QWEN_DIR / "config.local.env"
DEFAULT_DATA_DIR = ROOT_DIR / "data"

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_chronology_exercises import build_chronology_bank
from build_completion_exercises import build_completion_bank
from build_flashcard_exercises import build_flashcard_deck
from build_matching_exercises import build_matching_bank
from build_multiple_choice_exercises import build_multiple_choice_bank
from exercise_builder_common import graph_work_metadata, read_json, write_json


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_local_module(name: str, path: Path) -> ModuleType:
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Nu pot încărca modulul {path}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def packet_builder() -> ModuleType:
    return load_local_module("bacapp_question_packet_builder", QWEN_DIR / "build_graph_packets.py")


def qwen_runner() -> ModuleType:
    return load_local_module("bacapp_qwen_runner", QWEN_DIR / "run_qwen_packets.py")


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT_DIR.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def project_dir_for(work_id: str) -> Path:
    return DEFAULT_DATA_DIR / "generated_works" / work_id / "testare-rapida"


def question_specs(runner: ModuleType, packet_dir: Path) -> list[Any]:
    specs = []
    for order, (prompt_name, packet_name) in enumerate(runner.QUESTION_FILES, start=1):
        packet_path = packet_dir / packet_name
        packet = read_json(packet_path)
        category_id = str((packet.get("metadata") or {}).get("category_id") or "")
        if not category_id:
            raise ValueError(f"Packetul {packet_path} nu declară metadata.category_id.")
        slug = packet_path.name.removesuffix(".packet.json")
        specs.append(
            runner.TaskSpec(
                key=f"questions/{slug}",
                task_type="questions",
                order=order,
                slug=slug,
                label=category_id,
                prompt_path=QWEN_DIR / "prompturi intrebari" / prompt_name,
                packet_path=packet_path,
                expected_id=category_id,
            )
        )
    return specs


def load_selection_history(path: Path, work_id: str) -> dict[str, Any]:
    if not path.is_file():
        return {
            "schema_version": 1,
            "work_id": work_id,
            "last_batch_number": 0,
            "selected_event_ids": [],
            "focus_event_ids_by_category": {},
            "batches": [],
        }
    payload = read_json(path)
    if payload.get("work_id") != work_id:
        raise ValueError(f"Istoricul {path} aparține altei opere.")
    return payload


def reserve_batch(
    graph: dict,
    graph_path: Path,
    project_dir: Path,
    run_dir: Path,
    work_id: str,
) -> tuple[list[Any], dict[str, Any]]:
    builder = packet_builder()
    runner = qwen_runner()
    history_path = project_dir / "selection-history.json"
    history = load_selection_history(history_path, work_id)
    excluded_by_category = {
        str(category_id): {str(value) for value in values}
        for category_id, values in (history.get("focus_event_ids_by_category") or {}).items()
        if isinstance(values, list)
    }
    batch_number = int(history.get("last_batch_number") or 0) + 1
    packet_dir = run_dir / "inputs" / "question-packets"
    rows, context_events = builder.build_packet_set(
        graph,
        packet_dir,
        batch_number=batch_number,
        graph_path=graph_path,
        excluded_event_ids_by_category=excluded_by_category,
    )
    focus_by_category = {
        str(row["category_id"]): {str(value) for value in row.get("focus_event_ids") or []}
        for row in rows
    }
    for category_id, focus_ids in focus_by_category.items():
        overlap = excluded_by_category.get(category_id, set()) & focus_ids
        if overlap:
            raise ValueError(
                f"Lotul nou reutilizează evenimente-focus în {category_id}: {sorted(overlap)}"
            )
    all_focus = {value for values in focus_by_category.values() for value in values}
    record = {
        "batch_number": batch_number,
        "run_id": run_dir.name,
        "reserved_at_utc": utc_now().isoformat(),
        "algorithm_version": builder.SELECTION_ALGORITHM_VERSION,
        "focus_event_count": len(all_focus),
        "focus_event_ids": sorted(all_focus),
        "focus_event_ids_by_category": {
            category_id: sorted(values) for category_id, values in focus_by_category.items()
        },
        "context_event_count": len(context_events),
        "context_event_ids": sorted(context_events),
        "categories": rows,
    }
    history["last_batch_number"] = batch_number
    for category_id, focus_ids in focus_by_category.items():
        excluded_by_category.setdefault(category_id, set()).update(focus_ids)
    history["focus_event_ids_by_category"] = {
        category_id: sorted(values) for category_id, values in excluded_by_category.items()
    }
    history["selected_event_ids"] = sorted(
        {value for values in excluded_by_category.values() for value in values}
    )
    history.setdefault("batches", []).append(record)
    write_json(history_path, history)
    write_json(run_dir / "question-selection.json", record)
    return question_specs(runner, packet_dir), record


def banked_run_ids(bank_path: Path) -> set[str]:
    """Returnează rulările deja adăugate complet în banca cumulativă."""
    if not bank_path.is_file():
        return set()
    bank = read_json(bank_path)
    return {
        str((question.get("source") or {}).get("run_id"))
        for category in bank.get("categories", [])
        if isinstance(category, dict)
        for question in category.get("questions", [])
        if isinstance(question, dict) and (question.get("source") or {}).get("run_id")
    }


def pending_reserved_batch(
    project_dir: Path,
    work_id: str,
    questions_path: Path,
) -> tuple[Path, dict[str, Any]] | None:
    """Găsește lotul rezervat, dar neadăugat încă în banca de întrebări."""
    history = load_selection_history(project_dir / "selection-history.json", work_id)
    completed_run_ids = banked_run_ids(questions_path)
    for record in history.get("batches", []):
        if not isinstance(record, dict):
            continue
        run_id = str(record.get("run_id") or "")
        if not run_id or run_id in completed_run_ids:
            continue
        run_dir = project_dir / "runs" / run_id
        packet_dir = run_dir / "inputs" / "question-packets"
        if run_dir.is_dir() and packet_dir.is_dir():
            return run_dir, record
    return None


def local_batch_number(run_id: str, fallback: int = 1) -> int:
    match = re.search(r"-b(\d+)$", run_id)
    return int(match.group(1)) if match else fallback


def question_result_is_preserved(runner: ModuleType, run_dir: Path, spec: Any) -> bool:
    """Un rezultat existent nu se regenerează, indiferent de validarea semantică."""
    latest = runner.load_latest(run_dir, spec)
    if not latest:
        return False
    attempt_dir = run_dir / str(latest.get("attempt_dir") or "")
    return (attempt_dir / "result.json").is_file() or latest.get("status") == "unparseable"


def reasoning_effort_for_resume(
    runner: ModuleType,
    run_dir: Path,
    spec: Any,
    requested_effort: str,
) -> str:
    """Evită încă o ieșire goală când reasoning-ul a consumat limita de output."""
    latest = runner.load_latest(run_dir, spec)
    if not isinstance(latest, dict) or latest.get("status") != "error":
        return requested_effort
    error = latest.get("error") if isinstance(latest.get("error"), dict) else {}
    message = str(error.get("message") or "").lower()
    if "finish_reason='length'" in message or 'finish_reason="length"' in message:
        return "none"
    return requested_effort


def result_for_spec(runner: ModuleType, run_dir: Path, spec: Any) -> tuple[dict, dict]:
    latest = runner.load_latest(run_dir, spec)
    if not latest:
        raise RuntimeError(f"Lipsește rezultatul pentru {spec.key}.")
    attempt_dir = run_dir / str(latest["attempt_dir"])
    result_path = attempt_dir / "result.json"
    if result_path.is_file():
        return read_json(result_path), latest

    raw_path = attempt_dir / "response.raw.txt"
    raw = raw_path.read_text(encoding="utf-8").strip() if raw_path.is_file() else ""
    # Recuperarea este strict locală: elimină eventualul fence Markdown sau textul
    # din jurul obiectului, fără un al doilea apel către model.
    first_brace = raw.find("{")
    last_brace = raw.rfind("}")
    if first_brace >= 0 and last_brace > first_brace:
        try:
            recovered = json.loads(raw[first_brace : last_brace + 1])
        except json.JSONDecodeError:
            recovered = None
        if isinstance(recovered, dict):
            write_json(attempt_dir / "result.recovered-locally.json", recovered)
            return recovered, {**latest, "local_json_recovery": True}

    packet = read_json(spec.packet_path)
    slots = ((packet.get("selection") or {}).get("question_slots") or [])
    placeholders = [
        {
            "question_id": str(slot.get("slot_id") or f"UNPARSEABLE_{index:02d}"),
            "status": "unparseable",
            "reason": "Răspunsul Qwen a fost păstrat brut, dar nu a putut fi interpretat ca JSON.",
            "raw_response_path": display_path(raw_path),
        }
        for index, slot in enumerate(slots, start=1)
    ]
    return {
        "task": "question_generation",
        "category_id": spec.expected_id,
        "graph_version": str((packet.get("metadata") or {}).get("version") or ""),
        "questions": placeholders,
    }, {**latest, "validation_passed": False, "unparseable_preserved": True}


def empty_question_bank(work: dict[str, str]) -> dict:
    return {
        "schema_version": 1,
        "work_id": work["work_id"],
        "work": work,
        "task": "cumulative_question_bank",
        "question_count": 0,
        "generated_question_count": 0,
        "impossible_question_count": 0,
        "unparseable_question_count": 0,
        "run_count": 0,
        "category_count": 0,
        "categories": [],
    }


def append_run_to_question_bank(
    bank_path: Path,
    work: dict[str, str],
    runner: ModuleType,
    run_dir: Path,
    specs: Sequence[Any],
    *,
    model_id: str,
    batch_number: int,
) -> dict:
    bank = read_json(bank_path) if bank_path.is_file() else empty_question_bank(work)
    if bank.get("work_id") != work["work_id"]:
        raise ValueError(f"Banca {bank_path} aparține altei opere.")
    categories = {
        str(category.get("category_id")): category
        for category in bank.get("categories", [])
        if isinstance(category, dict) and category.get("category_id")
    }
    timestamp = utc_now().isoformat()
    for spec in specs:
        payload, latest = result_for_spec(runner, run_dir, spec)
        category = categories.setdefault(
            spec.expected_id,
            {"category_id": spec.expected_id, "question_count": 0, "questions": []},
        )
        existing_ids = {
            str(item.get("cumulative_id"))
            for item in category.get("questions", [])
            if isinstance(item, dict)
        }
        for index, question in enumerate(payload.get("questions", []), start=1):
            if not isinstance(question, dict):
                continue
            source_question_id = str(question.get("question_id") or f"QUESTION_{index:02d}")
            cumulative_id = f"{run_dir.name}::{spec.expected_id}::{source_question_id}"
            if cumulative_id in existing_ids:
                continue
            category.setdefault("questions", []).append(
                {
                    "cumulative_id": cumulative_id,
                    "source": {
                        "run_id": run_dir.name,
                        "timestamp_utc": timestamp,
                        "model": model_id,
                        "batch_number": batch_number,
                        "category_id": spec.expected_id,
                        "validation_passed": bool(latest.get("validation_passed")),
                    },
                    **question,
                }
            )
            existing_ids.add(cumulative_id)
        category["question_count"] = len(category.get("questions", []))

    ordered_ids = [spec.expected_id for spec in specs]
    ordered_categories = [categories[category_id] for category_id in ordered_ids if category_id in categories]
    ordered_categories.extend(
        category for category_id, category in categories.items() if category_id not in ordered_ids
    )
    all_questions = [
        question
        for category in ordered_categories
        for question in category.get("questions", [])
        if isinstance(question, dict)
    ]
    run_ids = {
        str((question.get("source") or {}).get("run_id"))
        for question in all_questions
        if (question.get("source") or {}).get("run_id")
    }
    bank.update(
        {
            "work": work,
            "question_count": len(all_questions),
            "generated_question_count": sum(
                question.get("status", "generated") == "generated" for question in all_questions
            ),
            "impossible_question_count": sum(
                question.get("status") == "impossible" for question in all_questions
            ),
            "unparseable_question_count": sum(
                question.get("status") == "unparseable" for question in all_questions
            ),
            "run_count": len(run_ids),
            "category_count": len(ordered_categories),
            "categories": ordered_categories,
        }
    )
    write_json(bank_path, bank)
    write_questions_text(project_dir=bank_path.parent, bank=bank)
    return bank


def write_questions_text(project_dir: Path, bank: dict) -> Path:
    work = bank.get("work") or {}
    lines = [
        f"ÎNTREBĂRI CUMULATIVE — {str(work.get('title') or bank.get('work_id')).upper()}",
        f"Total: {bank.get('question_count', 0)}",
        "",
    ]
    for category in bank.get("categories", []):
        lines.extend((str(category.get("category_id") or "CATEGORIE"), "=" * 72))
        for index, question in enumerate(category.get("questions", []), start=1):
            lines.append(f"{index}. {str(question.get('question_text') or '').strip()}")
            answer = question.get("answer") or {}
            if isinstance(answer, dict) and answer.get("text"):
                lines.append(f"   Răspuns: {str(answer['text']).strip()}")
        lines.append("")
    output = project_dir / "questions-by-category.txt"
    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output


def build_all_banks(
    questions_path: Path,
    graph_path: Path,
    work_id: str,
    data_dir: Path = DEFAULT_DATA_DIR,
) -> dict[str, dict]:
    exercise_dir = data_dir / "exercises" / work_id
    flashcard_path = data_dir / "flashcards" / f"{work_id}.json"
    payloads = {
        "flashcards": build_flashcard_deck(questions_path, graph_path, work_id),
        "multiple_choice": build_multiple_choice_bank(questions_path, graph_path, work_id),
        "chronology": build_chronology_bank(questions_path, graph_path, work_id),
        "completion": build_completion_bank(questions_path, graph_path, work_id),
        "matching": build_matching_bank(questions_path, graph_path, work_id),
    }
    write_json(flashcard_path, payloads["flashcards"])
    for name in ("multiple_choice", "chronology", "completion", "matching"):
        write_json(exercise_dir / f"{name}.json", payloads[name])
    return payloads


def build_manifest(
    project_dir: Path,
    graph_path: Path,
    questions_path: Path,
    data_dir: Path,
    work: dict[str, str],
    banks: dict[str, dict],
) -> dict:
    work_id = work["work_id"]
    return {
        "schema_version": 1,
        "pipeline": "testare-rapida",
        "status": "complete",
        "generated_at_utc": utc_now().isoformat(),
        "work": work,
        "input": {"knowledge_graph": display_path(graph_path)},
        "project": {
            "directory": display_path(project_dir),
            "questions_json": display_path(questions_path),
            "questions_text": display_path(project_dir / "questions-by-category.txt"),
            "selection_history": display_path(project_dir / "selection-history.json"),
        },
        "ui_artifacts": {
            "flashcards": display_path(data_dir / "flashcards" / f"{work_id}.json"),
            "multiple_choice": display_path(data_dir / "exercises" / work_id / "multiple_choice.json"),
            "chronology": display_path(data_dir / "exercises" / work_id / "chronology.json"),
            "completion": display_path(data_dir / "exercises" / work_id / "completion.json"),
            "matching": display_path(data_dir / "exercises" / work_id / "matching.json"),
        },
        "counts": {
            "flashcards": banks["flashcards"]["card_count"],
            "multiple_choice": banks["multiple_choice"]["exercise_count"],
            "chronology": banks["chronology"]["exercise_count"],
            "completion": banks["completion"]["exercise_count"],
            "matching_sets": banks["matching"]["exercise_count"],
            "matching_pairs": banks["matching"]["pair_count"],
        },
    }


def generate_batches(
    args: argparse.Namespace,
    graph: dict,
    graph_path: Path,
    project_dir: Path,
    work: dict[str, str],
) -> Path:
    runner = qwen_runner()
    config = runner.load_local_env(args.config)
    if not config.get("OPENROUTER_API_KEY") and args.config == runner.DEFAULT_CONFIG_PATH:
        config = {**runner.load_local_env(runner.LEGACY_CONFIG_PATH), **config}
    api_key = str(config.get("OPENROUTER_API_KEY") or "")
    if not api_key:
        raise ValueError(f"OPENROUTER_API_KEY lipsește din {args.config}.")
    model_id = args.model or config.get("OPENROUTER_MODEL") or runner.DEFAULT_MODEL
    print(f"Verific modelul Qwen: {model_id}")
    model_info = runner.get_model_info(api_key, model_id, args.timeout)
    questions_path = project_dir / "questions.json"
    pending = pending_reserved_batch(project_dir, work["work_id"], questions_path)
    first_new_local_batch = 1

    def execute_batch(
        local_batch: int,
        run_dir: Path,
        specs: Sequence[Any],
        selection: dict[str, Any],
    ) -> None:
        for position, spec in enumerate(specs, start=1):
            if question_result_is_preserved(runner, run_dir, spec):
                print(
                    f"[{local_batch}/{args.batches} · {position}/{len(specs)}] "
                    f"{spec.expected_id} - reutilizat local"
                )
                continue
            effective_reasoning = reasoning_effort_for_resume(
                runner, run_dir, spec, args.reasoning_effort
            )
            reasoning_note = (
                f"{effective_reasoning}; fallback după finish_reason=length"
                if effective_reasoning != args.reasoning_effort
                else effective_reasoning
            )
            print(
                f"[{local_batch}/{args.batches} · {position}/{len(specs)}] "
                f"{spec.expected_id} (reasoning={reasoning_note})"
            )
            latest = runner.run_one_task(
                spec,
                run_dir,
                api_key=api_key,
                model_id=model_id,
                model_info=model_info,
                max_tokens=args.max_tokens,
                timeout=args.timeout,
                reasoning_effort=effective_reasoning,
                allow_provider_fallbacks=not args.no_provider_fallbacks,
                provider_order=args.provider_order,
            )
            if not question_result_is_preserved(runner, run_dir, spec):
                raise RuntimeError(f"Apelul {spec.key} a eșuat: {latest}")
        append_run_to_question_bank(
            questions_path,
            work,
            runner,
            run_dir,
            specs,
            model_id=model_id,
            batch_number=selection["batch_number"],
        )

    if pending is not None:
        run_dir, selection = pending
        local_batch = local_batch_number(run_dir.name)
        specs = question_specs(runner, run_dir / "inputs" / "question-packets")
        print(
            f"Reiau lotul {selection.get('batch_number')} din {run_dir.name}; "
            "rezultatele existente rămân neschimbate."
        )
        execute_batch(local_batch, run_dir, specs, selection)
        first_new_local_batch = local_batch + 1
    elif questions_path.is_file() and not (project_dir / "manifest.json").is_file():
        history = load_selection_history(
            project_dir / "selection-history.json", work["work_id"]
        )
        batches = history.get("batches") or []
        if batches and local_batch_number(str(batches[-1].get("run_id") or ""), 0) >= args.batches:
            print("Cele patru loturi sunt deja în banca locală; reconstruiesc numai artefactele UI.")
            first_new_local_batch = args.batches + 1

    for local_batch in range(first_new_local_batch, args.batches + 1):
        stamp = utc_now().strftime("%Y%m%dT%H%M%S%fZ")
        run_dir = project_dir / "runs" / f"run-{stamp}-b{local_batch:03d}"
        run_dir.mkdir(parents=True, exist_ok=False)
        specs, selection = reserve_batch(
            graph, graph_path, project_dir, run_dir, work["work_id"]
        )
        runner.save_json(run_dir / "manifest.json", runner.build_manifest(specs))
        runner.save_json(
            run_dir / "metadata.json",
            {
                "schema_version": 1,
                "pipeline": "testare-rapida",
                "work": work,
                "run_id": run_dir.name,
                "timestamp_utc": utc_now().isoformat(),
                "requested_model": model_id,
                "question_batch_number": selection["batch_number"],
                "question_task_count": len(specs),
                "generation_policy": {
                    "max_attempts_per_task": 1,
                    "retry_on_validation_failure": False,
                    "retain_parseable_invalid_results": True,
                    "resume_transport_errors_on_next_command": True,
                },
                "api_key_saved": False,
            },
        )
        execute_batch(local_batch, run_dir, specs, selection)
    return questions_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH)
    parser.add_argument("--work-id", default=None, help="Opțional; implicit este derivat din graf.")
    parser.add_argument("--project-dir", type=Path, default=None)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--model", default=None)
    parser.add_argument(
        "--batches",
        type=int,
        default=4,
        help="Număr de loturi a câte 24 de întrebări (implicit: 4 = 96 întrebări).",
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=("none", "minimal", "low", "medium", "high", "xhigh", "max"),
        default="medium",
    )
    parser.add_argument("--max-tokens", type=int, default=12000)
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--provider-order", action="append", metavar="PROVIDER")
    parser.add_argument("--no-provider-fallbacks", action="store_true")
    parser.add_argument(
        "--build-only",
        action="store_true",
        help="Nu apelează Qwen; construiește băncile din --questions.",
    )
    parser.add_argument("--questions", type=Path, default=None)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args(argv)

    if args.batches < 1:
        parser.error("--batches trebuie să fie cel puțin 1.")
    graph_path = args.graph.resolve()
    if not graph_path.is_file():
        parser.error(f"Graful nu există: {graph_path}")
    graph = read_json(graph_path)
    work = graph_work_metadata(graph, args.work_id)
    project_dir = (args.project_dir or project_dir_for(work["work_id"])).resolve()
    questions_path = (args.questions or project_dir / "questions.json").resolve()

    if args.plan_only:
        print(f"Operă: {work['title']} ({work['work_id']})")
        print(f"Graf: {graph_path}")
        print(f"Proiect Testare rapidă: {project_dir}")
        print(f"Apeluri Qwen planificate: {args.batches * 8}")
        print(f"Întrebări planificate: {args.batches * 24}")
        print(f"Reasoning: {args.reasoning_effort}")
        print("Regenerare pentru rezultate invalide: nu")
        return 0

    project_dir.mkdir(parents=True, exist_ok=True)
    if args.build_only:
        if not questions_path.is_file():
            parser.error("--build-only necesită o bancă existentă prin --questions.")
    else:
        if args.questions:
            parser.error("--questions se folosește împreună cu --build-only.")
        try:
            questions_path = generate_batches(
                args, graph, graph_path, project_dir, work
            )
        except (ValueError, RuntimeError) as exc:
            parser.error(str(exc))

    write_questions_text(project_dir, read_json(questions_path))

    try:
        banks = build_all_banks(
            questions_path,
            graph_path,
            work["work_id"],
            args.data_dir.resolve(),
        )
    except ValueError as exc:
        parser.error(f"Băncile UI nu au putut fi construite: {exc}")
    manifest = build_manifest(
        project_dir,
        graph_path,
        questions_path,
        args.data_dir.resolve(),
        work,
        banks,
    )
    write_json(project_dir / "manifest.json", manifest)
    print(
        f"Testare rapidă finalizată pentru {work['title']}: "
        f"{banks['flashcards']['card_count']} flashcarduri, "
        f"{banks['multiple_choice']['exercise_count']} grile, "
        f"{banks['chronology']['exercise_count']} cronologii, "
        f"{banks['completion']['exercise_count']} completări și "
        f"{banks['matching']['exercise_count']} seturi de asociere."
    )
    print(f"Manifest: {project_dir / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
