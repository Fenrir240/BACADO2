"""Construiește seturi de asociere între întrebările Qwen și răspunsurile lor."""

from __future__ import annotations

import argparse
from pathlib import Path

from exercise_builder_common import (
    DEFAULT_EXERCISE_DIR,
    DEFAULT_GRAPH_PATH,
    DEFAULT_QUESTIONS_PATH,
    balanced_group_sizes,
    graph_work_metadata,
    load_source_data,
    question_source_id,
    questions_by_category,
    require_question_answer,
    round_robin_questions,
    source_summary,
    stable_id,
    write_json,
)


MATCHING_CATEGORIES = (
    "CHARACTER_RELATION",
    "NARRATIVE_ACTION",
    "CAUSE_EFFECT",
    "LITERARY_INTERPRETATION",
)


def build_matching_bank(
    questions_path: Path,
    graph_path: Path,
    work_id: str | None = None,
) -> dict:
    question_payload, graph, _ = load_source_data(questions_path, graph_path)
    work = graph_work_metadata(graph, work_id)
    categories = questions_by_category(question_payload)
    selected = round_robin_questions(categories, MATCHING_CATEGORIES)
    group_sizes = balanced_group_sizes(len(selected), maximum=5, minimum=3)
    groups: list[list[tuple[str, dict]]] = [[] for _ in group_sizes]
    answer_frequencies: dict[str, int] = {}
    for _, question in selected:
        _, answer = require_question_answer(question)
        key = answer.casefold()
        answer_frequencies[key] = answer_frequencies.get(key, 0) + 1
    prioritized = sorted(
        enumerate(selected),
        key=lambda item: (
            -answer_frequencies[require_question_answer(item[1][1])[1].casefold()],
            item[0],
        ),
    )
    for _, item in prioritized:
        category_id, question = item
        _, answer = require_question_answer(question)
        candidates = [
            index
            for index, group in enumerate(groups)
            if len(group) < group_sizes[index]
            and answer.casefold()
            not in {
                require_question_answer(group_question)[1].casefold()
                for _, group_question in group
            }
        ]
        if not candidates:
            raise ValueError(
                "Întrebările nu pot fi împărțite în seturi fără răspunsuri duplicate."
            )
        target = min(
            candidates,
            key=lambda index: (
                sum(1 for existing_category, _ in groups[index] if existing_category == category_id),
                len(groups[index]) / group_sizes[index],
                index,
            ),
        )
        groups[target].append(item)
    exercises = []
    for group in groups:
        pairs = []
        source_ids = []
        seen_answers: set[str] = set()
        for _, question in group:
            prompt, answer = require_question_answer(question)
            if answer.casefold() in seen_answers:
                raise ValueError("Un set de asociere ar avea două răspunsuri identice.")
            seen_answers.add(answer.casefold())
            source_id = question_source_id(question)
            source_ids.append(source_id)
            pairs.append(
                {
                    "left": prompt,
                    "right": answer,
                    "source_question_id": source_id,
                }
            )
        exercises.append(
            {
                "id": stable_id("MATCH", *source_ids),
                "pairs": pairs,
                "source_question_ids": source_ids,
                "category_ids": [category_id for category_id, _ in group],
            }
        )
    return {
        "version": 1,
        "work_id": work["work_id"],
        "work": work,
        "exercise_type": "matching",
        "source": source_summary(question_payload, questions_path, graph_path),
        "eligible_categories": list(MATCHING_CATEGORIES),
        "exercise_count": len(exercises),
        "pair_count": sum(len(item["pairs"]) for item in exercises),
        "exercises": exercises,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS_PATH)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH)
    parser.add_argument("--work-id", default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    payload = build_matching_bank(args.questions, args.graph, args.work_id)
    output = args.output or DEFAULT_EXERCISE_DIR.parent / payload["work_id"] / "matching.json"
    write_json(output, payload)
    print(
        f"Asocieri: {payload['exercise_count']} seturi / {payload['pair_count']} perechi "
        f"-> {output}"
    )


if __name__ == "__main__":
    main()
