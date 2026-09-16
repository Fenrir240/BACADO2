import json
import sys
import tempfile
import unittest
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
if str(EXPERIMENT_DIR) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_DIR))

from rquge_ro.aggregate_ratings import aggregate
from rquge_ro.data import (
    clamp_score,
    deterministic_group_split,
    format_qa_input,
    format_span_input,
    normalized_exact_match,
    read_jsonl,
    token_f1,
    validate_rating_records,
    write_jsonl,
)
from rquge_ro.prepare_qa_data import convert_squad


class RQuGERoDataTests(unittest.TestCase):
    def test_formats_follow_the_frozen_schema(self):
        self.assertEqual(
            format_qa_input(" Cine? ", " Text. "),
            "întrebare: Cine? context: Text.",
        )
        self.assertEqual(
            format_span_input("Cine?", "Ana", "Ana", "Ana vine."),
            "Cine? <q> Ana <r> Ana <c> Ana vine.",
        )

    def test_romanian_normalization_and_f1(self):
        self.assertEqual(normalized_exact_match("Ștefan!", "ștefan"), 1.0)
        self.assertAlmostEqual(token_f1("Ion al Glanetașului", "Ion Glanetașului"), 0.8)
        self.assertEqual(clamp_score(8), 5.0)
        self.assertEqual(clamp_score(-2), 1.0)

    def test_jsonl_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.jsonl"
            records = [{"question": "Cine?", "context": "Ana vine.", "answer": "Ana"}]
            write_jsonl(path, records)
            self.assertEqual(read_jsonl(path), records)

    def test_group_split_has_no_context_leakage(self):
        records = [
            {"id": "a1", "context": "A"},
            {"id": "a2", "context": "A"},
            {"id": "b", "context": "B"},
            {"id": "c", "context": "C"},
        ]
        train, validation = deterministic_group_split(records, ("context",), 0.25, 7)
        self.assertTrue(train)
        self.assertTrue(validation)
        self.assertTrue(
            {row["context"] for row in train}.isdisjoint(
                {row["context"] for row in validation}
            )
        )

    def test_rating_validation_and_aggregation(self):
        base = {
            "item_id": "item-1",
            "question": "Cine vine?",
            "context": "Ana vine.",
            "gold_answer": "Ana",
            "predicted_answer": "Ana",
        }
        records = [
            {**base, "score": score, "annotator_id": annotator}
            for score, annotator in [(5, "a"), (4, "b"), (5, "c")]
        ]
        validate_rating_records(records)
        aggregated = aggregate(records)
        self.assertEqual(aggregated[0]["annotator_count"], 3)
        self.assertAlmostEqual(aggregated[0]["score"], 14 / 3)

    def test_squad_conversion(self):
        payload = {
            "data": [
                {
                    "title": "Titlu",
                    "paragraphs": [
                        {
                            "context": "Ana vine.",
                            "qas": [
                                {
                                    "id": "q1",
                                    "question": "Cine vine?",
                                    "answers": [{"text": "Ana", "answer_start": 0}],
                                }
                            ],
                        }
                    ],
                }
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "xquad.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            records = convert_squad(path)
        self.assertEqual(records[0]["answer"], "Ana")
        self.assertEqual(records[0]["source"], "xquad_ro")


if __name__ == "__main__":
    unittest.main()
