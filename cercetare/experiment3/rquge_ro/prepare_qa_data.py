"""Convertește XQuAD/SQuAD sau CSV românesc în JSONL-ul QA pentru RQUGE-Ro."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rquge_ro.data import validate_qa_records, write_jsonl  # noqa: E402


def convert_squad(path: Path, all_answers: bool = False) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    documents = payload.get("data", payload) if isinstance(payload, dict) else payload
    if not isinstance(documents, list):
        raise ValueError("Fișierul XQuAD/SQuAD trebuie să conțină lista 'data'.")
    output: list[dict[str, Any]] = []
    for document in documents:
        title = str(document.get("title", ""))
        for paragraph in document.get("paragraphs", []):
            context = str(paragraph.get("context", "")).strip()
            for qa in paragraph.get("qas", []):
                answers = qa.get("answers", [])
                if not answers:
                    continue
                selected = answers if all_answers else answers[:1]
                for answer_index, answer in enumerate(selected):
                    text = str(answer.get("text", "")).strip()
                    if not text:
                        continue
                    identifier = str(qa.get("id", len(output) + 1))
                    if all_answers:
                        identifier = f"{identifier}-answer-{answer_index + 1}"
                    output.append(
                        {
                            "id": identifier,
                            "question": str(qa.get("question", "")).strip(),
                            "context": context,
                            "answer": text,
                            "source": "xquad_ro",
                            "title": title,
                        }
                    )
    validate_qa_records(output)
    return output


def convert_csv(args: argparse.Namespace) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    with args.input.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV-ul nu are antet.")
        required = [args.question_column, args.context_column, args.answer_column]
        missing = [column for column in required if column not in reader.fieldnames]
        if missing:
            raise ValueError(f"Coloane inexistente în CSV: {', '.join(missing)}")
        if args.filter_column and args.filter_column not in reader.fieldnames:
            raise ValueError(f"Coloana de filtrare {args.filter_column!r} nu există.")
        for row_number, row in enumerate(reader, 2):
            if args.filter_column and str(row.get(args.filter_column, "")) != args.keep_value:
                continue
            answer = str(row.get(args.answer_column, "")).strip()
            if not answer:
                continue
            output.append(
                {
                    "id": str(row.get(args.id_column, "")).strip() or f"csv-{row_number}",
                    "question": str(row.get(args.question_column, "")).strip(),
                    "context": str(row.get(args.context_column, "")).strip(),
                    "answer": answer,
                    "source": args.source_name,
                }
            )
    validate_qa_records(output)
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="format", required=True)

    squad = subparsers.add_parser("squad", help="XQuAD/SQuAD JSON")
    squad.add_argument("input", type=Path)
    squad.add_argument("output", type=Path)
    squad.add_argument("--all-answers", action="store_true")

    table = subparsers.add_parser("csv", help="CSV cu nume de coloane configurabile")
    table.add_argument("input", type=Path)
    table.add_argument("output", type=Path)
    table.add_argument("--question-column", default="question")
    table.add_argument("--context-column", default="context")
    table.add_argument("--answer-column", default="answer")
    table.add_argument("--id-column", default="id")
    table.add_argument("--source-name", default="romanian_qa_csv")
    table.add_argument("--filter-column")
    table.add_argument("--keep-value")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = convert_squad(args.input, args.all_answers) if args.format == "squad" else convert_csv(args)
    write_jsonl(args.output, records)
    print(f"Am scris {len(records)} exemple QA în {args.output}.")


if __name__ == "__main__":
    main()
