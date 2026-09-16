from __future__ import annotations

import sys
import unittest
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RESEARCH_DIR = EXPERIMENT_DIR.parent
sys.path.insert(0, str(EXPERIMENT_DIR))

import evaluator  # noqa: E402


class FakeBackend:
    model_id = "fake/minilm"

    def __init__(self, matrix: list[list[float]]) -> None:
        self.matrix = matrix

    def similarity_matrix(self, texts: list[str]) -> list[list[float]]:
        if len(texts) != len(self.matrix):
            raise AssertionError("Număr neașteptat de texte.")
        return self.matrix


class EvaluatorTests(unittest.TestCase):
    def test_compare_meaning_uses_duplicate_threshold(self) -> None:
        result = evaluator.compare_meaning(
            "Întrebarea A",
            "Întrebarea B",
            FakeBackend([[1.0, 0.9], [0.9, 1.0]]),
        )
        self.assertTrue(result["same_meaning"])
        self.assertEqual(result["decision"], "same_meaning")

    def test_semantic_matrix_replaces_lexical_duplicate_points(self) -> None:
        questions = {
            "benchmark_id": "TEST",
            "questions": [
                {"question_id": "Q1", "status": "generated", "question_text": "A?"},
                {"question_id": "Q2", "status": "generated", "question_text": "B?"},
                {"question_id": "Q3", "status": "generated", "question_text": "C?"},
            ],
        }
        backend = FakeBackend(
            [
                [1.0, 0.9, 0.2],
                [0.9, 1.0, 0.3],
                [0.2, 0.3, 1.0],
            ]
        )
        result = evaluator.score_question_generation(
            questions,
            RESEARCH_DIR / "graf1" / "knowledge-graph.json",
            EXPERIMENT_DIR / "inputs" / "question-manifest.json",
            similarity_backend=backend,
        )
        scored = result["questions"]
        self.assertEqual(scored[0]["breakdown"]["non_duplication"], 0.0)
        self.assertEqual(scored[1]["breakdown"]["non_duplication"], 0.0)
        self.assertEqual(scored[2]["breakdown"]["non_duplication"], 5.0)
        self.assertEqual(scored[0]["nearest_question_id"], "Q2")
        self.assertEqual(
            result["semantic_duplication"]["pairs_at_or_above_review_threshold"][0][
                "decision"
            ],
            "same_meaning",
        )


if __name__ == "__main__":
    unittest.main()
