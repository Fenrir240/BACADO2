import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import cost_reporting


class CostReportingTests(unittest.TestCase):
    def test_summarizes_openrouter_cost_and_reasoning_tokens(self):
        summary = cost_reporting.summarize_usages(
            [
                {
                    "prompt_tokens": 10,
                    "completion_tokens": 6,
                    "total_tokens": 16,
                    "cost": 0.001,
                    "completion_tokens_details": {"reasoning_tokens": 4},
                },
                {
                    "prompt_tokens": 20,
                    "completion_tokens": 8,
                    "total_tokens": 28,
                    "cost": 0.002,
                    "reasoning_tokens": 5,
                },
            ]
        )
        self.assertEqual(summary["api_calls"], 2)
        self.assertEqual(summary["prompt_tokens"], 30)
        self.assertEqual(summary["reasoning_tokens"], 9)
        self.assertEqual(summary["total_tokens"], 44)
        self.assertAlmostEqual(summary["cost_usd"], 0.003)

    def test_reads_each_quick_testing_attempt_once(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            run_dir = Path(temporary_directory) / "run-1"
            metadata_path = (
                run_dir
                / "questions"
                / "category"
                / "attempts"
                / "attempt-01"
                / "task-metadata.json"
            )
            metadata_path.parent.mkdir(parents=True)
            metadata_path.write_text(
                json.dumps({"usage": {"total_tokens": 12, "cost": 0.004}}),
                encoding="utf-8",
            )
            usages = cost_reporting.usages_from_attempt_metadata([run_dir])
        self.assertEqual(usages, [{"total_tokens": 12, "cost": 0.004}])


if __name__ == "__main__":
    unittest.main()
