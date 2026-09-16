"""Utilitare comune pentru băncile de exerciții construite din întrebările Qwen.

Modulul nu face apeluri către modele AI. Toate transformările sunt deterministe și
folosesc banca cumulativă de întrebări împreună cu graful canonic al romanului.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
import unicodedata
from pathlib import Path
from typing import Iterable, Sequence


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_QUESTIONS_PATH = ROOT_DIR / "cercetare-qwen" / "toate-intrebarile.json"
DEFAULT_GRAPH_PATH = ROOT_DIR / "cercetare" / "graf2" / "knowledge-graph.json"
DEFAULT_EXERCISE_DIR = ROOT_DIR / "data" / "exercises" / "ion"
DEFAULT_FLASHCARD_PATH = ROOT_DIR / "data" / "flashcards" / "ion.json"

WORD_RE = re.compile(r"[0-9A-Za-zĂÂÎȘȚăâîșț]+", re.UNICODE)


def read_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Fișierul {path} nu conține un obiect JSON.")
    return payload


def slugify(value: object) -> str:
    """Construiește ID-ul stabil al operei din titlul declarat în graf."""
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(character for character in text if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def graph_work_metadata(graph: dict, work_id: str | None = None) -> dict[str, str]:
    metadata = graph.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    nodes = graph.get("nodes", [])
    work_node = next(
        (node for node in nodes if isinstance(node, dict) and node.get("type") == "Work"),
        {},
    )
    author_node = next(
        (node for node in nodes if isinstance(node, dict) and node.get("type") == "Author"),
        {},
    )
    title = clean_text(metadata.get("work") or work_node.get("label"))
    author = clean_text(metadata.get("author") or author_node.get("label"))
    resolved_work_id = clean_text(work_id) or slugify(title)
    if not title:
        raise ValueError("Graful trebuie să declare opera în metadata.work sau într-un nod Work.")
    if not resolved_work_id:
        raise ValueError("Nu s-a putut deriva work_id din titlul operei.")
    return {"work_id": resolved_work_id, "title": title, "author": author}


def load_source_data(
    questions_path: Path = DEFAULT_QUESTIONS_PATH,
    graph_path: Path = DEFAULT_GRAPH_PATH,
) -> tuple[dict, dict, dict[str, dict]]:
    questions = read_json(questions_path)
    graph = read_json(graph_path)
    nodes = graph.get("nodes", [])
    if not isinstance(nodes, list):
        raise ValueError("Graful nu conține lista de noduri așteptată.")
    nodes_by_id = {
        str(node["id"]): node
        for node in nodes
        if isinstance(node, dict) and node.get("id")
    }
    return questions, graph, nodes_by_id


def questions_by_category(payload: dict) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for category in payload.get("categories", []):
        if not isinstance(category, dict):
            continue
        category_id = str(category.get("category_id", "")).strip()
        questions = category.get("questions", [])
        if category_id and isinstance(questions, list):
            result[category_id] = [
                item
                for item in questions
                if isinstance(item, dict)
                and item.get("status", "generated") == "generated"
                and clean_text(item.get("question_text"))
                and isinstance(item.get("answer"), dict)
                and clean_text(item["answer"].get("text"))
            ]
    return result


def generated_question_count(payload: dict) -> int:
    return sum(len(items) for items in questions_by_category(payload).values())


def round_robin_questions(
    categories: dict[str, list[dict]],
    selected_categories: Sequence[str],
) -> list[tuple[str, dict]]:
    """Intercalează categoriile ca seturile rezultate să rămână variate."""
    selected = [(category_id, categories.get(category_id, [])) for category_id in selected_categories]
    max_size = max((len(items) for _, items in selected), default=0)
    result: list[tuple[str, dict]] = []
    for index in range(max_size):
        for category_id, items in selected:
            if index < len(items):
                result.append((category_id, items[index]))
    return result


def question_source_id(question: dict) -> str:
    value = question.get("cumulative_id") or question.get("question_id")
    if not value:
        raise ValueError("O întrebare nu are cumulative_id sau question_id.")
    return str(value)


def stable_id(prefix: str, *values: object) -> str:
    raw = "\x1f".join(str(value) for value in values)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def deterministic_shuffle(values: Sequence[str], seed_value: str) -> list[str]:
    result = list(values)
    random.Random(seed_value).shuffle(result)
    return result


def clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def answer_text(question: dict) -> str:
    answer = question.get("answer", {})
    return clean_text(answer.get("text")) if isinstance(answer, dict) else ""


def evidence_node_ids(question: dict) -> list[str]:
    result: list[str] = []
    for container_name in ("answer", "evidence"):
        container = question.get(container_name, {})
        if not isinstance(container, dict):
            continue
        for node_id in container.get("node_ids", []):
            node_id = str(node_id)
            if node_id and node_id not in result:
                result.append(node_id)
    return result


def ordered_event_ids(question: dict, nodes_by_id: dict[str, dict]) -> list[str]:
    answer = question.get("answer", {})
    if not isinstance(answer, dict):
        return []
    result: list[str] = []
    for node_id in answer.get("ordered_node_ids", []):
        node_id = str(node_id)
        node = nodes_by_id.get(node_id, {})
        if node.get("type") == "NarrativeEvent" and node_id not in result:
            result.append(node_id)
    return result


def event_text(node: dict) -> str:
    attributes = node.get("attributes", {})
    if not isinstance(attributes, dict):
        attributes = {}
    return clean_text(
        attributes.get("simple_narration")
        or attributes.get("canonical_description")
        or attributes.get("action")
        or node.get("description")
        or node.get("label")
    )


def question_metadata(category_id: str, question: dict) -> dict:
    evidence = question.get("evidence", {})
    source = question.get("source", {})
    return {
        "category_id": category_id,
        "source_question_id": question_source_id(question),
        "difficulty": int(question.get("declared_difficulty", 1) or 1),
        "chapter_ids": list(evidence.get("chapter_ids", [])) if isinstance(evidence, dict) else [],
        "evidence_node_ids": evidence_node_ids(question),
        "source_run_id": source.get("run_id") if isinstance(source, dict) else None,
    }


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT_DIR.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def source_summary(
    question_payload: dict,
    questions_path: Path = DEFAULT_QUESTIONS_PATH,
    graph_path: Path = DEFAULT_GRAPH_PATH,
) -> dict:
    models = sorted(
        {
            str(question.get("source", {}).get("model"))
            for category in question_payload.get("categories", [])
            if isinstance(category, dict)
            for question in category.get("questions", [])
            if isinstance(question, dict)
            and isinstance(question.get("source"), dict)
            and question["source"].get("model")
        }
    )
    return {
        "question_bank": _display_path(questions_path),
        "knowledge_graph": _display_path(graph_path),
        "question_count": int(question_payload.get("question_count", 0) or 0),
        "models": models,
        "generation_mode": "deterministic_no_ai_calls",
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def token_set(value: str) -> set[str]:
    return {token.casefold() for token in WORD_RE.findall(value) if len(token) >= 3}


def balanced_group_sizes(item_count: int, maximum: int = 5, minimum: int = 3) -> list[int]:
    if item_count < minimum:
        return []
    group_count = math.ceil(item_count / maximum)
    while group_count > 1 and item_count // group_count < minimum:
        group_count -= 1
    base, extra = divmod(item_count, group_count)
    return [base + (1 if index < extra else 0) for index in range(group_count)]


def chunks_by_sizes(values: Sequence, sizes: Iterable[int]) -> list[list]:
    result: list[list] = []
    offset = 0
    for size in sizes:
        result.append(list(values[offset : offset + size]))
        offset += size
    return result


def require_question_answer(question: dict) -> tuple[str, str]:
    prompt = clean_text(question.get("question_text"))
    answer = answer_text(question)
    if not prompt or not answer:
        raise ValueError(f"Întrebarea {question_source_id(question)} nu are enunț și răspuns.")
    return prompt, answer
