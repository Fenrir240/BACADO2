"""Rulează secvențial pachetele Qwen și păstrează rezultate și consumul de tokeni.

Fluxul curent are 24 de sarcini independente: opt categorii de întrebări,
treisprezece rezumate de capitol și trei elemente compoziționale. Fiecare încercare
este salvată imediat, astfel încât o rulare întreruptă poate fi reluată fără
repetarea rezultatelor deja valide. Manifestele vechi cu 21 de sarcini rămân
compatibile.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import re
import sys
import time
import urllib.error
import urllib.request
import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
QUESTION_PROMPT_DIR = BASE_DIR / "prompturi intrebari"
QUESTION_PACKET_DIR = BASE_DIR / "graph-packets"
SUMMARY_DIR = BASE_DIR / "prompturi rezumate capitole"
COMPOSITION_DIR = BASE_DIR / "prompturi elemente compozitionale"
RUNS_DIR = BASE_DIR / "rulari"
GLOBAL_QUESTIONS_TEXT_PATH = BASE_DIR / "toate-intrebarile-pe-categorii.txt"
GLOBAL_QUESTIONS_JSON_PATH = BASE_DIR / "toate-intrebarile.json"
DEFAULT_CONFIG_PATH = BASE_DIR / "config.local.env"
LEGACY_CONFIG_PATH = BASE_DIR.parent / "cercetare" / "experiment2" / "config.local.env"
DEFAULT_MODEL = "qwen/qwen3.7-flash"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
QWEN_CHARS_PER_TOKEN = 3.142
DEFAULT_QUESTION_REASONING_EFFORT = "medium"
DEFAULT_SUMMARY_REASONING_EFFORT = "medium"
DEFAULT_SUMMARY_MAX_ATTEMPTS = 1
TERMINAL_GENERATION_STATUSES = {"succeeded", "unparseable"}

QUESTION_FILES = (
    ("01-intrebari-simple-lowhop.md", "01-simple-facts.packet.json"),
    ("02-relatii-dintre-personaje-lowhop.md", "02-character-relations.packet.json"),
    ("03-actiune-narativa-lowhop.md", "03-narrative-actions.packet.json"),
    ("04-ordine-narativa-midhop.md", "04-temporal-order.packet.json"),
    ("05-cauza-si-consecinta-midhop.md", "05-cause-effect.packet.json"),
    ("06-evolutia-personajelor-highhop.md", "06-character-evolution.packet.json"),
    ("07-teme-conflicte-si-simboluri-highhop.md", "07-literary-concepts.packet.json"),
    ("08-comparatii-intre-capitole-highhop.md", "08-cross-chapter-comparison.packet.json"),
)


@dataclass(frozen=True)
class TaskSpec:
    key: str
    task_type: str
    order: int
    slug: str
    label: str
    prompt_path: Path
    packet_path: Path
    expected_id: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_local_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def save_json(path: Path, value: Any) -> None:
    atomic_write_text(
        path,
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
    )


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value.replace("/", "__")).strip("._")


def relative_display(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(BASE_DIR.parent.resolve()))
    except ValueError:
        return str(path.resolve())


def replace_exactly_once(template: str, token: str, replacement: str) -> str:
    count = template.count(token)
    if count != 1:
        raise ValueError(f"{token} trebuie să apară exact o dată; apare de {count} ori.")
    return template.replace(token, replacement, 1)


def build_task_specs(question_packet_dir: Path = QUESTION_PACKET_DIR) -> list[TaskSpec]:
    specs: list[TaskSpec] = []
    for order, (prompt_name, packet_name) in enumerate(QUESTION_FILES, start=1):
        prompt_path = QUESTION_PROMPT_DIR / prompt_name
        packet_path = question_packet_dir / packet_name
        if not prompt_path.is_file() or not packet_path.is_file():
            raise FileNotFoundError(f"Lipsește perechea {prompt_path} / {packet_path}.")
        packet = read_json(packet_path)
        metadata = packet.get("metadata") or {}
        category_id = str(metadata.get("category_id") or "")
        if not category_id:
            raise ValueError(f"Packetul {packet_path} nu declară metadata.category_id.")
        slug = packet_path.name.removesuffix(".packet.json")
        specs.append(
            TaskSpec(
                key=f"questions/{slug}",
                task_type="questions",
                order=order,
                slug=slug,
                label=category_id,
                prompt_path=prompt_path,
                packet_path=packet_path,
                expected_id=category_id,
            )
        )

    summary_packets = sorted(SUMMARY_DIR.glob("[0-9][0-9]-*.graph-packet.json"))
    if len(summary_packets) != 13:
        raise ValueError(f"Sunt necesare 13 packeturi de rezumat; am găsit {len(summary_packets)}.")
    for order, packet_path in enumerate(summary_packets, start=1):
        stem = packet_path.name.removesuffix(".graph-packet.json")
        prompt_path = SUMMARY_DIR / f"{stem}.prompt.md"
        if not prompt_path.is_file():
            raise FileNotFoundError(f"Lipsește promptul {prompt_path}.")
        packet = read_json(packet_path)
        metadata = packet.get("metadata") or {}
        chapter_id = str(metadata.get("chapter_id") or "")
        chapter_title = str(metadata.get("chapter_title") or chapter_id)
        if not chapter_id:
            raise ValueError(f"Packetul {packet_path} nu declară metadata.chapter_id.")
        specs.append(
            TaskSpec(
                key=f"summaries/{stem}",
                task_type="summaries",
                order=order,
                slug=stem,
                label=chapter_title,
                prompt_path=prompt_path,
                packet_path=packet_path,
                expected_id=chapter_id,
            )
        )

    composition_packets = sorted(COMPOSITION_DIR.glob("[0-9][0-9]-*.graph-packet.json"))
    if len(composition_packets) != 3:
        raise ValueError(
            "Sunt necesare 3 packeturi pentru elementele compoziționale; "
            f"am găsit {len(composition_packets)}."
        )
    for order, packet_path in enumerate(composition_packets, start=1):
        stem = packet_path.name.removesuffix(".graph-packet.json")
        prompt_path = COMPOSITION_DIR / f"{stem}.prompt.md"
        if not prompt_path.is_file():
            raise FileNotFoundError(f"Lipsește promptul {prompt_path}.")
        packet = read_json(packet_path)
        metadata = packet.get("metadata") or {}
        element_id = str(metadata.get("element_id") or "")
        element_name = str(metadata.get("element_name") or element_id)
        if not element_id:
            raise ValueError(f"Packetul {packet_path} nu declară metadata.element_id.")
        specs.append(
            TaskSpec(
                key=f"compositions/{stem}",
                task_type="compositions",
                order=order,
                slug=stem,
                label=element_name,
                prompt_path=prompt_path,
                packet_path=packet_path,
                expected_id=element_id,
            )
        )
    return specs


def question_event_ids(packet: Mapping[str, Any]) -> set[str]:
    return {
        str(event_id)
        for slot in ((packet.get("selection") or {}).get("question_slots") or [])
        for event_id in slot.get("event_ids") or []
    }


def load_question_packet_builder() -> Any:
    module_name = "cercetare_qwen_question_packet_builder"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    path = BASE_DIR / "build_graph_packets.py"
    module_spec = importlib.util.spec_from_file_location(module_name, path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(f"Nu pot încărca generatorul de packeturi: {path}")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module


def question_selection_history() -> tuple[set[str], list[str], int]:
    """Reconstituie istoricul din loturile rezervate și din rulările vechi."""
    used: set[str] = set()
    sources: list[str] = []
    maximum_batch = 0
    selection_files = sorted(RUNS_DIR.glob("**/question-selection.json")) if RUNS_DIR.is_dir() else []
    selection_run_dirs = {path.parent.resolve() for path in selection_files}
    for path in selection_files:
        value = read_json(path)
        used.update(str(event_id) for event_id in value.get("selected_event_ids") or [])
        maximum_batch = max(maximum_batch, int(value.get("batch_number") or 0))
        sources.append(relative_display(path))

    # Manifestele create înainte de istoricul persistent au folosit packeturile statice
    # ale primului lot. Mai multe astfel de rulări reprezintă același lot, nu loturi noi.
    legacy_detected = False
    if RUNS_DIR.is_dir():
        for manifest_path in sorted(RUNS_DIR.glob("**/manifest.json")):
            if manifest_path.parent.resolve() in selection_run_dirs:
                continue
            manifest = read_json(manifest_path)
            question_tasks = [
                item for item in manifest.get("tasks") or []
                if str(item.get("task_type") or "") == "questions"
            ]
            if question_tasks:
                legacy_detected = True
                sources.append(relative_display(manifest_path))
        if legacy_detected:
            for _, packet_name in QUESTION_FILES:
                path = QUESTION_PACKET_DIR / packet_name
                if path.is_file():
                    used.update(question_event_ids(read_json(path)))
            maximum_batch = max(maximum_batch, 1)
    return used, sources, maximum_batch


def reserve_question_batch(run_dir: Path) -> tuple[Path, dict[str, Any]]:
    """Creează și rezervă următorul lot înaintea primului apel API."""
    used, sources, maximum_batch = question_selection_history()
    batch_number = maximum_batch + 1
    packet_dir = run_dir / "inputs" / "question-packets"
    builder = load_question_packet_builder()
    rows, selected = builder.build_packet_set(
        builder.load_graph(),
        packet_dir,
        excluded_event_ids=used,
        batch_number=batch_number,
    )
    overlap = used & selected
    if overlap:
        raise ValueError(f"Lotul nou reutilizează evenimente istorice: {sorted(overlap)}")
    categories: list[dict[str, Any]] = []
    for row in rows:
        packet = read_json(packet_dir / row["filename"])
        categories.append(
            {
                "category_id": row["category_id"],
                "packet_file": row["filename"],
                "selected_event_ids": row["selected_event_ids"],
                "question_slots": (packet.get("selection") or {}).get("question_slots") or [],
            }
        )
    record = {
        "schema_version": 1,
        "batch_number": batch_number,
        "algorithm_version": builder.SELECTION_ALGORITHM_VERSION,
        "history_source_files": sources,
        "excluded_previous_event_count": len(used),
        "excluded_previous_event_ids": sorted(used),
        "selected_event_count": len(selected),
        "selected_event_ids": sorted(selected),
        "categories": categories,
    }
    save_json(run_dir / "question-selection.json", record)
    return packet_dir, record


def render_prompt(spec: TaskSpec) -> tuple[str, dict[str, Any]]:
    packet = read_json(spec.packet_path)
    packet_text = spec.packet_path.read_text(encoding="utf-8").strip()
    prompt = replace_exactly_once(
        spec.prompt_path.read_text(encoding="utf-8"),
        "{{GRAPH_PACKET}}",
        packet_text,
    )
    return prompt, packet


def api_json(
    url: str,
    api_key: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: int = 1200,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://localhost/bac-romana-qwen-packets",
            "X-Title": "Bac Romana - pachete Qwen",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenRouter nu a putut fi contactat: {exc}") from exc


def get_model_info(api_key: str, model_id: str, timeout: int) -> dict[str, Any]:
    response = api_json(f"{OPENROUTER_BASE_URL}/models/user", api_key, timeout=timeout)
    for model in response.get("data", []):
        if model.get("id") == model_id or model.get("canonical_slug") == model_id:
            return model
    raise ValueError(f"Modelul {model_id!r} nu apare în /models/user pentru această cheie.")


def build_request(
    model_id: str,
    model_info: Mapping[str, Any],
    prompt: str,
    *,
    max_tokens: int,
    reasoning_effort: str,
    allow_provider_fallbacks: bool,
    provider_order: list[str] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    supported = set(model_info.get("supported_parameters") or [])
    provider: dict[str, Any] = {
        "allow_fallbacks": allow_provider_fallbacks,
        "require_parameters": True,
        "data_collection": "deny",
    }
    if provider_order:
        provider["order"] = provider_order
    system_instruction = (
        "Participi la un experiment controlat. Folosește exclusiv datele din "
        "prompt și returnează exclusiv obiectul JSON solicitat."
    )
    if reasoning_effort != "none":
        system_instruction += (
            " Înainte de răspuns, verifică intern fiecare cerință, fiecare ID, "
            "fiecare traseu și toate calculele de hop-uri. Nu include analiza internă "
            "în obiectul JSON final."
        )
    payload: dict[str, Any] = {
        "model": model_id,
        "messages": [
            {
                "role": "system",
                "content": system_instruction,
            },
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "provider": provider,
    }
    applied: dict[str, Any] = {
        "stream": False,
        "provider.allow_fallbacks": allow_provider_fallbacks,
        "provider.require_parameters": True,
        "provider.data_collection": "deny",
    }
    if provider_order:
        applied["provider.order"] = provider_order
    if "max_tokens" in supported:
        payload["max_tokens"] = max_tokens
        applied["max_tokens"] = max_tokens
    if "temperature" in supported:
        payload["temperature"] = 0
        applied["temperature"] = 0
    if "response_format" in supported or "structured_outputs" in supported:
        payload["response_format"] = {"type": "json_object"}
        applied["response_format"] = {"type": "json_object"}
    if "reasoning" in supported:
        reasoning_info = model_info.get("reasoning") or {}
        supported_efforts = reasoning_info.get("supported_efforts") or []
        if reasoning_effort == "none" and reasoning_info.get("mandatory"):
            raise ValueError("Modelul declară reasoning obligatoriu; effort=none nu este permis.")
        if reasoning_effort != "none" and supported_efforts and reasoning_effort not in supported_efforts:
            raise ValueError(
                f"Reasoning effort {reasoning_effort!r} nu este suportat: {supported_efforts}."
            )
        payload["reasoning"] = {"effort": reasoning_effort, "exclude": True}
        applied["reasoning"] = {"effort": reasoning_effort, "exclude": True}
    return payload, applied


def build_validator_retry_feedback(spec: TaskSpec, latest: Mapping[str, Any] | None) -> str | None:
    """Validarea este diagnostică; întrebările și rezumatele nu primesc retry."""
    return None


def extract_content(response: Mapping[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        raise ValueError("Răspunsul OpenRouter nu conține choices.")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "".join(
            str(item.get("text") or "") for item in content if isinstance(item, Mapping)
        ).strip()
    finish_reason = choices[0].get("finish_reason") or choices[0].get("native_finish_reason")
    raise ValueError(f"Răspunsul nu conține text final (finish_reason={finish_reason!r}).")


def verify_returned_model(
    requested_model: str,
    model_info: Mapping[str, Any],
    response: Mapping[str, Any],
) -> str:
    returned = str(response.get("model") or "")
    allowed = {
        str(value)
        for value in (requested_model, model_info.get("id"), model_info.get("canonical_slug"))
        if value
    }
    if not returned:
        raise ValueError("Răspunsul nu declară modelul folosit.")
    if returned not in allowed:
        raise RuntimeError(f"Model returnat {returned!r}, diferit de {requested_model!r}.")
    return returned


def packet_ids(packet: Mapping[str, Any]) -> tuple[set[str], set[str]]:
    node_ids = {
        str(item.get("id"))
        for item in packet.get("nodes") or []
        if isinstance(item, Mapping) and item.get("id")
    }
    edge_ids = {
        str(item.get("id"))
        for item in packet.get("edges") or []
        if isinstance(item, Mapping) and item.get("id")
    }
    return node_ids, edge_ids


def packet_edges(packet: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(item["id"]): item
        for item in packet.get("edges") or []
        if isinstance(item, Mapping) and item.get("id")
    }


def unknown_ids(values: Any, allowed: set[str]) -> list[str]:
    if not isinstance(values, list):
        return []
    return sorted({str(value) for value in values if str(value) not in allowed})


def validate_questions(
    parsed: Any,
    packet: Mapping[str, Any],
    expected_category: str,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(parsed, Mapping):
        return {"valid": False, "errors": ["Răspunsul JSON nu este un obiect."], "warnings": []}
    if parsed.get("task") != "question_generation":
        errors.append("task trebuie să fie question_generation.")
    if parsed.get("category_id") != expected_category:
        errors.append(f"category_id trebuie să fie {expected_category}.")
    graph_version = str((packet.get("metadata") or {}).get("version") or "")
    if graph_version and str(parsed.get("graph_version") or "") != graph_version:
        errors.append(f"graph_version trebuie să fie {graph_version}.")
    questions = parsed.get("questions")
    if not isinstance(questions, list):
        return {"valid": False, "errors": errors + ["Lipsește lista questions."], "warnings": warnings}
    if len(questions) != 3:
        errors.append(f"Au fost primite {len(questions)} întrebări în loc de 3.")
    slots = list(((packet.get("selection") or {}).get("question_slots") or []))
    if len(slots) != 3:
        errors.append("Packetul nu declară exact trei question_slots deterministe.")
    node_ids, edge_ids = packet_ids(packet)
    edges_by_id = packet_edges(packet)
    seen_ids: set[str] = set()
    seen_texts: set[str] = set()
    generated_count = 0
    impossible_count = 0
    for index, item in enumerate(questions, start=1):
        prefix = f"questions[{index - 1}]"
        slot = slots[index - 1] if index - 1 < len(slots) else {}
        allowed_nodes = {str(item_id) for item_id in slot.get("allowed_node_ids", [])}
        allowed_edges = {str(item_id) for item_id in slot.get("allowed_edge_ids", [])}
        allowed_chapters = {str(item_id) for item_id in slot.get("chapter_ids", [])}
        required_events = {str(item_id) for item_id in slot.get("event_ids", [])}
        required_anchors = {str(item_id) for item_id in slot.get("anchor_node_ids", [])}
        if not isinstance(item, Mapping):
            errors.append(f"{prefix} nu este obiect.")
            continue
        question_id = str(item.get("question_id") or "")
        if not question_id:
            errors.append(f"{prefix}.question_id lipsește.")
        elif question_id in seen_ids:
            errors.append(f"question_id duplicat: {question_id}.")
        seen_ids.add(question_id)
        expected_question_id = str(slot.get("slot_id") or "")
        if expected_question_id and question_id != expected_question_id:
            errors.append(f"{prefix}.question_id trebuie să fie {expected_question_id}.")
        status = item.get("status")
        if status not in {"generated", "impossible"}:
            errors.append(f"{prefix}.status trebuie să fie generated sau impossible.")
            continue
        if status == "impossible":
            impossible_count += 1
            if not str(item.get("reason") or "").strip():
                errors.append(f"{prefix} este impossible fără reason.")
            continue
        generated_count += 1
        text = str(item.get("question_text") or "").strip()
        if not text.endswith("?"):
            errors.append(f"{prefix}.question_text nu se termină cu ?.")
        normalized = text.casefold()
        if normalized in seen_texts:
            errors.append(f"Text de întrebare duplicat la {prefix}.")
        seen_texts.add(normalized)
        answer = item.get("answer")
        if not isinstance(answer, Mapping):
            errors.append(f"{prefix}.answer lipsește.")
        else:
            bad_answer_nodes = unknown_ids(answer.get("node_ids"), node_ids)
            bad_ordered_nodes = unknown_ids(answer.get("ordered_node_ids"), node_ids)
            if bad_answer_nodes or bad_ordered_nodes:
                errors.append(
                    f"{prefix}.answer are noduri inexistente: "
                    f"node_ids={bad_answer_nodes}, ordered_node_ids={bad_ordered_nodes}."
                )
            answer_nodes = {
                str(node_id) for node_id in (answer.get("node_ids") or []) + (answer.get("ordered_node_ids") or [])
            }
            outside_slot = sorted(answer_nodes - allowed_nodes)
            if outside_slot:
                errors.append(f"{prefix}.answer depășește slotul determinist: {outside_slot}.")
            if expected_category == "TEMPORAL_ORDER" and list(answer.get("ordered_node_ids") or []) != list(slot.get("event_ids") or []):
                errors.append(f"{prefix}.answer.ordered_node_ids nu reproduce event_ids ale slotului.")
        evidence = item.get("evidence")
        if not isinstance(evidence, Mapping):
            errors.append(f"{prefix}.evidence lipsește.")
            continue
        bad_nodes = unknown_ids(evidence.get("node_ids"), node_ids)
        bad_edges = unknown_ids(evidence.get("edge_ids"), edge_ids)
        if bad_nodes:
            errors.append(f"{prefix} folosește noduri inexistente: {bad_nodes}.")
        if bad_edges:
            errors.append(f"{prefix} folosește muchii inexistente: {bad_edges}.")
        evidence_nodes = {str(node_id) for node_id in evidence.get("node_ids") or []}
        evidence_edges = {str(edge_id) for edge_id in evidence.get("edge_ids") or []}
        evidence_chapters = {str(chapter_id) for chapter_id in evidence.get("chapter_ids") or []}
        outside_nodes = sorted(evidence_nodes - allowed_nodes)
        outside_edges = sorted(evidence_edges - allowed_edges)
        outside_chapters = sorted(evidence_chapters - allowed_chapters)
        if outside_nodes or outside_edges or outside_chapters:
            errors.append(
                f"{prefix}.evidence depășește slotul: nodes={outside_nodes}, "
                f"edges={outside_edges}, chapters={outside_chapters}."
            )
        missing_slot_evidence = sorted((required_events | required_anchors) - evidence_nodes)
        if missing_slot_evidence:
            errors.append(f"{prefix}.evidence nu acoperă ancorele slotului: {missing_slot_evidence}.")
        declared_path_hops: list[int] = []
        for path_index, path in enumerate(evidence.get("paths") or []):
            if not isinstance(path, Mapping):
                errors.append(f"{prefix}.evidence.paths[{path_index}] nu este obiect.")
                continue
            bad_path_nodes = unknown_ids(path.get("node_ids"), node_ids)
            bad_path_edges = unknown_ids(path.get("edge_ids"), edge_ids)
            if bad_path_nodes or bad_path_edges:
                errors.append(
                    f"{prefix}.paths[{path_index}] are ID-uri inexistente: "
                    f"nodes={bad_path_nodes}, edges={bad_path_edges}."
                )
                continue
            path_nodes = path.get("node_ids") or []
            path_edges = path.get("edge_ids") or []
            declared_path_hops.append(len(path_edges))
            path_outside_nodes = sorted({str(node_id) for node_id in path_nodes} - allowed_nodes)
            path_outside_edges = sorted({str(edge_id) for edge_id in path_edges} - allowed_edges)
            if path_outside_nodes or path_outside_edges:
                errors.append(
                    f"{prefix}.paths[{path_index}] depășește slotul: "
                    f"nodes={path_outside_nodes}, edges={path_outside_edges}."
                )
            if len(path_nodes) != len(path_edges) + 1 and path_edges:
                errors.append(
                    f"{prefix}.paths[{path_index}] nu are exact n+1 noduri pentru n muchii."
                )
                continue
            for hop, edge_id in enumerate(path_edges):
                edge = edges_by_id.get(str(edge_id)) or {}
                endpoints = {str(edge.get("source")), str(edge.get("target"))}
                declared = {str(path_nodes[hop]), str(path_nodes[hop + 1])}
                if endpoints != declared:
                    errors.append(
                        f"{prefix}.paths[{path_index}] nu traversează corect muchia {edge_id}."
                    )
        for attribute_index, attribute in enumerate(evidence.get("attribute_paths") or []):
            if not isinstance(attribute, Mapping):
                errors.append(f"{prefix}.attribute_paths[{attribute_index}] nu este obiect.")
                continue
            attribute_node = str(attribute.get("node_id") or "")
            if attribute_node not in allowed_nodes:
                errors.append(f"{prefix}.attribute_paths[{attribute_index}] depășește slotul.")
        hop_profile = item.get("hop_profile") or {}
        if not isinstance(hop_profile, Mapping):
            errors.append(f"{prefix}.hop_profile lipsește.")
        else:
            actual_total_hops = sum(declared_path_hops)
            actual_longest = max(declared_path_hops, default=0)
            if hop_profile.get("total_edge_hops") != actual_total_hops:
                errors.append(f"{prefix}.hop_profile.total_edge_hops este incorect.")
            if hop_profile.get("longest_continuous_path_hops") != actual_longest:
                errors.append(f"{prefix}.hop_profile.longest_continuous_path_hops este incorect.")
            bounds = slot.get("hop_bounds") or {}
            minimum = int(bounds.get("minimum") or 0)
            maximum = int(bounds.get("maximum") or 0)
            if not minimum <= actual_total_hops <= maximum:
                errors.append(
                    f"{prefix} are {actual_total_hops} hop-uri; slotul permite {minimum}-{maximum}."
                )
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "question_count": len(questions),
            "generated_count": generated_count,
            "impossible_count": impossible_count,
        },
    }


def count_words(text: str) -> int:
    return len(re.findall(r"[0-9A-Za-zĂÂÎȘȚăâîșț]+(?:[-’'][0-9A-Za-zĂÂÎȘȚăâîșț]+)*", text))


def count_paragraphs(text: str) -> int:
    return len([part for part in re.split(r"\n\s*\n", text.strip()) if part.strip()])


SUMMARY_RISKY_TERMS = {
    "complet",
    "completa",
    "definitiv",
    "definitiva",
    "exclusiv",
    "instantaneu",
    "instantanee",
    "imediat",
    "singura",
    "singurul",
}


def normalized_words(text: str) -> set[str]:
    decomposed = unicodedata.normalize("NFKD", text.casefold().replace("ş", "ș").replace("ţ", "ț"))
    ascii_text = "".join(character for character in decomposed if not unicodedata.combining(character))
    return set(re.findall(r"[a-z0-9]+", ascii_text))


def summary_sentences(text: str) -> list[str]:
    flattened = re.sub(r"\s+", " ", text.strip())
    return [item.strip() for item in re.findall(r"[^.!?]+(?:[.!?]+|$)", flattened) if item.strip()]


def validate_summary(
    parsed: Any,
    packet: Mapping[str, Any],
    expected_chapter: str,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(parsed, Mapping):
        return {"valid": False, "errors": ["Răspunsul JSON nu este un obiect."], "warnings": []}
    if parsed.get("task") != "chapter_summary":
        errors.append("task trebuie să fie chapter_summary.")
    if parsed.get("chapter_id") != expected_chapter:
        errors.append(f"chapter_id trebuie să fie {expected_chapter}.")
    if parsed.get("status") != "generated":
        errors.append("status trebuie să fie generated.")
    summary = parsed.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        errors.append("summary lipsește sau este gol.")
        summary = ""
    chapter = packet.get("chapter") or {}
    expected_events = list(chapter.get("verified_event_sequence") or [])
    excluded_events = list(chapter.get("excluded_event_sequence") or [])
    verified_by_id = {
        str(event.get("id")): event
        for event in packet.get("verified_events") or []
        if isinstance(event, Mapping) and event.get("id")
    }
    coverage = parsed.get("coverage")
    if not isinstance(coverage, Mapping):
        errors.append("coverage lipsește.")
        coverage = {}
    covered = coverage.get("covered_event_ids")
    excluded = coverage.get("excluded_event_ids")
    if covered != expected_events:
        errors.append("coverage.covered_event_ids nu reproduce exact verified_event_sequence.")
    if excluded != excluded_events:
        errors.append("coverage.excluded_event_ids nu reproduce exact excluded_event_sequence.")
    if coverage.get("event_count_expected") != len(expected_events):
        errors.append("coverage.event_count_expected este incorect.")
    if coverage.get("event_count_covered") != len(expected_events):
        errors.append("coverage.event_count_covered este incorect.")
    sentence_evidence = parsed.get("sentence_evidence")
    if not isinstance(sentence_evidence, list) or not sentence_evidence:
        errors.append("sentence_evidence lipsește sau este gol.")
        sentence_evidence = []
    actual_sentences = summary_sentences(summary)
    if len(sentence_evidence) != len(actual_sentences):
        errors.append(
            f"sentence_evidence are {len(sentence_evidence)} intrări, dar summary are "
            f"{len(actual_sentences)} propoziții."
        )
    evidence_coverage: list[str] = []
    support_scores: list[float] = []
    for index, item in enumerate(sentence_evidence):
        prefix = f"sentence_evidence[{index}]"
        if not isinstance(item, Mapping):
            errors.append(f"{prefix} nu este obiect.")
            continue
        if item.get("sentence_index") != index + 1:
            errors.append(f"{prefix}.sentence_index trebuie să fie {index + 1}.")
        sentence_text = str(item.get("sentence_text") or "").strip()
        if index < len(actual_sentences) and sentence_text != actual_sentences[index]:
            errors.append(f"{prefix}.sentence_text nu reproduce exact propoziția din summary.")
        event_ids = item.get("event_ids")
        if not isinstance(event_ids, list) or not 1 <= len(event_ids) <= 2:
            errors.append(f"{prefix}.event_ids trebuie să conțină unul sau două ID-uri.")
            event_ids = []
        unknown = [str(event_id) for event_id in event_ids if str(event_id) not in verified_by_id]
        if unknown:
            errors.append(f"{prefix} folosește evenimente neverificate: {unknown}.")
        evidence_coverage.extend(str(event_id) for event_id in event_ids)
        support_texts = []
        for event_id in event_ids:
            event = verified_by_id.get(str(event_id)) or {}
            expected_quote = str((event.get("provenance") or {}).get("evidence_quote") or "")
            support_texts.extend((str(event.get("fact") or ""), expected_quote))
        sentence_words = {word for word in normalized_words(sentence_text) if len(word) >= 4}
        support_words = {word for word in normalized_words(" ".join(support_texts)) if len(word) >= 4}
        matched = sum(
            any(word[:6] == support[:6] for support in support_words)
            for word in sentence_words
        )
        score = matched / len(sentence_words) if sentence_words else 1.0
        support_scores.append(score)
        if score < 0.45:
            errors.append(f"{prefix} are suport lexical insuficient ({score:.2f}).")
        risky = normalized_words(sentence_text) & SUMMARY_RISKY_TERMS
        supported_risky = normalized_words(" ".join(support_texts)) & SUMMARY_RISKY_TERMS
        unsupported_risky = sorted(risky - supported_risky)
        if unsupported_risky:
            errors.append(f"{prefix} adaugă intensificări nesusținute: {unsupported_risky}.")
    if set(evidence_coverage) != set(expected_events):
        errors.append("sentence_evidence nu acoperă exact evenimentele verificate.")
    if len(evidence_coverage) != len(set(evidence_coverage)):
        errors.append("Un eveniment este declarat în mai multe propoziții.")
    word_count = count_words(summary)
    paragraph_count = count_paragraphs(summary)
    if summary and not 120 <= word_count <= 260:
        warnings.append(f"Rezumatul are {word_count} cuvinte; intervalul recomandat este 120-260.")
    if summary and not 2 <= paragraph_count <= 4:
        warnings.append(f"Rezumatul are {paragraph_count} paragrafe; intervalul recomandat este 2-4.")
    style = parsed.get("style") or {}
    if isinstance(style, Mapping):
        if style.get("word_count") != word_count:
            warnings.append(
                f"style.word_count={style.get('word_count')!r}, dar recalcularea dă {word_count}."
            )
        if style.get("paragraph_count") != paragraph_count:
            warnings.append(
                f"style.paragraph_count={style.get('paragraph_count')!r}, "
                f"dar recalcularea dă {paragraph_count}."
            )
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "word_count": word_count,
            "paragraph_count": paragraph_count,
            "expected_event_count": len(expected_events),
            "excluded_event_count": len(excluded_events),
            "sentence_evidence_count": len(sentence_evidence),
            "minimum_sentence_support_score": round(min(support_scores), 4) if support_scores else 0,
        },
    }


def validate_composition(
    parsed: Any,
    packet: Mapping[str, Any],
    expected_element: str,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(parsed, Mapping):
        return {"valid": False, "errors": ["Răspunsul JSON nu este un obiect."], "warnings": []}
    if parsed.get("task") != "composition_element_schema":
        errors.append("task trebuie să fie composition_element_schema.")
    if parsed.get("element_id") != expected_element:
        errors.append(f"element_id trebuie să fie {expected_element}.")
    if parsed.get("status") != "generated":
        errors.append("status trebuie să fie generated.")
    if not str(parsed.get("central_thesis") or "").strip():
        errors.append("central_thesis lipsește.")

    node_ids, edge_ids = packet_ids(packet)
    brief_ids = {
        str(item.get("brief_id"))
        for item in packet.get("researcher_brief") or []
        if isinstance(item, Mapping) and item.get("brief_id")
    }
    used_briefs: set[str] = set()
    schemas = parsed.get("schema")
    if not isinstance(schemas, list):
        return {"valid": False, "errors": errors + ["Lipsește lista schema."], "warnings": warnings}
    if len(schemas) != 4:
        errors.append(f"Schema trebuie să aibă 4 secțiuni; are {len(schemas)}.")
    seen_sections: set[str] = set()
    idea_count = 0
    for section_index, section in enumerate(schemas):
        prefix = f"schema[{section_index}]"
        if not isinstance(section, Mapping):
            errors.append(f"{prefix} nu este obiect.")
            continue
        section_id = str(section.get("section_id") or "")
        if not section_id:
            errors.append(f"{prefix}.section_id lipsește.")
        elif section_id in seen_sections:
            errors.append(f"section_id duplicat: {section_id}.")
        seen_sections.add(section_id)
        if not str(section.get("heading") or "").strip():
            errors.append(f"{prefix}.heading lipsește.")
        ideas = section.get("ideas")
        if not isinstance(ideas, list):
            errors.append(f"{prefix}.ideas lipsește.")
            continue
        if not 2 <= len(ideas) <= 4:
            errors.append(f"{prefix} trebuie să aibă 2-4 idei; are {len(ideas)}.")
        idea_count += len(ideas)
        for idea_index, idea in enumerate(ideas):
            idea_prefix = f"{prefix}.ideas[{idea_index}]"
            if not isinstance(idea, Mapping):
                errors.append(f"{idea_prefix} nu este obiect.")
                continue
            if not str(idea.get("key_idea") or "").strip():
                errors.append(f"{idea_prefix}.key_idea lipsește.")
            if not str(idea.get("explanation") or "").strip():
                errors.append(f"{idea_prefix}.explanation lipsește.")
            basis = idea.get("basis")
            if not isinstance(basis, list) or not basis:
                errors.append(f"{idea_prefix}.basis lipsește.")
                basis = []
            unknown_basis = sorted(set(map(str, basis)) - {"graph", "researcher_brief"})
            if unknown_basis:
                errors.append(f"{idea_prefix}.basis conține valori necunoscute: {unknown_basis}.")
            bad_nodes = unknown_ids(idea.get("node_ids"), node_ids)
            bad_edges = unknown_ids(idea.get("edge_ids"), edge_ids)
            idea_briefs = {str(value) for value in idea.get("brief_ids") or []}
            bad_briefs = sorted(idea_briefs - brief_ids)
            used_briefs.update(idea_briefs & brief_ids)
            if bad_nodes:
                errors.append(f"{idea_prefix} folosește noduri inexistente: {bad_nodes}.")
            if bad_edges:
                errors.append(f"{idea_prefix} folosește muchii inexistente: {bad_edges}.")
            if bad_briefs:
                errors.append(f"{idea_prefix} folosește brief IDs inexistente: {bad_briefs}.")
            if "graph" in basis and not (
                idea.get("node_ids") or idea.get("edge_ids") or idea.get("attribute_paths")
            ):
                errors.append(f"{idea_prefix} declară basis=graph fără dovezi grafice.")
            if "researcher_brief" in basis and not idea_briefs:
                errors.append(f"{idea_prefix} declară researcher_brief fără brief_ids.")
            for attribute_index, attribute in enumerate(idea.get("attribute_paths") or []):
                if not isinstance(attribute, Mapping):
                    errors.append(
                        f"{idea_prefix}.attribute_paths[{attribute_index}] nu este obiect."
                    )
                    continue
                attribute_node = str(attribute.get("node_id") or "")
                if attribute_node not in node_ids:
                    errors.append(
                        f"{idea_prefix}.attribute_paths[{attribute_index}] folosește "
                        f"nodul inexistent {attribute_node!r}."
                    )

    missing_briefs = sorted(brief_ids - used_briefs)
    if missing_briefs:
        errors.append(f"Nu au fost folosite toate direcțiile obligatorii din brief: {missing_briefs}.")
    synthesis = str(parsed.get("bac_synthesis") or "").strip()
    if not synthesis:
        errors.append("bac_synthesis lipsește.")
    synthesis_words = count_words(synthesis)
    if synthesis and not 120 <= synthesis_words <= 180:
        warnings.append(
            f"bac_synthesis are {synthesis_words} cuvinte; intervalul cerut este 120-180."
        )
    memory_formula = parsed.get("memory_formula")
    if not isinstance(memory_formula, list) or not 3 <= len(memory_formula) <= 5:
        errors.append("memory_formula trebuie să conțină 3-5 formule.")
    validation = parsed.get("validation")
    if not isinstance(validation, Mapping):
        errors.append("validation lipsește.")
    else:
        if validation.get("unsupported_claims") != []:
            errors.append("validation.unsupported_claims trebuie să fie lista goală.")
        bad_validation_nodes = unknown_ids(validation.get("used_node_ids"), node_ids)
        bad_validation_edges = unknown_ids(validation.get("used_edge_ids"), edge_ids)
        bad_validation_briefs = sorted(
            {str(value) for value in validation.get("used_brief_ids") or []} - brief_ids
        )
        if bad_validation_nodes or bad_validation_edges or bad_validation_briefs:
            errors.append(
                "validation conține ID-uri inexistente: "
                f"nodes={bad_validation_nodes}, edges={bad_validation_edges}, "
                f"briefs={bad_validation_briefs}."
            )
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "section_count": len(schemas),
            "idea_count": idea_count,
            "synthesis_word_count": synthesis_words,
            "brief_count_expected": len(brief_ids),
            "brief_count_used": len(used_briefs),
        },
    }


def validate_payload(spec: TaskSpec, parsed: Any, packet: Mapping[str, Any]) -> dict[str, Any]:
    if spec.task_type == "questions":
        return validate_questions(parsed, packet, spec.expected_id)
    if spec.task_type == "summaries":
        return validate_summary(parsed, packet, spec.expected_id)
    return validate_composition(parsed, packet, spec.expected_id)


def task_dir(run_dir: Path, spec: TaskSpec) -> Path:
    return run_dir / spec.task_type / spec.slug


def load_latest(run_dir: Path, spec: TaskSpec) -> dict[str, Any] | None:
    path = task_dir(run_dir, spec) / "latest.json"
    return read_json(path) if path.is_file() else None


def validation_passed(metadata: Mapping[str, Any]) -> bool:
    if "validation_passed" in metadata:
        return bool(metadata.get("validation_passed"))
    return metadata.get("status") == "succeeded"


def next_attempt_dir(run_dir: Path, spec: TaskSpec) -> tuple[int, Path]:
    attempts_dir = task_dir(run_dir, spec) / "attempts"
    attempts_dir.mkdir(parents=True, exist_ok=True)
    numbers: list[int] = []
    for path in attempts_dir.glob("attempt-[0-9][0-9][0-9]"):
        try:
            numbers.append(int(path.name.removeprefix("attempt-")))
        except ValueError:
            pass
    number = max(numbers, default=0) + 1
    path = attempts_dir / f"attempt-{number:03d}"
    path.mkdir(parents=False, exist_ok=False)
    return number, path


def public_task_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in metadata.items() if key not in {"content", "parsed"}}


def run_one_task(
    spec: TaskSpec,
    run_dir: Path,
    *,
    api_key: str,
    model_id: str,
    model_info: Mapping[str, Any],
    max_tokens: int,
    timeout: int,
    reasoning_effort: str,
    allow_provider_fallbacks: bool,
    provider_order: list[str] | None,
    retry_feedback: str | None = None,
    retry_source_attempt: int | None = None,
) -> dict[str, Any]:
    if spec.task_type in {"questions", "summaries"}:
        retry_feedback = None
        retry_source_attempt = None
    prompt, packet = render_prompt(spec)
    if retry_feedback:
        prompt = f"{prompt.rstrip()}\n\n{retry_feedback.strip()}\n"
    payload, applied = build_request(
        model_id,
        model_info,
        prompt,
        max_tokens=max_tokens,
        reasoning_effort=reasoning_effort,
        allow_provider_fallbacks=allow_provider_fallbacks,
        provider_order=provider_order,
    )
    attempt_number, attempt_dir = next_attempt_dir(run_dir, spec)
    started_at = utc_now()
    initial = {
        "task_key": spec.key,
        "attempt": attempt_number,
        "status": "running",
        "started_at_utc": started_at.isoformat(),
        "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
        "prompt_characters": len(prompt),
        "estimated_prompt_tokens": math.ceil(len(prompt) / QWEN_CHARS_PER_TOKEN),
        "applied_parameters": applied,
        "validator_feedback_applied": bool(retry_feedback),
        "retry_source_attempt": retry_source_attempt,
    }
    atomic_write_text(attempt_dir / "prompt.txt", prompt)
    save_json(attempt_dir / "request.json", payload)
    save_json(attempt_dir / "task-metadata.json", initial)

    started = time.perf_counter()
    response: dict[str, Any] = {}
    try:
        response = api_json(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            api_key,
            method="POST",
            payload=payload,
            timeout=timeout,
        )
        duration = time.perf_counter() - started
        save_json(attempt_dir / "response.openrouter.json", response)
        api_error = response.get("error")
        if isinstance(api_error, Mapping):
            raise RuntimeError(
                f"OpenRouter API {api_error.get('code', 'necunoscut')}: "
                f"{api_error.get('message', 'eroare fără mesaj')}"
            )
        returned_model = verify_returned_model(model_id, model_info, response)
        content = extract_content(response)
        atomic_write_text(attempt_dir / "response.raw.txt", content + "\n")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            validation = {
                "valid": False,
                "errors": [f"JSON invalid la linia {exc.lineno}, coloana {exc.colno}: {exc.msg}."],
                "warnings": [],
            }
            parsed = None
        else:
            save_json(attempt_dir / "result.json", parsed)
            validation = validate_payload(spec, parsed, packet)
        save_json(attempt_dir / "validation.json", validation)
        if spec.task_type == "questions":
            final_status = "succeeded" if parsed is not None else "unparseable"
        else:
            final_status = "succeeded" if validation["valid"] else "invalid"
        metadata = {
            **initial,
            "status": final_status,
            "finished_at_utc": utc_now().isoformat(),
            "duration_seconds": round(duration, 3),
            "json_syntax_valid": parsed is not None,
            "json_valid": parsed is not None,
            "validation_passed": bool(validation["valid"]),
            "returned_model": returned_model,
            "model_verification": "accepted_exact_or_canonical_model_id",
            "provider": response.get("provider"),
            "generation_id": response.get("id"),
            "usage": response.get("usage") or {},
            "validation_errors": validation.get("errors") or [],
            "validation_warnings": validation.get("warnings") or [],
        }
    except Exception as exc:
        duration = time.perf_counter() - started
        error = {"error_type": type(exc).__name__, "message": str(exc)}
        save_json(attempt_dir / "error.json", error)
        metadata = {
            **initial,
            "status": "error",
            "finished_at_utc": utc_now().isoformat(),
            "duration_seconds": round(duration, 3),
            "json_syntax_valid": False,
            "json_valid": False,
            "validation_passed": False,
            "error": error,
            "returned_model": response.get("model"),
            "provider": response.get("provider"),
            "generation_id": response.get("id"),
            "usage": response.get("usage") or {},
        }
    save_json(attempt_dir / "task-metadata.json", metadata)
    latest = {
        **public_task_metadata(metadata),
        "attempt_dir": str(attempt_dir.relative_to(run_dir)),
    }
    save_json(task_dir(run_dir, spec) / "latest.json", latest)
    return latest


def build_manifest(specs: Sequence[TaskSpec]) -> dict[str, Any]:
    tasks: list[dict[str, Any]] = []
    for spec in specs:
        prompt, packet = render_prompt(spec)
        tasks.append(
            {
                **asdict(spec),
                "prompt_path": relative_display(spec.prompt_path),
                "packet_path": relative_display(spec.packet_path),
                "prompt_template_sha256": sha256_file(spec.prompt_path),
                "packet_sha256": sha256_file(spec.packet_path),
                "rendered_prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
                "prompt_characters": len(prompt),
                "estimated_prompt_tokens": math.ceil(len(prompt) / QWEN_CHARS_PER_TOKEN),
                "packet_id": (packet.get("metadata") or {}).get("packet_id"),
            }
        )
    return {"schema_version": 1, "task_count": len(tasks), "tasks": tasks}


def verify_manifest_inputs(manifest: Mapping[str, Any], specs: Sequence[TaskSpec]) -> None:
    saved = {str(item.get("key")): item for item in manifest.get("tasks") or []}
    current = build_manifest(specs)
    for item in current["tasks"]:
        old = saved.get(item["key"])
        if old is None:
            raise ValueError(f"Manifestul rulării nu conține sarcina {item['key']}.")
        for field in ("prompt_template_sha256", "packet_sha256", "rendered_prompt_sha256"):
            if old.get(field) != item.get(field):
                raise ValueError(
                    f"Inputul pentru {item['key']} s-a schimbat ({field}). "
                    "Pornește o rulare nouă pentru comparabilitate."
                )


def attempt_metadata(run_dir: Path) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for path in sorted(run_dir.glob("*/**/attempts/attempt-*/task-metadata.json")):
        value = read_json(path)
        value["attempt_dir"] = str(path.parent.relative_to(run_dir))
        values.append(value)
    return values


def latest_results(run_dir: Path, specs: Sequence[TaskSpec]) -> dict[str, dict[str, Any]]:
    return {spec.key: value for spec in specs if (value := load_latest(run_dir, spec)) is not None}


def load_attempt_result(run_dir: Path, latest: Mapping[str, Any]) -> Any:
    path = run_dir / str(latest["attempt_dir"]) / "result.json"
    return read_json(path) if path.is_file() else None


def usage_number(usage: Mapping[str, Any], key: str) -> int | float:
    value = usage.get(key)
    return value if isinstance(value, (int, float)) else 0


def reasoning_tokens(usage: Mapping[str, Any]) -> int | float:
    details = usage.get("completion_tokens_details") or {}
    value = details.get("reasoning_tokens") if isinstance(details, Mapping) else 0
    return value if isinstance(value, (int, float)) else 0


def totals(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "api_attempts": len(rows),
        "duration_seconds": 0.0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "reasoning_tokens": 0,
        "total_tokens": 0,
        "cost_usd": 0.0,
    }
    for row in rows:
        usage = row.get("usage") or {}
        result["duration_seconds"] += float(row.get("duration_seconds") or 0)
        result["prompt_tokens"] += int(usage_number(usage, "prompt_tokens"))
        result["completion_tokens"] += int(usage_number(usage, "completion_tokens"))
        result["reasoning_tokens"] += int(reasoning_tokens(usage))
        result["total_tokens"] += int(usage_number(usage, "total_tokens"))
        result["cost_usd"] += float(usage_number(usage, "cost"))
    result["duration_seconds"] = round(result["duration_seconds"], 3)
    result["cost_usd"] = round(result["cost_usd"], 10)
    return result


def build_question_set_metrics(
    run_dir: Path,
    specs: Sequence[TaskSpec],
    *,
    latest: Mapping[str, Mapping[str, Any]] | None = None,
    attempts: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Calculează costul apelurilor unice pentru setul de întrebări."""
    question_specs = [spec for spec in specs if spec.task_type == "questions"]
    current = dict(latest) if latest is not None else latest_results(run_dir, question_specs)
    all_attempts = list(attempts) if attempts is not None else attempt_metadata(run_dir)
    question_attempts = [
        item for item in all_attempts if str(item.get("task_key") or "").startswith("questions/")
    ]
    attempts_by_task: dict[str, list[Mapping[str, Any]]] = {
        spec.key: [] for spec in question_specs
    }
    for item in question_attempts:
        key = str(item.get("task_key") or "")
        if key in attempts_by_task:
            attempts_by_task[key].append(item)

    categories: list[dict[str, Any]] = []
    expected_question_count = 0
    generated_question_count = 0
    generated_category_count = 0
    validated_question_count = 0
    validated_category_count = 0
    for spec in question_specs:
        packet = read_json(spec.packet_path)
        expected_for_category = len(((packet.get("selection") or {}).get("question_slots") or []))
        expected_question_count += expected_for_category
        category_attempts = attempts_by_task.get(spec.key) or []
        category_totals = totals(category_attempts)
        latest_value = current.get(spec.key) or {}
        latest_status = str(latest_value.get("status") or "pending")
        retained = 0
        if latest_status == "succeeded":
            parsed = load_attempt_result(run_dir, latest_value)
            if isinstance(parsed, Mapping):
                retained = len(parsed.get("questions") or [])
            generated_category_count += 1
            generated_question_count += retained
            if validation_passed(latest_value):
                validated_category_count += 1
                validated_question_count += retained
        categories.append(
            {
                "task_key": spec.key,
                "category_id": spec.expected_id,
                "label": spec.label,
                "latest_status": latest_status,
                "latest_attempt": latest_value.get("attempt"),
                "expected_questions": expected_for_category,
                "generated_questions": retained,
                "validated_questions": retained if validation_passed(latest_value) else 0,
                "validation_passed": validation_passed(latest_value),
                "api_attempts": len(category_attempts),
                "retries": max(0, len(category_attempts) - 1),
                "invalid_attempts": sum(item.get("status") == "invalid" for item in category_attempts),
                "error_attempts": sum(item.get("status") == "error" for item in category_attempts),
                **category_totals,
            }
        )

    aggregate = totals(question_attempts)
    complete = bool(question_specs) and generated_category_count == len(question_specs)
    complete = complete and generated_question_count == expected_question_count
    return {
        "report_type": "question_set_cost",
        "cost_scope": "all_billable_question_calls; semantic_validation_is_diagnostic_only",
        "set_status": "complete_generated" if complete else "incomplete_generation",
        "set_complete_and_valid": complete and validated_question_count == expected_question_count,
        "expected_categories": len(question_specs),
        "expected_questions": expected_question_count,
        "generated_categories": generated_category_count,
        "generated_questions": generated_question_count,
        "validated_categories": validated_category_count,
        "validated_questions": validated_question_count,
        "categories_attempted": sum(bool(attempts_by_task.get(spec.key)) for spec in question_specs),
        "api_attempts": len(question_attempts),
        "retries": sum(max(0, len(attempts_by_task.get(spec.key) or []) - 1) for spec in question_specs),
        "invalid_attempts": sum(item.get("status") == "invalid" for item in question_attempts),
        "error_attempts": sum(item.get("status") == "error" for item in question_attempts),
        "succeeded_attempts": sum(item.get("status") == "succeeded" for item in question_attempts),
        **aggregate,
        "categories": categories,
    }


def build_summary_set_metrics(
    run_dir: Path,
    specs: Sequence[TaskSpec],
    *,
    latest: Mapping[str, Mapping[str, Any]] | None = None,
    attempts: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Calculează costul integral al celor 13 rezumate, inclusiv reluările."""
    summary_specs = [spec for spec in specs if spec.task_type == "summaries"]
    current = dict(latest) if latest is not None else latest_results(run_dir, summary_specs)
    all_attempts = list(attempts) if attempts is not None else attempt_metadata(run_dir)
    summary_attempts = [
        item for item in all_attempts if str(item.get("task_key") or "").startswith("summaries/")
    ]
    attempts_by_task: dict[str, list[Mapping[str, Any]]] = {
        spec.key: [] for spec in summary_specs
    }
    for item in summary_attempts:
        key = str(item.get("task_key") or "")
        if key in attempts_by_task:
            attempts_by_task[key].append(item)

    chapters: list[dict[str, Any]] = []
    validated_count = 0
    generated_count = 0
    for spec in summary_specs:
        chapter_attempts = attempts_by_task.get(spec.key) or []
        chapter_totals = totals(chapter_attempts)
        latest_value = current.get(spec.key) or {}
        latest_status = str(latest_value.get("status") or "pending")
        parsed = load_attempt_result(run_dir, latest_value) if latest_value else None
        has_summary = bool(isinstance(parsed, Mapping) and str(parsed.get("summary") or "").strip())
        generated_count += int(has_summary)
        validated_count += int(latest_status == "succeeded" and has_summary)
        chapters.append(
            {
                "task_key": spec.key,
                "chapter_id": spec.expected_id,
                "chapter_title": spec.label,
                "latest_status": latest_status,
                "latest_attempt": latest_value.get("attempt"),
                "summary_generated": has_summary,
                "summary_validated": latest_status == "succeeded" and has_summary,
                "api_attempts": len(chapter_attempts),
                "retries": max(0, len(chapter_attempts) - 1),
                "invalid_attempts": sum(item.get("status") == "invalid" for item in chapter_attempts),
                "error_attempts": sum(item.get("status") == "error" for item in chapter_attempts),
                **chapter_totals,
            }
        )

    aggregate = totals(summary_attempts)
    complete = bool(summary_specs) and validated_count == len(summary_specs)
    return {
        "report_type": "summary_set_cost",
        "cost_scope": "all_billable_summary_attempts_including_invalid_outputs_and_retries",
        "set_status": "complete_valid" if complete else "incomplete_or_invalid",
        "set_complete_and_valid": complete,
        "expected_chapters": len(summary_specs),
        "generated_chapters": generated_count,
        "validated_chapters": validated_count,
        "chapters_attempted": sum(bool(attempts_by_task.get(spec.key)) for spec in summary_specs),
        "api_attempts": len(summary_attempts),
        "retries": sum(max(0, len(attempts_by_task.get(spec.key) or []) - 1) for spec in summary_specs),
        "invalid_attempts": sum(item.get("status") == "invalid" for item in summary_attempts),
        "error_attempts": sum(item.get("status") == "error" for item in summary_attempts),
        "succeeded_attempts": sum(item.get("status") == "succeeded" for item in summary_attempts),
        **aggregate,
        "chapters": chapters,
    }


def write_questions_text_file(
    run_dir: Path,
    specs: Sequence[TaskSpec],
    *,
    latest: Mapping[str, Mapping[str, Any]] | None = None,
) -> Path:
    """Scrie ultima variantă disponibilă a întrebărilor într-un TXT lizibil."""
    question_specs = [spec for spec in specs if spec.task_type == "questions"]
    current = dict(latest) if latest is not None else latest_results(run_dir, question_specs)
    status_labels = {
        "succeeded": "GENERATĂ",
        "unparseable": "GENERATĂ, DAR JSON-UL NU POATE FI CITIT",
        "invalid": "RESPINSĂ DE VALIDATOR",
        "error": "EROARE DE APEL",
        "running": "ÎN CURS",
        "pending": "ÎN AȘTEPTARE",
    }
    valid_categories = 0
    validated_questions = 0
    displayed_questions = 0
    category_blocks: list[str] = []
    for index, spec in enumerate(question_specs, start=1):
        latest_value = current.get(spec.key) or {}
        status = str(latest_value.get("status") or "pending")
        parsed = load_attempt_result(run_dir, latest_value) if latest_value else None
        questions = list(parsed.get("questions") or []) if isinstance(parsed, Mapping) else []
        if status == "succeeded" and validation_passed(latest_value):
            valid_categories += 1
            validated_questions += len(questions)
        displayed_questions += len(questions)
        attempt = latest_value.get("attempt")
        attempt_text = f", încercarea {attempt}" if attempt is not None else ""
        category_blocks.extend(
            (
                f"{index}. {spec.expected_id}",
                (
                    "Statut: GENERATĂ, CU AVERTISMENTE DE VALIDARE" + attempt_text
                    if status == "succeeded" and not validation_passed(latest_value)
                    else f"Statut: {status_labels.get(status, status.upper())}{attempt_text}"
                ),
                "",
            )
        )
        if questions:
            for question_index, question in enumerate(questions, start=1):
                if not isinstance(question, Mapping):
                    continue
                text = str(question.get("question_text") or "").strip()
                if text:
                    category_blocks.extend((f"{question_index}. {text}", ""))
        else:
            category_blocks.extend(("Nicio întrebare disponibilă încă.", ""))
        category_blocks.append("")

    lines = [
        "ÎNTREBĂRI QWEN 3.7 FLASH — ULTIMA VARIANTĂ PE CATEGORII",
        "",
        f"Rulare: {run_dir.name}",
        f"Categorii validate: {valid_categories}/{len(question_specs)}",
        f"Întrebări validate: {validated_questions}/{len(question_specs) * 3}",
        f"Întrebări afișate în acest fișier: {displayed_questions}",
        "",
        "Notă: fiecare categorie este apelată o singură dată. Rezultatul este păstrat chiar dacă validatorul semantic raportează probleme; validarea este doar diagnostică și nu declanșează regenerarea.",
        "",
        "",
        *category_blocks,
    ]
    path = run_dir / "intrebari-pe-categorii.txt"
    atomic_write_text(path, "\n".join(lines).rstrip() + "\n")
    return path


def collect_global_question_entries() -> tuple[list[str], dict[str, str], dict[str, list[dict[str, Any]]]]:
    """Colectează o singură dată ultima ieșire a fiecărei categorii/rulări."""
    category_order: list[str] = []
    category_labels: dict[str, str] = {}
    for _, packet_name in QUESTION_FILES:
        packet_path = QUESTION_PACKET_DIR / packet_name
        if not packet_path.is_file():
            continue
        category_id = str((read_json(packet_path).get("metadata") or {}).get("category_id") or "")
        if category_id:
            category_order.append(category_id)
            category_labels[category_id] = category_id

    entries: dict[str, list[dict[str, Any]]] = {category_id: [] for category_id in category_order}
    latest_files = sorted(RUNS_DIR.glob("**/questions/*/latest.json")) if RUNS_DIR.is_dir() else []
    for latest_path in latest_files:
        latest = read_json(latest_path)
        attempt_dir_value = str(latest.get("attempt_dir") or "")
        if not attempt_dir_value:
            continue
        run_dir = latest_path.parents[2]
        result_path = run_dir / attempt_dir_value / "result.json"
        if not result_path.is_file():
            continue
        result = read_json(result_path)
        if not isinstance(result, Mapping):
            continue
        category_id = str(result.get("category_id") or "")
        questions = [
            dict(question)
            for question in result.get("questions") or []
            if isinstance(question, Mapping) and str(question.get("question_text") or "").strip()
        ]
        if not category_id or not questions:
            continue
        if category_id not in entries:
            entries[category_id] = []
            category_order.append(category_id)
        metadata_path = run_dir / "metadata.json"
        metadata = read_json(metadata_path) if metadata_path.is_file() else {}
        selection_path = run_dir / "question-selection.json"
        selection = read_json(selection_path) if selection_path.is_file() else {}
        entries[category_id].append(
            {
                "run_id": str(metadata.get("run_id") or run_dir.name),
                "timestamp_utc": str(metadata.get("timestamp_utc") or ""),
                "model": str(metadata.get("requested_model") or run_dir.parent.name),
                "batch_number": metadata.get("question_batch_number") or selection.get("batch_number") or "legacy",
                "validation_passed": validation_passed(latest),
                "questions": questions,
            }
        )
    return category_order, category_labels, entries


def write_global_questions_archive(
    output_path: Path = GLOBAL_QUESTIONS_TEXT_PATH,
) -> Path:
    """Reconstruiește registrul TXT cumulativ din ultima ieșire a fiecărei categorii/rulări."""
    category_order, category_labels, entries = collect_global_question_entries()

    total_questions = sum(
        len(entry["questions"])
        for category_entries in entries.values()
        for entry in category_entries
    )
    run_ids = {
        entry["run_id"]
        for category_entries in entries.values()
        for entry in category_entries
    }
    lines = [
        "TOATE ÎNTREBĂRILE QWEN — ARHIVĂ CUMULATIVĂ PE CATEGORII",
        "",
        f"Total întrebări păstrate: {total_questions}",
        f"Rulări incluse: {len(run_ids)}",
        "",
        "Fișier reconstruit automat din rezultatele salvate; o reluare nu dublează aceeași categorie din aceeași rulare.",
        "",
        "",
    ]
    for category_index, category_id in enumerate(category_order, start=1):
        category_entries = sorted(
            entries.get(category_id) or [],
            key=lambda item: (item["timestamp_utc"], item["run_id"]),
        )
        category_total = sum(len(entry["questions"]) for entry in category_entries)
        heading = f"{category_index}. {category_labels.get(category_id, category_id)} — {category_total} întrebări"
        lines.extend((heading, "=" * len(heading), ""))
        question_number = 0
        for entry in category_entries:
            validation_text = "validare trecută" if entry["validation_passed"] else "validare diagnostică netrecută"
            lines.extend(
                (
                    f"Lot {entry['batch_number']} | {entry['run_id']} | {entry['model']} | {validation_text}",
                    "-" * 72,
                )
            )
            for question in entry["questions"]:
                question_number += 1
                lines.append(f"{question_number}. {str(question.get('question_text') or '').strip()}")
            lines.extend(("", ""))
        if not category_entries:
            lines.extend(("Nicio întrebare salvată încă.", "", ""))
    atomic_write_text(output_path, "\n".join(lines).rstrip() + "\n")
    return output_path


def write_global_questions_json(
    output_path: Path = GLOBAL_QUESTIONS_JSON_PATH,
) -> Path:
    """Reconstruiește banca JSON cumulativă, păstrând răspunsurile și dovezile complete."""
    category_order, _, entries = collect_global_question_entries()
    categories: list[dict[str, Any]] = []
    run_ids: set[str] = set()
    total_questions = 0
    for category_id in category_order:
        cumulative_questions: list[dict[str, Any]] = []
        category_entries = sorted(
            entries.get(category_id) or [],
            key=lambda item: (item["timestamp_utc"], item["run_id"]),
        )
        for entry in category_entries:
            run_ids.add(entry["run_id"])
            for index, question in enumerate(entry["questions"], start=1):
                source_question_id = str(question.get("question_id") or f"QUESTION_{index:02d}")
                cumulative_questions.append(
                    {
                        "cumulative_id": (
                            f"{entry['run_id']}::{category_id}::{source_question_id}"
                        ),
                        "source": {
                            "run_id": entry["run_id"],
                            "timestamp_utc": entry["timestamp_utc"],
                            "model": entry["model"],
                            "batch_number": entry["batch_number"],
                            "category_id": category_id,
                            "validation_passed": entry["validation_passed"],
                        },
                        **question,
                    }
                )
        total_questions += len(cumulative_questions)
        categories.append(
            {
                "category_id": category_id,
                "question_count": len(cumulative_questions),
                "questions": cumulative_questions,
            }
        )
    save_json(
        output_path,
        {
            "schema_version": 1,
            "work_id": "ion",
            "task": "cumulative_question_bank",
            "question_count": total_questions,
            "run_count": len(run_ids),
            "category_count": len(categories),
            "categories": categories,
        },
    )
    return output_path


def write_summaries_text_file(
    run_dir: Path,
    specs: Sequence[TaskSpec],
    *,
    latest: Mapping[str, Mapping[str, Any]] | None = None,
) -> Path:
    """Scrie prima bucată de rezumat pentru fiecare capitol, inclusiv cele invalide."""
    summary_specs = [spec for spec in specs if spec.task_type == "summaries"]
    current = dict(latest) if latest is not None else latest_results(run_dir, summary_specs)
    status_labels = {
        "succeeded": "VALIDAT",
        "invalid": "RESPINS DE VALIDATOR",
        "error": "EROARE DE APEL",
        "running": "ÎN CURS",
        "pending": "ÎN AȘTEPTARE",
    }
    valid_count = 0
    displayed_count = 0
    blocks: list[str] = []
    for index, spec in enumerate(summary_specs, start=1):
        latest_value = current.get(spec.key) or {}
        status = str(latest_value.get("status") or "pending")
        parsed = load_attempt_result(run_dir, latest_value) if latest_value else None
        summary_text = str(parsed.get("summary") or "").strip() if isinstance(parsed, Mapping) else ""
        if status == "succeeded":
            valid_count += 1
        if summary_text:
            displayed_count += 1
        attempt = latest_value.get("attempt")
        attempt_text = f", încercarea {attempt}" if attempt is not None else ""
        heading = f"{index}. {spec.label} ({spec.expected_id})"
        blocks.extend(
            (
                heading,
                "=" * len(heading),
                f"Statut: {status_labels.get(status, status.upper())}{attempt_text}",
                "",
                summary_text or "Nicio bucată de rezumat disponibilă încă.",
                "",
                "",
            )
        )

    lines = [
        "REZUMATE QWEN 3.7 FLASH — PRIMA VARIANTĂ PE CAPITOLE",
        "",
        f"Rulare: {run_dir.name}",
        f"Capitole validate: {valid_count}/{len(summary_specs)}",
        f"Bucăți de rezumat afișate: {displayed_count}/{len(summary_specs)}",
        "",
        "Notă: fiecare secțiune conține prima încercare finalizată pentru capitolul respectiv. Rezumatele respinse sunt păstrate și marcate clar; validatorul este numai diagnostic și nu declanșează regenerarea.",
        "",
        "",
        *blocks,
    ]
    content = "\n".join(lines).rstrip() + "\n"
    path = run_dir / "rezumate-pe-capitole.txt"
    atomic_write_text(path, content)
    atomic_write_text(run_dir / "summaries.all.txt", content)
    return path


def write_consolidated_results(run_dir: Path, specs: Sequence[TaskSpec]) -> dict[str, Any]:
    latest = latest_results(run_dir, specs)
    statuses = Counter(value.get("status", "unknown") for value in latest.values())
    question_categories: list[Any] = []
    summaries: list[Any] = []
    summary_texts: list[tuple[str, str, str]] = []
    compositions: list[Any] = []
    result_index: list[dict[str, Any]] = []
    for spec in specs:
        value = latest.get(spec.key)
        status = value.get("status") if value else "pending"
        parsed = load_attempt_result(run_dir, value) if value else None
        result_index.append(
            {
                "task_key": spec.key,
                "type": spec.task_type,
                "label": spec.label,
                "status": status,
                "attempt": value.get("attempt") if value else None,
                "attempt_dir": value.get("attempt_dir") if value else None,
                "json_valid": bool(value and value.get("json_valid")),
                "usage": (value.get("usage") or {}) if value else {},
            }
        )
        if parsed is not None:
            if spec.task_type == "questions" and status == "succeeded":
                question_categories.append(parsed)
            elif spec.task_type == "summaries" and status in {"succeeded", "invalid"}:
                summaries.append(parsed)
                summary_text = str(parsed.get("summary") or "").strip()
                if summary_text:
                    chapter_id = str(parsed.get("chapter_id") or spec.expected_id)
                    chapter_title = str(parsed.get("chapter_title") or spec.label)
                    if status == "succeeded":
                        summary_texts.append((chapter_id, chapter_title, summary_text))
                    plain_text = summary_text + "\n"
                    atomic_write_text(task_dir(run_dir, spec) / "summary.txt", plain_text)
                    attempt_relative = str(value.get("attempt_dir") or "")
                    if attempt_relative:
                        attempt_path = run_dir / attempt_relative
                        if attempt_path.is_dir():
                            atomic_write_text(attempt_path / "summary.txt", plain_text)
            elif spec.task_type == "compositions" and status == "succeeded":
                compositions.append(parsed)
    question_count = sum(
        len(item.get("questions") or []) for item in question_categories if isinstance(item, Mapping)
    )
    save_json(
        run_dir / "questions.all.json",
        {
            "task": "all_question_categories",
            "category_count": len(question_categories),
            "question_count": question_count,
            "categories": question_categories,
        },
    )
    write_questions_text_file(run_dir, specs, latest=latest)
    if run_dir.resolve().is_relative_to(RUNS_DIR.resolve()):
        write_global_questions_archive()
        write_global_questions_json()
    save_json(
        run_dir / "summaries.all.json",
        {
            "task": "all_chapter_summaries",
            "chapter_count": len(summaries),
            "summaries": summaries,
        },
    )
    summary_blocks: list[str] = []
    for chapter_id, chapter_title, summary_text in summary_texts:
        summary_blocks.extend(
            (
                f"{chapter_title} ({chapter_id})",
                "=" * len(f"{chapter_title} ({chapter_id})"),
                "",
                summary_text,
                "",
            )
        )
    atomic_write_text(
        run_dir / "summaries.validated.txt",
        "\n".join(summary_blocks).rstrip() + ("\n" if summary_blocks else ""),
    )
    write_summaries_text_file(run_dir, specs, latest=latest)
    save_json(
        run_dir / "compositions.all.json",
        {
            "task": "all_composition_elements",
            "element_count": len(compositions),
            "elements": compositions,
        },
    )
    all_attempts = attempt_metadata(run_dir)
    latest_attempts = [value for value in latest.values()]
    question_set = build_question_set_metrics(
        run_dir,
        specs,
        latest=latest,
        attempts=all_attempts,
    )
    save_json(run_dir / "questions-cost-report.json", question_set)
    summary_set = build_summary_set_metrics(
        run_dir,
        specs,
        latest=latest,
        attempts=all_attempts,
    )
    save_json(run_dir / "summaries-cost-report.json", summary_set)
    summary = {
        "task_count": len(specs),
        "completed": statuses.get("succeeded", 0),
        "invalid": statuses.get("invalid", 0),
        "errors": statuses.get("error", 0),
        "pending": len(specs) - len(latest),
        "question_categories_completed": len(question_categories),
        "questions_retained": question_count,
        "chapter_summaries_completed": len(summaries),
        "composition_elements_completed": len(compositions),
        "question_set_cost": question_set,
        "summary_set_cost": summary_set,
        "latest_attempt_totals": totals(latest_attempts),
        "billable_all_attempt_totals": totals(all_attempts),
        "results": result_index,
    }
    save_json(run_dir / "results.json", summary)
    write_usage_csv(run_dir, all_attempts)
    return summary


def write_usage_csv(run_dir: Path, attempts: Sequence[Mapping[str, Any]]) -> None:
    fields = (
        "task_key",
        "attempt",
        "status",
        "provider",
        "returned_model",
        "duration_seconds",
        "prompt_tokens",
        "completion_tokens",
        "reasoning_tokens",
        "total_tokens",
        "cost_usd",
        "started_at_utc",
        "attempt_dir",
    )
    path = run_dir / "token-usage.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in attempts:
            usage = item.get("usage") or {}
            writer.writerow(
                {
                    "task_key": item.get("task_key"),
                    "attempt": item.get("attempt"),
                    "status": item.get("status"),
                    "provider": item.get("provider"),
                    "returned_model": item.get("returned_model"),
                    "duration_seconds": item.get("duration_seconds"),
                    "prompt_tokens": usage_number(usage, "prompt_tokens"),
                    "completion_tokens": usage_number(usage, "completion_tokens"),
                    "reasoning_tokens": reasoning_tokens(usage),
                    "total_tokens": usage_number(usage, "total_tokens"),
                    "cost_usd": usage_number(usage, "cost"),
                    "started_at_utc": item.get("started_at_utc"),
                    "attempt_dir": item.get("attempt_dir"),
                }
            )
    temporary.replace(path)


def format_integer(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return "—"
    return f"{int(value):,}".replace(",", ".")


def format_decimal(value: Any, digits: int = 3) -> str:
    if not isinstance(value, (int, float)):
        return "—"
    return f"{float(value):.{digits}f}".replace(".", ",")


def write_question_cost_report(run_dir: Path, specs: Sequence[TaskSpec]) -> Path:
    data = build_question_set_metrics(run_dir, specs)
    save_json(run_dir / "questions-cost-report.json", data)
    lines = [
        "# Raport cost — setul de 24 de întrebări",
        "",
        "## Rezultatul setului",
        "",
        f"- Stare: `{data['set_status']}`",
        f"- Categorii generate și păstrate: {data['generated_categories']} din {data['expected_categories']}",
        f"- Întrebări generate și păstrate: {data['generated_questions']} din {data['expected_questions']}",
        f"- Categorii validate: {data['validated_categories']} din {data['expected_categories']}",
        f"- Întrebări validate: {data['validated_questions']} din {data['expected_questions']}",
        f"- Apeluri API pentru întrebări: {data['api_attempts']}",
        f"- Reluări: {data['retries']}",
        f"- Încercări invalide facturate: {data['invalid_attempts']}",
        f"- Încercări cu eroare facturate: {data['error_attempts']}",
        f"- Cost total al setului, cu toate reluările: {format_decimal(data['cost_usd'], 8)} USD",
        f"- Tokenuri totale facturate pentru set: {format_integer(data['total_tokens'])}",
        f"- Tokenuri de reasoning: {format_integer(data['reasoning_tokens'])}",
        "",
        "Fiecare categorie de întrebări este apelată o singură dată. Validarea rămâne în raport doar ca diagnostic și nu declanșează o regenerare.",
        "",
        "## Detaliu pe categorie",
        "",
        "| Categorie | Stare finală | Întrebări păstrate | Validate | Apeluri | Reluări | Invalide | Tokenuri | Reasoning | Cost (USD) |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for category in data["categories"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    markdown(category["category_id"]),
                    markdown(category["latest_status"]),
                    f"{category['generated_questions']}/{category['expected_questions']}",
                    f"{category['validated_questions']}/{category['expected_questions']}",
                    format_integer(category["api_attempts"]),
                    format_integer(category["retries"]),
                    format_integer(category["invalid_attempts"]),
                    format_integer(category["total_tokens"]),
                    format_integer(category["reasoning_tokens"]),
                    format_decimal(category["cost_usd"], 8),
                )
            )
            + " |"
        )
    lines.extend(
        (
            "",
            "Fișierul `questions-cost-report.json` conține aceleași valori într-un format prelucrabil automat.",
            "",
        )
    )
    path = run_dir / "raport-cost-intrebari.md"
    atomic_write_text(path, "\n".join(lines))
    return path


def write_summary_cost_report(run_dir: Path, specs: Sequence[TaskSpec]) -> Path:
    data = build_summary_set_metrics(run_dir, specs)
    save_json(run_dir / "summaries-cost-report.json", data)
    lines = [
        "# Raport cost — setul de 13 rezumate pe capitole",
        "",
        "## Rezultatul setului",
        "",
        f"- Stare: `{data['set_status']}`",
        f"- Capitole generate: {data['generated_chapters']} din {data['expected_chapters']}",
        f"- Capitole validate: {data['validated_chapters']} din {data['expected_chapters']}",
        f"- Apeluri API pentru rezumate: {data['api_attempts']}",
        f"- Reluări: {data['retries']}",
        f"- Încercări invalide facturate: {data['invalid_attempts']}",
        f"- Încercări cu eroare facturate: {data['error_attempts']}",
        f"- Cost total al setului, cu toate reluările: {format_decimal(data['cost_usd'], 8)} USD",
        f"- Tokenuri totale facturate pentru set: {format_integer(data['total_tokens'])}",
        f"- Tokenuri de reasoning: {format_integer(data['reasoning_tokens'])}",
        "",
        "Costul însumează toate apelurile pentru rezumate din această rulare, inclusiv variantele respinse și reluările. Nu include întrebările sau elementele compoziționale.",
        "",
        "## Detaliu pe capitol",
        "",
        "| Capitol | Stare finală | Apeluri | Reluări | Invalide | Tokenuri | Reasoning | Cost (USD) |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for chapter in data["chapters"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    markdown(chapter["chapter_title"]),
                    markdown(chapter["latest_status"]),
                    format_integer(chapter["api_attempts"]),
                    format_integer(chapter["retries"]),
                    format_integer(chapter["invalid_attempts"]),
                    format_integer(chapter["total_tokens"]),
                    format_integer(chapter["reasoning_tokens"]),
                    format_decimal(chapter["cost_usd"], 8),
                )
            )
            + " |"
        )
    lines.extend(
        (
            "",
            "Fișierul `summaries-cost-report.json` conține aceleași valori într-un format prelucrabil automat.",
            "",
        )
    )
    path = run_dir / "raport-cost-rezumate.md"
    atomic_write_text(path, "\n".join(lines))
    return path


def markdown(value: Any) -> str:
    text = str(value if value not in (None, "") else "—")
    return text.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def generate_report(run_dir: Path, specs: Sequence[TaskSpec], metadata: Mapping[str, Any]) -> Path:
    summary = write_consolidated_results(run_dir, specs)
    write_question_cost_report(run_dir, specs)
    write_summary_cost_report(run_dir, specs)
    latest = latest_results(run_dir, specs)
    all_attempts = attempt_metadata(run_dir)
    latest_totals = summary["latest_attempt_totals"]
    billed_totals = summary["billable_all_attempt_totals"]
    lines = [
        f"# Raport rulare — {metadata.get('model_name') or metadata.get('requested_model')}",
        "",
        "## Identificarea rulării",
        "",
        f"- Rulare: `{metadata.get('run_id')}`",
        f"- Data UTC: `{metadata.get('timestamp_utc')}`",
        f"- Model solicitat: `{metadata.get('requested_model')}`",
        f"- Lot de întrebări: {metadata.get('question_batch_number', 'legacy')}",
        (
            f"- Sarcini planificate: {len(specs)} "
            f"({sum(spec.task_type == 'questions' for spec in specs)} categorii de întrebări + "
            f"{sum(spec.task_type == 'summaries' for spec in specs)} rezumate + "
            f"{sum(spec.task_type == 'compositions' for spec in specs)} elemente compoziționale)"
        ),
        "- Fallback-ul poate schimba providerul, nu modelul solicitat.",
        "",
        "## Starea rezultatelor",
        "",
        f"- Sarcini generate și păstrate: {summary['completed']} din {summary['task_count']}",
        f"- Categorii de întrebări păstrate: {summary['question_categories_completed']} din 8",
        f"- Întrebări păstrate: {summary['questions_retained']} din 24",
        f"- Rezumate păstrate: {summary['chapter_summaries_completed']} din 13",
        (
            "- Scheme pentru elemente compoziționale păstrate: "
            f"{summary['composition_elements_completed']} din "
            f"{sum(spec.task_type == 'compositions' for spec in specs)}"
        ),
        f"- Outputuri invalidate semantic (numai diagnostic): {summary['invalid']}",
        f"- Erori de apel: {summary['errors']}",
        f"- Sarcini încă neapelate: {summary['pending']}",
        (
            "- Cost integral întrebări: "
            f"{format_decimal(summary['question_set_cost']['cost_usd'], 8)} USD "
            f"în {summary['question_set_cost']['api_attempts']} apeluri"
        ),
        (
            "- Cost integral rezumate, inclusiv reluări: "
            f"{format_decimal(summary['summary_set_cost']['cost_usd'], 8)} USD "
            f"în {summary['summary_set_cost']['api_attempts']} apeluri"
        ),
        "",
        "## Consum curent per pachet",
        "",
        "| # | Sarcină | Tip | Stare | Încercare | Durată (s) | Tokenuri prompt | Tokenuri completare | Reasoning | Total | Cost (USD) |",
        "|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for index, spec in enumerate(specs, start=1):
        value = latest.get(spec.key) or {}
        usage = value.get("usage") or {}
        lines.append(
            "| "
            + " | ".join(
                (
                    str(index),
                    markdown(spec.label),
                    {
                        "questions": "întrebări",
                        "summaries": "rezumat",
                        "compositions": "element compozițional",
                    }.get(spec.task_type, spec.task_type),
                    markdown(value.get("status") or "pending"),
                    format_integer(value.get("attempt")),
                    format_decimal(value.get("duration_seconds")),
                    format_integer(usage.get("prompt_tokens")),
                    format_integer(usage.get("completion_tokens")),
                    format_integer(reasoning_tokens(usage)),
                    format_integer(usage.get("total_tokens")),
                    format_decimal(usage.get("cost"), 6),
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Totaluri",
            "",
            "| Bază de calcul | Apeluri | Durată (s) | Prompt | Completare | Reasoning | Total tokenuri | Cost (USD) |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
            (
                "| Ultima încercare per pachet | "
                f"{latest_totals['api_attempts']} | {format_decimal(latest_totals['duration_seconds'])} | "
                f"{format_integer(latest_totals['prompt_tokens'])} | "
                f"{format_integer(latest_totals['completion_tokens'])} | "
                f"{format_integer(latest_totals['reasoning_tokens'])} | "
                f"{format_integer(latest_totals['total_tokens'])} | "
                f"{format_decimal(latest_totals['cost_usd'], 6)} |"
            ),
            (
                "| Toate încercările facturabile, inclusiv reluări | "
                f"{billed_totals['api_attempts']} | {format_decimal(billed_totals['duration_seconds'])} | "
                f"{format_integer(billed_totals['prompt_tokens'])} | "
                f"{format_integer(billed_totals['completion_tokens'])} | "
                f"{format_integer(billed_totals['reasoning_tokens'])} | "
                f"{format_integer(billed_totals['total_tokens'])} | "
                f"{format_decimal(billed_totals['cost_usd'], 6)} |"
            ),
            "",
            "## Istoricul tuturor încercărilor",
            "",
            "| Sarcină | Încercare | Stare | Provider | Durată (s) | Prompt | Completare | Total | Cost (USD) |",
            "|---|---:|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for item in all_attempts:
        usage = item.get("usage") or {}
        lines.append(
            "| "
            + " | ".join(
                (
                    markdown(item.get("task_key")),
                    format_integer(item.get("attempt")),
                    markdown(item.get("status")),
                    markdown(item.get("provider")),
                    format_decimal(item.get("duration_seconds")),
                    format_integer(usage.get("prompt_tokens")),
                    format_integer(usage.get("completion_tokens")),
                    format_integer(usage.get("total_tokens")),
                    format_decimal(usage.get("cost"), 6),
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Fișiere verificabile",
            "",
            "- `questions.all.json` — toate categoriile de întrebări generate, indiferent de diagnosticul validatorului;",
            "- `intrebari-pe-categorii.txt` — rezultatul unic al fiecărei categorii într-un format lizibil;",
            "- `../../../toate-intrebarile-pe-categorii.txt` — arhiva cumulativă pe categorii a tuturor rulărilor;",
            "- `../../../toate-intrebarile.json` — banca JSON cumulativă cu întrebări, răspunsuri și dovezi;",
            "- `question-selection.json` — evenimentele rezervate de lot și istoricul exclus din selecție;",
            "- `raport-cost-intrebari.md` — costul setului de 24 de întrebări;",
            "- `questions-cost-report.json` — aceleași costuri și încercări într-un format prelucrabil automat;",
            "- `raport-cost-rezumate.md` — costul integral al celor 13 rezumate, inclusiv reluările;",
            "- `summaries-cost-report.json` — aceleași costuri per capitol într-un format prelucrabil automat;",
            "- `summaries.all.json` — toate rezumatele valide concatenate;",
            "- `summaries.all.txt` — ultima bucată pentru toate cele 13 capitole, cu titlu și statut;",
            "- `summaries.validated.txt` — numai textele curate ale rezumatelor validate;",
            "- `rezumate-pe-capitole.txt` — ultima bucată generată pentru fiecare capitol, inclusiv cele încă invalide, cu titlu și statut;",
            "- `compositions.all.json` — toate schemele compoziționale valide concatenate;",
            "- `results.json` — indexul stărilor și totalurile;",
            "- `token-usage.csv` — câte un rând pentru fiecare apel API;",
            "- `manifest.json` — hash-urile prompturilor și packeturilor;",
            "- subdirectoarele `questions/`, `summaries/` și `compositions/` — prompt, request, răspuns brut, JSON, validare și răspuns OpenRouter pentru fiecare încercare.",
            "",
            "Raportul este reconstruit determinist din artefactele salvate și nu necesită un apel AI suplimentar.",
            "",
        ]
    )
    path = run_dir / "raport-rulare.md"
    atomic_write_text(path, "\n".join(lines))
    return path


def resolve_run_dir(value: Path) -> Path:
    candidates = [value, BASE_DIR / value, RUNS_DIR / value]
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.is_dir() and (resolved / "metadata.json").is_file():
            return resolved
    raise ValueError(f"Folderul de reluat nu există sau nu conține metadata.json: {value}")


def select_specs(specs: Sequence[TaskSpec], group: str, only: list[str] | None) -> list[TaskSpec]:
    selected = [spec for spec in specs if group == "all" or spec.task_type == group]
    if only:
        wanted = set(only)
        selected = [spec for spec in selected if spec.key in wanted or spec.slug in wanted]
        unmatched = wanted - {value for spec in selected for value in (spec.key, spec.slug)}
        if unmatched:
            raise ValueError(f"Sarcini --only necunoscute: {sorted(unmatched)}")
    return selected


def print_plan(specs: Sequence[TaskSpec]) -> None:
    total_estimate = 0
    print("Ordinea apelurilor:")
    for index, spec in enumerate(specs, start=1):
        prompt, _ = render_prompt(spec)
        estimate = math.ceil(len(prompt) / QWEN_CHARS_PER_TOKEN)
        total_estimate += estimate
        print(f"{index:02d}. {spec.key}: ~{estimate:,} tokenuri input")
    print(f"Total estimat pentru selecție: ~{total_estimate:,} tokenuri input")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Rulează secvențial packeturile de întrebări, rezumate și elemente "
            "compoziționale prin Qwen/OpenRouter."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--model", default=None, help=f"Model OpenRouter (implicit: {DEFAULT_MODEL}).")
    parser.add_argument(
        "--tasks",
        choices=("all", "questions", "summaries", "compositions"),
        default="all",
    )
    parser.add_argument(
        "--only",
        action="append",
        metavar="TASK",
        help="Rulează numai cheia sau slug-ul indicat; opțiunea se poate repeta.",
    )
    parser.add_argument("--max-tokens", type=int, default=12000)
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--plan-only", action="store_true", help="Arată ordinea și estimările fără API.")
    parser.add_argument("--preflight-only", action="store_true", help="Verifică modelul fără generare.")
    parser.add_argument("--resume-run", type=Path, help="Continuă o rulare existentă.")
    parser.add_argument(
        "--finalize-only",
        action="store_true",
        help="Reconstruiește agregările și raportul fără niciun apel API; necesită --resume-run.",
    )
    parser.add_argument(
        "--retry-succeeded",
        action="store_true",
        help="Retrimite numai schemele compoziționale; nu se aplică întrebărilor sau rezumatelor.",
    )
    parser.add_argument(
        "--questions-reasoning-effort",
        choices=("none", "minimal", "low", "medium", "high", "xhigh", "max"),
        default=DEFAULT_QUESTION_REASONING_EFFORT,
        help=(
            "Reasoning pentru întrebări (implicit: "
            f"{DEFAULT_QUESTION_REASONING_EFFORT})."
        ),
    )
    parser.add_argument(
        "--summaries-reasoning-effort",
        choices=("none", "minimal", "low", "medium", "high", "xhigh", "max"),
        default=DEFAULT_SUMMARY_REASONING_EFFORT,
        help=(
            "Reasoning pentru rezumate (implicit: "
            f"{DEFAULT_SUMMARY_REASONING_EFFORT})."
        ),
    )
    parser.add_argument(
        "--summaries-max-attempts",
        type=int,
        default=DEFAULT_SUMMARY_MAX_ATTEMPTS,
        metavar="N",
        help=(
            "Compatibilitate CLI: valoarea acceptată este 1. Prima variantă este "
            "păstrată indiferent de validarea semantică."
        ),
    )
    parser.add_argument(
        "--compositions-reasoning-effort",
        choices=("none", "minimal", "low", "medium", "high", "xhigh", "max"),
        default="none",
    )
    parser.add_argument("--provider-order", action="append", metavar="PROVIDER")
    fallback = parser.add_mutually_exclusive_group()
    fallback.add_argument("--allow-provider-fallbacks", dest="allow_fallbacks", action="store_true")
    fallback.add_argument("--no-provider-fallbacks", dest="allow_fallbacks", action="store_false")
    parser.set_defaults(allow_fallbacks=True)
    args = parser.parse_args(argv)

    if args.finalize_only and not args.resume_run:
        parser.error("--finalize-only necesită --resume-run.")
    if args.summaries_max_attempts != 1:
        parser.error(
            "Rezumatele folosesc exact o încercare; --summaries-max-attempts trebuie să fie 1."
        )
    try:
        available_specs = build_task_specs()
    except (ValueError, FileNotFoundError) as exc:
        parser.error(str(exc))
    if args.plan_only:
        try:
            selected = select_specs(available_specs, args.tasks, args.only)
        except ValueError as exc:
            parser.error(str(exc))
        print_plan(selected)
        return 0

    if args.resume_run:
        try:
            run_dir = resolve_run_dir(args.resume_run)
        except ValueError as exc:
            parser.error(str(exc))
        metadata = read_json(run_dir / "metadata.json")
        saved_question_packets = run_dir / "inputs" / "question-packets"
        if saved_question_packets.is_dir():
            try:
                available_specs = build_task_specs(saved_question_packets)
            except (ValueError, FileNotFoundError) as exc:
                parser.error(str(exc))
        model_id = str(metadata.get("requested_model") or "")
        if args.model and args.model != model_id:
            parser.error(f"Rularea folosește {model_id!r}; nu poate fi reluată cu {args.model!r}.")
        manifest = read_json(run_dir / "manifest.json")
        available_by_key = {spec.key: spec for spec in available_specs}
        saved_keys = [str(item.get("key")) for item in manifest.get("tasks") or []]
        missing_specs = [key for key in saved_keys if key not in available_by_key]
        if missing_specs:
            parser.error(f"Nu mai există definițiile locale pentru sarcinile: {missing_specs}.")
        specs = [available_by_key[key] for key in saved_keys]
        try:
            verify_manifest_inputs(manifest, specs)
        except ValueError as exc:
            parser.error(str(exc))
    else:
        run_dir = None
        metadata = {}
        model_id = args.model or DEFAULT_MODEL
        specs = available_specs

    try:
        selected = select_specs(specs, args.tasks, args.only)
    except ValueError as exc:
        parser.error(str(exc))
    if not selected:
        parser.error(
            f"Rularea selectată nu conține sarcini pentru grupul {args.tasks!r}. "
            "Pornește o rulare nouă pentru noile tipuri de pachete."
        )

    if args.finalize_only:
        assert run_dir is not None
        report = generate_report(run_dir, specs, metadata)
        print(f"Raport reconstruit fără apel API: {report}")
        return 0

    config = load_local_env(args.config)
    config_used = args.config
    if not config.get("OPENROUTER_API_KEY") and args.config == DEFAULT_CONFIG_PATH:
        legacy = load_local_env(LEGACY_CONFIG_PATH)
        if legacy.get("OPENROUTER_API_KEY"):
            config = {**legacy, **config}
            config_used = LEGACY_CONFIG_PATH
    api_key = config.get("OPENROUTER_API_KEY", "")
    if not api_key:
        parser.error(
            f"OPENROUTER_API_KEY lipsește din {args.config}; vezi config.local.env.example."
        )
    if not args.resume_run and not args.model and args.config.is_file():
        model_id = config.get("OPENROUTER_MODEL") or DEFAULT_MODEL

    print(f"Verific modelul: {model_id}")
    try:
        model_info = get_model_info(api_key, model_id, args.timeout)
    except Exception as exc:
        parser.error(str(exc))
    print(f"Model disponibil: {model_info.get('name') or model_id}")
    print(f"Context declarat: {model_info.get('context_length')} tokenuri")
    if args.preflight_only:
        return 0

    context_length = int(model_info.get("context_length") or 0)
    for spec in selected:
        prompt, _ = render_prompt(spec)
        estimate = math.ceil(len(prompt) / QWEN_CHARS_PER_TOKEN)
        if context_length and estimate + args.max_tokens > context_length:
            parser.error(
                f"{spec.key}: input estimat {estimate} + max output {args.max_tokens} "
                f"depășește contextul {context_length}."
            )

    if run_dir is None:
        timestamp = utc_now()
        run_id = timestamp.strftime("run-%Y%m%dT%H%M%SZ")
        run_dir = RUNS_DIR / safe_name(model_id) / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        try:
            question_packet_dir, selection_record = reserve_question_batch(run_dir)
            specs = build_task_specs(question_packet_dir)
            selected = select_specs(specs, args.tasks, args.only)
        except (ValueError, FileNotFoundError) as exc:
            save_json(run_dir / "question-selection.error.json", {"message": str(exc)})
            parser.error(str(exc))
        manifest = build_manifest(specs)
        save_json(run_dir / "manifest.json", manifest)
        metadata = {
            "experiment": "Pachete Qwen — întrebări și rezumate pe capitole",
            "schema_version": 1,
            "run_id": run_id,
            "timestamp_utc": timestamp.isoformat(),
            "requested_model": model_id,
            "model_name": model_info.get("name"),
            "context_length": model_info.get("context_length"),
            "config_path": relative_display(config_used),
            "api_key_saved": False,
            "task_count": len(specs),
            "question_task_count": 8,
            "question_batch_number": selection_record["batch_number"],
            "question_selected_event_count": selection_record["selected_event_count"],
            "summary_task_count": 13,
            "composition_task_count": 3,
        }
        save_json(run_dir / "metadata.json", metadata)
        generate_report(run_dir, specs, metadata)
        print(f"Rulare nouă: {run_dir}")
    else:
        print(f"Reiau rularea: {run_dir}")

    # Pentru o rulare nouă, packeturile de întrebări tocmai au fost materializate
    # în folderul ei; verificarea exactă trebuie făcută pe aceste snapshoturi.
    for spec in selected:
        prompt, _ = render_prompt(spec)
        estimate = math.ceil(len(prompt) / QWEN_CHARS_PER_TOKEN)
        if context_length and estimate + args.max_tokens > context_length:
            parser.error(
                f"{spec.key}: input estimat {estimate} + max output {args.max_tokens} "
                f"depășește contextul {context_length}."
            )

    tasks_to_run: list[TaskSpec] = []
    for spec in selected:
        latest = load_latest(run_dir, spec)
        may_retry_completed = args.retry_succeeded and spec.task_type == "compositions"
        summary_first_result_kept = bool(
            latest and spec.task_type == "summaries" and latest.get("status") == "invalid"
        )
        if (
            latest
            and (latest.get("status") in TERMINAL_GENERATION_STATUSES or summary_first_result_kept)
            and not may_retry_completed
        ):
            print(f"Sar peste {spec.key}: există deja un răspuns generat și păstrat.")
        else:
            tasks_to_run.append(spec)

    if not tasks_to_run:
        report = generate_report(run_dir, specs, metadata)
        print(f"Nu există sarcini de trimis. Raport actualizat: {report}")
        return 0

    print_plan(tasks_to_run)
    for position, spec in enumerate(tasks_to_run, start=1):
        effort = {
            "questions": args.questions_reasoning_effort,
            "summaries": args.summaries_reasoning_effort,
            "compositions": args.compositions_reasoning_effort,
        }[spec.task_type]
        max_attempts = {
            "questions": 1,
            "summaries": 1,
            "compositions": 1,
        }[spec.task_type]
        previous = load_latest(run_dir, spec)
        for local_attempt in range(1, max_attempts + 1):
            retry_feedback = build_validator_retry_feedback(spec, previous)
            retry_source_attempt = (
                int(previous["attempt"])
                if retry_feedback and isinstance(previous, Mapping) and previous.get("attempt") is not None
                else None
            )
            print(
                f"[{position}/{len(tasks_to_run)}] Trimit {spec.key} cu reasoning={effort} "
                f"(apel {local_attempt}/{max_attempts})..."
            )
            try:
                latest = run_one_task(
                    spec,
                    run_dir,
                    api_key=api_key,
                    model_id=model_id,
                    model_info=model_info,
                    max_tokens=args.max_tokens,
                    timeout=args.timeout,
                    reasoning_effort=effort,
                    allow_provider_fallbacks=args.allow_fallbacks,
                    provider_order=args.provider_order,
                    retry_feedback=retry_feedback,
                    retry_source_attempt=retry_source_attempt,
                )
            except KeyboardInterrupt:
                generate_report(run_dir, specs, metadata)
                print("\nRulare întreruptă; progresul de până acum a fost păstrat.")
                return 130
            report = generate_report(run_dir, specs, metadata)
            usage = latest.get("usage") or {}
            print(
                f"{spec.key}: {latest.get('status')} în {latest.get('duration_seconds')} s; "
                f"tokenuri={usage.get('total_tokens', '—')}; cost={usage.get('cost', '—')} USD"
            )
            print(f"Raport intermediar: {report}")
            if latest.get("status") == "invalid" and spec.task_type == "summaries":
                print(f"{spec.key}: varianta invalidă a fost păstrată; nu se regenerează.")
            break

    final = write_consolidated_results(run_dir, specs)
    report = generate_report(run_dir, specs, metadata)
    print(
        f"Finalizat: {final['completed']}/{final['task_count']} rezultate păstrate; "
        f"{final['questions_retained']} întrebări; "
        f"{final['chapter_summaries_completed']} rezumate; "
        f"{final['composition_elements_completed']} scheme compoziționale."
    )
    print(f"Raport: {report}")
    return 0 if final["invalid"] == 0 and final["errors"] == 0 else 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
