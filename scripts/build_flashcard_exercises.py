"""Construiește flashcardurile direct din toate întrebările cumulative Qwen."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from exercise_builder_common import (
    DEFAULT_FLASHCARD_PATH,
    DEFAULT_GRAPH_PATH,
    DEFAULT_QUESTIONS_PATH,
    answer_text,
    evidence_node_ids,
    generated_question_count,
    graph_work_metadata,
    load_source_data,
    question_source_id,
    questions_by_category,
    round_robin_questions,
    source_summary,
    stable_id,
    write_json,
)


TECHNICAL_ID = r"(?:EV|CH|CHAR|LOC|CONCEPT|STATE|PART|WORK|G2_EDGE)_\d+"


def learner_facing_text(value: str) -> str:
    """Elimină ID-urile grafului din textele vizibile, păstrând explicațiile lor."""
    text = str(value or "").strip()
    text = re.sub(
        rf"\b{TECHNICAL_ID}\s*\(([^()]*)\)",
        lambda match: match.group(1).strip(),
        text,
    )
    text = re.sub(
        rf"\s*\((?:\s*{TECHNICAL_ID}\s*,?)+\)",
        "",
        text,
    )
    text = re.sub(rf"\b{TECHNICAL_ID}\b", "", text)
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r",\s*,", ",", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip(" ,")


def build_flashcard_deck(
    questions_path: Path,
    graph_path: Path,
    work_id: str | None = None,
) -> dict:
    question_payload, graph, nodes_by_id = load_source_data(questions_path, graph_path)
    work = graph_work_metadata(graph, work_id)
    categories = questions_by_category(question_payload)
    ordered_categories = list(categories)
    ordered_questions = round_robin_questions(categories, ordered_categories)

    cards: list[dict] = []
    card_evidence: dict[str, set[str]] = {}
    for category_id, question in ordered_questions:
        prompt = learner_facing_text(str(question.get("question_text", "")))
        answer = learner_facing_text(answer_text(question))
        if not prompt or not answer:
            continue
        source_id = question_source_id(question)
        node_ids = evidence_node_ids(question)
        characters = [
            nodes_by_id[node_id]["label"]
            for node_id in node_ids
            if node_id in nodes_by_id and nodes_by_id[node_id].get("type") == "Character"
        ]
        concepts = [
            nodes_by_id[node_id]["label"]
            for node_id in node_ids
            if node_id in nodes_by_id
            and nodes_by_id[node_id].get("type")
            in {"Theme", "Conflict", "Motif", "Value", "LiteraryTechnique"}
        ]
        card_id = stable_id("QF", source_id)
        cards.append(
            {
                "id": card_id,
                "front": prompt,
                "back": answer,
                "source": "qwen_cumulative_question_bank",
                "source_question_id": source_id,
                "category": category_id,
                "characters": list(dict.fromkeys(characters)),
                "concepts": list(dict.fromkeys(concepts)),
                "difficulty": int(question.get("declared_difficulty", 1) or 1),
                "evidence_node_ids": node_ids,
            }
        )
        card_evidence[card_id] = {
            node_id
            for node_id in node_ids
            if nodes_by_id.get(node_id, {}).get("type") not in {"Chapter", "Part", "Work"}
        }

    edges: list[dict] = []
    for index, left in enumerate(cards):
        left_nodes = card_evidence[left["id"]]
        for right in cards[index + 1 :]:
            right_nodes = card_evidence[right["id"]]
            shared = left_nodes & right_nodes
            if not shared:
                continue
            union = left_nodes | right_nodes
            weight = round(len(shared) / max(1, len(union)), 4)
            edges.append(
                {
                    "source": left["id"],
                    "target": right["id"],
                    "relation": "shared_graph_evidence",
                    "weight": weight,
                    "shared_node_ids": sorted(shared),
                }
            )

    quick_sets = []
    for index in range(0, len(cards), 4):
        group = cards[index : index + 4]
        if len(group) < 2:
            continue
        quick_sets.append(
            {
                "id": stable_id("FLIP", *(card["id"] for card in group)),
                "cards": [
                    {
                        "prompt": card["front"],
                        "answer": card["back"],
                        "source_question_id": card["source_question_id"],
                    }
                    for card in group
                ],
            }
        )

    expected_cards = generated_question_count(question_payload)
    if len(cards) != expected_cards:
        raise ValueError(
            f"Au fost construite {len(cards)} carduri din "
            f"{expected_cards} întrebări utilizabile."
        )
    return {
        "version": 2,
        "work_id": work["work_id"],
        "work": work,
        "exercise_type": "flashcards",
        "source": source_summary(question_payload, questions_path, graph_path),
        "card_count": len(cards),
        "quick_set_count": len(quick_sets),
        "cards": cards,
        "quick_sets": quick_sets,
        "edges": edges,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS_PATH)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH)
    parser.add_argument("--work-id", default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    payload = build_flashcard_deck(args.questions, args.graph, args.work_id)
    output = args.output or DEFAULT_FLASHCARD_PATH.with_name(f"{payload['work_id']}.json")
    write_json(output, payload)
    print(f"Flashcarduri: {payload['card_count']} -> {output}")


if __name__ == "__main__":
    main()
