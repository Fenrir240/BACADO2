from __future__ import annotations

import json
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT_DIR / "scripts"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from build_chronology_exercises import build_chronology_bank
from build_character_mindmaps import build_character_mindmaps
from build_composition_schemas import ELEMENTS, build_packet, validate_schema
from build_completion_exercises import build_completion_bank
from build_flashcard_exercises import build_flashcard_deck
from build_matching_exercises import build_matching_bank
from build_multiple_choice_exercises import build_multiple_choice_bank
from build_quick_testing import (
    append_run_to_question_bank,
    banked_run_ids,
    build_all_banks,
    local_batch_number,
    pending_reserved_batch,
    question_specs,
    qwen_runner,
    reasoning_effort_for_resume,
    result_for_spec,
    main as quick_testing_main,
)
from exercise_builder_common import (
    DEFAULT_GRAPH_PATH,
    DEFAULT_QUESTIONS_PATH,
    graph_work_metadata,
)
from services.exercise_bank_service import (
    choose_prebuilt_exercise,
    load_prebuilt_exercises,
    multiple_choice_test_items,
)


class ExerciseBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.question_payload = json.loads(DEFAULT_QUESTIONS_PATH.read_text(encoding="utf-8"))
        cls.category_counts = {
            category["category_id"]: len(category["questions"])
            for category in cls.question_payload["categories"]
        }
        cls.flashcards = build_flashcard_deck(DEFAULT_QUESTIONS_PATH, DEFAULT_GRAPH_PATH)
        cls.multiple_choice = build_multiple_choice_bank(DEFAULT_QUESTIONS_PATH, DEFAULT_GRAPH_PATH)
        cls.chronology = build_chronology_bank(DEFAULT_QUESTIONS_PATH, DEFAULT_GRAPH_PATH)
        cls.completion = build_completion_bank(DEFAULT_QUESTIONS_PATH, DEFAULT_GRAPH_PATH)
        cls.matching = build_matching_bank(DEFAULT_QUESTIONS_PATH, DEFAULT_GRAPH_PATH)

    def test_all_questions_become_unique_flashcards(self) -> None:
        cards = self.flashcards["cards"]
        expected = self.question_payload["question_count"]
        self.assertEqual(len(cards), expected)
        self.assertEqual(len({card["id"] for card in cards}), expected)
        self.assertEqual(len({card["source_question_id"] for card in cards}), expected)
        self.assertTrue(all(card["front"] and card["back"] for card in cards))

    def test_character_mindmaps_are_deterministic_and_graph_grounded(self) -> None:
        graph = json.loads(DEFAULT_GRAPH_PATH.read_text(encoding="utf-8"))
        first = build_character_mindmaps(graph)
        second = build_character_mindmaps(graph)
        self.assertEqual(first, second)
        self.assertFalse(first["source"]["uses_ai"])
        graph_character_ids = {
            node["id"] for node in graph["nodes"] if node.get("type") == "Character"
        }
        self.assertTrue(set(first["characters"]).issubset(graph_character_ids))
        self.assertIn(
            first["relation_graph"]["central_node_id"],
            first["relation_graph"]["nodes"],
        )
        for edge in first["relation_graph"]["edges"]:
            self.assertIn(edge["source"], graph_character_ids)
            self.assertIn(edge["target"], graph_character_ids)

    def test_composition_packets_cover_three_elements_and_validate_ui_contract(self) -> None:
        graph = json.loads(DEFAULT_GRAPH_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            [element["id"] for element in ELEMENTS],
            ["incipit_final", "conflict", "title"],
        )
        for element in ELEMENTS:
            packet = build_packet(graph, element, DEFAULT_GRAPH_PATH)
            node_ids = {node["id"] for node in packet["nodes"]}
            self.assertTrue(node_ids)
            self.assertTrue(
                all(
                    edge["source"] in node_ids and edge["target"] in node_ids
                    for edge in packet["edges"]
                )
            )
            payload = {
                "task": "composition_element_schema",
                "element_id": element["id"],
                "title": element["title"],
                "central_idea": "Idee centrală.",
                "branches": [
                    {
                        "heading": heading,
                        "key_idea": "Idee-cheie.",
                        "explanation": "Explicație clară.",
                        "evidence_node_ids": [next(iter(node_ids))],
                    }
                    for heading in element["branch_headings"]
                ],
                "essay_paragraph": "Paragraf pentru eseu.",
                "memory_formula": ["unu", "doi", "trei"],
            }
            self.assertTrue(validate_schema(payload, packet)["valid"])

    def test_work_identity_is_derived_from_graph(self) -> None:
        graph = json.loads(DEFAULT_GRAPH_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            graph_work_metadata(graph),
            {"work_id": "ion", "title": "Ion", "author": "Liviu Rebreanu"},
        )
        custom = build_flashcard_deck(DEFAULT_QUESTIONS_PATH, DEFAULT_GRAPH_PATH, "opera_noua")
        self.assertEqual(custom["work_id"], "opera_noua")
        self.assertEqual(custom["work"]["title"], "Ion")

    def test_multiple_choice_contract(self) -> None:
        exercises = self.multiple_choice["exercises"]
        expected = sum(
            self.category_counts[category]
            for category in self.multiple_choice["eligible_categories"]
        )
        self.assertEqual(len(exercises), expected)
        for exercise in exercises:
            self.assertEqual(len(exercise["options"]), 4)
            self.assertEqual(len(set(exercise["options"])), 4)
            self.assertEqual(exercise["options"].count(exercise["answer"]), 1)

    def test_chronology_uses_ordered_graph_events(self) -> None:
        exercises = self.chronology["exercises"]
        expected = sum(
            self.category_counts[category]
            for category in self.chronology["eligible_categories"]
        )
        self.assertEqual(len(exercises), expected)
        self.assertEqual(self.chronology["skipped_count"], 0)
        for exercise in exercises:
            positions = [item["position"] for item in exercise["items"]]
            self.assertEqual(positions, list(range(1, len(positions) + 1)))
            self.assertTrue(all(item["event_id"].startswith("EV_") for item in exercise["items"]))

    def test_completion_contract(self) -> None:
        exercises = self.completion["exercises"]
        eligible_questions = sum(
            self.category_counts[category]
            for category in self.completion["eligible_categories"]
        )
        self.assertEqual(len(exercises), eligible_questions // 3)
        for exercise in exercises:
            self.assertEqual(exercise["text"].count("____"), 3)
            self.assertEqual(len(exercise["answers"]), 3)
            self.assertEqual(len(exercise["source_question_ids"]), 3)

    def test_matching_uses_each_eligible_question_once(self) -> None:
        exercises = self.matching["exercises"]
        source_ids = [
            pair["source_question_id"]
            for exercise in exercises
            for pair in exercise["pairs"]
        ]
        expected = sum(
            self.category_counts[category]
            for category in self.matching["eligible_categories"]
        )
        self.assertEqual(len(source_ids), expected)
        self.assertEqual(len(set(source_ids)), expected)
        self.assertTrue(all(3 <= len(exercise["pairs"]) <= 5 for exercise in exercises))

    def test_ui_service_loads_and_rotates_every_contract(self) -> None:
        expected_counts = {
            "Ordine cronologică": len(self.chronology["exercises"]),
            "Asociere": len(self.matching["exercises"]),
            "Completare": len(self.completion["exercises"]),
            "Alege răspunsul": len(self.multiple_choice["exercises"]),
            "Întoarce cartea": len(self.flashcards["quick_sets"]),
        }
        for label, count in expected_counts.items():
            bank = load_prebuilt_exercises("ion", label)
            self.assertEqual(len(bank), count)
            first = choose_prebuilt_exercise("ion", label)
            second = choose_prebuilt_exercise("ion", label, [first["id"]])
            self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(len(multiple_choice_test_items("ion", 10, 45)), 10)

    def test_unified_pipeline_writes_every_ui_artifact(self) -> None:
        tmp_root = ROOT_DIR / "tmp"
        tmp_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tmp_root) as directory:
            data_dir = Path(directory)
            payloads = build_all_banks(
                DEFAULT_QUESTIONS_PATH,
                DEFAULT_GRAPH_PATH,
                "ion_pipeline_test",
                data_dir,
            )
            expected = [
                data_dir / "flashcards" / "ion_pipeline_test.json",
                data_dir / "exercises" / "ion_pipeline_test" / "multiple_choice.json",
                data_dir / "exercises" / "ion_pipeline_test" / "chronology.json",
                data_dir / "exercises" / "ion_pipeline_test" / "completion.json",
                data_dir / "exercises" / "ion_pipeline_test" / "matching.json",
            ]
            self.assertTrue(all(path.is_file() for path in expected))
            self.assertTrue(all(payload["work_id"] == "ion_pipeline_test" for payload in payloads.values()))

    def test_unified_pipeline_accumulates_one_qwen_batch(self) -> None:
        tmp_root = ROOT_DIR / "tmp"
        tmp_root.mkdir(exist_ok=True)
        runner = qwen_runner()
        specs = question_specs(runner, ROOT_DIR / "cercetare-qwen" / "graph-packets")
        questions_by_category = {
            category["category_id"]: category["questions"][:3]
            for category in self.question_payload["categories"]
        }
        with tempfile.TemporaryDirectory(dir=tmp_root) as directory:
            project = Path(directory)
            run_dir = project / "run-test-b001"
            for spec in specs:
                relative_attempt = Path("questions") / spec.slug / "attempts" / "attempt-001"
                attempt_dir = run_dir / relative_attempt
                attempt_dir.mkdir(parents=True)
                (attempt_dir / "result.json").write_text(
                    json.dumps(
                        {
                            "task": "question_generation",
                            "category_id": spec.expected_id,
                            "questions": questions_by_category[spec.expected_id],
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                latest_path = run_dir / "questions" / spec.slug / "latest.json"
                latest_path.write_text(
                    json.dumps(
                        {
                            "status": "succeeded",
                            "validation_passed": False,
                            "attempt_dir": str(relative_attempt),
                        }
                    ),
                    encoding="utf-8",
                )
            bank = append_run_to_question_bank(
                project / "questions.json",
                {"work_id": "ion_pipeline_test", "title": "Ion", "author": "Liviu Rebreanu"},
                runner,
                run_dir,
                specs,
                model_id="qwen/test",
                batch_number=1,
            )
            self.assertEqual(bank["question_count"], 24)
            self.assertEqual(bank["generated_question_count"], 24)
            self.assertEqual(bank["run_count"], 1)
            self.assertTrue((project / "questions-by-category.txt").is_file())

    def test_unified_pipeline_defaults_to_96_questions_without_api_call(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            result = quick_testing_main(
                ["--graph", str(DEFAULT_GRAPH_PATH), "--plan-only"]
            )
        self.assertEqual(result, 0)
        self.assertIn("Apeluri Qwen planificate: 32", output.getvalue())
        self.assertIn("Întrebări planificate: 96", output.getvalue())

    def test_failed_reserved_batch_is_resumed_without_reserving_new_events(self) -> None:
        tmp_root = ROOT_DIR / "tmp"
        tmp_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tmp_root) as directory:
            project = Path(directory)
            run_id = "run-20260822T120000000000Z-b004"
            packet_dir = project / "runs" / run_id / "inputs" / "question-packets"
            packet_dir.mkdir(parents=True)
            (project / "selection-history.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "work_id": "opera_test",
                        "last_batch_number": 4,
                        "batches": [{"batch_number": 4, "run_id": run_id}],
                    }
                ),
                encoding="utf-8",
            )
            (project / "questions.json").write_text(
                json.dumps(
                    {
                        "work_id": "opera_test",
                        "categories": [
                            {
                                "category_id": "SIMPLE_FACT",
                                "questions": [
                                    {"source": {"run_id": "run-anterior-b003"}}
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            pending = pending_reserved_batch(
                project, "opera_test", project / "questions.json"
            )

            self.assertIsNotNone(pending)
            assert pending is not None
            self.assertEqual(pending[0].name, run_id)
            self.assertEqual(pending[1]["batch_number"], 4)
            self.assertEqual(local_batch_number(run_id), 4)
            self.assertEqual(banked_run_ids(project / "questions.json"), {"run-anterior-b003"})

    def test_length_error_resumes_without_reasoning(self) -> None:
        class FakeRunner:
            @staticmethod
            def load_latest(_run_dir: Path, _spec: object) -> dict:
                return {
                    "status": "error",
                    "error": {
                        "message": "Răspunsul nu conține text final (finish_reason='length')."
                    },
                }

        self.assertEqual(
            reasoning_effort_for_resume(FakeRunner(), Path("run"), object(), "medium"),
            "none",
        )

    def test_unparseable_qwen_output_is_preserved_without_retry(self) -> None:
        tmp_root = ROOT_DIR / "tmp"
        tmp_root.mkdir(exist_ok=True)
        runner = qwen_runner()
        spec = question_specs(runner, ROOT_DIR / "cercetare-qwen" / "graph-packets")[0]
        with tempfile.TemporaryDirectory(dir=tmp_root) as directory:
            run_dir = Path(directory)
            relative_attempt = Path("questions") / spec.slug / "attempts" / "attempt-001"
            attempt_dir = run_dir / relative_attempt
            attempt_dir.mkdir(parents=True)
            (attempt_dir / "response.raw.txt").write_text("răspuns care nu este JSON", encoding="utf-8")
            latest_path = run_dir / "questions" / spec.slug / "latest.json"
            latest_path.write_text(
                json.dumps(
                    {
                        "status": "unparseable",
                        "validation_passed": False,
                        "attempt_dir": str(relative_attempt),
                    }
                ),
                encoding="utf-8",
            )
            payload, latest = result_for_spec(runner, run_dir, spec)
            self.assertEqual(len(payload["questions"]), 3)
            self.assertTrue(all(item["status"] == "unparseable" for item in payload["questions"]))
            self.assertTrue(latest["unparseable_preserved"])


if __name__ == "__main__":
    unittest.main()
