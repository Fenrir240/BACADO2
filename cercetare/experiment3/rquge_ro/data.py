"""Utilitare pure pentru datele și scorurile RQUGE-Ro."""

from __future__ import annotations

import json
import math
import random
import re
import statistics
import unicodedata
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


QA_REQUIRED_FIELDS = ("question", "context", "answer")
RATING_REQUIRED_FIELDS = (
    "question",
    "context",
    "gold_answer",
    "predicted_answer",
    "score",
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: fiecare linie trebuie să fie obiect JSON.")
        records.append(value)
    return records


def write_jsonl(path: Path, records: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(dict(record), ensure_ascii=False) + "\n")


def require_text(record: Mapping[str, Any], field: str, record_index: int) -> str:
    value = str(record.get(field, "")).strip()
    if not value:
        raise ValueError(f"Înregistrarea {record_index} nu conține câmpul text {field!r}.")
    return value


def validate_qa_records(records: Sequence[Mapping[str, Any]]) -> None:
    if not records:
        raise ValueError("Setul QA este gol.")
    for index, record in enumerate(records, 1):
        for field in QA_REQUIRED_FIELDS:
            require_text(record, field, index)


def validate_rating_records(records: Sequence[Mapping[str, Any]]) -> None:
    if not records:
        raise ValueError("Setul de scoruri umane este gol.")
    for index, record in enumerate(records, 1):
        for field in RATING_REQUIRED_FIELDS[:-1]:
            require_text(record, field, index)
        score = float(record.get("score", math.nan))
        if not 1.0 <= score <= 5.0:
            raise ValueError(
                f"Înregistrarea {index} are score={score}; RQUGE folosește intervalul [1, 5]."
            )


def format_qa_input(question: str, context: str) -> str:
    """Format unic, folosit identic la antrenare și inferență."""

    return f"întrebare: {question.strip()} context: {context.strip()}"


def format_span_input(
    question: str,
    gold_answer: str,
    predicted_answer: str,
    context: str,
) -> str:
    """Ordinea câmpurilor urmează span scorer-ul din paper-ul RQUGE."""

    return (
        f"{question.strip()} <q> {gold_answer.strip()} <r> "
        f"{predicted_answer.strip()} <c> {context.strip()}"
    )


def normalize_answer(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).lower()
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    return " ".join(value.split())


def normalized_exact_match(prediction: str, reference: str) -> float:
    return float(normalize_answer(prediction) == normalize_answer(reference))


def token_f1(prediction: str, reference: str) -> float:
    predicted_tokens = normalize_answer(prediction).split()
    reference_tokens = normalize_answer(reference).split()
    if not predicted_tokens and not reference_tokens:
        return 1.0
    if not predicted_tokens or not reference_tokens:
        return 0.0
    remaining: dict[str, int] = {}
    for token in reference_tokens:
        remaining[token] = remaining.get(token, 0) + 1
    overlap = 0
    for token in predicted_tokens:
        if remaining.get(token, 0) > 0:
            overlap += 1
            remaining[token] -= 1
    if overlap == 0:
        return 0.0
    precision = overlap / len(predicted_tokens)
    recall = overlap / len(reference_tokens)
    return 2 * precision * recall / (precision + recall)


def clamp_score(value: float, minimum: float = 1.0, maximum: float = 5.0) -> float:
    return max(minimum, min(maximum, float(value)))


def deterministic_split(
    records: Sequence[dict[str, Any]],
    validation_fraction: float = 0.1,
    seed: int = 42,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not 0.0 < validation_fraction < 1.0:
        raise ValueError("validation_fraction trebuie să fie strict între 0 și 1.")
    if len(records) < 2:
        raise ValueError("Sunt necesare minimum două înregistrări pentru împărțire.")
    shuffled = [dict(record) for record in records]
    random.Random(seed).shuffle(shuffled)
    validation_count = max(1, round(len(shuffled) * validation_fraction))
    validation_count = min(validation_count, len(shuffled) - 1)
    return shuffled[validation_count:], shuffled[:validation_count]


def deterministic_group_split(
    records: Sequence[dict[str, Any]],
    group_fields: Sequence[str],
    validation_fraction: float = 0.1,
    seed: int = 42,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Împarte grupuri întregi pentru a evita contaminarea între train și validare."""

    if not 0.0 < validation_fraction < 1.0:
        raise ValueError("validation_fraction trebuie să fie strict între 0 și 1.")
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for record in records:
        key = tuple(str(record.get(field, "")) for field in group_fields)
        grouped.setdefault(key, []).append(dict(record))
    groups = list(grouped.values())
    if len(groups) < 2:
        raise ValueError("Sunt necesare minimum două grupuri pentru împărțire.")
    random.Random(seed).shuffle(groups)
    target = max(1, round(len(records) * validation_fraction))
    validation_groups: list[list[dict[str, Any]]] = []
    validation_size = 0
    while len(groups) > 1 and (validation_size < target or not validation_groups):
        group = groups.pop()
        validation_groups.append(group)
        validation_size += len(group)
    train = [record for group in groups for record in group]
    validation = [record for group in validation_groups for record in group]
    return train, validation


def summary_statistics(values: Sequence[float]) -> dict[str, float | int]:
    if not values:
        return {"count": 0, "mean": 0.0, "median": 0.0, "stdev": 0.0}
    return {
        "count": len(values),
        "mean": round(statistics.fmean(values), 6),
        "median": round(statistics.median(values), 6),
        "stdev": round(statistics.stdev(values), 6) if len(values) > 1 else 0.0,
    }
