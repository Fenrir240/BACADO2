"""Agregă evaluările individuale într-o țintă medie pentru span-scorer."""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rquge_ro.data import read_jsonl, validate_rating_records, write_jsonl  # noqa: E402


GROUP_FIELDS = ("question", "context", "gold_answer", "predicted_answer")


def aggregate(records: list[dict[str, Any]], minimum_annotators: int = 3) -> list[dict[str, Any]]:
    validate_rating_records(records)
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for record in records:
        key = tuple(str(record[field]).strip() for field in GROUP_FIELDS)
        groups.setdefault(key, []).append(record)
    output: list[dict[str, Any]] = []
    for index, (key, ratings) in enumerate(groups.items(), 1):
        annotators = [str(row.get("annotator_id", "")).strip() for row in ratings]
        named_annotators = [value for value in annotators if value]
        if len(named_annotators) != len(set(named_annotators)):
            raise ValueError(f"Grupul {index} conține annotator_id duplicat.")
        if len(ratings) < minimum_annotators:
            raise ValueError(
                f"Grupul {index} are {len(ratings)} evaluări; sunt necesare {minimum_annotators}."
            )
        scores = [float(row["score"]) for row in ratings]
        output.append(
            {
                "id": ratings[0].get("item_id", ratings[0].get("id", f"rating-{index}")),
                **dict(zip(GROUP_FIELDS, key)),
                "score": statistics.fmean(scores),
                "score_stdev": statistics.stdev(scores) if len(scores) > 1 else 0.0,
                "annotator_count": len(scores),
                "annotator_ids": named_annotators,
            }
        )
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_jsonl", type=Path)
    parser.add_argument("output_jsonl", type=Path)
    parser.add_argument("--minimum-annotators", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.minimum_annotators < 1:
        raise ValueError("--minimum-annotators trebuie să fie pozitiv.")
    result = aggregate(read_jsonl(args.input_jsonl), args.minimum_annotators)
    write_jsonl(args.output_jsonl, result)
    print(f"Am scris {len(result)} exemple agregate în {args.output_jsonl}.")


if __name__ == "__main__":
    main()
