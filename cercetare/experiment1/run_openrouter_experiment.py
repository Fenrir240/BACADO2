"""Rulează Experimentul 1 prin OpenRouter și salvează outputurile pe model."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import re
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prepare_inputs import OUTPUT_PATH as CHAPTER_PACKET_PATH
from prepare_inputs import build_chapter_packet


EXPERIMENT_DIR = Path(__file__).resolve().parent
RESEARCH_DIR = EXPERIMENT_DIR.parent
EXPERIMENT_NAME = "Experimentul 1"
EXTRA_METADATA: dict[str, Any] = {}
PREFLIGHT_HOOK: Any | None = None
RESULTS_WORKBOOK_SYNC_HOOK: Any | None = None
DEFAULT_SUMMARY_REASONING_EFFORT = "low"
GRAPH_PATH = RESEARCH_DIR / "graf1" / "knowledge-graph.json"
QUESTION_PROMPT_PATH = RESEARCH_DIR / "benchmark1" / "prompts" / "prompt-generare-intrebari.md"
SUMMARY_PROMPT_PATH = RESEARCH_DIR / "benchmark1" / "prompts" / "prompt-rezumat-capitolul-1.md"
EVALUATOR_PATH = RESEARCH_DIR / "benchmark1" / "scoring" / "evaluator.py"
QUESTION_MANIFEST_PATH = EXPERIMENT_DIR / "inputs" / "question-manifest.json"
QUESTION_BLUEPRINTS_PATH = EXPERIMENT_DIR / "inputs" / "question-blueprints.json"
SUMMARY_MANIFEST_PATH = EXPERIMENT_DIR / "inputs" / "summary-manifest.json"
DEFAULT_CONFIG_PATH = EXPERIMENT_DIR / "config.local.env"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def load_local_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def model_folder_name(model_id: str) -> str:
    normalized = model_id.replace("/", "__")
    return re.sub(r"[^A-Za-z0-9._-]+", "_", normalized).strip("._")


def api_json(
    url: str,
    api_key: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: int = 1200,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://localhost/bac-romana-experiment",
            "X-Title": f"Bac Romana - {EXPERIMENT_NAME}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter HTTP {exc.code}: {error_body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenRouter nu a putut fi contactat: {exc}") from exc


def get_model_info(api_key: str, model_id: str, timeout: int) -> dict[str, Any]:
    response = api_json(
        f"{OPENROUTER_BASE_URL}/models/user",
        api_key,
        timeout=timeout,
    )
    for model in response.get("data", []):
        if model.get("id") == model_id or model.get("canonical_slug") == model_id:
            return model
    raise ValueError(
        f"Modelul {model_id!r} nu apare în lista /models/user pentru această cheie OpenRouter."
    )


def replace_exactly_once(template: str, token: str, replacement: str) -> str:
    occurrence_count = template.count(token)
    if occurrence_count != 1:
        raise ValueError(
            f"Placeholder-ul {token} trebuie să apară exact o dată în template; "
            f"apare de {occurrence_count} ori."
        )
    return template.replace(token, replacement, 1)


def render_question_prompt(graph: dict[str, Any]) -> str:
    rendered = QUESTION_PROMPT_PATH.read_text(encoding="utf-8")
    rendered = replace_exactly_once(
        rendered,
        "{{TASK_MANIFEST}}",
        json.dumps(read_json(QUESTION_MANIFEST_PATH), ensure_ascii=False, indent=2),
    )
    rendered = replace_exactly_once(
        rendered,
        "{{QUESTION_BLUEPRINTS}}",
        json.dumps(read_json(QUESTION_BLUEPRINTS_PATH), ensure_ascii=False, indent=2),
    )
    return replace_exactly_once(rendered, "{{GRAPH_PACKET}}", compact_json(graph))


def render_summary_prompt(chapter_packet: dict[str, Any]) -> str:
    rendered = SUMMARY_PROMPT_PATH.read_text(encoding="utf-8")
    rendered = replace_exactly_once(
        rendered,
        "{{SUMMARY_MANIFEST}}",
        json.dumps(read_json(SUMMARY_MANIFEST_PATH), ensure_ascii=False, indent=2),
    )
    return replace_exactly_once(
        rendered,
        "{{CHAPTER_01_GRAPH_PACKET}}",
        compact_json(chapter_packet),
    )


def build_request(
    model_id: str,
    prompt: str,
    model_info: dict[str, Any],
    max_tokens: int,
    allow_provider_fallbacks: bool,
    reasoning_effort: str,
    provider_order: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    supported = set(model_info.get("supported_parameters") or [])
    payload: dict[str, Any] = {
        "model": model_id,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Participi la un experiment controlat. Folosește exclusiv datele "
                    "din prompt și returnează exclusiv obiectul JSON solicitat."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "provider": {
            "allow_fallbacks": allow_provider_fallbacks,
            "require_parameters": True,
            "data_collection": "deny",
        },
    }
    applied: dict[str, Any] = {
        "stream": False,
        "provider.allow_fallbacks": allow_provider_fallbacks,
        "provider.require_parameters": True,
        "provider.data_collection": "deny",
    }
    if provider_order:
        payload["provider"]["order"] = provider_order
        applied["provider.order"] = provider_order

    if "max_tokens" in supported:
        payload["max_tokens"] = max_tokens
        applied["max_tokens"] = max_tokens
    if "temperature" in supported:
        payload["temperature"] = 0
        applied["temperature"] = 0
    if "response_format" in supported or "structured_outputs" in supported:
        payload["response_format"] = {"type": "json_object"}
        applied["response_format"] = {"type": "json_object"}
    if "reasoning" in supported:
        reasoning_info = model_info.get("reasoning") or {}
        supported_efforts = reasoning_info.get("supported_efforts") or []
        reasoning_mandatory = bool(reasoning_info.get("mandatory"))
        if reasoning_effort == "none":
            if reasoning_mandatory:
                raise ValueError(
                    "Modelul declară reasoning obligatoriu; effort='none' nu este permis."
                )
            payload["reasoning"] = {"effort": "none", "exclude": True}
            applied["reasoning"] = {"effort": "none", "exclude": True}
        elif supported_efforts and reasoning_effort not in supported_efforts:
            raise ValueError(
                f"Modelul nu declară suport pentru reasoning effort {reasoning_effort!r}; "
                f"valorile declarate sunt: {supported_efforts}."
            )
        else:
            payload["reasoning"] = {"effort": reasoning_effort, "exclude": True}
            applied["reasoning"] = {"effort": reasoning_effort, "exclude": True}

    return payload, applied


def extract_content(response: dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        raise ValueError("Răspunsul OpenRouter nu conține choices.")
    content = (choices[0].get("message") or {}).get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        texts = [item.get("text", "") for item in content if isinstance(item, dict)]
        return "".join(texts).strip()
    choice = choices[0]
    finish_reason = choice.get("finish_reason") or choice.get("native_finish_reason")
    usage = response.get("usage") or {}
    completion_details = usage.get("completion_tokens_details") or {}
    if finish_reason == "length":
        raise ValueError(
            "Generarea a atins limita fără text final "
            f"(finish_reason=length, completion_tokens={usage.get('completion_tokens')}, "
            f"reasoning_tokens={completion_details.get('reasoning_tokens')})."
        )
    raise ValueError(
        "Răspunsul modelului nu conține text final "
        f"(finish_reason={finish_reason!r})."
    )


def verify_returned_model(
    requested_model: str,
    model_info: dict[str, Any],
    response: dict[str, Any],
) -> str:
    returned_model = str(response.get("model") or "")
    allowed_models = {
        value
        for value in (
            requested_model,
            model_info.get("id"),
            model_info.get("canonical_slug"),
        )
        if value
    }
    if not returned_model:
        raise ValueError("Răspunsul OpenRouter nu declară modelul care a fost folosit.")
    if returned_model not in allowed_models:
        raise RuntimeError(
            "Răspuns respins: modelul returnat "
            f"{returned_model!r} diferă de modelul solicitat {requested_model!r}."
        )
    return returned_model


def load_evaluator() -> Any:
    spec = importlib.util.spec_from_file_location("ion_benchmark_evaluator", EVALUATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Evaluatorul nu poate fi încărcat.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def save_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_task_payload(task_name: str, parsed: Any) -> tuple[bool, str | None]:
    if not isinstance(parsed, Mapping):
        return False, (
            "Răspunsul JSON trebuie să fie un obiect, nu "
            f"{type(parsed).__name__}."
        )
    if task_name == "questions":
        if not isinstance(parsed.get("questions"), list):
            return False, "Obiectul JSON pentru questions trebuie să conțină lista questions."
    elif task_name == "summary":
        summaries = parsed.get("summaries")
        if not isinstance(summaries, Mapping):
            return False, "Obiectul JSON pentru summary trebuie să conțină obiectul summaries."
        for register_name in ("simple", "elevated"):
            register = summaries.get(register_name)
            if not isinstance(register, Mapping):
                return False, f"Lipsește obiectul summaries.{register_name}."
            if not isinstance(register.get("summary_text"), str):
                return False, f"Lipsește textul summaries.{register_name}.summary_text."
    return True, None


def run_task(
    task_name: str,
    prompt: str,
    api_key: str,
    model_id: str,
    model_info: dict[str, Any],
    run_dir: Path,
    max_tokens: int,
    timeout: int,
    allow_provider_fallbacks: bool,
    reasoning_effort: str,
    provider_order: list[str] | None = None,
) -> dict[str, Any]:
    payload, applied_parameters = build_request(
        model_id,
        prompt,
        model_info,
        max_tokens,
        allow_provider_fallbacks,
        reasoning_effort,
        provider_order,
    )
    prompt_bytes = prompt.encode("utf-8")
    started = time.perf_counter()
    response = api_json(
        f"{OPENROUTER_BASE_URL}/chat/completions",
        api_key,
        method="POST",
        payload=payload,
        timeout=timeout,
    )
    duration = time.perf_counter() - started
    save_json(run_dir / f"{task_name}.openrouter-response.json", response)
    api_error = response.get("error")
    if isinstance(api_error, dict):
        error_code = api_error.get("code", "necunoscut")
        error_message = api_error.get("message", "eroare fără mesaj")
        raise RuntimeError(f"OpenRouter API {error_code}: {error_message}")
    returned_model = verify_returned_model(model_id, model_info, response)
    content = extract_content(response)

    (run_dir / f"{task_name}.raw.txt").write_text(content + "\n", encoding="utf-8")

    json_syntax_valid = False
    json_valid = False
    validation_error: str | None = None
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = None
    else:
        json_syntax_valid = True
        json_valid, validation_error = validate_task_payload(task_name, parsed)
        save_json(run_dir / f"{task_name}.json", parsed)

    usage = response.get("usage") or {}
    return {
        "task": task_name,
        "content": content,
        "parsed": parsed,
        "json_syntax_valid": json_syntax_valid,
        "json_valid": json_valid,
        "validation_error": validation_error,
        "duration_seconds": round(duration, 3),
        "prompt_sha256": sha256_bytes(prompt_bytes),
        "prompt_characters": len(prompt),
        "estimated_prompt_tokens": math.ceil(len(prompt) / 2.5),
        "applied_parameters": applied_parameters,
        "returned_model": returned_model,
        "model_verification": "accepted_exact_or_canonical_model_id",
        "provider": response.get("provider"),
        "generation_id": response.get("id"),
        "usage": usage,
    }


def resolve_resume_run(value: Path) -> Path:
    candidates = [value]
    if not value.is_absolute():
        candidates.append(EXPERIMENT_DIR / value)
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.is_dir() and (resolved / "metadata.json").is_file():
            return resolved
    raise ValueError(
        f"Folderul de reluat nu există sau nu conține metadata.json: {value}"
    )


def load_saved_task(
    run_dir: Path,
    task_name: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    parsed_path = run_dir / f"{task_name}.json"
    raw_path = run_dir / f"{task_name}.raw.txt"
    parsed = read_json(parsed_path) if parsed_path.exists() else None
    if raw_path.exists():
        content = raw_path.read_text(encoding="utf-8").strip()
    elif parsed is not None:
        content = compact_json(parsed)
    else:
        content = ""
    saved_metadata = dict((metadata.get("tasks") or {}).get(task_name) or {})
    json_valid, validation_error = validate_task_payload(task_name, parsed)
    return {
        **saved_metadata,
        "task": task_name,
        "content": content,
        "parsed": parsed,
        "json_syntax_valid": parsed is not None,
        "json_valid": json_valid,
        "validation_error": validation_error,
    }


def archive_task_artifacts(run_dir: Path, task_name: str) -> Path | None:
    artifact_names = (
        f"{task_name}.openrouter-response.json",
        f"{task_name}.raw.txt",
        f"{task_name}.json",
        f"{task_name}.error.json",
    )
    existing = [run_dir / name for name in artifact_names if (run_dir / name).exists()]
    if not existing:
        return None
    attempt_id = datetime.now(timezone.utc).strftime("retry-%Y%m%dT%H%M%SZ")
    archive_dir = run_dir / "previous-attempts" / f"{task_name}-{attempt_id}"
    archive_dir.mkdir(parents=True, exist_ok=False)
    for path in existing:
        path.replace(archive_dir / path.name)
    return archive_dir


def ensure_results_csv_writable(csv_path: Path) -> None:
    if not csv_path.exists():
        return
    try:
        with csv_path.open("a", encoding="utf-8-sig", newline=""):
            pass
    except PermissionError as exc:
        raise PermissionError(
            f"Nu pot scrie în {csv_path}. Închide fișierul în Excel și rulează din nou."
        ) from exc


def upsert_results_csv(
    csv_path: Path,
    metadata: dict[str, Any],
    scores: dict[str, Any],
    question_run: dict[str, Any],
    summary_run: dict[str, Any],
    run_dir: Path,
) -> None:
    question_data = question_run.get("parsed") or {}
    summary_data = summary_run.get("parsed") or {}
    if not isinstance(question_data, Mapping):
        question_data = {}
    if not isinstance(summary_data, Mapping):
        summary_data = {}
    question_values = question_data.get("questions")
    if not isinstance(question_values, list):
        question_values = []
    questions = [
        item.get("question_text", "")
        for item in question_values
        if isinstance(item, Mapping)
    ]
    summaries = summary_data.get("summaries", {})
    if not isinstance(summaries, Mapping):
        summaries = {}
    simple_summary = summaries.get("simple")
    if not isinstance(simple_summary, Mapping):
        simple_summary = {}
    elevated_summary = summaries.get("elevated")
    if not isinstance(elevated_summary, Mapping):
        elevated_summary = {}
    row = {
        "timestamp_utc": metadata["timestamp_utc"],
        "run_id": metadata["run_id"],
        "model": metadata["requested_model"],
        "provider": question_run.get("provider") or summary_run.get("provider") or "",
        "question_score": scores.get("question_generation", {}).get("score", 0),
        "summary_score": scores.get("chapter_1_summary", {}).get("score", 0),
        "overall_score": scores.get("overall_score", 0),
        "questions_json_valid": question_run.get("json_valid", False),
        "summary_json_valid": summary_run.get("json_valid", False),
        "questions": json.dumps(questions, ensure_ascii=False),
        "simple_summary": simple_summary.get("summary_text", ""),
        "elevated_summary": elevated_summary.get("summary_text", ""),
        "result_folder": str(run_dir.relative_to(EXPERIMENT_DIR)),
    }
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    existing_rows: list[dict[str, str]] = []
    if csv_path.exists():
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames and reader.fieldnames != list(row):
                raise ValueError(
                    "Antetul rezultate-experiment.csv nu coincide cu schema runnerului."
                )
            existing_rows = list(reader)
    updated_rows = [item for item in existing_rows if item.get("run_id") != metadata["run_id"]]
    updated_rows.append(row)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader()
        writer.writerows(updated_rows)


def format_decimal(value: Any, digits: int = 3) -> str:
    if not isinstance(value, (int, float)):
        return "—"
    return f"{float(value):.{digits}f}".replace(".", ",")


def format_integer(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return "—"
    return f"{int(value):,}".replace(",", ".")


def markdown_cell(value: Any) -> str:
    text = str(value if value not in (None, "") else "—")
    return text.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def yes_no(value: Any) -> str:
    return "da" if value else "nu"


def generate_run_report(
    run_dir: Path,
    metadata: dict[str, Any],
    scores: dict[str, Any],
    runs: dict[str, dict[str, Any]],
) -> Path:
    question_run = runs.get("questions") or {}
    summary_run = runs.get("summary") or {}
    question_scores = scores.get("question_generation") or {}
    summary_scores = scores.get("chapter_1_summary") or {}
    question_usage = question_run.get("usage") or {}
    summary_usage = summary_run.get("usage") or {}

    def reasoning_tokens(usage: dict[str, Any]) -> Any:
        return (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")

    def task_error(run: dict[str, Any]) -> str:
        if run.get("json_valid"):
            return "—"
        return str(run.get("message") or "JSON invalid sau răspuns final absent")

    total_duration = sum(
        float(run.get("duration_seconds") or 0) for run in (question_run, summary_run)
    )
    total_cost = sum(
        float((run.get("usage") or {}).get("cost") or 0)
        for run in (question_run, summary_run)
    )

    lines = [
        f"# Raport rulare — {metadata.get('model_name') or metadata.get('requested_model')}",
        "",
        "## Identificarea rulării",
        "",
        f"- Rulare: `{metadata.get('run_id', '—')}`",
        f"- Data UTC: `{metadata.get('timestamp_utc', '—')}`",
        f"- Model solicitat: `{metadata.get('requested_model', '—')}`",
        f"- Model returnat pentru întrebări: `{question_run.get('returned_model', '—')}`",
        f"- Model returnat pentru rezumat: `{summary_run.get('returned_model', '—')}`",
        f"- Provider întrebări: {question_run.get('provider') or '—'}",
        f"- Provider rezumat: {summary_run.get('provider') or '—'}",
        "- Fallback între modele: inexistent; runnerul trimite un singur model și îi verifică identitatea",
        (
            "- Fallback între providerii aceluiași model — întrebări: "
            f"{yes_no((question_run.get('applied_parameters') or {}).get('provider.allow_fallbacks'))}"
        ),
        (
            "- Fallback între providerii aceluiași model — rezumat: "
            f"{yes_no((summary_run.get('applied_parameters') or {}).get('provider.allow_fallbacks'))}"
        ),
        "",
        "## Rezultate generale",
        "",
        (
            "- Întrebări generate: "
            f"{question_scores.get('received_question_count', 0)} din "
            f"{question_scores.get('expected_question_count', 0)}"
        ),
        f"- JSON întrebări valid: {yes_no(question_run.get('json_valid'))}",
        f"- JSON rezumat valid: {yes_no(summary_run.get('json_valid'))}",
        f"- Scor întrebări: {format_decimal(question_scores.get('score'))} / 100",
        f"- Scor rezumat: {format_decimal(summary_scores.get('score'))} / 100",
        f"- Scor general: {format_decimal(scores.get('overall_score'))} / 100",
        f"- Eroare întrebări: {task_error(question_run)}",
        f"- Eroare rezumat: {task_error(summary_run)}",
        "",
        "## Performanță și cost",
        "",
        "| Sarcină | Reasoning | Durată (s) | Tokenuri prompt | Tokenuri completare | Tokenuri reasoning | Cost (USD) |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]

    for label, run, usage in (
        ("Întrebări", question_run, question_usage),
        ("Rezumat", summary_run, summary_usage),
    ):
        effort = ((run.get("applied_parameters") or {}).get("reasoning") or {}).get(
            "effort", "—"
        )
        lines.append(
            "| "
            + " | ".join(
                (
                    label,
                    markdown_cell(effort),
                    format_decimal(run.get("duration_seconds")),
                    format_integer(usage.get("prompt_tokens")),
                    format_integer(usage.get("completion_tokens")),
                    format_integer(reasoning_tokens(usage)),
                    format_decimal(usage.get("cost"), 6),
                )
            )
            + " |"
        )

    lines.extend(
        (
            "",
            f"- Durată API cumulată: {format_decimal(total_duration)} secunde",
            f"- Cost total: {format_decimal(total_cost, 6)} USD",
            "",
            "## Scorurile întrebărilor",
            "",
            "| ID | Slot | Tipologie | Întrebare | Scor | Diagnostic |",
            "|---|---|---|---|---:|---|",
        )
    )
    for question in question_scores.get("questions") or []:
        diagnostics = "; ".join(question.get("diagnostics") or []) or "—"
        lines.append(
            "| "
            + " | ".join(
                (
                    markdown_cell(question.get("question_id")),
                    markdown_cell(question.get("slot_id")),
                    markdown_cell(question.get("blueprint_id")),
                    markdown_cell(question.get("question_text")),
                    format_decimal(question.get("score")),
                    markdown_cell(diagnostics),
                )
            )
            + " |"
        )

    lines.extend(
        (
            "",
            (
                "- Media întrebărilor: "
                f"{format_decimal(question_scores.get('question_average'))} / 100"
            ),
            (
                "- Scorul de acoperire și diversitate al setului: "
                f"{format_decimal(question_scores.get('set_coverage_score'))} / 100"
            ),
            "",
            "## Scorurile rezumatelor",
            "",
            "| Registru | Scor | Cuvinte | Acoperire evenimente | Afirmații valide | Ordine corectă | Recall cauzal | Diagnostic |",
            "|---|---:|---:|---:|---:|---:|---:|---|",
        )
    )
    for register_name, register in (summary_scores.get("registers") or {}).items():
        metrics = register.get("metrics") or {}
        diagnostics = "; ".join(register.get("diagnostics") or []) or "—"
        lines.append(
            "| "
            + " | ".join(
                (
                    markdown_cell(register_name),
                    format_decimal(register.get("score")),
                    format_integer(metrics.get("actual_word_count")),
                    format_decimal(metrics.get("event_coverage")),
                    format_decimal(metrics.get("valid_claim_ratio")),
                    format_decimal(metrics.get("event_order_accuracy")),
                    format_decimal(metrics.get("causal_recall")),
                    markdown_cell(diagnostics),
                )
            )
            + " |"
        )

    summary_data = summary_run.get("parsed") or {}
    if not isinstance(summary_data, Mapping):
        summary_data = {}
    generated_summaries = summary_data.get("summaries") or {}
    if not isinstance(generated_summaries, Mapping):
        generated_summaries = {}
    lines.extend(("", "## Rezumatele generate", ""))
    for register_name in ("simple", "elevated"):
        register = generated_summaries.get(register_name) or {}
        if not isinstance(register, Mapping):
            register = {}
        summary_text = register.get("summary_text")
        lines.extend(
            (
                f"### {register_name.capitalize()}",
                "",
                str(summary_text or "Rezumat indisponibil."),
                "",
            )
        )

    resume_history = metadata.get("resume_history") or []
    lines.extend(("## Istoricul reluărilor", ""))
    if resume_history:
        for index, entry in enumerate(resume_history, start=1):
            retried = ", ".join(entry.get("retried_tasks") or []) or "niciuna"
            skipped = ", ".join(entry.get("skipped_valid_tasks") or []) or "niciuna"
            finalized_invalid = (
                ", ".join(entry.get("finalized_invalid_tasks") or []) or "niciuna"
            )
            lines.append(
                f"{index}. `{entry.get('resumed_at', '—')}` — retrimise: {retried}; "
                f"reutilizate valide: {skipped}; finalizate ca invalide fără apel API: "
                f"{finalized_invalid}."
            )
    else:
        lines.append("Rularea nu a fost reluată.")

    lines.extend(
        (
            "",
            "## Fișierele verificabile ale rulării",
            "",
            "- `questions.json` și `questions.openrouter-response.json`",
            "- `summary.json` și `summary.openrouter-response.json`",
            "- `scores.json`",
            "- `metadata.json`",
            "",
            "Raportul a fost construit determinist din fișierele rulării, fără apel AI suplimentar.",
            "",
        )
    )
    report_path = run_dir / "raport-rulare.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Rulează {EXPERIMENT_NAME} prin OpenRouter.")
    parser.add_argument("--model", help="Suprascrie OPENROUTER_MODEL din config.local.env.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--max-tokens", type=int, default=60000)
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument(
        "--sync-results-only",
        action="store_true",
        help="Sincronizează registrul Excel din CSV fără apeluri OpenRouter.",
    )
    parser.add_argument(
        "--provider-order",
        action="append",
        metavar="PROVIDER",
        help=(
            "Fixează ordinea providerilor OpenRouter. Opțiunea poate fi repetată; "
            "exemplu: --provider-order DeepInfra."
        ),
    )
    parser.add_argument(
        "--resume-run",
        type=Path,
        help=(
            "Reia un folder run existent și retrimite exclusiv sarcinile fără JSON valid. "
            "Sarcinile deja reușite sunt încărcate de pe disc, fără apel API nou."
        ),
    )
    parser.add_argument(
        "--finalize-without-retry",
        action="store_true",
        help=(
            "Cu --resume-run, recalculează scorurile și rapoartele fără a retrimite "
            "sarcinile cu output invalid."
        ),
    )
    parser.add_argument(
        "--questions-reasoning-effort",
        choices=("none", "minimal", "low", "medium", "high", "xhigh", "max"),
        default="high",
        help="Nivelul de reasoning pentru întrebări (implicit: high).",
    )
    parser.add_argument(
        "--summary-reasoning-effort",
        choices=("none", "minimal", "low", "medium", "high", "xhigh", "max"),
        default=DEFAULT_SUMMARY_REASONING_EFFORT,
        help=(
            "Nivelul de reasoning pentru rezumat "
            f"(implicit: {DEFAULT_SUMMARY_REASONING_EFFORT})."
        ),
    )
    fallback_group = parser.add_mutually_exclusive_group()
    fallback_group.add_argument(
        "--allow-provider-fallbacks",
        dest="allow_provider_fallbacks",
        action="store_true",
        help="Permite OpenRouter să încerce alt provider pentru același model (implicit).",
    )
    fallback_group.add_argument(
        "--no-provider-fallbacks",
        dest="allow_provider_fallbacks",
        action="store_false",
        help="Dezactivează fallback-ul între provideri pentru această rulare.",
    )
    parser.set_defaults(allow_provider_fallbacks=True)
    args = parser.parse_args()

    if args.finalize_without_retry and not args.resume_run:
        parser.error("--finalize-without-retry necesită --resume-run.")

    if args.sync_results_only:
        if RESULTS_WORKBOOK_SYNC_HOOK is None:
            parser.error("Acest experiment nu configurează un registru Excel sincronizat.")
        results_csv_path = EXPERIMENT_DIR / "results" / "rezultate-experiment.csv"
        try:
            workbook_path = RESULTS_WORKBOOK_SYNC_HOOK(results_csv_path)
        except Exception as exc:
            parser.error(f"Registrul Excel nu a putut fi sincronizat: {exc}")
        print(f"Registru Excel actualizat: {workbook_path}")
        return 0

    local_env = load_local_env(args.config)
    api_key = local_env.get("OPENROUTER_API_KEY", "")
    if not api_key:
        parser.error(f"OPENROUTER_API_KEY lipsește din {args.config}.")

    previous_metadata: dict[str, Any] = {}
    run_dir: Path | None = None
    if args.resume_run:
        try:
            run_dir = resolve_resume_run(args.resume_run)
        except ValueError as exc:
            parser.error(str(exc))
        previous_metadata = read_json(run_dir / "metadata.json")
        resume_model = str(previous_metadata.get("requested_model") or "")
        if not resume_model:
            parser.error("Rularea de reluat nu declară requested_model în metadata.json.")
        if args.model and args.model != resume_model:
            parser.error(
                f"Rularea existentă folosește {resume_model!r}; nu poate fi reluată cu "
                f"modelul diferit {args.model!r}."
            )
        model_id = resume_model
    else:
        model_id = args.model or local_env.get("OPENROUTER_MODEL", "")
    if not model_id:
        parser.error(f"OPENROUTER_MODEL lipsește din {args.config}.")

    if args.finalize_without_retry:
        model_info = {
            "id": model_id,
            "name": previous_metadata.get("model_name") or model_id,
            "context_length": previous_metadata.get("context_length"),
            "supported_parameters": [],
        }
        print(f"Finalizez local rularea pentru modelul: {model_id}")
    else:
        print(f"Verific modelul: {model_id}")
        model_info = get_model_info(api_key, model_id, args.timeout)
        print(f"Model disponibil: {model_info.get('name', model_id)}")
    print(f"Context declarat: {model_info.get('context_length')} tokenuri")
    if not args.finalize_without_retry:
        print(f"Parametri suportați: {', '.join(model_info.get('supported_parameters') or [])}")
    if PREFLIGHT_HOOK is not None:
        PREFLIGHT_HOOK()
    if args.preflight_only:
        return 0

    graph = read_json(GRAPH_PATH)
    chapter_packet = build_chapter_packet()
    prompts = {
        "questions": render_question_prompt(graph),
        "summary": render_summary_prompt(chapter_packet),
    }
    reasoning_efforts = {
        "questions": args.questions_reasoning_effort,
        "summary": args.summary_reasoning_effort,
    }

    context_length = int(model_info.get("context_length") or 0)
    for name, prompt in prompts.items():
        estimate = math.ceil(len(prompt) / 2.5)
        print(f"Estimare conservatoare {name}: {estimate} tokenuri de input")
        if context_length and estimate + args.max_tokens > context_length:
            raise ValueError(
                f"Pachetul {name} plus outputul maxim depășesc contextul declarat al modelului."
            )

    results_csv_path = EXPERIMENT_DIR / "results" / "rezultate-experiment.csv"
    try:
        ensure_results_csv_writable(results_csv_path)
    except PermissionError as exc:
        parser.error(str(exc))

    resumed_at = datetime.now(timezone.utc)
    archived_attempts: dict[str, str] = {}
    invalid_tasks: list[str] = []
    if run_dir is not None:
        run_id = str(previous_metadata["run_id"])
        runs = {
            task_name: load_saved_task(run_dir, task_name, previous_metadata)
            for task_name in prompts
        }
        invalid_tasks = [name for name, run in runs.items() if not run["json_valid"]]
        tasks_to_run = [] if args.finalize_without_retry else invalid_tasks
        print(f"Reiau rularea existentă: {run_dir}")
        for task_name in prompts:
            if runs[task_name]["json_valid"]:
                print(f"Sar peste {task_name}: există deja JSON valid; nu fac apel API.")
            elif args.finalize_without_retry:
                print(
                    f"Nu retrimit {task_name}: output invalid păstrat pentru evaluare "
                    "și raportare."
                )
        if args.finalize_without_retry and invalid_tasks:
            print("Finalizez fără apeluri OpenRouter pentru sarcinile invalide.")
        elif not tasks_to_run:
            print("Nu există sarcini eșuate; refac doar scorurile și sincronizarea CSV.")
    else:
        timestamp = resumed_at
        run_id = timestamp.strftime("run-%Y%m%dT%H%M%SZ")
        model_dir = EXPERIMENT_DIR / model_folder_name(model_id)
        run_dir = model_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        runs: dict[str, dict[str, Any]] = {}
        tasks_to_run = list(prompts)
        print(f"Rezultatele vor fi salvate în: {run_dir}")

    for task_name in tasks_to_run:
        if previous_metadata:
            archived = archive_task_artifacts(run_dir, task_name)
            if archived is not None:
                archived_attempts[task_name] = str(archived.relative_to(run_dir))
                print(f"Încercarea veche pentru {task_name} a fost arhivată în: {archived}")
        print(
            f"Trimit sarcina {task_name} către {model_id} "
            f"cu reasoning={reasoning_efforts[task_name]}..."
        )
        try:
            runs[task_name] = run_task(
                task_name,
                prompts[task_name],
                api_key,
                model_id,
                model_info,
                run_dir,
                args.max_tokens,
                args.timeout,
                args.allow_provider_fallbacks,
                reasoning_efforts[task_name],
                args.provider_order,
            )
            print(
                f"{task_name}: primit în {runs[task_name]['duration_seconds']} s; "
                f"JSON valid={runs[task_name]['json_valid']}"
            )
        except Exception as exc:  # păstrăm eroarea fără a pierde cealaltă sarcină
            error = {"task": task_name, "error_type": type(exc).__name__, "message": str(exc)}
            save_json(run_dir / f"{task_name}.error.json", error)
            runs[task_name] = {"content": "", "parsed": None, "json_valid": False, **error}
            print(f"{task_name}: EROARE: {exc}")

    evaluator = load_evaluator()
    scores = evaluator.score_agent_submission(
        runs["questions"].get("content", ""),
        runs["summary"].get("content", ""),
        GRAPH_PATH,
        QUESTION_MANIFEST_PATH,
    )
    save_json(run_dir / "scores.json", scores)

    metadata = dict(previous_metadata)
    metadata.update(
        {
            "experiment": EXPERIMENT_NAME,
            "run_id": run_id,
            "timestamp_utc": metadata.get("timestamp_utc", resumed_at.isoformat()),
            "requested_model": model_id,
            "model_name": model_info.get("name"),
            "context_length": model_info.get("context_length"),
            "graph_path": str(GRAPH_PATH),
            "graph_sha256": sha256_file(GRAPH_PATH),
            "chapter_packet_path": str(CHAPTER_PACKET_PATH),
            "chapter_packet_sha256": sha256_file(CHAPTER_PACKET_PATH),
            "question_prompt_template_sha256": sha256_file(QUESTION_PROMPT_PATH),
            "summary_prompt_template_sha256": sha256_file(SUMMARY_PROMPT_PATH),
            "evaluator_sha256": sha256_file(EVALUATOR_PATH),
            "api_key_saved": False,
            "task_settings": {
                "questions": {"reasoning_effort": reasoning_efforts["questions"]},
                "summary": {"reasoning_effort": reasoning_efforts["summary"]},
            },
            "tasks": {
                key: {
                    field: value
                    for field, value in run.items()
                    if field not in {"content", "parsed"}
                }
                for key, run in runs.items()
            },
        }
    )
    metadata.update(EXTRA_METADATA)
    if previous_metadata:
        resume_history = list(metadata.get("resume_history") or [])
        resume_history.append(
            {
                "resumed_at": resumed_at.isoformat(),
                "retried_tasks": tasks_to_run,
                "skipped_valid_tasks": [
                    name for name in prompts if runs[name]["json_valid"]
                ],
                "finalized_invalid_tasks": (
                    invalid_tasks if args.finalize_without_retry else []
                ),
                "archived_attempts": archived_attempts,
            }
        )
        metadata["resume_history"] = resume_history
    save_json(run_dir / "metadata.json", metadata)
    report_path = generate_run_report(run_dir, metadata, scores, runs)
    print(f"Raport Markdown: {report_path}")

    try:
        upsert_results_csv(
            results_csv_path,
            metadata,
            scores,
            runs["questions"],
            runs["summary"],
            run_dir,
        )
    except PermissionError:
        print(
            "Rezultatele JSON au fost salvate, dar CSV-ul este blocat. Închide-l în "
            "Excel și rulează din nou aceeași comandă --resume-run; nu se vor repeta "
            "sarcinile care au deja JSON valid."
        )
        return 2

    if RESULTS_WORKBOOK_SYNC_HOOK is not None:
        try:
            workbook_path = RESULTS_WORKBOOK_SYNC_HOOK(results_csv_path)
        except Exception as exc:
            print(
                "CSV-ul a fost actualizat, dar registrul Excel nu a putut fi "
                f"sincronizat: {exc}"
            )
        else:
            print(f"Registru Excel actualizat: {workbook_path}")

    print(f"Scor întrebări: {scores['question_generation']['score']}")
    print(f"Scor rezumat: {scores['chapter_1_summary']['score']}")
    print(f"Scor general: {scores['overall_score']}")
    print(f"Finalizat: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
