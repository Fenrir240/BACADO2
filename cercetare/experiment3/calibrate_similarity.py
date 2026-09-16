"""Calibrează pragul MiniLM pe perechi etichetate din domeniul întrebărilor BAC."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from evaluator import SEMANTIC_CONFIG_PATH, SentenceTransformerSimilarity


def load_pairs(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    result = []
    for line_number, row in enumerate(rows, start=2):
        if not row.get("sentence_a") or not row.get("sentence_b"):
            raise ValueError(f"Linia {line_number}: lipsesc sentence_a/sentence_b.")
        try:
            label = int(row.get("same_meaning", ""))
        except ValueError as exc:
            raise ValueError(f"Linia {line_number}: same_meaning trebuie să fie 0 sau 1.") from exc
        if label not in {0, 1}:
            raise ValueError(f"Linia {line_number}: same_meaning trebuie să fie 0 sau 1.")
        result.append({**row, "same_meaning": label})
    return result


def balanced_accuracy(scores: list[float], labels: list[int], threshold: float) -> float:
    positives = sum(labels)
    negatives = len(labels) - positives
    true_positive = sum(score >= threshold and label == 1 for score, label in zip(scores, labels))
    true_negative = sum(score < threshold and label == 0 for score, label in zip(scores, labels))
    sensitivity = true_positive / positives if positives else 0.0
    specificity = true_negative / negatives if negatives else 0.0
    return (sensitivity + specificity) / 2.0


def choose_threshold(scores: list[float], labels: list[int]) -> tuple[float, float]:
    unique = sorted(set(scores))
    candidates = [0.0, 1.0]
    candidates.extend(unique)
    candidates.extend((left + right) / 2 for left, right in zip(unique, unique[1:]))
    ranked = sorted(
        ((balanced_accuracy(scores, labels, threshold), threshold) for threshold in candidates),
        key=lambda item: (-item[0], -item[1]),
    )
    accuracy, threshold = ranked[0]
    return threshold, accuracy


def main() -> int:
    parser = argparse.ArgumentParser(description="Calibrează pragul semantic pe date etichetate.")
    parser.add_argument("pairs_csv", type=Path)
    parser.add_argument("--output", type=Path, default=Path("calibration-report.json"))
    parser.add_argument("--write-config", action="store_true")
    args = parser.parse_args()

    config = json.loads(SEMANTIC_CONFIG_PATH.read_text(encoding="utf-8"))
    pairs = load_pairs(args.pairs_csv)
    labels = [int(item["same_meaning"]) for item in pairs]
    if len(pairs) < 10 or not any(labels) or all(labels):
        parser.error("Sunt necesare minimum 10 perechi și exemple din ambele clase.")

    backend = SentenceTransformerSimilarity(str(config["model_id"]), config.get("device"))
    texts = [text for pair in pairs for text in (pair["sentence_a"], pair["sentence_b"])]
    embeddings = backend.model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    scores = [
        float(embeddings[index * 2] @ embeddings[index * 2 + 1])
        for index in range(len(pairs))
    ]
    threshold, accuracy = choose_threshold(scores, labels)
    report = {
        "model_id": backend.model_id,
        "pair_count": len(pairs),
        "positive_count": sum(labels),
        "negative_count": len(labels) - sum(labels),
        "selected_threshold": round(threshold, 6),
        "training_balanced_accuracy": round(accuracy, 6),
        "warning": (
            "Acuratețea este calculată pe setul de calibrare, nu pe un test separat. "
            "Pentru raportare științifică, păstrează un set de test nefolosit la prag."
        ),
        "pairs": [
            {
                "pair_id": pair.get("pair_id") or index + 1,
                "same_meaning": label,
                "similarity": round(score, 6),
            }
            for index, (pair, label, score) in enumerate(zip(pairs, labels, scores))
        ],
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Prag selectat: {threshold:.6f}; balanced accuracy: {accuracy:.3f}")
    print(f"Raport: {args.output}")

    if args.write_config:
        config["duplicate_threshold"] = round(threshold, 6)
        config["review_threshold"] = round(max(0.0, threshold - 0.08), 6)
        config["threshold_status"] = "calibrated_on_domain_pairs"
        config["calibration_report"] = str(args.output)
        SEMANTIC_CONFIG_PATH.write_text(
            json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Config actualizat: {SEMANTIC_CONFIG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
