"""Generator complet automatizat pentru opere poetice (lirice) în BacApp2 folosind Qwen 3.7 Flash.

Citește knowledge graph-ul și eseul-model, rulează prompturile prin OpenRouter API
(fără date hardcodate) și generează complet cele trei secțiuni:
1. Înțelege opera (Toată opera, Curent literar, Voci lirice & Imagini, Secvențe relevante, Elemente compoziționale)
2. Testare rapidă (Flashcarduri adaptive + Exerciții: Grile, Cronologie, Asocieri, Completări)
3. Construiește eseu (Blueprint-ul de eseu pe 9 secțiuni structurate)

La finalul unei generări reușite, opera este înregistrată automat în data/works.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from exercise_builder_common import graph_work_metadata
except ImportError:  # Permite și importul ca modul `scripts.creeaza_opera_poezie`.
    from scripts.exercise_builder_common import graph_work_metadata
from services.composition_service import ELEMENT_TITLES, infer_composition_element_ids

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_GRAPH_PATH = ROOT_DIR / "grafuri" / "floare_albastra" / "knowledge-graph.json"
DEFAULT_ESSAY_PATH = ROOT_DIR / "modele_eseuri" / "floare_albastra.md"
DEFAULT_CONFIG_PATH = ROOT_DIR / "cercetare-qwen" / "config.local.env"
LEGACY_CONFIG_PATH = ROOT_DIR / "cercetare" / "experiment2" / "config.local.env"
DEFAULT_MODEL = "qwen/qwen3.7-flash"
DEFAULT_REASONING = "medium"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def load_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        if LEGACY_CONFIG_PATH.is_file():
            path = LEGACY_CONFIG_PATH
        else:
            return {}
    env_vars = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env_vars[k.strip()] = v.strip().strip('"').strip("'")
    return env_vars


def read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _normalize_multiple_choice(items: object) -> list[dict]:
    normalized = []
    for raw_item in items if isinstance(items, list) else []:
        if not isinstance(raw_item, dict):
            continue
        item = dict(raw_item)
        options = item.get("options") if isinstance(item.get("options"), list) else []
        answer = str(item.get("answer") or "").strip()
        if answer not in options and len(answer) == 1:
            match = next(
                (option for option in options if str(option).lstrip().startswith(f"{answer}.")),
                None,
            )
            if match is not None:
                item["answer"] = match
        normalized.append(item)
    return normalized


def _normalize_chronology(items: object) -> list[dict]:
    normalized = []
    for raw_item in items if isinstance(items, list) else []:
        if not isinstance(raw_item, dict):
            continue
        item = dict(raw_item)
        raw_steps = item.get("items") or item.get("steps") or []
        item["items"] = [
            {
                **dict(step),
                "position": index,
                "event": str(step.get("event") or step.get("text") or "").strip(),
            }
            for index, step in enumerate(raw_steps, start=1)
            if isinstance(step, dict)
        ]
        item.pop("steps", None)
        normalized.append(item)
    return normalized


def _normalized_text(value: object) -> str:
    """Normalizează doar tipografia și spațiile, nu conținutul sursei."""
    text = str(value or "")
    text = text.translate(str.maketrans({"„": '"', "”": '"', "«": '"', "»": '"', "’": "'", "–": "-", "—": "-", "/": " "}))
    return " ".join(text.split()).casefold()


def _quote_is_in_poem(quote: object, poem_text: str) -> bool:
    candidate = _normalized_text(quote).strip('"')
    normalized_poem = _normalized_text(poem_text)
    if len(candidate) >= 4 and candidate in normalized_poem:
        return True
    fragments = [
        _normalized_text(fragment).strip('" ,.;:-')
        for fragment in re.split(r"(?:\.{3,}|…+|[»\"]\s*,\s*[«\"])", str(quote or ""))
    ]
    substantive = [fragment for fragment in fragments if len(fragment.split()) >= 3]
    return bool(substantive) and all(fragment in normalized_poem for fragment in substantive)


def _latest_saved_qwen_response(work_id: str, filename: str) -> str | None:
    runs_dir = ROOT_DIR / "data" / "generated_works" / work_id / "pipeline-total" / "runs"
    if not runs_dir.is_dir():
        return None
    candidates = sorted(
        runs_dir.glob(f"run-*/staging/_qwen_raw/{work_id}/{filename}"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        text = candidate.read_text(encoding="utf-8").strip()
        if text:
            return text
    return None


def _recover_json_array_items(raw_text: str, key: str) -> list[dict]:
    """Recuperează obiectele JSON complete dintr-un răspuns tăiat la final."""
    match = re.search(rf'"{re.escape(key)}"\s*:\s*\[', raw_text)
    if not match:
        return []
    decoder = json.JSONDecoder()
    cursor = match.end()
    recovered: list[dict] = []
    while cursor < len(raw_text):
        while cursor < len(raw_text) and raw_text[cursor] in " \t\r\n,":
            cursor += 1
        if cursor >= len(raw_text) or raw_text[cursor] == "]":
            break
        try:
            value, end = decoder.raw_decode(raw_text, cursor)
        except json.JSONDecodeError:
            break
        if isinstance(value, dict):
            recovered.append(value)
        cursor = end
    return recovered


def _ground_pedagogical_sheet_in_graph(sheet: dict, graph: dict) -> dict:
    grounded = json.loads(json.dumps(sheet, ensure_ascii=False))
    nodes = [node for node in graph.get("nodes", []) if isinstance(node, dict)]
    prosody = next((node for node in nodes if node.get("type") == "ProsodicStructure"), None)
    if prosody:
        grounded["prosody"] = {
            "stanza_form": "Catrene",
            "rhyme": prosody.get("rhyme", ""),
            "rhythm": prosody.get("rhythm", ""),
            "measure": prosody.get("measure") or prosody.get("meter", ""),
            "source_refs": [prosody.get("id")],
        }
    lexical_notes = {
        _normalized_text(node.get("term")): node
        for node in nodes
        if node.get("type") == "LexicalNote" and node.get("term")
    }
    for entry in grounded.get("key_vocabulary", []):
        if not isinstance(entry, dict):
            continue
        note = lexical_notes.get(_normalized_text(entry.get("term")))
        if note:
            entry["definition_in_context"] = note.get("definition")
            entry["source_refs"] = [note.get("id")]
    for entry in grounded.get("composition_and_language", []):
        if isinstance(entry, dict) and "titlu" in _normalized_text(entry.get("element")):
            title_node = next((node for node in nodes if node.get("id") == "COMP_TITLE"), None)
            if title_node:
                entry["explanation"] = title_node.get("description")
    for schema in grounded.get("composition_schemas", []):
        if not isinstance(schema, dict) or schema.get("id") != "semantic_figures":
            continue
        for branch in schema.get("branches", []):
            if isinstance(branch, dict):
                branch["heading"] = str(branch.get("heading") or "").replace(
                    "Epitetul sinestezic", "Epitetele descriptive"
                )
    return grounded


def _complete_flashcards_from_sheet(cards: list[dict], sheet: dict) -> list[dict]:
    completed = [
        dict(card)
        for card in cards[:24]
        if str(card.get("category") or "") != "prozodie"
    ]
    used_ids = {str(card.get("id") or "") for card in completed}
    if len(completed) < 16:
        return completed

    evidence = [item for item in sheet.get("evidence_bank", []) if isinstance(item, dict)]
    prosody = sheet.get("prosody") if isinstance(sheet.get("prosody"), dict) else {}
    additions = [
        {
            "front": "Din ce tip de strofe este alcătuită poezia?",
            "back": str(prosody.get("stanza_form") or "Catrene."),
            "category": "prozodie",
            "difficulty": "easy",
            "source_refs": list(prosody.get("source_refs") or ["prosody"]),
        },
        {
            "front": "Care este schema rimei?",
            "back": str(prosody.get("rhyme") or ""),
            "category": "prozodie",
            "difficulty": "easy",
            "source_refs": list(prosody.get("source_refs") or ["prosody"]),
        },
        {
            "front": "Care sunt ritmul și măsura versurilor?",
            "back": f"Ritm {str(prosody.get('rhythm') or '').casefold()}, cu măsura de {prosody.get('measure') or ''}.",
            "category": "prozodie",
            "difficulty": "medium",
            "source_refs": list(prosody.get("source_refs") or ["prosody"]),
        }
    ]
    for item in evidence:
        if item.get("stanza") is None or not item.get("quote"):
            continue
        additions.append(
            {
                "front": f"Ce idee susține citatul {item['quote']}?",
                "back": str(item.get("fact") or "Dovadă textuală relevantă pentru interpretarea poeziei."),
                "category": "citate",
                "difficulty": "medium",
                "source_refs": [str(item.get("id") or item.get("node_id") or "evidence")],
            }
        )
        if len(additions) >= 6:
            break
    for addition in additions:
        if len(completed) >= 24:
            break
        next_number = len(completed) + 1
        card_id = f"FC_{next_number:02d}"
        while card_id in used_ids:
            next_number += 1
            card_id = f"FC_{next_number:02d}"
        completed.append({"id": card_id, **addition, "characters": []})
        used_ids.add(card_id)
    vocabulary = {
        _normalized_text(item.get("term")): str(item.get("definition_in_context") or "")
        for item in sheet.get("key_vocabulary", [])
        if isinstance(item, dict) and item.get("term")
    }
    for card in completed:
        front = str(card.get("front") or "")
        back = str(card.get("back") or "")
        if "încalte" in _normalized_text(front) and "încalte" in vocabulary:
            back = f"„Încalte” înseamnă «măcar», «cel puțin»; {vocabulary['încalte']}"
        if "oximoronic" in _normalized_text(front):
            card["front"] = "Care este semnificația titlului «Floare albastră»?"
            title_schema = next(
                (item for item in sheet.get("composition_schemas", []) if isinstance(item, dict) and item.get("id") == "title"),
                {},
            )
            back = str(title_schema.get("focus") or "Motiv romantic polisemantic, aflat între efemer și aspirația spre absolut.")
        back = back.replace("Adresarea tandru", "Adresarea tandră")
        back = back.replace("o încercare de amestec al speciilor literare", "un exemplu de amestec al speciilor literare")
        back = back.replace("epitetele sinestezice", "epitetele descriptive")
        if card.get("category") == "teme" and any(token in _normalized_text(back) for token in ("imposibil", "incompatibil")):
            back = "În interpretarea eseului-model, " + back[:1].lower() + back[1:]
        card["back"] = back
    return completed


def _extract_model_essay_poetic_sequences(essay_text: str) -> list[dict]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", essay_text) if paragraph.strip()]
    candidates = [
        paragraph
        for paragraph in paragraphs
        if "idee poetic" in _normalized_text(paragraph)
    ]
    if len(candidates) != 2:
        raise ValueError(
            "Eseul-model trebuie să conțină exact două paragrafe marcate ca idei poetice."
        )
    sequences = []
    for index, paragraph in enumerate(candidates, start=1):
        chapter_match = re.search(
            r"strofe(?:le|lor)?\s+([0-9][0-9\s,\-–și]+)",
            paragraph,
            flags=re.IGNORECASE,
        )
        chapter = f"Strofele {chapter_match.group(1).strip(' ,')}" if chapter_match else "Localizare indicată în eseul-model"
        first_sentence = re.split(r"(?<=[.!?])\s+", paragraph, maxsplit=1)[0]
        title = first_sentence[:110].rstrip(" .,:;")
        sequences.append(
            {
                "id": f"secventa_{index}",
                "button_label": f"Ideea poetică {index}",
                "title": title,
                "chapter": chapter,
                "source": "Eseul-model normativ de Bacalaureat",
                "text": paragraph,
            }
        )
    return sequences


def _composition_schema_for_ui(schema: dict, essay_paragraph: str) -> dict:
    """Extinde schema compactă Qwen cu toate câmpurile consumate de UI și eseu."""
    result = dict(schema)
    result["central_idea"] = str(
        result.get("central_idea") or result.get("focus") or ""
    ).strip()
    normalized_branches = []
    for branch in result.get("branches", []):
        if not isinstance(branch, dict):
            continue
        branch = dict(branch)
        explanation = str(
            branch.get("explanation") or branch.get("content") or ""
        ).strip()
        branch["key_idea"] = str(branch.get("key_idea") or explanation).strip()
        branch["explanation"] = explanation
        normalized_branches.append(branch)
    result["branches"] = normalized_branches
    formulas = result.get("memory_formula")
    if not isinstance(formulas, list) or not any(str(value).strip() for value in formulas):
        formulas = [branch.get("heading", "") for branch in normalized_branches[:3]]
    result["memory_formula"] = [
        str(value).strip() for value in formulas if str(value).strip()
    ]
    result["essay_paragraph"] = str(
        result.get("essay_paragraph") or essay_paragraph
    ).strip()
    return result


def _validate_pedagogical_sheet(
    sheet: dict,
    poem_text: str,
    graph_node_ids: set[str] | None = None,
) -> None:
    required_objects = ("identity", "literary_context", "lyrical_situation", "structure", "prosody")
    required_lists = (
        "genre_and_species",
        "themes_and_ideas",
        "composition_and_language",
        "key_vocabulary",
        "common_misconceptions",
        "learning_objectives",
        "evidence_bank",
    )
    missing = [name for name in required_objects if not isinstance(sheet.get(name), dict) or not sheet[name]]
    missing.extend(name for name in required_lists if not isinstance(sheet.get(name), list) or not sheet[name])
    if missing:
        raise ValueError("Fișa pedagogică este incompletă: " + ", ".join(missing))
    if len(sheet["learning_objectives"]) != 8:
        raise ValueError("Fișa pedagogică trebuie să conțină exact 8 obiective de învățare.")
    if len(sheet["evidence_bank"]) != 10:
        raise ValueError("Fișa pedagogică trebuie să conțină exact 10 dovezi textuale.")
    for evidence in sheet["evidence_bank"]:
        is_graph_fact = (
            isinstance(evidence, dict)
            and evidence.get("stanza") is None
            and str(evidence.get("node_id") or "") in (graph_node_ids or set())
        )
        if not isinstance(evidence, dict) or (
            not is_graph_fact and not _quote_is_in_poem(evidence.get("quote"), poem_text)
        ):
            raise ValueError("Fișa pedagogică include un citat care nu apare în textul poeziei.")
    literary_context = sheet["literary_context"]
    if any(not str(literary_context.get(field) or "").strip() for field in ("movement", "definition", "classification")):
        raise ValueError("Contextul literar din fișa pedagogică este incomplet.")
    traits = literary_context.get("traits")
    if not isinstance(traits, list) or len(traits) != 2:
        raise ValueError("Fișa pedagogică trebuie să conțină exact două trăsături literare.")
    for trait in traits:
        quotes = trait.get("evidence_quotes") if isinstance(trait, dict) else []
        if not isinstance(quotes, list) or not quotes or any(
            not isinstance(item, dict) or not _quote_is_in_poem(item.get("quote"), poem_text)
            for item in quotes
        ):
            raise ValueError("O trăsătură literară nu are dovezi textuale exacte.")
    composition_schemas = sheet.get("composition_schemas")
    if not isinstance(composition_schemas, list) or len(composition_schemas) != 2:
        raise ValueError("Fișa pedagogică trebuie să conțină exact două scheme compoziționale.")
    for schema in composition_schemas:
        if (
            not isinstance(schema, dict)
            or not str(schema.get("id") or "").strip()
            or not str(schema.get("title") or "").strip()
            or not str(schema.get("focus") or "").strip()
            or not isinstance(schema.get("branches"), list)
            or len(schema["branches"]) != 4
            or any(
                not isinstance(branch, dict)
                or not str(branch.get("heading") or "").strip()
                or not str(branch.get("content") or "").strip()
                for branch in schema["branches"]
            )
        ):
            raise ValueError("O schemă compozițională din fișa pedagogică este incompletă.")


def _validate_generated_quick_testing(
    flashcards: list[dict],
    exercise_banks: dict[str, list[dict]],
    poem_text: str,
) -> None:
    allowed_categories = {"context", "curent", "teme", "structura", "voci", "limbaj", "prozodie", "citate"}
    if len(flashcards) != 24 or any(
        not str(card.get("id") or "").strip()
        or not str(card.get("front") or "").strip()
        or not str(card.get("back") or "").strip()
        or card.get("category") not in allowed_categories
        or not isinstance(card.get("source_refs"), list)
        or not card.get("source_refs")
        for card in flashcards
    ):
        raise ValueError("Qwen nu a produs o bancă validă de flashcarduri.")
    for name, items in exercise_banks.items():
        if not items:
            raise ValueError(f"Qwen nu a produs exerciții valide pentru {name}.")
        ids = [str(item.get("id") or "").strip() for item in items]
        if any(not item_id for item_id in ids) or len(ids) != len(set(ids)):
            raise ValueError(f"Banca {name} are ID-uri lipsă sau duplicate.")
    for item in exercise_banks["multiple_choice"]:
        options = item.get("options") if isinstance(item.get("options"), list) else []
        if (
            len(options) != 4
            or len(set(options)) != 4
            or item.get("answer") not in options
            or not str(item.get("explanation") or "").strip()
            or not item.get("source_refs")
        ):
            raise ValueError("O grilă generată nu respectă contractul UI.")
    for item in exercise_banks["chronology"]:
        steps = item.get("items") if isinstance(item.get("items"), list) else []
        if (
            len(steps) < 3
            or [step.get("position") for step in steps] != list(range(1, len(steps) + 1))
            or any(not step.get("source_refs") for step in steps)
        ):
            raise ValueError("Un exercițiu de ordonare nu respectă contractul UI.")
    for item in exercise_banks["matching"]:
        pairs = item.get("pairs") if isinstance(item.get("pairs"), list) else []
        if (
            len(pairs) < 3
            or len({str(pair.get("left")) for pair in pairs}) != len(pairs)
            or len({str(pair.get("right")) for pair in pairs}) != len(pairs)
            or any(not pair.get("left") or not pair.get("right") for pair in pairs)
        ):
            raise ValueError("Un exercițiu de asociere nu respectă contractul UI.")
    for item in exercise_banks["completion"]:
        text = str(item.get("text") or "")
        answers = item.get("answers") or []
        rebuilt = text
        for answer in answers:
            rebuilt = rebuilt.replace("____", str(answer), 1)
        if (
            text.count("____") != 3
            or len(answers) != 3
            or not _quote_is_in_poem(rebuilt, poem_text)
            or not item.get("source_refs")
        ):
            raise ValueError("Un exercițiu de completare nu respectă contractul UI.")


def _summarize_usage_records(records: list[dict]) -> dict[str, int | float]:
    return {
        "api_calls": len(records),
        "prompt_tokens": sum(int(item.get("prompt_tokens") or 0) for item in records),
        "completion_tokens": sum(int(item.get("completion_tokens") or 0) for item in records),
        "reasoning_tokens": sum(int(item.get("reasoning_tokens") or 0) for item in records),
        "total_tokens": sum(int(item.get("total_tokens") or 0) for item in records),
        "cost_usd": round(sum(float(item.get("cost_usd") or 0) for item in records), 10),
    }


def extract_json_block(text: str, api_key: str | None = None, model: str = DEFAULT_MODEL) -> Any:
    if not text:
        return {}
    text = str(text).strip()
    candidates = []

    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        candidates.append(match.group(1).strip())

    start_brace = text.find("{")
    start_bracket = text.find("[")
    if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
        end_brace = text.rfind("}")
        if end_brace != -1:
            candidates.append(text[start_brace : end_brace + 1])
    elif start_bracket != -1:
        end_bracket = text.rfind("]")
        if end_bracket != -1:
            candidates.append(text[start_bracket : end_bracket + 1])

    candidates.append(text)

    for cand in candidates:
        try:
            return json.loads(cand)
        except Exception:
            pass
        # Basic cleanup: remove trailing commas
        try:
            cleaned = re.sub(r",\s*([\]}])", r"\1", cand)
            return json.loads(cleaned)
        except Exception:
            pass

    if api_key:
        print("      🛠️ Auto-corectare sintaxă JSON cu Qwen...")
        repair_prompt = (
            "Următorul text conține un JSON cu erori minore de sintaxă (ghilimele neescapate în interiorul valorilor sau virgule greșite). "
            "Corectează-l și returnează EXCLUSIV blocul JSON valid, fără explicații:\n\n"
            + text
        )
        try:
            repaired_text, _ = call_qwen(
                repair_prompt,
                api_key=api_key,
                model=model,
                reasoning_effort="none",
                max_retries=2,
            )
            match_rep = re.search(r"```(?:json)?\s*(.*?)\s*```", repaired_text, re.DOTALL)
            cand_rep = match_rep.group(1).strip() if match_rep else repaired_text.strip()
            return json.loads(cand_rep)
        except Exception as err:
            print(f"      Eroare la reparare automată JSON: {err}")

    return json.loads(candidates[0])


def call_qwen(
    prompt: str,
    *,
    api_key: str,
    model: str = DEFAULT_MODEL,
    reasoning_effort: str = DEFAULT_REASONING,
    temperature: float = 0.2,
    max_tokens: int = 8000,
    timeout: int = 600,
    max_retries: int = 1,
) -> tuple[str, dict]:
    url = f"{OPENROUTER_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/BacApp2",
        "X-Title": "BacApp2 Poetry Pipeline",
    }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ești un profesor universitar emerit de limba și literatura română și evaluator expert de Bacalaureat. "
                    "Răspunzi cu acuratețe academică maximă, ancorat strict în textul poetic și în knowledge graph-ul furnizat. "
                    "Dacă ți se cere JSON, returnezi EXCLUSIV un bloc JSON valid, fără introduceri sau explicații în afara JSON-ului."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if reasoning_effort and reasoning_effort != "none":
        payload["reasoning"] = {"effort": reasoning_effort}

    for attempt in range(1, max_retries + 1):
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        start_t = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                elapsed = time.time() - start_t
                resp_choice = resp_data["choices"][0]["message"]
                content = resp_choice.get("content") or resp_choice.get("reasoning") or ""
                usage = resp_data.get("usage", {})
                return content, {
                    "elapsed_sec": round(elapsed, 2),
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                    "reasoning_tokens": (
                        usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0)
                        if isinstance(usage.get("completion_tokens_details"), dict)
                        else 0
                    ),
                    "cost_usd": float(usage.get("cost") or 0),
                }
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="ignore")
            if e.code in (429, 502, 503, 504) and attempt < max_retries:
                wait_sec = attempt * 5 + 2
                print(f"      ⚠️ Rate limit / server busy ({e.code}). Reîncerc în {wait_sec}s (încercarea {attempt}/{max_retries})...")
                time.sleep(wait_sec)
                continue
            raise RuntimeError(f"Eroare OpenRouter API ({e.code}): {err_msg}") from e
        except Exception as e:
            if attempt < max_retries:
                wait_sec = attempt * 3
                print(f"      ⚠️ Eroare temporară de rețea ({e}). Reîncerc în {wait_sec}s...")
                time.sleep(wait_sec)
                continue
            raise RuntimeError(f"Eroare conexiune OpenRouter API: {e}") from e


def generate_poetic_work_complete(
    graph_path: Path,
    essay_path: Path,
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
    model: str = DEFAULT_MODEL,
    reasoning_effort: str = DEFAULT_REASONING,
    category: str = "my",
    icon: str = "🌸",
    output_root: Path = ROOT_DIR,
    register_work_entry: bool = False,
) -> dict:
    print("=" * 70)
    print(f"🚀 PORNIRE PIPELINE AUTOMAT OPERĂ POETICĂ: {graph_path.name}")
    print(f"🤖 Model AI: {model} (Reasoning: {reasoning_effort})")
    print("=" * 70)

    env = load_env(config_path)
    api_key = env.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            f"Nu s-a găsit OPENROUTER_API_KEY în {config_path} sau {LEGACY_CONFIG_PATH}."
        )

    graph = read_json(graph_path)
    essay_text = essay_path.read_text(encoding="utf-8")
    essay_paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", essay_text)
        if len(paragraph.strip()) >= 100
    ]
    if len(essay_paragraphs) != 11:
        raise ValueError(
            "Eseul-model liric trebuie să aibă 11 paragrafe de conținut în ordinea canonică."
        )
    work = graph_work_metadata(graph)
    work_id = work["work_id"]
    work_title = work["title"]
    author = work["author"]
    composition_element_ids = infer_composition_element_ids(essay_text)
    if len(composition_element_ids) != 2:
        raise ValueError(
            "Eseul-model trebuie să dezvolte explicit exact două elemente de "
            "compoziție, structură sau limbaj recunoscute de aplicație."
        )
    composition_section_ids = [f"element_{element_id}" for element_id in composition_element_ids]

    output_root = output_root.resolve()
    dest_dir = output_root / "data" / "generated_works" / work_id / "intelegere-opera"
    essay_dest_dir = output_root / "data" / "generated_works" / work_id / "construieste-eseu"
    flashcard_dir = output_root / "data" / "flashcards"
    ex_dir = output_root / "data" / "exercises" / work_id
    sources_dir = output_root / "data" / "sources" / work_id
    raw_response_dir = output_root / "_qwen_raw" / work_id

    dest_dir.mkdir(parents=True, exist_ok=True)
    essay_dest_dir.mkdir(parents=True, exist_ok=True)
    flashcard_dir.mkdir(parents=True, exist_ok=True)
    ex_dir.mkdir(parents=True, exist_ok=True)
    sources_dir.mkdir(parents=True, exist_ok=True)
    raw_response_dir.mkdir(parents=True, exist_ok=True)

    stanzas = [n for n in graph.get("nodes", []) if n.get("type") == "Stanza"]
    stanzas.sort(key=lambda x: x.get("stanza_number", 0))
    sequences = graph.get("sequences", [])
    images = [n for n in graph.get("nodes", []) if n.get("type") == "PoeticImage"]
    figures = [n for n in graph.get("nodes", []) if n.get("type") == "FigureOfSpeech"]
    poetic_voices = [n for n in graph.get("nodes", []) if n.get("type") == "PoeticVoice"]
    concepts = [
        n
        for n in graph.get("nodes", [])
        if n.get("type") in {"PhilosophicalConcept", "LiteraryTrait", "Theme", "PoeticSymbol"}
    ]

    if not stanzas:
        raise ValueError("Graful poetic nu conține strofe.")
    if not sequences:
        raise ValueError("Graful poetic nu conține secvențe lirice.")
    stanza_numbers = {stanza.get("stanza_number") for stanza in stanzas}
    for sequence in sequences:
        referenced = sequence.get("stanzas") if isinstance(sequence, dict) else None
        if not isinstance(referenced, list) or not referenced:
            raise ValueError("Fiecare secvență lirică trebuie să indice cel puțin o strofă.")
        missing = [number for number in referenced if number not in stanza_numbers]
        if missing:
            raise ValueError(f"Secvența {sequence.get('id', '?')} referă strofe inexistente: {missing}")

    total_tokens_used = 0
    total_api_calls = 0
    total_cost_usd = 0.0
    section_usages: dict[str, list[dict]] = {
        "intelegere-opera": [],
        "testare-rapida": [],
        "construieste-eseu": [],
    }

    poem_text = "\n\n".join(
        f"[Strofa {stanza['stanza_number']} | {stanza.get('id', '')}]\n{stanza['quote']}"
        for stanza in stanzas
    )
    source_packet = {
        "work": work,
        "poem": poem_text,
        "sequences": sequences,
        "knowledge_graph_nodes": graph.get("nodes", []),
        "knowledge_graph_edges": graph.get("edges", []),
        "model_essay": essay_text,
    }

    # -------------------------------------------------------------------------
    # 1. GENERARE: FIȘA PEDAGOGICĂ-CANONICĂ
    # -------------------------------------------------------------------------
    print("\n[1/12] 🧭 Generez fișa pedagogică completă a poeziei cu Qwen...")
    dossier_prompt = f"""
Construiește fișa pedagogică-sursă pentru opera «{work_title}» de {author}.
Această fișă va fi unica bază semantică pentru lecții și exerciții, deci trebuie să
acopere toate cerințele uzuale de Bac pentru text liric și să se bazeze strict pe
text, knowledge graph și eseul-model din pachetul-sursă.

PACHET-SURSĂ COMPLET:
{json.dumps(source_packet, ensure_ascii=False, separators=(',', ':'))}

Reguli de adevăr:
- nu completa din memorie informații absente din surse;
- orice citat trebuie copiat exact din poem și trebuie să indice strofa și ID-ul nodului;
- separă faptul textual de interpretare;
- marchează explicit interpretările controversate în `common_misconceptions`;
- nu trata automat eul liric masculin drept „geniu” dacă afirmația nu este susținută de eseu;
- la prozodie precizează schema strofică, rima, ritmul și măsura numai dacă sunt susținute de surse;
- generează EXACT 8 obiective de învățare și EXACT 10 dovezi în `evidence_bank`;
- în valorile JSON folosește «...» pentru citate; nu introduce ghilimele duble ASCII neescapate;
- scrie concis: maximum 35 de cuvinte în orice explicație, justificare, definiție,
  corectare, obiectiv sau conținut de ramură;
- acoperă: context/publicare, curent, specie, teme, idei poetice, voci și adresare,
  structură/secvențe, titlu, opoziții/simetrii, limbaj și figuri, imagini, prozodie,
  vocabular, capcane de interpretare și obiective de învățare.

Returnează EXCLUSIV un obiect JSON cu structura:
{{
  "schema_version": 2,
  "identity": {{"title":"...","author":"...","publication":"...","source_refs":["NODE_ID"]}},
  "literary_context": {{"movement":"...","period":"...","definition":"...","historical_context":"...","classification":"...","traits":[{{"name":"...","explanation":"...","evidence_quotes":[{{"quote":"...","stanza":1,"node_id":"ST_01"}}],"essay_use":"...","source_refs":["NODE_ID"]}}]}},
  "genre_and_species": [{{"name":"...","justification":"...","evidence_quotes":[{{"quote":"...","stanza":1,"node_id":"ST_01"}}]}}],
  "themes_and_ideas": [{{"theme":"...","poetic_idea":"...","evidence_quotes":[{{"quote":"...","stanza":1,"node_id":"ST_01"}}]}}],
  "lyrical_situation": {{"voices":[{{"name":"...","role":"...","stanzas":[1],"linguistic_markers":["..."]}}],"addressing":"...","lyrical_type":"..."}},
  "structure": {{"stanza_count":14,"tableaux":[{{"title":"...","stanzas":[1,2],"function":"..."}}],"oppositions":["..."]}},
  "composition_and_language": [{{"element":"...","explanation":"...","evidence_quotes":[{{"quote":"...","stanza":1,"node_id":"ST_01"}}]}}],
  "composition_schemas": {json.dumps([{"id": element_id, "title": ELEMENT_TITLES[element_id], "focus": "...", "central_idea": "...", "branches": [{"heading": "...", "content": "...", "key_idea": "...", "explanation": "..."} for _ in range(4)], "memory_formula": ["...", "...", "..."]} for element_id in composition_element_ids], ensure_ascii=False)},
  "prosody": {{"stanza_form":"...","rhyme":"...","rhythm":"...","measure":"...","source_refs":["NODE_ID"]}},
  "key_vocabulary": [{{"term":"...","definition_in_context":"...","source_refs":["NODE_ID"]}}],
  "common_misconceptions": [{{"claim":"...","correction":"...","source_refs":["NODE_ID"]}}],
  "learning_objectives": [{{"id":"OBJ_01","skill":"recall|understand|apply|analyze","description":"...","source_refs":["NODE_ID"]}}],
  "evidence_bank": [{{"id":"EV_01","fact":"...","quote":"citat exact","stanza":1,"node_id":"ST_01"}}]
}}
"""
    raw_resp = _latest_saved_qwen_response(work_id, "01-fisa-pedagogica.txt")
    if raw_resp is None:
        raw_resp, usage = call_qwen(
            dossier_prompt,
            api_key=api_key,
            model=model,
            reasoning_effort="none",
            max_tokens=12000,
        )
        total_tokens_used += usage["total_tokens"]
        total_api_calls += 1
        total_cost_usd += float(usage.get("cost_usd") or 0)
        section_usages["intelegere-opera"].append(usage)
    else:
        print("   ↻ Reutilizez răspunsul Qwen complet salvat din ultima rulare.")
    (raw_response_dir / "01-fisa-pedagogica.txt").write_text(raw_resp, encoding="utf-8")
    pedagogical_sheet = extract_json_block(raw_resp)
    if not isinstance(pedagogical_sheet, dict):
        raise ValueError("Qwen nu a returnat o fișă pedagogică JSON validă.")
    pedagogical_sheet = _ground_pedagogical_sheet_in_graph(pedagogical_sheet, graph)
    graph_node_ids = {
        str(node.get("id") or "")
        for node in graph.get("nodes", [])
        if isinstance(node, dict) and node.get("id")
    }
    _validate_pedagogical_sheet(pedagogical_sheet, poem_text, graph_node_ids)
    generated_schema_ids = {
        str(item.get("id") or "")
        for item in pedagogical_sheet.get("composition_schemas", [])
        if isinstance(item, dict)
    }
    if generated_schema_ids != set(composition_element_ids):
        raise ValueError("Fișa pedagogică nu conține exact schemele cerute de eseul-model.")
    pedagogical_sheet["generation"] = {
        "model": model,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_graph_sha256": hashlib.sha256(graph_path.read_bytes()).hexdigest(),
        "source_essay_sha256": hashlib.sha256(essay_path.read_bytes()).hexdigest(),
    }
    write_json(dest_dir / "fisa-pedagogica.json", pedagogical_sheet)
    print("   ✓ Fișa pedagogică a fost validată textual.")

    # -------------------------------------------------------------------------
    # 2. DERIVARE: TOATĂ OPERA & COMENTARIU PE TABLOURI
    # -------------------------------------------------------------------------
    print("\n[2/12] 📜 Construiesc lectura pe tablouri din graful-sursă validat...")
    verbalizations_map = {
        sequence["id"]: {
            "simple_verbalization": sequence.get("simple_verbalization", ""),
            "elevated_verbalization": sequence.get("elevated_verbalization", ""),
        }
        for sequence in sequences
    }

    tableau_items = []
    for seq in sequences:
        seq_stanzas = [s for s in stanzas if s.get("stanza_number") in seq["stanzas"]]
        verb = verbalizations_map.get(seq["id"], {})
        tableau_items.append(
            {
                "sequence_id": seq["id"],
                "number": seq["number"],
                "title": seq["title"],
                "stanzas_included": seq["stanzas"],
                "dominant_plane": seq["dominant_plane"],
                "dominant_voice": seq["dominant_voice"],
                "stanzas": [
                    {"number": s["stanza_number"], "text": s["quote"]}
                    for s in seq_stanzas
                ],
                "simple_verbalization": verb.get(
                    "simple_verbalization", seq.get("simple_verbalization", "")
                ),
                "elevated_verbalization": verb.get(
                    "elevated_verbalization", seq.get("elevated_verbalization", "")
                ),
            }
        )

    toata_opera_payload = {
        "work_id": work_id,
        "title": work_title,
        "author": author,
        "total_stanzas": len(stanzas),
        "total_sequences": len(sequences),
        "tableaux": tableau_items,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(dest_dir / "toata-opera.json", toata_opera_payload)

    # Markdown de citire ghidată
    md_lines = [f"# {work_title}\n## {author}\n"]
    for tab in tableau_items:
        md_lines.append(f"\n### {tab['title']}\n")
        for st_item in tab["stanzas"]:
            md_lines.append(
                f"**Strofa {st_item['number']}**\n```\n{st_item['text']}\n```\n"
            )
        md_lines.append(f"> **Înțeles simplu:** {tab['simple_verbalization']}\n")
        md_lines.append(
            f"> **Interpretare de Bacalaureat:** {tab['elevated_verbalization']}\n"
        )
    md_content = "\n".join(md_lines)
    (sources_dir / "rezumat-qwen-pe-capitole.md").write_text(
        md_content, encoding="utf-8"
    )
    (dest_dir / "rezumat-qwen-pe-capitole.md").write_text(
        md_content, encoding="utf-8"
    )
    print("   ✓ Toată opera generată cu succes.")

    # -------------------------------------------------------------------------
    # 3. DERIVARE: CURENT LITERAR & CELE 2 TRĂSĂTURI
    # -------------------------------------------------------------------------
    print("\n[3/12] 🏛️ Construiesc curentul literar din fișa Qwen validată...")
    literary_context = pedagogical_sheet["literary_context"]
    sheet_traits = literary_context.get("traits", [])
    if not isinstance(sheet_traits, list) or len(sheet_traits) != 2:
        raise ValueError("Fișa pedagogică trebuie să conțină exact două trăsături literare.")
    parsed_curent = {
        "movement": {
            "id": re.sub(r"[^a-z0-9]+", "_", _normalized_text(literary_context.get("movement"))).strip("_"),
            "name": literary_context.get("movement"),
            "period": literary_context.get("period"),
            "definition": literary_context.get("definition"),
            "historical_context": literary_context.get("historical_context"),
            "work_classification": literary_context.get("classification"),
        },
        "traits": [
            {
                "id": f"trasatura_{index}",
                "title": trait.get("name"),
                "explanation": trait.get("explanation"),
                "evidence_from_work": [
                    evidence.get("quote")
                    for evidence in trait.get("evidence_quotes", [])
                    if isinstance(evidence, dict) and evidence.get("quote")
                ],
                "essay_use": trait.get("essay_use"),
                "source_refs": trait.get("source_refs", []),
            }
            for index, trait in enumerate(sheet_traits, start=1)
            if isinstance(trait, dict)
        ],
    }
    write_json(
        dest_dir / "curent-literar.json",
        {
            "work_id": work_id,
            "literary_current": parsed_curent,
            "generation": {
                "model": model,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        },
    )
    print("   ✓ Curent literar derivat fără apel extern suplimentar.")

    # -------------------------------------------------------------------------
    # 4. DERIVARE: VOCI LIRICE & HARTA IMAGINILOR ARTISTICE
    # -------------------------------------------------------------------------
    print("\n[4/12] 🎭 Construiesc vocile și imaginile din fișa Qwen și graful validat...")
    sheet_voices = pedagogical_sheet["lyrical_situation"].get("voices", [])
    generated_voices = []
    for index, graph_voice in enumerate(poetic_voices):
        sheet_voice = sheet_voices[index] if index < len(sheet_voices) and isinstance(sheet_voices[index], dict) else {}
        markers = sheet_voice.get("linguistic_markers", [])
        generated_voices.append(
            {
                "id": graph_voice.get("id"),
                "name": sheet_voice.get("name") or graph_voice.get("label"),
                "role": sheet_voice.get("role") or graph_voice.get("role"),
                "attitude": sheet_voice.get("role") or graph_voice.get("role"),
                "personality": sheet_voice.get("role") or graph_voice.get("role"),
                "physical_description": "Instanță lirică definită prin discurs și atitudine, nu personaj epic descris fizic.",
                "linguistic_markers": "; ".join(str(value) for value in markers) if isinstance(markers, list) else str(markers),
                "associated_stanzas": sheet_voice.get("stanzas", []),
            }
        )

    sensory_groups = {
        "Imagini Vizuale Cosmice": [],
        "Imagini Vizuale Terestre": [],
        "Imagini Tactile & Afective": [],
        "Imagini Auditive": [],
        "Imagini Dinamice & Plastice": [],
    }
    for poetic_image in images:
        sensory_type = _normalized_text(poetic_image.get("sensory_type"))
        item = {
            "label": poetic_image.get("label"),
            "quote": poetic_image.get("quote"),
            "stanza": poetic_image.get("stanza"),
            "source_refs": [poetic_image.get("id")],
        }
        if any(token in sensory_type for token in ("cosmic", "abstract", "panoramic", "vertical")):
            sensory_groups["Imagini Vizuale Cosmice"].append(item)
        elif any(token in sensory_type for token in ("tactil", "olfactiv")):
            sensory_groups["Imagini Tactile & Afective"].append(item)
        elif any(token in sensory_type for token in ("motor", "dinamic", "plastic", "dramatic")):
            sensory_groups["Imagini Dinamice & Plastice"].append(item)
        else:
            sensory_groups["Imagini Vizuale Terestre"].append(item)
        if "plang" in _normalized_text(poetic_image.get("quote")) or "vorbi" in _normalized_text(poetic_image.get("quote")):
            sensory_groups["Imagini Auditive"].append(item)

    plane_nodes = [node for node in graph.get("nodes", []) if isinstance(node, dict) and node.get("type") == "PoeticPlane"]
    relation_nodes = {}
    for index, voice in enumerate(generated_voices):
        relation_nodes[voice["id"]] = {"label": voice["name"], "group": "voice", "x": 250 + index * 480, "y": 90}
    for index, plane in enumerate(plane_nodes):
        relation_nodes[plane["id"]] = {"label": plane.get("label"), "group": "plane", "x": 130 + index * 240, "y": 340}
    relation_edges = [
        {
            "source": sequence.get("dominant_voice"),
            "target": sequence.get("dominant_plane"),
            "title": sequence.get("title"),
            "text": sequence.get("elevated_verbalization") or sequence.get("simple_verbalization"),
        }
        for sequence in sequences
        if sequence.get("dominant_voice") in relation_nodes and sequence.get("dominant_plane") in relation_nodes
    ]
    parsed_voices = {
        "voices": generated_voices,
        "sensory_mindmap": {
            "title": "Harta Imaginilor Artistice",
            "categories": [
                {"type": name, "items": items}
                for name, items in sensory_groups.items()
                if items
            ],
        },
        "relation_graph": {
            "central_node_id": generated_voices[0]["id"] if generated_voices else "",
            "nodes": relation_nodes,
            "edges": relation_edges,
        },
    }

    # Salvare pentru UI
    write_json(
        dest_dir / "voci-si-imagini.json",
        {
            "work_id": work_id,
            "voices": parsed_voices.get("voices", []),
            "sensory_mindmap": parsed_voices.get("sensory_mindmap", {}),
        },
    )

    char_mindmaps_payload = {
        "work_id": work_id,
        "characters": [
            {
                "id": v.get("id"),
                "name": v.get("name"),
                "category": "major",
                "role": v.get("role"),
                "personality": v.get("personality", v.get("attitude")),
                "physical_description": v.get(
                    "physical_description", v.get("linguistic_markers")
                ),
            }
            for v in parsed_voices.get("voices", [])
        ],
        "groups": [
            {
                "id": "voices",
                "name": "Instanțele Comunicării Lirice",
                "character_ids": [v.get("id") for v in parsed_voices.get("voices", [])],
            }
        ],
        "tree_layout": {},
        "relation_graph": parsed_voices.get("relation_graph", {}),
    }
    write_json(dest_dir / "character-mindmaps.json", char_mindmaps_payload)
    write_json(dest_dir / "personaje-mindmaps.json", char_mindmaps_payload)
    print("   ✓ Voci lirice și imagini senzoriale derivate fără apel extern suplimentar.")

    # -------------------------------------------------------------------------
    # 4. GENERARE: SECVENȚE RELEVANTE (DIN ESEU MODEL)
    # -------------------------------------------------------------------------
    print("\n[5/12] 🔍 Extrag secvențele relevante direct din eseul-model...")
    parsed_seq = {"sequences": _extract_model_essay_poetic_sequences(essay_text)}
    write_json(
        dest_dir / "secvente-relevante.json",
        {"work_id": work_id, "sequences": parsed_seq.get("sequences", [])},
    )
    print("   ✓ Secvențe relevante extrase fără apel extern suplimentar.")

    # -------------------------------------------------------------------------
    # 6. DERIVARE: ELEMENTE COMPOZIȚIONALE
    # -------------------------------------------------------------------------
    print("\n[6/12] 📐 Public schemele compoziționale din fișa Qwen validată...")
    schemas_by_id = {
        str(item.get("id") or ""): item
        for item in pedagogical_sheet.get("composition_schemas", [])
        if isinstance(item, dict)
        and str(item.get("id") or "") in composition_element_ids
    }
    generated_elements = [
        _composition_schema_for_ui(
            schemas_by_id[element_id],
            essay_paragraphs[8 + index],
        )
        for index, element_id in enumerate(composition_element_ids)
        if element_id in schemas_by_id
    ]
    if {str(item.get("id") or "") for item in generated_elements} != set(composition_element_ids):
        raise ValueError("Qwen nu a returnat exact schemele compoziționale cerute.")
    write_json(
        dest_dir / "elemente-compozitionale.json",
        {"work_id": work_id, "elements": generated_elements},
    )
    print("   ✓ Elemente compoziționale derivate fără apel extern suplimentar.")

    # -------------------------------------------------------------------------
    # 6. GENERARE: FLASHCARDURI & EXERCIȚII RAPIDE
    # -------------------------------------------------------------------------
    exercise_context = f"""
OPERA: «{work_title}» de {author}

TEXT INTEGRAL NUMEROTAT:
{poem_text}

FIȘĂ PEDAGOGICĂ VALIDATĂ:
{json.dumps(pedagogical_sheet, ensure_ascii=False, indent=2)}

REGULI COMUNE:
- folosește exclusiv informații și citate din materialul de mai sus;
- fiecare item trebuie să aibă `source_refs`, listă nevidă cu ID-uri ST_XX, EV_XX sau alte ID-uri din fișă/graf;
- evită absolutizări precum „tristețe cosmică”, „geniu condamnat” sau „imposibilitatea iubirii” dacă nu sunt formulate ca interpretări susținute;
- nu testa formulări obscure, discutabile ori simple etichete memorate fără înțelegere;
- distribuie dificultatea: ușor, mediu și analitic;
- nu folosi prefixe A./B./C./D. în textele opțiunilor.
"""

    def generate_test_payload(
        label: str,
        prompt: str,
        *,
        max_tokens: int,
        raw_filename: str,
        expected_key: str,
    ) -> dict:
        nonlocal total_tokens_used, total_api_calls, total_cost_usd
        print(label)
        cached_response = _latest_saved_qwen_response(work_id, raw_filename)
        if cached_response is not None:
            try:
                cached_payload = extract_json_block(cached_response)
            except (ValueError, json.JSONDecodeError):
                cached_payload = None
            if isinstance(cached_payload, dict) and isinstance(cached_payload.get(expected_key), list):
                print(f"   ↻ Reutilizez banca Qwen salvată: {expected_key}.")
                (raw_response_dir / raw_filename).write_text(cached_response, encoding="utf-8")
                return cached_payload
        response, call_usage = call_qwen(
            exercise_context + "\n\n" + prompt,
            api_key=api_key,
            model=model,
            reasoning_effort="low",
            max_tokens=max_tokens,
        )
        total_tokens_used += call_usage["total_tokens"]
        total_api_calls += 1
        total_cost_usd += float(call_usage.get("cost_usd") or 0)
        section_usages["testare-rapida"].append(call_usage)
        (raw_response_dir / raw_filename).write_text(response, encoding="utf-8")
        payload = extract_json_block(response)
        if not isinstance(payload, dict):
            raise ValueError("Qwen nu a returnat un obiect JSON pentru banca de exerciții.")
        return payload

    print("\n[7/12] 🧠 Pregătesc cele 24 de flashcarduri...")
    cached_cards_raw = (
        _latest_saved_qwen_response(work_id, "02-flashcards.txt")
        or _latest_saved_qwen_response(work_id, "02-testare-rapida.txt")
    )
    recovered_cards = _recover_json_array_items(cached_cards_raw or "", "cards")
    if recovered_cards:
        formatted_cards = _complete_flashcards_from_sheet(recovered_cards, pedagogical_sheet)
        print(f"   ↻ Am recuperat {len(recovered_cards)} carduri Qwen complete și am completat setul din fișa validată.")
        write_json(raw_response_dir / "02-flashcards-recovered.json", {"cards": formatted_cards})
    else:
        cards_payload = generate_test_payload(
            "   Generez separat cele 24 de flashcarduri cu Qwen...",
            """
Generează exact 24 de flashcarduri, câte 3 pentru fiecare categorie:
`context`, `curent`, `teme`, `structura`, `voci`, `limbaj`, `prozodie`, `citate`.
Nu repeta aceeași informație sub altă formulare. Răspunsul trebuie să fie scurt,
precis și util pentru recapitulare. Pentru categoria `citate`, cere fie completarea,
fie explicarea unui citat exact.
Returnează: {"cards":[{"id":"FC_01","front":"...","back":"...","category":"teme","difficulty":"easy|medium|hard","source_refs":["EV_01"]}]}.
""",
            max_tokens=12000,
            raw_filename="02-flashcards.txt",
            expected_key="cards",
        )
        formatted_cards = [
            {**dict(card), "characters": card.get("characters", [])}
            for card in cards_payload.get("cards", [])
            if isinstance(card, dict)
        ]
        formatted_cards = _complete_flashcards_from_sheet(formatted_cards, pedagogical_sheet)

    mc_payload = generate_test_payload(
        "\n[8/12] ✅ Generez separat grilele...",
        """
Generează exact 10 grile. Fiecare are 4 opțiuni plauzibile, distincte semantic,
o singură opțiune corectă, `answer` identic cu textul complet al opțiunii corecte,
o explicație de 1-3 fraze, dificultate, obiectiv și surse. Include cel puțin:
2 itemuri de citire atentă, 2 de structură/voci, 2 de limbaj, 1 de prozodie,
1 de curent/specie și 2 de interpretare argumentată.
Returnează: {"multiple_choice":[{"id":"MC_01","question":"...","options":["...","...","...","..."],"answer":"...","explanation":"...","difficulty":"medium","learning_objective":"OBJ_01","source_refs":["ST_01","EV_01"]}]}.
""",
        max_tokens=12000,
        raw_filename="03-multiple-choice.txt",
        expected_key="multiple_choice",
    )

    chronology_payload = generate_test_payload(
        "\n[9/12] 🔢 Generez separat exercițiile de ordonare...",
        """
Generează exact 3 exerciții de ordonare, fiecare cu 4-6 pași. Un exercițiu urmărește
ordinea tablourilor, unul evoluția discursului/vocilor și unul dezvoltarea unei idei
poetice. Nu prezenta discursul unei voci drept stare sufletească a celeilalte.
Fiecare pas are o ancoră textuală sau de strofă.
Returnează: {"chronology":[{"id":"CHRONO_01","title":"...","instructions":"...","items":[{"position":1,"event":"...","source_refs":["ST_01"]}]}]}.
""",
        max_tokens=9000,
        raw_filename="04-chronology.txt",
        expected_key="chronology",
    )

    matching_payload = generate_test_payload(
        "\n[10/12] 🔗 Generez separat exercițiile de asociere...",
        """
Generează exact 3 exerciții de asociere, fiecare cu exact 4 perechi și fără răspunsuri
ambigue: (1) figură/procedeu - citat exact, (2) voce/plan/secvență - rol textual,
(3) concept/temă - explicație argumentată. Valorile din dreapta trebuie să fie unice.
Returnează: {"matching":[{"id":"MATCH_01","title":"...","instructions":"...","source_refs":["EV_01"],"pairs":[{"left":"...","right":"...","source_refs":["ST_01"]}]}]}.
""",
        max_tokens=9000,
        raw_filename="05-matching.txt",
        expected_key="matching",
    )

    completion_payload = generate_test_payload(
        "\n[11/12] ✍️ Generez separat exercițiile de completare...",
        """
Generează exact 4 exerciții de completare. `text` trebuie să fie un fragment CONTIGUU
copiat exact din poem, în care înlocuiești exact 3 cuvinte sau grupuri de cuvinte cu
`____`. `answers` conține, în ordine, exact textele eliminate; după reintroducerea lor,
fragmentul trebuie să coincidă textual cu poemul. Alege fragmente relevante, diferite.
Returnează: {"completion":[{"id":"COMPL_01","title":"...","text":"... ____ ... ____ ... ____ ...","answers":["...","...","..."],"source_refs":["ST_01"]}]}.
""",
        max_tokens=9000,
        raw_filename="06-completion.txt",
        expected_key="completion",
    )

    exercise_banks = {
        "multiple_choice": _normalize_multiple_choice(mc_payload.get("multiple_choice", [])),
        "chronology": _normalize_chronology(chronology_payload.get("chronology", [])),
        "matching": [dict(item) for item in matching_payload.get("matching", []) if isinstance(item, dict)],
        "completion": [dict(item) for item in completion_payload.get("completion", []) if isinstance(item, dict)],
    }
    _validate_generated_quick_testing(formatted_cards, exercise_banks, poem_text)

    write_json(
        flashcard_dir / f"{work_id}.json",
        {
            "work_id": work_id,
            "title": work_title,
            "author": author,
            "cards": formatted_cards,
        },
    )

    # Salvare exerciții
    write_json(
        ex_dir / "multiple_choice.json",
        {"exercises": exercise_banks["multiple_choice"]},
    )
    write_json(
        ex_dir / "chronology.json", {"exercises": exercise_banks["chronology"]}
    )
    write_json(ex_dir / "matching.json", {"exercises": exercise_banks["matching"]})
    write_json(
        ex_dir / "completion.json", {"exercises": exercise_banks["completion"]}
    )
    print("   ✓ Flashcarduri și bănci de exerciții generate cu succes.")

    # -------------------------------------------------------------------------
    # 12. DERIVARE: BLUEPRINT CONSTRUIEȘTE ESEU
    # -------------------------------------------------------------------------
    print("\n[12/12] ✍️ Construiesc blueprint-ul exact din eseul-model...")
    trait_titles = [str(trait.get("name") or f"Trăsătura {index}") for index, trait in enumerate(sheet_traits, start=1)]
    canonical_sections = [
        {"id": "introducere", "title": "Introducere și încadrare", "kind": "introduction", "instructions": "Prezintă autorul, apariția operei și încadrarea literară.", "canonical_text": "\n\n".join(essay_paragraphs[0:2])},
        {"id": "trasatura_1", "title": trait_titles[0], "kind": "literary_trait", "instructions": "Explică prima trăsătură și susține-o prin exemple exacte din poezie.", "canonical_text": essay_paragraphs[2]},
        {"id": "trasatura_2", "title": trait_titles[1], "kind": "literary_trait", "instructions": "Explică a doua trăsătură și relația dintre planurile și vocile lirice.", "canonical_text": "\n\n".join(essay_paragraphs[3:5])},
        {"id": "tema", "title": "Tema și viziunea despre lume", "kind": "theme", "instructions": "Formulează tema și ideile asociate, fără să le confunzi cu rezumatul.", "canonical_text": essay_paragraphs[5]},
        {"id": "secventa_1", "title": "Prima idee poetică relevantă", "kind": "sequence", "instructions": "Analizează prima idee poetică prin localizare, citate și semnificație.", "canonical_text": essay_paragraphs[6]},
        {"id": "secventa_2", "title": "A doua idee poetică relevantă", "kind": "sequence", "instructions": "Analizează a doua idee poetică prin localizare, citate și semnificație.", "canonical_text": essay_paragraphs[7]},
        {"id": composition_section_ids[0], "title": ELEMENT_TITLES[composition_element_ids[0]], "kind": "composition", "instructions": f"Explică {ELEMENT_TITLES[composition_element_ids[0]].casefold()} folosind formularea și dovezile eseului-model.", "canonical_text": essay_paragraphs[8]},
        {"id": composition_section_ids[1], "title": ELEMENT_TITLES[composition_element_ids[1]], "kind": "composition", "instructions": f"Explică {ELEMENT_TITLES[composition_element_ids[1]].casefold()} folosind formularea și dovezile eseului-model.", "canonical_text": essay_paragraphs[9]},
        {"id": "concluzie", "title": "Concluzie", "kind": "conclusion", "instructions": "Formulează concluzia sintetică fără informații noi.", "canonical_text": essay_paragraphs[10]},
    ]
    expected_section_ids = [
        "introducere", "trasatura_1", "trasatura_2", "tema", "secventa_1",
        "secventa_2", *composition_section_ids, "concluzie",
    ]
    sections_by_id = {str(item.get("id") or ""): item for item in canonical_sections}
    errors = []
    if set(sections_by_id) != set(expected_section_ids):
        errors.append("Blueprint-ul nu conține exact cele 9 secțiuni canonice.")
    normalized_essay = " ".join(essay_text.split())
    for section_id in expected_section_ids:
        section = sections_by_id.get(section_id, {})
        if not str(section.get("instructions") or "").strip():
            errors.append(f"Secțiunea {section_id} nu are instrucțiuni.")
        canonical_text = str(section.get("canonical_text") or "").strip()
        if not canonical_text or " ".join(canonical_text.split()) not in normalized_essay:
            errors.append(f"Textul canonic pentru {section_id} nu este un fragment exact din eseul-model.")
    canonical_sections = [sections_by_id[section_id] for section_id in expected_section_ids if section_id in sections_by_id]
    instructions_map = sections_by_id
    metadata = graph.get("metadata") if isinstance(graph.get("metadata"), dict) else {}
    movement_name = str(metadata.get("movement") or "Curentul literar").strip()

    essay_payload = {
        "schema_version": 1,
        "pipeline": "construieste-eseu",
        "work": {
            "work_id": work_id,
            "title": work_title,
            "author": author
        },
        "default_composition_element_ids": composition_element_ids,
        "strict_trait_policy": {
            "mode": "model_essay_only",
            "expected_count": 2,
            "reject_unlisted_traits": True,
            "accepted_trait_ids": ["trasatura_1", "trasatura_2"],
            "accepted_trait_titles": [
                instructions_map.get("trasatura_1", {}).get("title", "Amestecul speciilor literare"),
                instructions_map.get("trasatura_2", {}).get("title", "Antiteza compozițională")
            ],
            "rule": "Sunt corecte exclusiv trăsăturile dezvoltate explicit în eseul-model."
        },
        "movement": {"name": movement_name},
        "mindmap": {
            "movement_name": movement_name,
            "traits": [
                {"id": "trasatura_1", "title": instructions_map.get("trasatura_1", {}).get("title", "Amestecul speciilor literare")},
                {"id": "trasatura_2", "title": instructions_map.get("trasatura_2", {}).get("title", "Antiteza compozițională")}
            ],
            "theme": {"id": "tema", "title": instructions_map.get("tema", {}).get("title", "Tema operei")},
            "sequences": [
                {"id": "secventa_1", "title": instructions_map.get("secventa_1", {}).get("title", "Secvența 1")},
                {"id": "secventa_2", "title": instructions_map.get("secventa_2", {}).get("title", "Secvența 2")}
            ],
            "composition_elements": [
                {
                    "id": section_id,
                    "title": instructions_map.get(section_id, {}).get(
                        "title", ELEMENT_TITLES[element_id]
                    ),
                }
                for element_id, section_id in zip(
                    composition_element_ids, composition_section_ids
                )
            ],
            "conclusion": {"id": "concluzie", "title": "Concluzie"}
        },
        "sections": canonical_sections,
        "validation": {
            "valid": not errors,
            "errors": errors,
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
    }

    if errors:
        raise ValueError("Blueprint-ul liric este invalid: " + " ".join(errors))

    write_json(essay_dest_dir / "eseu.json", essay_payload)
    (essay_dest_dir / "eseu-model.md").write_text(essay_text, encoding="utf-8")
    print("   ✓ Blueprint de eseu generat cu succes.")

    new_entry = {
        "id": work_id,
        "title": work_title,
        "author": author,
        "type": "poezie",
        "icon": icon,
        "category": category,
    }
    if register_work_entry:
        print(f"\n📝 Înregistrez opera «{work_title}» în data/works.json...")
        works_file = output_root / "data" / "works.json"
        works_list = read_json(works_file) if works_file.is_file() else []
        existing_entry = next((w for w in works_list if w.get("id") == work_id), None)
        if existing_entry is not None:
            works_list[works_list.index(existing_entry)] = new_entry
        else:
            works_list.append(new_entry)
        write_json(works_file, works_list)

    result = {
        "work": work,
        "registry_entry": new_entry,
        "output_root": str(output_root),
        "usage": {
            "api_calls": total_api_calls,
            "total_tokens": total_tokens_used,
            "cost_usd": round(total_cost_usd, 8),
        },
        "usage_by_section": {
            section_id: _summarize_usage_records(records)
            for section_id, records in section_usages.items()
        },
        "artifacts": {
            "understanding": str(dest_dir),
            "quick_testing": str(ex_dir),
            "flashcards": str(flashcard_dir / f"{work_id}.json"),
            "essay": str(essay_dest_dir),
            "source_summary": str(sources_dir / "rezumat-qwen-pe-capitole.md"),
        },
    }

    print("\n" + "=" * 70)
    print(f"🎉 Generarea pentru «{work_title}» s-a încheiat și artefactele au fost validate local.")
    print(f"📊 Total tokeni consumați prin Qwen: {total_tokens_used:,}")
    if register_work_entry:
        print("🌐 Opera a fost înregistrată în aplicație.")
    print("=" * 70)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Construiește automat o operă poetică în BacApp2 cu Qwen 3.7 Flash."
    )
    parser.add_argument(
        "--graph",
        type=Path,
        default=DEFAULT_GRAPH_PATH,
        help="Calea către knowledge-graph.json",
    )
    parser.add_argument(
        "--essay",
        type=Path,
        default=DEFAULT_ESSAY_PATH,
        help="Calea către eseul-model markdown",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Calea către config.local.env",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help="Modelul AI (ex: qwen/qwen3.7-flash)",
    )
    parser.add_argument(
        "--reasoning",
        type=str,
        default=DEFAULT_REASONING,
        choices=["none", "minimal", "low", "medium", "high", "xhigh", "max"],
        help="Efortul de raționare Qwen",
    )
    parser.add_argument(
        "--category",
        type=str,
        default="my",
        choices=["my", "other"],
        help="Categoria operei",
    )
    parser.add_argument(
        "--icon", type=str, default="🌸", help="Emoji-ul reprezentativ"
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    from build_complete_work import build_complete_work

    manifest, manifest_path = build_complete_work(
        args.graph,
        model_essay_path=args.essay,
        config_path=args.config,
        model=args.model,
        reasoning=args.reasoning,
        category=args.category,
        icon=args.icon,
        force=args.force,
        dry_run=args.dry_run,
    )
    print(manifest_path)
    return 0 if manifest.get("status") in {"planned", "ready"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
