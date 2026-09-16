"""Construiește seturi deterministe cu câte trei spații de completat."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from exercise_builder_common import (
    DEFAULT_EXERCISE_DIR,
    DEFAULT_GRAPH_PATH,
    DEFAULT_QUESTIONS_PATH,
    clean_text,
    chunks_by_sizes,
    evidence_node_ids,
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


COMPLETION_CATEGORIES = (
    "SIMPLE_FACT_LOWHOP",
    "CHARACTER_RELATION",
    "NARRATIVE_ACTION",
)


def _cloze_from_answer(question: dict, nodes_by_id: dict[str, dict]) -> tuple[str, str]:
    """Ascunde o entitate verificabilă din răspuns, păstrând propoziția originală."""
    prompt, answer = require_question_answer(question)
    candidates: list[str] = []
    for node_id in evidence_node_ids(question):
        node = nodes_by_id.get(node_id, {})
        node_type = node.get("type")
        if node_type not in {"Character", "Location", "Chapter", "Part", "Institution"}:
            continue
        values = [node.get("label"), *node.get("aliases", [])]
        if node_type == "Character" and node.get("label"):
            values.append(str(node["label"]).split()[0])
        for value in values:
            value = clean_text(value)
            if len(value) >= 3 and value.casefold() not in {item.casefold() for item in candidates}:
                candidates.append(value)

    # Unele răspunsuri indică în answer.node_ids numai evenimentul, deși în text
    # apare clar un personaj. Lista canonică permite detectarea lui fără NLP/AI.
    for node in nodes_by_id.values():
        if node.get("type") != "Character" or not node.get("label"):
            continue
        for value in (str(node["label"]), str(node["label"]).split()[0]):
            if len(value) >= 3 and value.casefold() not in {item.casefold() for item in candidates}:
                candidates.append(value)

    for candidate in sorted(candidates, key=lambda value: (-len(value), value.casefold())):
        match = re.search(
            rf"(?<!\w){re.escape(candidate)}(?!\w)",
            answer,
            flags=re.IGNORECASE,
        )
        if match:
            cloze = answer[: match.start()] + "____" + answer[match.end() :]
            if not re.search(r"[0-9A-Za-zĂÂÎȘȚăâîșț]", cloze.replace("____", "")):
                cloze = (
                    f"La întrebarea „{prompt.rstrip(' ?.!')}?”, "
                    "răspunsul corect este ____."
                )
            return cloze, match.group(0)

    return (
        f"La întrebarea „{prompt.rstrip(' ?.!')}?”, răspunsul corect este ____.",
        answer,
    )


def build_completion_bank(
    questions_path: Path,
    graph_path: Path,
    work_id: str | None = None,
) -> dict:
    question_payload, graph, nodes_by_id = load_source_data(questions_path, graph_path)
    work = graph_work_metadata(graph, work_id)
    categories = questions_by_category(question_payload)
    selected = round_robin_questions(categories, COMPLETION_CATEGORIES)
    usable_count = len(selected) - (len(selected) % 3)
    skipped = [
        {"source_question_id": question_source_id(question), "reason": "incomplete_group_of_three"}
        for _, question in selected[usable_count:]
    ]
    selected = selected[:usable_count]
    exercises = []
    for group in chunks_by_sizes(selected, [3] * (len(selected) // 3)):
        prompts = []
        answers = []
        source_ids = []
        cloze_sentences = []
        for category_id, question in group:
            prompt, _ = require_question_answer(question)
            cloze, answer = _cloze_from_answer(question, nodes_by_id)
            prompts.append(prompt.rstrip(" ?.!"))
            answers.append(answer)
            cloze_sentences.append(cloze)
            source_ids.append(question_source_id(question))
        text = "\n".join(
            f"{index}. {sentence}"
            for index, sentence in enumerate(cloze_sentences, 1)
        )
        exercises.append(
            {
                "id": stable_id("CLOZE", *source_ids),
                "text": text,
                "answers": answers,
                "prompts": prompts,
                "source_question_ids": source_ids,
                "category_ids": [category_id for category_id, _ in group],
            }
        )
    return {
        "version": 1,
        "work_id": work["work_id"],
        "work": work,
        "exercise_type": "completion",
        "source": source_summary(question_payload, questions_path, graph_path),
        "eligible_categories": list(COMPLETION_CATEGORIES),
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
    payload = build_completion_bank(args.questions, args.graph, args.work_id)
    output = args.output or DEFAULT_EXERCISE_DIR.parent / payload["work_id"] / "completion.json"
    write_json(output, payload)
    print(f"Completări: {payload['exercise_count']} -> {output}")


if __name__ == "__main__":
    main()
