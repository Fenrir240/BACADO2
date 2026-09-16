"""Utilitare comune pentru raportarea costurilor reale returnate de OpenRouter."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


SUMMARY_FIELDS = (
    "api_calls",
    "prompt_tokens",
    "completion_tokens",
    "reasoning_tokens",
    "total_tokens",
    "cost_usd",
)


def empty_cost_summary() -> dict[str, int | float]:
    return {
        "api_calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "reasoning_tokens": 0,
        "total_tokens": 0,
        "cost_usd": 0.0,
    }


def _number(value: Any) -> int | float:
    if isinstance(value, bool):
        return 0
    return value if isinstance(value, (int, float)) else 0


def _reasoning_tokens(usage: Mapping[str, Any]) -> int:
    direct = _number(usage.get("reasoning_tokens"))
    details = usage.get("completion_tokens_details")
    nested = _number(details.get("reasoning_tokens")) if isinstance(details, Mapping) else 0
    return int(direct or nested)


def summarize_usages(usages: Iterable[Mapping[str, Any] | None]) -> dict[str, int | float]:
    summary = empty_cost_summary()
    for raw_usage in usages:
        usage = raw_usage if isinstance(raw_usage, Mapping) else {}
        summary["api_calls"] += 1
        summary["prompt_tokens"] += int(_number(usage.get("prompt_tokens")))
        summary["completion_tokens"] += int(_number(usage.get("completion_tokens")))
        summary["reasoning_tokens"] += _reasoning_tokens(usage)
        summary["total_tokens"] += int(_number(usage.get("total_tokens")))
        summary["cost_usd"] += float(_number(usage.get("cost")))
    summary["cost_usd"] = round(float(summary["cost_usd"]), 10)
    return summary


def combine_cost_summaries(
    summaries: Iterable[Mapping[str, Any] | None],
) -> dict[str, int | float]:
    result = empty_cost_summary()
    for summary in summaries:
        if not isinstance(summary, Mapping):
            continue
        for field in SUMMARY_FIELDS:
            result[field] += _number(summary.get(field))
    for field in SUMMARY_FIELDS[:-1]:
        result[field] = int(result[field])
    result["cost_usd"] = round(float(result["cost_usd"]), 10)
    return result


def usages_from_attempt_metadata(run_dirs: Iterable[Path]) -> list[dict[str, Any]]:
    usages: list[dict[str, Any]] = []
    for run_dir in sorted({path.resolve() for path in run_dirs}):
        for metadata_path in sorted(
            run_dir.glob("*/**/attempts/attempt-*/task-metadata.json")
        ):
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            usage = metadata.get("usage") if isinstance(metadata, dict) else None
            usages.append(dict(usage) if isinstance(usage, Mapping) else {})
    return usages


def response_paths_by_section(work_dir: Path) -> dict[str, set[Path]]:
    return {
        section_id: {
            path.resolve()
            for path in (work_dir / section_id).glob("**/response.openrouter.json")
            if path.is_file()
        }
        for section_id in (
            "intelegere-opera",
            "testare-rapida",
            "construieste-eseu",
        )
    }


def summarize_openrouter_responses(paths: Iterable[Path]) -> dict[str, int | float]:
    usages: list[dict[str, Any]] = []
    for response_path in sorted({path.resolve() for path in paths}):
        try:
            response = json.loads(response_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        usage = response.get("usage") if isinstance(response, dict) else None
        usages.append(dict(usage) if isinstance(usage, Mapping) else {})
    return summarize_usages(usages)


def section_costs_from_responses(
    paths_by_section: Mapping[str, Iterable[Path]],
) -> dict[str, dict[str, int | float]]:
    return {
        section_id: summarize_openrouter_responses(paths_by_section.get(section_id, []))
        for section_id in (
            "intelegere-opera",
            "testare-rapida",
            "construieste-eseu",
        )
    }


def build_cost_report(
    *,
    work: Mapping[str, Any],
    total_run_dir: Path,
    current_by_section: Mapping[str, Mapping[str, Any]],
    previous_report: Mapping[str, Any] | None = None,
    lifetime_by_section: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    previous_lifetime = (
        previous_report.get("lifetime")
        if isinstance(previous_report, Mapping)
        and isinstance(previous_report.get("lifetime"), Mapping)
        else {}
    )
    previous_by_section = (
        previous_lifetime.get("by_section")
        if isinstance(previous_lifetime, Mapping)
        and isinstance(previous_lifetime.get("by_section"), Mapping)
        else {}
    )
    section_ids = (
        "intelegere-opera",
        "testare-rapida",
        "construieste-eseu",
    )
    normalized_current = {
        section_id: combine_cost_summaries([current_by_section.get(section_id)])
        for section_id in section_ids
    }
    normalized_lifetime = (
        {
            section_id: combine_cost_summaries([lifetime_by_section.get(section_id)])
            for section_id in section_ids
        }
        if isinstance(lifetime_by_section, Mapping)
        else {
            section_id: combine_cost_summaries(
                [previous_by_section.get(section_id), normalized_current[section_id]]
            )
            for section_id in section_ids
        }
    )
    return {
        "schema_version": 1,
        "report_type": "complete_work_openrouter_cost",
        "currency": "USD",
        "cost_source": "OpenRouter usage.cost returned for each API call",
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "work": dict(work),
        "latest_total_run": {
            "run_dir": str(total_run_dir),
            "by_section": normalized_current,
            "total": combine_cost_summaries(normalized_current.values()),
        },
        "lifetime": {
            "by_section": normalized_lifetime,
            "total": combine_cost_summaries(normalized_lifetime.values()),
        },
    }
