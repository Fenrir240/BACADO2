"""Construiește exercițiile cronologice din ordinea explicită a nodurilor-eveniment."""

from __future__ import annotations

import argparse
from pathlib import Path

from exercise_builder_common import (
    DEFAULT_EXERCISE_DIR,
    DEFAULT_GRAPH_PATH,
    DEFAULT_QUESTIONS_PATH,
    event_text,
    graph_work_metadata,
    load_source_data,
    ordered_event_ids,
    question_metadata,
    question_source_id,
    questions_by_category,
    round_robin_questions,
    source_summary,
    stable_id,
    write_json,
)


CHRONOLOGY_CATEGORIES = ("TEMPORAL_ORDER", "CHARACTER_EVOLUTION")


def build_chronology_bank(
    questions_path: Path,
    graph_path: Path,
    work_id: str | None = None,
) -> dict:
    question_payload, graph, nodes_by_id = load_source_data(questions_path, graph_path)
    work = graph_work_metadata(graph, work_id)
    categories = questions_by_category(question_payload)
    selected = round_robin_questions(categories, CHRONOLOGY_CATEGORIES)
    exercises = []
    skipped = []
    for category_id, question in selected:
        source_id = question_source_id(question)
        event_ids = ordered_event_ids(question, nodes_by_id)
        if len(event_ids) < 3:
            skipped.append({"source_question_id": source_id, "reason": "fewer_than_3_ordered_events"})
            continue
        items = [
            {
                "event_id": event_id,
                "event": event_text(nodes_by_id[event_id]),
                "position": position,
            }
            for position, event_id in enumerate(event_ids, 1)
        ]
        if any(not item["event"] for item in items):
            raise ValueError(f"Cronologia {source_id} conține un eveniment fără text.")
        exercises.append(
            {
                "id": stable_id("CHRON", source_id),
                "instruction_source": str(question.get("question_text", "")).strip(),
                "items": items,
                **question_metadata(category_id, question),
            }
        )
    return {
        "version": 1,
        "work_id": work["work_id"],
        "work": work,
        "exercise_type": "chronology",
        "source": source_summary(question_payload, questions_path, graph_path),
        "eligible_categories": list(CHRONOLOGY_CATEGORIES),
        "exercise_count": len(exercises),
        "skipped_count": len(skipped),
        "skipped": skipped,
        "exercises": exercises,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS_PATH)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH)
    parser.add_argument("--work-id", default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    payload = build_chronology_bank(args.questions, args.graph, args.work_id)
    output = args.output or DEFAULT_EXERCISE_DIR.parent / payload["work_id"] / "chronology.json"
    write_json(output, payload)
    print(
        f"Cronologii: {payload['exercise_count']} "
        f"(omise: {payload['skipped_count']}) -> {output}"
    )


if __name__ == "__main__":
    main()
