"""Construiește integral secțiunea UI „Înțelege opera” pentru o operă nouă.

Singurul input obligatoriu este knowledge graph-ul. Pipeline-ul generează rezumatul
pe capitole, mind-mapurile personajelor, materialul despre curent, două secvențe
relevante verbatim și cele trei scheme compoziționale. Fiecare sarcină Qwen are o
singură încercare; validarea este diagnostică și nu declanșează regenerări.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_character_mindmaps import build_and_write as build_character_mindmaps
from build_composition_schemas import (
    DEFAULT_MAX_TOKENS as DEFAULT_COMPOSITION_MAX_TOKENS,
    generate_composition_schemas,
)
from build_literary_current import (
    build_packet as build_literary_current_packet,
    generate_literary_current,
    render_prompt as render_literary_current_prompt,
)
from cost_reporting import combine_cost_summaries, summarize_usages
from exercise_builder_common import (
    DEFAULT_GRAPH_PATH,
    ROOT_DIR,
    clean_text,
    graph_work_metadata,
    read_json,
    write_json,
)


QWEN_DIR = ROOT_DIR / "cercetare-qwen"
DEFAULT_CONFIG_PATH = QWEN_DIR / "config.local.env"
LEGACY_CONFIG_PATH = ROOT_DIR / "cercetare" / "experiment2" / "config.local.env"
DEFAULT_MODEL = "qwen/qwen3.7-flash"
DEFAULT_REASONING = "medium"
DEFAULT_SUMMARY_MAX_TOKENS = 12_000
DEFAULT_SELECTION_MAX_TOKENS = 8_000
REASONING_CHOICES = ("none", "minimal", "low", "medium", "high", "xhigh", "max")


def _runner() -> ModuleType:
    name = "bacapp_understanding_qwen_runner"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    path = QWEN_DIR / "run_qwen_packets.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Nu pot încărca runner-ul Qwen din {path}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _slug(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(character for character in text if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_") or "item"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_model_essay(
    graph: dict,
    graph_path: Path,
    explicit_path: Path | None,
) -> Path:
    if explicit_path is not None:
        resolved = explicit_path.resolve()
        if not resolved.is_file():
            raise ValueError(f"Eseul-model nu există: {resolved}")
        return resolved
    for source in graph.get("sources", []):
        if not isinstance(source, dict) or source.get("source_type") != "model_essay":
            continue
        raw_path = Path(str(source.get("path") or ""))
        if not str(raw_path):
            continue
        candidates = (
            [raw_path]
            if raw_path.is_absolute()
            else [ROOT_DIR / raw_path, graph_path.parent / raw_path]
        )
        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve()
    raise ValueError(
        "Înțelege opera necesită eseul-model pentru cele două trăsături ale "
        "curentului. Declară-l în sources cu source_type='model_essay' sau "
        "folosește --model-essay."
    )


def _extract_json(text: str) -> dict | None:
    cleaned = str(text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        value = json.loads(cleaned)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            return None
        try:
            value = json.loads(match.group(0))
            return value if isinstance(value, dict) else None
        except json.JSONDecodeError:
            return None


def _chapters(graph: dict) -> list[dict]:
    declared = graph.get("chapters")
    if isinstance(declared, list) and declared:
        chapters = [dict(value) for value in declared if isinstance(value, dict)]
    else:
        chapters = []
        for node in graph.get("nodes", []):
            if not isinstance(node, dict) or node.get("type") != "Chapter":
                continue
            attributes = node.get("attributes") if isinstance(node.get("attributes"), dict) else {}
            chapters.append(
                {
                    "id": str(node.get("id") or ""),
                    "ordinal": attributes.get("ordinal") or attributes.get("order") or 0,
                    "title": clean_text(node.get("label") or node.get("description")),
                    "event_sequence": [],
                }
            )
        chapter_by_id = {str(chapter.get("id")): chapter for chapter in chapters}
        for node in graph.get("nodes", []):
            if not isinstance(node, dict) or node.get("type") not in {"NarrativeEvent", "Event"}:
                continue
            attributes = node.get("attributes") if isinstance(node.get("attributes"), dict) else {}
            chapter_id = str(attributes.get("chapter_id") or "")
            if not chapter_id and isinstance(node.get("chapter_ids"), list) and node["chapter_ids"]:
                chapter_id = str(node["chapter_ids"][0])
            if chapter_id in chapter_by_id:
                chapter_by_id[chapter_id]["event_sequence"].append(str(node.get("id")))
    chapters.sort(key=lambda value: (int(value.get("ordinal") or 0), str(value.get("id") or "")))
    if not chapters:
        raise ValueError("Knowledge graph-ul nu declară niciun capitol.")
    return chapters


def _events_by_id(graph: dict) -> dict[str, dict]:
    return {
        str(node["id"]): node
        for node in graph.get("nodes", [])
        if isinstance(node, dict)
        and node.get("id")
        and node.get("type") in {"NarrativeEvent", "Event"}
    }


def _event_attributes(event: dict) -> dict:
    return event.get("attributes") if isinstance(event.get("attributes"), dict) else {}


def _event_quote(event: dict) -> str:
    attributes = _event_attributes(event)
    verification = attributes.get("verification") if isinstance(attributes.get("verification"), dict) else {}
    return clean_text(
        verification.get("evidence_quote")
        or attributes.get("evidence_quote")
        or event.get("evidence_quote")
    )


def _event_fact(event: dict) -> str:
    attributes = _event_attributes(event)
    return clean_text(
        attributes.get("canonical_description")
        or attributes.get("simple_narration")
        or attributes.get("action")
        or event.get("description")
        or event.get("label")
    )


def _chapter_packet(graph: dict, chapter: dict) -> dict:
    events_by_id = _events_by_id(graph)
    event_ids = [str(value) for value in chapter.get("event_sequence", []) if str(value) in events_by_id]
    if not event_ids:
        chapter_id = str(chapter.get("id") or "")
        candidates = []
        for event_id, event in events_by_id.items():
            attributes = _event_attributes(event)
            ids = [str(value) for value in event.get("chapter_ids", [])] if isinstance(event.get("chapter_ids"), list) else []
            if str(attributes.get("chapter_id") or "") == chapter_id or chapter_id in ids:
                candidates.append(event_id)
        event_ids = sorted(
            candidates,
            key=lambda event_id: (
                int(_event_attributes(events_by_id[event_id]).get("chapter_order") or 0),
                event_id,
            ),
        )
    return {
        "schema_version": 1,
        "task": "chapter_summary",
        "work": graph_work_metadata(graph),
        "chapter": {
            "id": str(chapter.get("id") or ""),
            "ordinal": int(chapter.get("ordinal") or 0),
            "title": clean_text(chapter.get("title")) or str(chapter.get("id") or "Capitol"),
            "event_ids": event_ids,
        },
        "events": [
            {
                "id": event_id,
                "order": _event_attributes(events_by_id[event_id]).get("chapter_order"),
                "fact": _event_fact(events_by_id[event_id]),
                "evidence_quote": _event_quote(events_by_id[event_id]),
            }
            for event_id in event_ids
        ],
    }


def _summary_prompt(packet: dict) -> str:
    chapter = packet["chapter"]
    return f"""
Ești un verbalizator factual pentru Bacalaureat. Scrie rezumatul capitolului
„{chapter['title']}” al operei „{packet['work']['title']}”.

REGULI:
- folosește exclusiv evenimentele din packet și păstrează ordinea lor;
- nu inventa fapte, citate, cauze sau consecințe;
- scrie natural în română, în 2-4 paragrafe;
- produce o singură variantă;
- răspunde exclusiv cu JSON valid, fără markdown.

SCHEMA:
{{"chapter_id":"{chapter['id']}","summary":"rezumatul", "covered_event_ids":["ID"]}}

PACKET:
{json.dumps(packet, ensure_ascii=False, separators=(',', ':'))}
""".strip()


def _normalize_chapter_summary(raw: dict | None, raw_text: str, packet: dict) -> dict:
    payload = raw if isinstance(raw, dict) else {}
    summary = str(payload.get("summary") or "").strip()
    if not summary:
        stripped = str(raw_text or "").strip()
        if stripped:
            summary = stripped.strip("`").strip()
    if not summary:
        summary = " ".join(
            value for value in (clean_text(event.get("fact")) for event in packet["events"]) if value
        )
    expected_ids = [str(value) for value in packet["chapter"]["event_ids"]]
    covered = payload.get("covered_event_ids") if isinstance(payload.get("covered_event_ids"), list) else []
    covered_ids = [str(value) for value in covered if str(value) in expected_ids]
    errors = []
    if not clean_text(payload.get("summary")):
        errors.append("Răspunsul JSON nu conține un câmp summary utilizabil.")
    if set(covered_ids) != set(expected_ids):
        errors.append("Lista covered_event_ids nu acoperă exact evenimentele capitolului.")
    return {
        **packet["chapter"],
        "summary": summary,
        "covered_event_ids": covered_ids,
        "validation": {"valid": not errors, "errors": errors},
    }


def _request_qwen(
    runner: ModuleType,
    api_key: str,
    prompt: str,
    *,
    model: str,
    reasoning: str,
    timeout: int,
    max_tokens: int,
) -> tuple[dict, str]:
    request = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.15,
        "reasoning": {"effort": reasoning, "exclude": True},
        "provider": {
            "allow_fallbacks": True,
            "require_parameters": True,
            "data_collection": "deny",
        },
        "response_format": {"type": "json_object"},
    }
    response = runner.api_json(
        f"{runner.OPENROUTER_BASE_URL}/chat/completions",
        api_key,
        method="POST",
        payload=request,
        timeout=timeout,
    )
    try:
        content = runner.extract_content(response)
    except ValueError:
        choices = response.get("choices") or []
        first_choice = choices[0] if choices and isinstance(choices[0], dict) else {}
        finish_reason = first_choice.get("finish_reason") or first_choice.get(
            "native_finish_reason"
        )
        if finish_reason != "length":
            raise
        # Nu relansăm cererea: răspunsul și costul sunt păstrate, iar normalizatorul
        # marchează rezultatul invalid și construiește fallback-ul determinist.
        content = ""
    return {"request": request, "response": response}, content


def _load_api(config_path: Path) -> tuple[ModuleType, str]:
    runner = _runner()
    config = runner.load_local_env(config_path)
    if not config.get("OPENROUTER_API_KEY"):
        config = {**runner.load_local_env(LEGACY_CONFIG_PATH), **config}
    api_key = str(config.get("OPENROUTER_API_KEY") or "")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY lipsește din configurație.")
    return runner, api_key


def _find_cached_chapter_summary(
    output_dir: Path,
    chapter_dir_name: str,
    packet: dict,
    prompt: str,
    *,
    model: str,
    reasoning: str,
) -> dict[str, Any] | None:
    runs_dir = output_dir / "qwen-summary-runs"
    if not runs_dir.is_dir():
        return None
    for previous_run in sorted(runs_dir.glob("run-*"), reverse=True):
        previous_chapter_dir = previous_run / chapter_dir_name
        packet_path = previous_chapter_dir / "packet.json"
        request_path = previous_chapter_dir / "request.json"
        response_path = previous_chapter_dir / "response.openrouter.json"
        raw_path = previous_chapter_dir / "response.raw.txt"
        if not all(path.is_file() for path in (packet_path, request_path, response_path, raw_path)):
            continue
        try:
            cached_packet = read_json(packet_path)
            request = read_json(request_path)
            response = read_json(response_path)
            content = raw_path.read_text(encoding="utf-8").strip()
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        messages = request.get("messages") if isinstance(request.get("messages"), list) else []
        request_prompt = ""
        if messages and isinstance(messages[-1], dict):
            request_prompt = str(messages[-1].get("content") or "")
        request_reasoning = request.get("reasoning") if isinstance(request.get("reasoning"), dict) else {}
        if (
            cached_packet != packet
            or str(request.get("model") or "") != model
            or str(request_reasoning.get("effort") or "none") != reasoning
            or request_prompt != prompt
        ):
            continue
        parsed = _extract_json(content)
        normalized = _normalize_chapter_summary(parsed, content, packet)
        return {
            "source_chapter_dir": previous_chapter_dir,
            "response_path": response_path,
            "content": content,
            "parsed": parsed,
            "normalized": normalized,
            "response": response,
        }
    return None


def _find_reusable_artifact(
    output_path: Path,
    expected_packet: dict,
    expected_prompt: str,
    *,
    model: str,
    reasoning: str,
) -> dict[str, Any] | None:
    if not output_path.is_file():
        return None
    try:
        artifact = read_json(output_path)
        generation = artifact.get("generation") if isinstance(artifact.get("generation"), dict) else {}
        validation = artifact.get("validation") if isinstance(artifact.get("validation"), dict) else {}
        sequences = artifact.get("sequences") if isinstance(artifact.get("sequences"), list) else []
        if (
            generation.get("locked_from_regeneration") is True
            and validation.get("all_text_is_verbatim") is True
            and validation.get("matched_to_model_essay") is True
            and len(sequences) == 2
            and all(
                isinstance(item, dict)
                and item.get("source_mode") == "verbatim_pdf_excerpt"
                and clean_text(item.get("text"))
                for item in sequences
            )
        ):
            reused = json.loads(json.dumps(artifact, ensure_ascii=False))
            reused_generation = reused.setdefault("generation", {})
            reused_generation["usage"] = {}
            reused_generation["reused"] = True
            reused_generation["reused_from"] = str(output_path)
            reused_generation["new_api_call"] = False
            return reused
        run_dir = Path(str(generation.get("run_dir") or ""))
        packet_path = run_dir / "packet.json"
        prompt_path = run_dir / "prompt.txt"
        if not packet_path.is_file() or not prompt_path.is_file():
            return None
        packet = read_json(packet_path)
        prompt = prompt_path.read_text(encoding="utf-8").rstrip("\n")
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if (
        packet != expected_packet
        or prompt != expected_prompt
        or str(generation.get("model") or "") != model
        or str(generation.get("reasoning_effort") or "none") != reasoning
    ):
        return None
    reused = json.loads(json.dumps(artifact, ensure_ascii=False))
    reused_generation = reused.setdefault("generation", {})
    reused_generation["usage"] = {}
    reused_generation["reused"] = True
    reused_generation["reused_from"] = str(output_path)
    reused_generation["new_api_call"] = False
    return reused


def generate_chapter_summaries(
    graph: dict,
    graph_path: Path,
    output_dir: Path,
    *,
    runner: ModuleType,
    api_key: str,
    model: str,
    reasoning: str,
    timeout: int,
    max_tokens: int,
) -> tuple[dict, Path, Path]:
    run_dir = output_dir / "qwen-summary-runs" / f"run-{_stamp()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    results = []
    usage = []
    reused_chapters = []
    chapters = _chapters(graph)
    for index, chapter in enumerate(chapters, start=1):
        packet = _chapter_packet(graph, chapter)
        chapter_dir = run_dir / f"{index:02d}-{_slug(packet['chapter']['title'])}"
        chapter_dir.mkdir(parents=True, exist_ok=False)
        prompt = _summary_prompt(packet)
        write_json(chapter_dir / "packet.json", packet)
        (chapter_dir / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")
        cached = _find_cached_chapter_summary(
            output_dir,
            chapter_dir.name,
            packet,
            prompt,
            model=model,
            reasoning=reasoning,
        )
        if cached is not None:
            print(
                f"[Rezumat {index}/{len(chapters)}] {packet['chapter']['title']} "
                "- reutilizat local"
            )
            reuse_record = {
                "reused": True,
                "source_chapter_dir": str(cached["source_chapter_dir"]),
                "source_response": str(cached["response_path"]),
                "new_api_call": False,
            }
            write_json(chapter_dir / "reuse.json", reuse_record)
            (chapter_dir / "response.raw.reused.txt").write_text(
                str(cached["content"]) + "\n", encoding="utf-8"
            )
            if cached["parsed"] is not None:
                write_json(chapter_dir / "result.json", cached["parsed"])
            write_json(
                chapter_dir / "validation.json", cached["normalized"]["validation"]
            )
            results.append(cached["normalized"])
            reused_chapters.append(
                {
                    "chapter_id": packet["chapter"]["id"],
                    **reuse_record,
                }
            )
            continue
        print(f"[Rezumat {index}/{len(chapters)}] {packet['chapter']['title']}")
        exchange, content = _request_qwen(
            runner, api_key, prompt, model=model, reasoning=reasoning,
            timeout=timeout, max_tokens=max_tokens,
        )
        write_json(chapter_dir / "request.json", exchange["request"])
        write_json(chapter_dir / "response.openrouter.json", exchange["response"])
        (chapter_dir / "response.raw.txt").write_text(content + "\n", encoding="utf-8")
        parsed = _extract_json(content)
        if parsed is not None:
            write_json(chapter_dir / "result.json", parsed)
        normalized = _normalize_chapter_summary(parsed, content, packet)
        write_json(chapter_dir / "validation.json", normalized["validation"])
        results.append(normalized)
        usage.append(exchange["response"].get("usage") or {})
    artifact = {
        "schema_version": 1,
        "work": graph_work_metadata(graph),
        "generation": {
            "model": model,
            "reasoning_effort": reasoning,
            "attempts_per_chapter": 1,
            "retry_on_invalid": False,
            "api_calls": len(usage),
            "reused_chapter_count": len(reused_chapters),
            "reused_chapters": reused_chapters,
            "source_graph": str(graph_path),
            "run_dir": str(run_dir),
            "usage": usage,
        },
        "chapters": results,
        "validation": {
            "valid_chapters": sum(bool(item["validation"]["valid"]) for item in results),
            "chapter_count": len(results),
            "diagnostic_only": True,
        },
    }
    json_path = output_dir / "rezumat-pe-capitole.json"
    markdown_path = output_dir / "rezumat-pe-capitole.md"
    markdown = [f"# Rezumat pe capitole — {artifact['work']['title']}", ""]
    for chapter in results:
        markdown.extend((f"## {chapter['title']}", "", chapter["summary"], ""))
    write_json(json_path, artifact)
    markdown_path.write_text("\n".join(markdown).rstrip() + "\n", encoding="utf-8")
    write_json(run_dir / "manifest.json", artifact)
    return artifact, json_path, markdown_path


def _model_essay_from_graph(graph: dict, graph_path: Path) -> tuple[str, str]:
    for source in graph.get("sources", []):
        if not isinstance(source, dict) or source.get("source_type") != "model_essay":
            continue
        raw_path = Path(str(source.get("path") or ""))
        candidates = [raw_path] if raw_path.is_absolute() else [ROOT_DIR / raw_path, graph_path.parent / raw_path]
        for candidate in candidates:
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8").strip(), str(candidate)
    return "", ""


def _sequence_candidates(graph: dict, chapters: list[dict]) -> list[dict]:
    events = _events_by_id(graph)
    chapter_by_id = {str(chapter.get("id")): chapter for chapter in chapters}
    candidates = []
    for event_id, event in events.items():
        quote = _event_quote(event)
        if not quote:
            continue
        attributes = _event_attributes(event)
        chapter_id = str(attributes.get("chapter_id") or "")
        if not chapter_id and isinstance(event.get("chapter_ids"), list) and event["chapter_ids"]:
            chapter_id = str(event["chapter_ids"][0])
        if chapter_id not in chapter_by_id:
            continue
        candidates.append(
            {
                "id": event_id,
                "chapter_id": chapter_id,
                "chapter_order": int(attributes.get("chapter_order") or 0),
                "importance": str(event.get("importance") or "minor"),
                "title": clean_text(attributes.get("title") or event.get("label")),
                "fact": _event_fact(event),
                "evidence_quote": quote,
            }
        )
    candidates.sort(
        key=lambda item: (
            int(chapter_by_id[item["chapter_id"]].get("ordinal") or 0),
            item["chapter_order"],
            item["id"],
        )
    )
    if len(candidates) < 2:
        raise ValueError(
            "Graful trebuie să conțină cel puțin două evenimente cu evidence_quote "
            "verbatim din textul integral pentru secvențele relevante."
        )
    return candidates


def _sequence_prompt(graph: dict, graph_path: Path, candidates: list[dict]) -> str:
    model_essay, model_essay_path = _model_essay_from_graph(graph, graph_path)
    packet = {
        "work": graph_work_metadata(graph),
        "model_essay_path": model_essay_path,
        "model_essay": model_essay,
        "candidate_events": [
            {key: item[key] for key in ("id", "chapter_id", "chapter_order", "importance", "title", "fact")}
            for item in candidates[:160]
        ],
    }
    return f"""
Selectează exact două secvențe relevante pentru înțelegerea și eseul operei din packet.
Eseul-model are prioritate când există. Tu NU ai voie să generezi, să copiezi sau să
parafrazezi textul operei: returnezi numai ID-uri existente.

Pentru fiecare secvență selectează între 1 și 3 evenimente din același capitol, în ordine.
Selectează NUMAI evenimentele care aparțin direct scenei descrise în eseul-model.
Nu adăuga începutul capitolului, context îndepărtat, alte întâmplări din același capitol
sau evenimente despre alte teme doar pentru a forma o succesiune mai lungă.
Răspunde exclusiv cu JSON valid:
{{"sequences":[{{"title":"etichetă scurtă", "event_ids":["EV_1"]}},{{"title":"etichetă scurtă", "event_ids":["EV_2"]}}]}}

PACKET:
{json.dumps(packet, ensure_ascii=False, separators=(',', ':'))}
""".strip()


def _normalize_sequence_selection(raw: dict | None, graph: dict, candidates: list[dict]) -> dict:
    chapters = _chapters(graph)
    chapter_by_id = {str(chapter.get("id")): chapter for chapter in chapters}
    candidate_by_id = {item["id"]: item for item in candidates}
    raw_items = raw.get("sequences") if isinstance(raw, dict) and isinstance(raw.get("sequences"), list) else []
    normalized = []
    errors = []
    used_ids: set[str] = set()

    def build_item(item: dict, position: int) -> dict | None:
        requested = item.get("event_ids") if isinstance(item.get("event_ids"), list) else []
        valid = [str(value) for value in requested if str(value) in candidate_by_id]
        if not valid:
            return None
        chapter_counts = Counter(candidate_by_id[event_id]["chapter_id"] for event_id in valid)
        chapter_id = chapter_counts.most_common(1)[0][0]
        valid = [event_id for event_id in valid if candidate_by_id[event_id]["chapter_id"] == chapter_id]
        valid = sorted(
            dict.fromkeys(valid),
            key=lambda event_id: (candidate_by_id[event_id]["chapter_order"], event_id),
        )[:3]
        selected = [candidate_by_id[event_id] for event_id in valid]
        title = clean_text(item.get("title")) or selected[0]["title"] or f"Secvența {position}"
        return {
            "id": f"secventa_{position}_{_slug(title)}",
            "button_label": f"Secvența {position}",
            "title": title,
            "chapter_id": chapter_id,
            "chapter": clean_text(chapter_by_id[chapter_id].get("title")) or chapter_id,
            "source": "Text verbatim din opera integrală · dovezi păstrate în knowledge graph",
            "text": "\n\n".join(candidate_by_id[event_id]["evidence_quote"] for event_id in valid),
            "event_ids": valid,
            "source_mode": "verbatim_graph_evidence",
        }

    for raw_item in raw_items[:2]:
        if not isinstance(raw_item, dict):
            continue
        built = build_item(raw_item, len(normalized) + 1)
        if built:
            normalized.append(built)
            used_ids.update(built["event_ids"])
        else:
            errors.append("O secvență Qwen nu conține niciun ID cu dovadă verbatim validă.")

    ranked = sorted(
        candidates,
        key=lambda item: (
            {"major": 0, "supporting": 1, "minor": 2}.get(item["importance"], 3),
            -len(item["evidence_quote"]),
            item["chapter_id"],
            item["chapter_order"],
        ),
    )
    while len(normalized) < 2:
        fallback = next(
            (item for item in ranked if item["id"] not in used_ids and item["chapter_id"] not in {value["chapter_id"] for value in normalized}),
            None,
        ) or next((item for item in ranked if item["id"] not in used_ids), None)
        if fallback is None:
            break
        built = build_item({"title": fallback["title"], "event_ids": [fallback["id"]]}, len(normalized) + 1)
        if built:
            normalized.append(built)
            used_ids.update(built["event_ids"])
            errors.append("Selecția Qwen incompletă a fost completată determinist cu o dovadă verbatim din graf.")
    if len(normalized) != 2:
        errors.append(f"Au putut fi construite doar {len(normalized)} din cele două secvențe obligatorii.")
    return {
        "sequences": normalized,
        "validation": {
            "valid": not errors and len(normalized) == 2,
            "errors": errors,
            "diagnostic_only": True,
            "all_text_is_verbatim": all(value.get("source_mode") == "verbatim_graph_evidence" for value in normalized),
        },
    }


def generate_relevant_sequences(
    graph: dict,
    graph_path: Path,
    output_dir: Path,
    *,
    runner: ModuleType,
    api_key: str,
    model: str,
    reasoning: str,
    timeout: int,
    max_tokens: int,
) -> tuple[dict, Path]:
    candidates = _sequence_candidates(graph, _chapters(graph))
    prompt = _sequence_prompt(graph, graph_path, candidates)
    run_dir = output_dir / "qwen-sequence-selection-runs" / f"run-{_stamp()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    packet = {"work": graph_work_metadata(graph), "candidate_events": candidates}
    write_json(run_dir / "packet.json", packet)
    (run_dir / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")
    exchange, content = _request_qwen(
        runner, api_key, prompt, model=model, reasoning=reasoning,
        timeout=timeout, max_tokens=max_tokens,
    )
    write_json(run_dir / "request.json", exchange["request"])
    write_json(run_dir / "response.openrouter.json", exchange["response"])
    (run_dir / "response.raw.txt").write_text(content + "\n", encoding="utf-8")
    parsed = _extract_json(content)
    if parsed is not None:
        write_json(run_dir / "result.json", parsed)
    normalized = _normalize_sequence_selection(parsed, graph, candidates)
    artifact = {
        "schema_version": 1,
        "work": graph_work_metadata(graph),
        "generation": {
            "model": model,
            "reasoning_effort": reasoning,
            "attempts": 1,
            "retry_on_invalid": False,
            "selection_only": True,
            "text_generated_by_ai": False,
            "source_graph": str(graph_path),
            "run_dir": str(run_dir),
            "usage": exchange["response"].get("usage") or {},
        },
        **normalized,
    }
    output_path = output_dir / "secvente-relevante.json"
    write_json(output_path, artifact)
    write_json(run_dir / "manifest.json", artifact)
    return artifact, output_path


def build_understanding_project(
    graph_path: Path,
    *,
    model_essay_path: Path | None = None,
    config_path: Path = DEFAULT_CONFIG_PATH,
    model: str = DEFAULT_MODEL,
    reasoning: str = DEFAULT_REASONING,
    timeout: int = 1200,
    summary_max_tokens: int = DEFAULT_SUMMARY_MAX_TOKENS,
    selection_max_tokens: int = DEFAULT_SELECTION_MAX_TOKENS,
    dry_run: bool = False,
) -> tuple[dict, Path]:
    graph = read_json(graph_path)
    work = graph_work_metadata(graph)
    model_essay = _resolve_model_essay(graph, graph_path, model_essay_path)
    chapters = _chapters(graph)
    output_dir = ROOT_DIR / "data" / "generated_works" / work["work_id"] / "intelegere-opera"
    pipeline_run_dir = output_dir / "pipeline-runs" / f"run-{_stamp()}"
    pipeline_run_dir.mkdir(parents=True, exist_ok=False)
    qwen_calls = len(chapters) + 5
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "pipeline": "intelegere-opera",
        "status": "planned" if dry_run else "running",
        "work": work,
        "source_graph": str(graph_path),
        "model_essay": str(model_essay),
        "model_essay_sha256": _sha256(model_essay),
        "source_graph_sha256_before": _sha256(graph_path),
        "source_graph_modified": False,
        "model": model,
        "reasoning_effort": reasoning,
        "qwen_calls": qwen_calls,
        "retry_on_invalid": False,
        "steps": [
            {"id": "summary", "calls": len(chapters)},
            {"id": "characters", "calls": 0, "deterministic": True},
            {"id": "relevant_sequences", "calls": 1, "text_generated_by_ai": False},
            {"id": "literary_current", "calls": 1},
            {"id": "composition", "calls": 3},
        ],
        "pipeline_run_dir": str(pipeline_run_dir),
    }
    if dry_run:
        write_json(pipeline_run_dir / "manifest.json", manifest)
        return manifest, pipeline_run_dir / "manifest.json"

    runner, api_key = _load_api(config_path)
    artifacts: dict[str, str] = {}
    reused_artifacts: list[str] = []
    try:
        summary_artifact, summary_json_path, summary_markdown_path = generate_chapter_summaries(
            graph, graph_path, output_dir, runner=runner, api_key=api_key,
            model=model, reasoning=reasoning, timeout=timeout,
            max_tokens=summary_max_tokens,
        )
        artifacts["summary_json"] = str(summary_json_path)
        artifacts["summary_markdown"] = str(summary_markdown_path)

        _, characters_path = build_character_mindmaps(graph_path)
        artifacts["characters"] = str(characters_path)

        sequence_candidates = _sequence_candidates(graph, _chapters(graph))
        sequence_packet = {
            "work": graph_work_metadata(graph),
            "candidate_events": sequence_candidates,
        }
        sequence_prompt = _sequence_prompt(graph, graph_path, sequence_candidates)
        sequences_path = output_dir / "secvente-relevante.json"
        sequences_artifact = _find_reusable_artifact(
            sequences_path,
            sequence_packet,
            sequence_prompt,
            model=model,
            reasoning=reasoning,
        )
        if sequences_artifact is None:
            sequences_artifact, sequences_path = generate_relevant_sequences(
                graph, graph_path, output_dir, runner=runner, api_key=api_key,
                model=model, reasoning=reasoning, timeout=timeout,
                max_tokens=selection_max_tokens,
            )
        else:
            print("[Secvențe relevante] reutilizate local")
            reused_artifacts.append("relevant_sequences")
        artifacts["relevant_sequences"] = str(sequences_path)

        current_path = output_dir / "curent-literar.json"
        current_packet = build_literary_current_packet(graph, graph_path, model_essay)
        current_prompt = render_literary_current_prompt(current_packet)
        current_artifact = _find_reusable_artifact(
            current_path,
            current_packet,
            current_prompt,
            model=model,
            reasoning=reasoning,
        )
        if current_artifact is None:
            current_artifact, current_path = generate_literary_current(
                graph_path, model_essay_path=model_essay, config_path=config_path,
                model=model, reasoning=reasoning,
                timeout=timeout, max_tokens=6000, dry_run=False, enrich=False,
            )
        else:
            print("[Curent literar] reutilizat local")
            reused_artifacts.append("literary_current")
        artifacts["literary_current"] = str(current_path)

        composition_artifact, composition_path = generate_composition_schemas(
            graph_path, config_path=config_path, model_id=model,
            reasoning_effort=reasoning, timeout=timeout,
            max_tokens=DEFAULT_COMPOSITION_MAX_TOKENS,
            dry_run=False,
        )
        artifacts["composition"] = str(composition_path)
        cost_summary = combine_cost_summaries(
            [
                summarize_usages(summary_artifact.get("generation", {}).get("usage", [])),
                summarize_usages(
                    [sequences_artifact.get("generation", {}).get("usage", {})]
                ),
                summarize_usages(
                    [current_artifact.get("generation", {}).get("usage", {})]
                ),
                summarize_usages(
                    [
                        item.get("usage", {})
                        for item in composition_artifact.get("diagnostics", [])
                    ]
                ),
            ]
        )
    except Exception as error:
        manifest.update({"status": "failed", "artifacts": artifacts, "error": str(error)})
        write_json(pipeline_run_dir / "manifest.json", manifest)
        raise

    source_graph_sha256_after = _sha256(graph_path)
    manifest.update(
        {
            "status": "ready",
            "artifacts": artifacts,
            "cost_summary": cost_summary,
            "executed_qwen_calls": int(cost_summary.get("api_calls") or 0),
            "reused_summary_chapters": int(
                summary_artifact.get("generation", {}).get("reused_chapter_count") or 0
            ),
            "reused_artifacts": reused_artifacts,
            "source_graph_sha256_after": source_graph_sha256_after,
            "source_graph_modified": (
                source_graph_sha256_after != manifest["source_graph_sha256_before"]
            ),
        }
    )
    write_json(output_dir / "manifest.json", manifest)
    write_json(pipeline_run_dir / "manifest.json", manifest)
    return manifest, output_dir / "manifest.json"


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH)
    parser.add_argument(
        "--model-essay",
        type=Path,
        default=None,
        help="Opțional; implicit este citit din sources[source_type=model_essay].",
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--reasoning-effort", choices=REASONING_CHOICES, default=DEFAULT_REASONING)
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument(
        "--summary-max-tokens", type=int, default=DEFAULT_SUMMARY_MAX_TOKENS
    )
    parser.add_argument(
        "--selection-max-tokens", type=int, default=DEFAULT_SELECTION_MAX_TOKENS
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    graph_path = args.graph.resolve()
    if not graph_path.is_file():
        parser.error(f"Knowledge graph-ul nu există: {graph_path}")
    try:
        manifest, path = build_understanding_project(
            graph_path,
            model_essay_path=args.model_essay,
            config_path=args.config.resolve(),
            model=args.model,
            reasoning=args.reasoning_effort,
            timeout=args.timeout,
            summary_max_tokens=args.summary_max_tokens,
            selection_max_tokens=args.selection_max_tokens,
            dry_run=args.dry_run,
        )
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        parser.error(str(error))
    if args.dry_run:
        print(f"Plan pregătit fără apeluri API: {path}")
        print(f"Apeluri Qwen planificate: {manifest['qwen_calls']}")
        return 0
    print(f"Înțelege opera finalizat pentru {manifest['work']['title']}.")
    print(f"Apeluri Qwen: {manifest['qwen_calls']}; regenerări: 0.")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
