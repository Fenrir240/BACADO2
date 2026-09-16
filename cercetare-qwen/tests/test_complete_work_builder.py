import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_complete_work as builder


def sample_graph(model_essay_path: str) -> dict:
    return {
        "metadata": {
            "work": "Opera Test",
            "author": "Autor Test",
            "work_type": "roman",
        },
        "sources": [
            {
                "id": "SRC_ESSAY",
                "source_type": "model_essay",
                "path": model_essay_path,
            }
        ],
        "nodes": [
            {"id": "WORK", "type": "Work", "label": "Opera Test"},
            {"id": "AUTHOR", "type": "Author", "label": "Autor Test"},
            {"id": "CH_01", "type": "Chapter", "label": "Capitolul I"},
        ],
        "edges": [],
        "chapters": [
            {
                "id": "CH_01",
                "ordinal": 1,
                "title": "Capitolul I",
                "event_sequence": [],
            }
        ],
    }


class CompleteWorkBuilderTests(unittest.TestCase):
    def prepare(self, root: Path) -> tuple[Path, Path]:
        source_dir = root / "sources"
        source_dir.mkdir(parents=True)
        model_path = source_dir / "eseu-model.md"
        model_path.write_text("Eseu-model pentru opera test.", encoding="utf-8")
        graph_path = root / "graf-opera test.json"
        graph_path.write_text(
            json.dumps(sample_graph("sources/eseu-model.md"), ensure_ascii=False),
            encoding="utf-8",
        )
        return graph_path, model_path

    def test_dry_run_needs_only_graph_and_plans_all_three_sections(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            graph_path, _ = self.prepare(root)
            with mock.patch.object(builder, "ROOT_DIR", root):
                manifest, manifest_path = builder.build_complete_work(
                    graph_path,
                    dry_run=True,
                )
            self.assertEqual(manifest["status"], "planned")
            self.assertEqual(manifest["planned_questions"], 96)
            self.assertEqual(manifest["qwen_calls"], 39)
            self.assertEqual(
                [step["id"] for step in manifest["steps"]],
                ["intelegere-opera", "testare-rapida", "construieste-eseu", "register-work"],
            )
            self.assertTrue(manifest_path.is_file())

    def test_full_orchestrator_registers_once_and_rerun_skips_ready_steps(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            graph_path, _ = self.prepare(root)
            original_hash = builder._sha256(graph_path)

            def fake_understanding(canonical_graph: Path, **_: object):
                path = root / "data/generated_works/opera_test/intelegere-opera/manifest.json"
                payload = {
                    "status": "ready",
                    "cost_summary": {
                        "api_calls": 6,
                        "prompt_tokens": 100,
                        "completion_tokens": 50,
                        "reasoning_tokens": 10,
                        "total_tokens": 150,
                        "cost_usd": 0.01,
                    },
                }
                builder.write_json(path, payload)
                return payload, path

            def fake_quick(canonical_graph: Path, **_: object):
                path = root / "data/generated_works/opera_test/testare-rapida/manifest.json"
                builder.write_json(path, {"status": "complete"})
                return {
                    "api_calls": 32,
                    "prompt_tokens": 200,
                    "completion_tokens": 100,
                    "reasoning_tokens": 20,
                    "total_tokens": 300,
                    "cost_usd": 0.02,
                }

            def fake_essay(canonical_graph: Path, model_essay: Path, **_: object):
                path = root / "data/generated_works/opera_test/construieste-eseu/manifest.json"
                builder.write_json(path, {"status": "ready"})
                return {
                    "validation": {"valid": True},
                    "generation": {
                        "usage": {
                            "prompt_tokens": 30,
                            "completion_tokens": 20,
                            "total_tokens": 50,
                            "cost": 0.005,
                            "completion_tokens_details": {"reasoning_tokens": 5},
                        }
                    },
                }, path

            with (
                mock.patch.object(builder, "ROOT_DIR", root),
                mock.patch.object(builder, "build_understanding_project", side_effect=fake_understanding) as understanding_mock,
                mock.patch.object(builder, "_run_quick_testing", side_effect=fake_quick) as quick_mock,
                mock.patch.object(builder, "generate_essay_blueprint", side_effect=fake_essay) as essay_mock,
            ):
                first, output_path = builder.build_complete_work(graph_path)
                second, _ = builder.build_complete_work(graph_path)

            self.assertEqual(first["status"], "ready")
            self.assertEqual(first["executed_qwen_calls"], 39)
            self.assertEqual(second["executed_qwen_calls"], 0)
            self.assertEqual(first["costs"]["latest_run"]["api_calls"], 39)
            self.assertAlmostEqual(first["costs"]["work_lifetime"]["cost_usd"], 0.035)
            self.assertEqual(second["costs"]["latest_run"]["api_calls"], 0)
            self.assertAlmostEqual(second["costs"]["work_lifetime"]["cost_usd"], 0.035)
            self.assertTrue(first["registered_in_app"])
            self.assertFalse(first["source_graph_modified"])
            self.assertEqual(builder._sha256(graph_path), original_hash)
            self.assertEqual(understanding_mock.call_count, 1)
            self.assertEqual(quick_mock.call_count, 1)
            self.assertEqual(essay_mock.call_count, 1)
            works = json.loads((root / "data/works.json").read_text(encoding="utf-8"))
            self.assertEqual(len(works), 1)
            self.assertEqual(works[0]["id"], "opera_test")
            self.assertEqual(works[0]["category"], "my")
            self.assertTrue(output_path.is_file())
            cost_report = json.loads(
                (root / "data/generated_works/opera_test/cost-report.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(cost_report["lifetime"]["total"]["total_tokens"], 500)


if __name__ == "__main__":
    unittest.main()
