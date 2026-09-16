"""Construiește grile și distractori determinist, fără apeluri suplimentare la Qwen."""

from __future__ import annotations

import argparse
from pathlib import Path

from exercise_builder_common import (
    DEFAULT_EXERCISE_DIR,
    DEFAULT_GRAPH_PATH,
    DEFAULT_QUESTIONS_PATH,
    answer_text,
    deterministic_shuffle,
    evidence_node_ids,
    graph_work_metadata,
    load_source_data,
    question_metadata,
    question_source_id,
    questions_by_category,
    require_question_answer,
    round_robin_questions,
    source_summary,
    stable_id,
    token_set,
    write_json,
)


MCQ_CATEGORIES = (
    "SIMPLE_FACT_LOWHOP",
    "CHARACTER_RELATION",
    "NARRATIVE_ACTION",
    "CAUSE_EFFECT",
)


def _answer_signature(question: dict, nodes_by_id: dict[str, dict]) -> tuple[str, ...]:
    types = {
        str(nodes_by_id[node_id].get("type"))
        for node_id in question.get("answer", {}).get("node_ids", [])
        if node_id in nodes_by_id
    }
    return tuple(sorted(types)) or ("Text",)


def _distractors(
    category_id: str,
    question: dict,
    candidates: list[tuple[str, dict]],
    nodes_by_id: dict[str, dict],
) -> list[str]:
    correct = answer_text(question)
    correct_tokens = token_set(correct)
    source_event_ids = {
        node_id
        for node_id in evidence_node_ids(question)
        if nodes_by_id.get(node_id, {}).get("type") == "NarrativeEvent"
    }
    signature = _answer_signature(question, nodes_by_id)
    prompt_tokens = token_set(str(question.get("question_text", "")))
    source_id = question_source_id(question)
    answer_node_ids = [
        str(node_id)
        for node_id in question.get("answer", {}).get("node_ids", [])
        if str(node_id) in nodes_by_id
    ]
    if len(answer_node_ids) == 1:
        answer_node = nodes_by_id[answer_node_ids[0]]
        answer_label = str(answer_node.get("label", "")).strip()
        answer_type = answer_node.get("type")
        typed_labels = [
            str(node.get("label", "")).strip()
            for node in sorted(nodes_by_id.values(), key=lambda item: str(item.get("id", "")))
            if node.get("type") == answer_type
            and str(node.get("label", "")).strip()
            and str(node.get("label", "")).strip().casefold() != correct.casefold()
        ]
        if answer_label.casefold() == correct.casefold() and len(typed_labels) >= 3:
            return typed_labels[:3]

    scored: list[tuple[float, str, str]] = []
    for candidate_category, candidate in candidates:
        candidate_id = question_source_id(candidate)
        candidate_answer = answer_text(candidate)
        if candidate_id == source_id or not candidate_answer or candidate_answer.casefold() == correct.casefold():
            continue
        candidate_event_ids = {
            node_id
            for node_id in evidence_node_ids(candidate)
            if nodes_by_id.get(node_id, {}).get("type") == "NarrativeEvent"
        }
        if source_event_ids & candidate_event_ids:
            continue
        candidate_answer_tokens = token_set(candidate_answer)
        answer_similarity = len(correct_tokens & candidate_answer_tokens) / max(
            1, len(correct_tokens | candidate_answer_tokens)
        )
        if answer_similarity >= 0.65:
            continue
        candidate_tokens = token_set(str(candidate.get("question_text", "")))
        overlap = len(prompt_tokens & candidate_tokens) / max(1, len(prompt_tokens | candidate_tokens))
        score = overlap
        if candidate_category == category_id:
            score += 5
        if _answer_signature(candidate, nodes_by_id) == signature:
            score += 7
        if candidate.get("declared_difficulty") == question.get("declared_difficulty"):
            score += 1
        scored.append((score, candidate_id, candidate_answer))
    scored.sort(key=lambda item: (-item[0], item[1]))
    result: list[str] = []
    for _, _, candidate_answer in scored:
        candidate_tokens = token_set(candidate_answer)
        too_similar = any(
            len(candidate_tokens & token_set(value))
            / max(1, len(candidate_tokens | token_set(value)))
            >= 0.8
            for value in result
        )
        if candidate_answer.casefold() not in {value.casefold() for value in result} and not too_similar:
            result.append(candidate_answer)
        if len(result) == 3:
            break
    if len(result) != 3:
        raise ValueError(f"Nu s-au putut crea trei distractori pentru {source_id}.")
    return result


def build_multiple_choice_bank(
    questions_path: Path,
    graph_path: Path,
    work_id: str | None = None,
) -> dict:
    question_payload, graph, nodes_by_id = load_source_data(questions_path, graph_path)
    work = graph_work_metadata(graph, work_id)
    categories = questions_by_category(question_payload)
    selected = round_robin_questions(categories, MCQ_CATEGORIES)
    exercises = []
    skipped = []
    for category_id, question in selected:
        prompt, correct = require_question_answer(question)
        source_id = question_source_id(question)
        try:
            distractors = _distractors(category_id, question, selected, nodes_by_id)
        except ValueError as exc:
            skipped.append({"source_question_id": source_id, "reason": str(exc)})
            continue
        options = deterministic_shuffle([correct, *distractors], source_id)
        item = {
            "id": stable_id("MCQ", source_id),
            "question": prompt,
            "options": options,
            "answer": correct,
            "answer_node_ids": list(question.get("answer", {}).get("node_ids", [])),
            **question_metadata(category_id, question),
        }
        if len(options) != 4 or options.count(correct) != 1:
            raise ValueError(f"Grila {item['id']} nu are patru opțiuni distincte.")
        exercises.append(item)
    return {
        "version": 1,
        "work_id": work["work_id"],
        "work": work,
        "exercise_type": "multiple_choice",
        "source": source_summary(question_payload, questions_path, graph_path),
        "eligible_categories": list(MCQ_CATEGORIES),
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
    payload = build_multiple_choice_bank(args.questions, args.graph, args.work_id)
    output = args.output or DEFAULT_EXERCISE_DIR.parent / payload["work_id"] / "multiple_choice.json"
    write_json(output, payload)
    print(f"Grile: {payload['exercise_count']} -> {output}")


if __name__ == "__main__":
    main()
