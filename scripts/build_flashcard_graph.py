"""Build the pre-generated flashcard deck without runtime AI calls.

The normal mode uses two Gemini requests: one classifies every card and one
creates the sparse weighted graph. ``--combined-recovery`` can rebuild both in
one compact request when the API quota is especially constrained.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai


CATEGORIES = [
    "fir_narativ",
    "personaje",
    "relatii",
    "conflict",
    "tema",
    "secvente",
    "compozitie",
    "tehnica_narativa",
    "simboluri",
    "limbaj",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("tmp/flashcards_ion_100_for_review.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/flashcards/ion.json"),
    )
    parser.add_argument("--work-id", default="ion")
    parser.add_argument(
        "--combined-recovery",
        action="store_true",
        help="Use one compact request for metadata and graph after a quota-sensitive failure.",
    )
    return parser.parse_args()


def read_base_cards(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_cards = [
        *payload.get("summary_flashcards", []),
        *payload.get("full_text_flashcards", []),
    ]
    cards = []
    for raw_card in raw_cards:
        card = {
            "id": str(raw_card.get("id", "")).strip(),
            "front": str(raw_card.get("front", "")).strip(),
            "back": str(raw_card.get("back", "")).strip(),
            "source": str(raw_card.get("source", "")).strip(),
        }
        if not all(card.values()):
            raise ValueError(f"Card incomplet în fișierul sursă: {card!r}")
        cards.append(card)

    ids = [card["id"] for card in cards]
    if len(cards) != 100 or len(set(ids)) != 100:
        raise ValueError("Fișierul sursă trebuie să conțină exact 100 de carduri unice.")
    return cards


def metadata_schema() -> dict[str, Any]:
    return {
        "type": "OBJECT",
        "properties": {
            "cards": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "id": {"type": "STRING"},
                        "category": {"type": "STRING"},
                        "characters": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"},
                        },
                        "concepts": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"},
                        },
                        "difficulty": {"type": "INTEGER"},
                    },
                    "required": ["id", "category", "characters", "concepts", "difficulty"],
                },
            }
        },
        "required": ["cards"],
    }


def graph_schema() -> dict[str, Any]:
    return {
        "type": "OBJECT",
        "properties": {
            "edges": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "source": {"type": "STRING"},
                        "target": {"type": "STRING"},
                        "weight": {"type": "NUMBER"},
                        "relation": {"type": "STRING"},
                    },
                    "required": ["source", "target", "weight", "relation"],
                },
            }
        },
        "required": ["edges"],
    }


def generate_metadata(client: genai.Client, model: str, cards: list[dict]) -> list[dict]:
    compact_cards = [
        {"id": card["id"], "front": card["front"], "back": card["back"]}
        for card in cards
    ]
    prompt = f"""
Clasifică EXACT cele 100 de flashcarduri despre romanul „Ion”. Pentru fiecare întoarce
doar ID-ul și metadatele cerute. Ignoră orice clasificare anterioară: aceasta este
clasificarea canonică folosită de aplicație.

Reguli:
- category trebuie aleasă din: {", ".join(CATEGORIES)};
- characters conține numai personaje numite explicit sau indispensabile răspunsului;
- ordonează personajele după importanță, personajul principal fiind primul;
- concepts conține 2-6 concepte scurte, normalizate și consecvente între carduri;
- difficulty: 1 = reproducere directă, 2 = explicație/legătură, 3 = analiză complexă;
- nu omite și nu duplica niciun ID;
- nu repeta întrebarea sau răspunsul în rezultat.

FLASHCARDURI:
{json.dumps(compact_cards, ensure_ascii=False)}
""".strip()
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": metadata_schema(),
            "temperature": 0.1,
            "max_output_tokens": 24_000,
        },
    )
    payload = json.loads(response.text or "")
    metadata = payload.get("cards", [])
    expected_ids = {card["id"] for card in cards}
    actual_ids = [str(item.get("id", "")) for item in metadata]
    if len(metadata) != 100 or set(actual_ids) != expected_ids or len(set(actual_ids)) != 100:
        raise ValueError("Gemini nu a întors metadate pentru exact cele 100 de ID-uri.")
    return metadata


def generate_graph(client: genai.Client, model: str, cards: list[dict]) -> list[dict]:
    graph_input = [
        {
            "id": card["id"],
            "front": card["front"],
            "category": card["category"],
            "characters": card["characters"],
            "concepts": card["concepts"],
            "difficulty": card["difficulty"],
        }
        for card in cards
    ]
    prompt = f"""
Construiește un graf semantic ponderat, neorientat și rar pentru aceste 100 de
flashcarduri despre romanul „Ion”. Fiecare nod este identificat prin ID.

Reguli obligatorii:
- fiecare nod trebuie să aibă între 3 și 5 vecini relevanți;
- scrie fiecare muchie o singură dată;
- nu crea auto-legături și nu inventa ID-uri;
- nu lega două carduri numai fiindcă menționează același personaj;
- prioritizează obiectivul de învățare, conceptele, cauza-efectul, contrastul și aprofundarea;
- weight 0.90-1.00 = aprofundare directă;
- weight 0.75-0.89 = legătură semantică puternică;
- weight 0.60-0.74 = legătură utilă, dar mai generală;
- sub 0.60 nu crea muchia;
- relation trebuie să fie una dintre: acelasi_concept, aceeasi_secventa,
  cauza_efect, contrast, prerechizita, aprofundare;
- graful trebuie să lege util cardurile din rezumat de cele din textul integral;
- răspunde compact, fără explicații în afara JSON-ului.

CARDURI CLASIFICATE:
{json.dumps(graph_input, ensure_ascii=False)}
""".strip()
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": graph_schema(),
            "temperature": 0.1,
            "max_output_tokens": 24_000,
        },
    )
    return json.loads(response.text or "").get("edges", [])


def generate_combined_bundle(
    client: genai.Client,
    model: str,
    cards: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Generate metadata and a sparse graph in one compact, tolerant response."""
    compact_cards = [
        {"id": card["id"], "front": card["front"], "back": card["back"]}
        for card in cards
    ]
    prompt = f"""
Clasifică aceste 100 de flashcarduri despre romanul „Ion” și construiește între ele
un graf semantic ponderat, neorientat și rar.

Răspunde NUMAI cu linii în cele două formate de mai jos, fără markdown:
M|ID|categorie|dificultate|personaj1;personaj2|concept1;concept2;concept3
E|ID_sursa|ID_tinta|pondere|tip_legatura

Reguli pentru liniile M:
- exact o linie M pentru fiecare dintre cele 100 de ID-uri;
- categorie din: {", ".join(CATEGORIES)};
- dificultate 1, 2 sau 3;
- personajele sunt ordonate după importanță, personajul principal primul;
- 2-6 concepte scurte și normalizate; folosește aceleași denumiri pentru idei identice.

Reguli pentru liniile E:
- fiecare nod are 3-5 vecini;
- fiecare muchie apare o singură dată, fără auto-legături și fără ID-uri inventate;
- pondere între 0.60 și 1.00;
- tip_legatura din: acelasi_concept, aceeasi_secventa, cauza_efect, contrast,
  prerechizita, aprofundare;
- nu lega două carduri doar pentru că menționează același personaj;
- prioritizează obiectivele de învățare, conceptele, cauza-efectul și contrastul;
- creează și legături utile între cardurile S și O.

FLASHCARDURI:
{json.dumps(compact_cards, ensure_ascii=False)}
""".strip()
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={
            "temperature": 0.1,
            "max_output_tokens": 32_000,
        },
    )
    metadata = []
    edges = []
    for raw_line in (response.text or "").splitlines():
        line = raw_line.strip().strip("`")
        if line.startswith("M|"):
            parts = line.split("|", 5)
            if len(parts) != 6:
                continue
            _, card_id, category, difficulty, characters, concepts = parts
            try:
                parsed_difficulty = int(difficulty.strip())
            except ValueError:
                continue
            metadata.append(
                {
                    "id": card_id.strip(),
                    "category": category.strip(),
                    "difficulty": parsed_difficulty,
                    "characters": [item.strip() for item in characters.split(";") if item.strip()],
                    "concepts": [item.strip() for item in concepts.split(";") if item.strip()],
                }
            )
        elif line.startswith("E|"):
            parts = line.split("|", 4)
            if len(parts) != 5:
                continue
            _, source, target, weight, relation = parts
            try:
                parsed_weight = float(weight.strip().replace(",", "."))
            except ValueError:
                continue
            edges.append(
                {
                    "source": source.strip(),
                    "target": target.strip(),
                    "weight": parsed_weight,
                    "relation": relation.strip(),
                }
            )

    expected_ids = {card["id"] for card in cards}
    actual_ids = [item["id"] for item in metadata]
    if len(metadata) != 100 or set(actual_ids) != expected_ids or len(set(actual_ids)) != 100:
        raise ValueError(
            f"Răspunsul compact conține {len(metadata)} clasificări valide din 100."
        )
    return metadata, edges


def normalize_text_list(value: Any, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned = []
    for item in value:
        text = str(item).strip()
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned[:limit]


def merge_metadata(cards: list[dict], metadata: list[dict]) -> list[dict]:
    metadata_by_id = {item["id"]: item for item in metadata}
    enriched = []
    for card in cards:
        item = metadata_by_id[card["id"]]
        category = str(item.get("category", "")).strip()
        if category not in CATEGORIES:
            raise ValueError(f"Categorie invalidă pentru {card['id']}: {category}")
        concepts = normalize_text_list(item.get("concepts"), 6)
        if len(concepts) < 2:
            raise ValueError(f"Prea puține concepte pentru {card['id']}.")
        enriched.append(
            {
                **card,
                "category": category,
                "characters": normalize_text_list(item.get("characters"), 6),
                "concepts": concepts,
                "difficulty": max(1, min(3, int(item.get("difficulty", 2)))),
            }
        )
    return enriched


def metadata_similarity(left: dict, right: dict) -> float:
    left_characters = {item.casefold() for item in left["characters"]}
    right_characters = {item.casefold() for item in right["characters"]}
    left_concepts = {item.casefold() for item in left["concepts"]}
    right_concepts = {item.casefold() for item in right["concepts"]}
    score = 0.45
    score += min(0.20, 0.10 * len(left_characters & right_characters))
    score += min(0.25, 0.08 * len(left_concepts & right_concepts))
    if left["category"] == right["category"]:
        score += 0.10
    return round(min(score, 0.84), 2)


def validate_and_repair_graph(cards: list[dict], raw_edges: list[dict]) -> list[dict]:
    cards_by_id = {card["id"]: card for card in cards}
    edges: dict[tuple[str, str], dict] = {}
    for raw_edge in raw_edges:
        source = str(raw_edge.get("source", "")).strip()
        target = str(raw_edge.get("target", "")).strip()
        if source not in cards_by_id or target not in cards_by_id or source == target:
            continue
        pair = tuple(sorted((source, target)))
        try:
            weight = max(0.6, min(1.0, float(raw_edge.get("weight", 0.6))))
        except (TypeError, ValueError):
            continue
        candidate = {
            "source": pair[0],
            "target": pair[1],
            "weight": round(weight, 3),
            "relation": str(raw_edge.get("relation", "legatura_semantica")).strip(),
            "generated_by": "gemini-2.5-flash",
        }
        if pair not in edges or candidate["weight"] > edges[pair]["weight"]:
            edges[pair] = candidate

    def degree(card_id: str) -> int:
        return sum(card_id in pair for pair in edges)

    # Local repair is intentionally structural; Gemini still supplies the
    # semantic graph. It avoids spending a third request if a node is omitted.
    for card in cards:
        if degree(card["id"]) >= 3:
            continue
        candidates = sorted(
            (
                (metadata_similarity(card, other), other["id"])
                for other in cards
                if other["id"] != card["id"]
                and tuple(sorted((card["id"], other["id"]))) not in edges
            ),
            reverse=True,
        )
        for weight, other_id in candidates:
            pair = tuple(sorted((card["id"], other_id)))
            edges[pair] = {
                "source": pair[0],
                "target": pair[1],
                "weight": max(0.6, weight),
                "relation": "reparatie_metadate",
                "generated_by": "local-validator",
            }
            if degree(card["id"]) >= 3:
                break

    return sorted(edges.values(), key=lambda edge: (edge["source"], edge["target"]))


def main() -> None:
    args = parse_args()
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("Lipsește GOOGLE_API_KEY din .env.")

    model = "gemini-2.5-flash"
    cards = read_base_cards(args.input)
    client = genai.Client(api_key=api_key)

    if args.combined_recovery:
        metadata, raw_edges = generate_combined_bundle(client, model, cards)
        request_count = 1
        generation_mode = "combined-recovery"
    else:
        metadata = generate_metadata(client, model, cards)
        enriched_for_graph = merge_metadata(cards, metadata)
        raw_edges = generate_graph(client, model, enriched_for_graph)
        request_count = 2
        generation_mode = "two-stage"

    enriched_cards = merge_metadata(cards, metadata)
    edges = validate_and_repair_graph(enriched_cards, raw_edges)

    output = {
        "version": 1,
        "work_id": args.work_id,
        "model": model,
        "generation_requests": request_count,
        "generation_mode": generation_mode,
        "cards": enriched_cards,
        "edges": edges,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Carduri: {len(enriched_cards)}")
    print(f"Muchii: {len(edges)}")
    print(f"Salvat: {args.output}")


if __name__ == "__main__":
    main()
