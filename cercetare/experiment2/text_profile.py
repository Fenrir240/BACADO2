"""Indicatori lexicali reproductibili pentru rezumatele Experimentului 2.

Modulul nu apelează niciun LLM. El tokenizează textul, numără un lexicon înghețat
de conectori și identifică numele personajelor care există în knowledge graph.
Procentele sunt calculate din text, nu sunt preluate din declarațiile agentului.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


WORD_RE = re.compile(
    r"[0-9A-Za-zĂÂÎȘŞȚŢăâîșşțţ]+(?:[-’'][0-9A-Za-zĂÂÎȘŞȚŢăâîșşțţ]+)?"
)
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

# Lexicoanele sunt intenționat scurte și auditabile. Formele sunt normalizate mai jos.
DISCOURSE_CONNECTORS = (
    "aici",
    "apoi",
    "astfel",
    "așadar",
    "atunci",
    "cu toate acestea",
    "deși",
    "după aceea",
    "în cele din urmă",
    "în consecință",
    "însă",
    "între timp",
    "mai târziu",
    "pe de altă parte",
    "prin urmare",
    "totuși",
    "ulterior",
)

FILLER_PHRASES = (
    "de asemenea",
    "după cum se poate observa",
    "este important de menționat",
    "în acest context",
    "în ceea ce privește",
    "în continuare",
    "la rândul său",
    "mai apoi",
    "merită menționat",
    "referitor la",
    "trebuie precizat",
)

CONJUNCTIONS_AND_SUBORDINATORS = {
    "că",
    "căci",
    "când",
    "dar",
    "dacă",
    "deoarece",
    "fiindcă",
    "iar",
    "ori",
    "sau",
    "și",
    "unde",
}

PREPOSITIONS = {
    "asupra",
    "ca",
    "către",
    "contra",
    "cu",
    "de",
    "despre",
    "din",
    "dintre",
    "după",
    "fără",
    "în",
    "într-o",
    "la",
    "până",
    "pe",
    "pentru",
    "peste",
    "prin",
    "spre",
    "sub",
}

NAME_PARTICLES = {"a", "ai", "al", "ale", "lui"}


def normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(character for character in text if not unicodedata.combining(character))
    return " ".join(WORD_RE.findall(text.lower().replace("ş", "ș").replace("ţ", "ț")))


def canonical_word(value: Any) -> str:
    """Normalizează variantele cu sedilă, dar păstrează diacriticele distinctive."""

    return unicodedata.normalize("NFC", str(value or "")).lower().replace("ş", "ș").replace("ţ", "ț")


def words(text: Any) -> list[str]:
    return WORD_RE.findall(str(text or ""))


def normalized_words(text: Any) -> list[str]:
    return [normalize(token) for token in words(text)]


def sentences(text: Any) -> list[str]:
    value = str(text or "").strip()
    if not value:
        return []
    return [item.strip() for item in SENTENCE_RE.split(value) if item.strip()]


def _phrase_tokens(phrases: Iterable[str]) -> list[tuple[str, ...]]:
    result = {tuple(normalized_words(phrase)) for phrase in phrases}
    return sorted((item for item in result if item), key=lambda item: (-len(item), item))


def find_phrases(tokens: Sequence[str], phrases: Iterable[str]) -> list[str]:
    """Găsește apariții fără suprapunere, preferând expresia cea mai lungă."""

    patterns = _phrase_tokens(phrases)
    matches: list[str] = []
    index = 0
    while index < len(tokens):
        match: tuple[str, ...] | None = None
        for pattern in patterns:
            if tuple(tokens[index : index + len(pattern)]) == pattern:
                match = pattern
                break
        if match is None:
            index += 1
            continue
        matches.append(" ".join(match))
        index += len(match)
    return matches


def _load_graph(graph: Any | None) -> dict[str, Any]:
    if graph is None:
        return {}
    if isinstance(graph, Mapping):
        return dict(graph)
    path = Path(graph)
    return json.loads(path.read_text(encoding="utf-8"))


def character_vocabulary(graph: Any | None) -> tuple[set[str], dict[str, set[str]]]:
    """Întoarce tokenurile de nume și aliasurile neambigue ale personajelor."""

    graph_data = _load_graph(graph)
    labels: dict[str, list[str]] = {}
    token_to_ids: dict[str, set[str]] = {}
    for node in graph_data.get("nodes", []):
        if node.get("type") != "Character" or not node.get("id") or not node.get("label"):
            continue
        significant = [
            token
            for token in normalized_words(node["label"])
            if token not in NAME_PARTICLES
        ]
        if not significant:
            continue
        node_id = str(node["id"])
        labels[node_id] = significant
        for token in significant:
            token_to_ids.setdefault(token, set()).add(node_id)

    vocabulary = set(token_to_ids)
    aliases: dict[str, set[str]] = {}
    for node_id, label_tokens in labels.items():
        full_alias = " ".join(label_tokens)
        aliases.setdefault(full_alias, set()).add(node_id)
        for token in label_tokens:
            if len(token_to_ids[token]) == 1:
                aliases.setdefault(token, set()).add(node_id)
    return vocabulary, aliases


def analyze_text(text: str, graph: Any | None = None) -> dict[str, Any]:
    raw_tokens = words(text)
    token_values = [normalize(token) for token in raw_tokens]
    grammatical_tokens = [canonical_word(token) for token in raw_tokens]
    sentence_values = sentences(text)
    total = len(token_values)
    sentence_lengths = [len(words(item)) for item in sentence_values]

    connector_matches = find_phrases(token_values, DISCOURSE_CONNECTORS)
    filler_matches = find_phrases(token_values, FILLER_PHRASES)
    filler_word_count = sum(len(item.split()) for item in filler_matches)
    conjunction_count = sum(
        token in CONJUNCTIONS_AND_SUBORDINATORS for token in grammatical_tokens
    )
    preposition_count = sum(token in PREPOSITIONS for token in grammatical_tokens)

    character_tokens, character_aliases = character_vocabulary(graph)
    character_name_token_count = sum(token in character_tokens for token in token_values)
    mentioned_ids: set[str] = set()
    for alias, ids in character_aliases.items():
        if find_phrases(token_values, (alias,)):
            mentioned_ids.update(ids)

    normalized_connectors = {normalize(value) for value in DISCOURSE_CONNECTORS}
    connector_starts = 0
    for sentence in sentence_values:
        sentence_tokens = normalized_words(sentence)
        if any(
            " ".join(sentence_tokens[: len(connector.split())]) == connector
            for connector in normalized_connectors
        ):
            connector_starts += 1

    connector_frequency = Counter(connector_matches)
    most_repeated = max(connector_frequency.values(), default=0)

    def ratio(count: int | float) -> float:
        return round(float(count) / total, 6) if total else 0.0

    return {
        "word_count": total,
        "sentence_count": len(sentence_values),
        "average_sentence_length": round(
            sum(sentence_lengths) / len(sentence_lengths), 3
        ) if sentence_lengths else 0.0,
        "sentence_lengths": sentence_lengths,
        "discourse_connector_count": len(connector_matches),
        "discourse_connector_ratio": ratio(len(connector_matches)),
        "discourse_connectors": dict(sorted(connector_frequency.items())),
        "connector_sentence_start_count": connector_starts,
        "connector_sentence_start_ratio": round(
            connector_starts / len(sentence_values), 6
        ) if sentence_values else 0.0,
        "most_repeated_connector_count": most_repeated,
        "most_repeated_connector_per_200_words": round(
            most_repeated * 200 / total, 6
        ) if total else 0.0,
        "filler_phrase_count": len(filler_matches),
        "filler_word_count": filler_word_count,
        "filler_word_ratio": ratio(filler_word_count),
        "filler_phrases": dict(sorted(Counter(filler_matches).items())),
        "conjunction_count": conjunction_count,
        "conjunction_ratio": ratio(conjunction_count),
        "preposition_count": preposition_count,
        "preposition_ratio": ratio(preposition_count),
        "character_name_token_count": character_name_token_count,
        "character_name_token_ratio": ratio(character_name_token_count),
        "mentioned_character_ids": sorted(mentioned_ids),
    }


def _range_score(value: float, minimum: float | None, maximum: float | None) -> float:
    if minimum is not None and value < minimum:
        scale = max(abs(minimum), (maximum or minimum) - minimum, 0.01)
        return max(0.0, 1.0 - (minimum - value) / scale)
    if maximum is not None and value > maximum:
        scale = max(abs(maximum), maximum - (minimum or 0.0), 0.01)
        return max(0.0, 1.0 - (value - maximum) / scale)
    return 1.0


def evaluate_profile(profile: Mapping[str, Any], constraints: Mapping[str, Any]) -> dict[str, Any]:
    """Compară profilul cu intervalele și întoarce conformitatea 0..1."""

    results: dict[str, Any] = {}
    weighted_total = 0.0
    weight_total = 0.0
    for name, rule in constraints.items():
        if not isinstance(rule, Mapping) or "metric" not in rule:
            continue
        metric = str(rule["metric"])
        value = float(profile.get(metric, 0.0))
        minimum = float(rule["min"]) if "min" in rule else None
        maximum = float(rule["max"]) if "max" in rule else None
        weight = float(rule.get("weight", 1.0))
        score = _range_score(value, minimum, maximum)
        results[name] = {
            "metric": metric,
            "value": round(value, 6),
            "minimum": minimum,
            "maximum": maximum,
            "weight": weight,
            "passed": score == 1.0,
            "score": round(score, 6),
        }
        weighted_total += score * weight
        weight_total += weight
    compliance = weighted_total / weight_total if weight_total else 1.0
    return {
        "compliance": round(compliance, 6),
        "all_rules_passed": all(item["passed"] for item in results.values()),
        "rules": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analizează profilul lexical al unui rezumat.")
    parser.add_argument("text_file", type=Path)
    parser.add_argument("--graph", type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    profile = analyze_text(args.text_file.read_text(encoding="utf-8"), args.graph)
    result: dict[str, Any] = {"profile": profile}
    if args.manifest:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        result["evaluation"] = evaluate_profile(
            profile, manifest.get("style_constraints", {})
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
