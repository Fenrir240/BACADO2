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

import build_understanding as builder
import build_literary_current as literary_current_builder


def sample_graph() -> dict:
    return {
        "metadata": {"work": "Opera Test", "author": "Autor Test", "version": "1"},
        "sources": [],
        "nodes": [
            {"id": "WORK", "type": "Work", "label": "Opera Test"},
            {"id": "AUTHOR", "type": "Author", "label": "Autor Test"},
            {"id": "CH_01", "type": "Chapter", "label": "Capitolul I"},
            {"id": "CH_02", "type": "Chapter", "label": "Capitolul II"},
            {
                "id": "EV_01",
                "type": "NarrativeEvent",
                "label": "Prima scenă",
                "description": "Personajul ajunge în sat.",
                "importance": "major",
                "chapter_ids": ["CH_01"],
                "attributes": {
                    "chapter_id": "CH_01",
                    "chapter_order": 1,
                    "canonical_description": "Personajul ajunge în sat.",
                    "verification": {"evidence_quote": "Personajul păși pentru prima dată în sat."},
                },
            },
            {
                "id": "EV_02",
                "type": "NarrativeEvent",
                "label": "A doua scenă",
                "description": "Personajul ia hotărârea decisivă.",
                "importance": "major",
                "chapter_ids": ["CH_02"],
                "attributes": {
                    "chapter_id": "CH_02",
                    "chapter_order": 1,
                    "canonical_description": "Personajul ia hotărârea decisivă.",
                    "verification": {"evidence_quote": "Atunci hotărî, fără ezitare, să plece."},
                },
            },
        ],
        "edges": [],
        "chapters": [
            {"id": "CH_01", "ordinal": 1, "title": "Capitolul I", "event_sequence": ["EV_01"]},
            {"id": "CH_02", "ordinal": 2, "title": "Capitolul II", "event_sequence": ["EV_02"]},
        ],
    }


class UnderstandingBuilderTests(unittest.TestCase):
    def test_completed_chapter_is_reused_only_for_identical_packet_and_prompt(self):
        graph = sample_graph()
        packet = builder._chapter_packet(graph, graph["chapters"][0])
        prompt = builder._summary_prompt(packet)
        chapter_name = f"01-{builder._slug(packet['chapter']['title'])}"
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            cached_dir = output_dir / "qwen-summary-runs" / "run-old" / chapter_name
            cached_dir.mkdir(parents=True)
            builder.write_json(cached_dir / "packet.json", packet)
            builder.write_json(
                cached_dir / "request.json",
                {
                    "model": "qwen/qwen3.7-flash",
                    "messages": [{"role": "user", "content": prompt}],
                    "reasoning": {"effort": "medium", "exclude": True},
                },
            )
            builder.write_json(
                cached_dir / "response.openrouter.json",
                {"choices": [{"finish_reason": "stop"}], "usage": {"cost": 0.001}},
            )
            (cached_dir / "response.raw.txt").write_text(
                json.dumps(
                    {
                        "summary": "Prima variantă salvată.",
                        "covered_event_ids": packet["chapter"]["event_ids"],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            cached = builder._find_cached_chapter_summary(
                output_dir,
                chapter_name,
                packet,
                prompt,
                model="qwen/qwen3.7-flash",
                reasoning="medium",
            )
            changed_prompt = builder._find_cached_chapter_summary(
                output_dir,
                chapter_name,
                packet,
                prompt + " schimbat",
                model="qwen/qwen3.7-flash",
                reasoning="medium",
            )

        self.assertIsNotNone(cached)
        self.assertEqual(cached["normalized"]["summary"], "Prima variantă salvată.")
        self.assertIsNone(changed_prompt)

    def test_length_response_is_kept_without_retry_and_uses_empty_content(self):
        response = {
            "choices": [
                {
                    "finish_reason": "length",
                    "message": {"content": None},
                }
            ],
            "usage": {"completion_tokens": 2600, "cost": 0.001},
        }
        runner = mock.Mock()
        runner.OPENROUTER_BASE_URL = "https://example.test/api/v1"
        runner.api_json.return_value = response
        runner.extract_content.side_effect = ValueError(
            "Răspunsul nu conține text final (finish_reason='length')."
        )

        exchange, content = builder._request_qwen(
            runner,
            "test-key",
            "prompt",
            model="qwen/qwen3.7-flash",
            reasoning="medium",
            timeout=30,
            max_tokens=builder.DEFAULT_SUMMARY_MAX_TOKENS,
        )

        self.assertEqual(content, "")
        self.assertIs(exchange["response"], response)
        self.assertEqual(runner.api_json.call_count, 1)

    def test_understanding_output_budgets_leave_room_for_medium_reasoning(self):
        self.assertGreaterEqual(builder.DEFAULT_SUMMARY_MAX_TOKENS, 12_000)
        self.assertGreaterEqual(builder.DEFAULT_SELECTION_MAX_TOKENS, 8_000)

    def test_summary_keeps_first_payload_even_when_coverage_is_invalid(self):
        graph = sample_graph()
        packet = builder._chapter_packet(graph, graph["chapters"][0])
        result = builder._normalize_chapter_summary(
            {"summary": "Prima variantă Qwen.", "covered_event_ids": []},
            "",
            packet,
        )
        self.assertEqual(result["summary"], "Prima variantă Qwen.")
        self.assertFalse(result["validation"]["valid"])

    def test_sequence_text_comes_only_from_graph_quotes(self):
        graph = sample_graph()
        candidates = builder._sequence_candidates(graph, builder._chapters(graph))
        result = builder._normalize_sequence_selection(
            {
                "sequences": [
                    {"title": "Sosirea", "event_ids": ["EV_01"]},
                    {"title": "Hotărârea", "event_ids": ["EV_02"]},
                ]
            },
            graph,
            candidates,
        )
        self.assertTrue(result["validation"]["all_text_is_verbatim"])
        self.assertEqual(
            [item["text"] for item in result["sequences"]],
            [
                "Personajul păși pentru prima dată în sat.",
                "Atunci hotărî, fără ezitare, să plece.",
            ],
        )

    def test_verified_pdf_sequences_are_preserved_on_future_runs(self):
        artifact = {
            "generation": {"locked_from_regeneration": True},
            "sequences": [
                {
                    "id": "scene_1",
                    "text": "Fragment verificat din PDF.",
                    "source_mode": "verbatim_pdf_excerpt",
                },
                {
                    "id": "scene_2",
                    "text": "Al doilea fragment verificat din PDF.",
                    "source_mode": "verbatim_pdf_excerpt",
                },
            ],
            "validation": {
                "all_text_is_verbatim": True,
                "matched_to_model_essay": True,
            },
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "secvente-relevante.json"
            builder.write_json(output_path, artifact)
            reused = builder._find_reusable_artifact(
                output_path,
                {"packet": "nou"},
                "prompt nou",
                model="alt-model",
                reasoning="none",
            )

        self.assertIsNotNone(reused)
        self.assertTrue(reused["generation"]["reused"])
        self.assertFalse(reused["generation"]["new_api_call"])
        self.assertEqual(reused["generation"]["usage"], {})

    def test_dry_run_plans_whole_pipeline_without_qwen(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            model_essay_path = root / "eseu-model.md"
            model_essay_path.write_text(
                "Eseul argumentează obiectivitatea și tipicitatea personajelor.",
                encoding="utf-8",
            )
            graph = sample_graph()
            graph["sources"] = [
                {
                    "id": "SRC_MODEL_ESSAY",
                    "source_type": "model_essay",
                    "path": "eseu-model.md",
                }
            ]
            graph_path = root / "knowledge-graph.json"
            graph_path.write_text(json.dumps(graph, ensure_ascii=False), encoding="utf-8")
            with mock.patch.object(builder, "ROOT_DIR", root):
                manifest, manifest_path = builder.build_understanding_project(
                    graph_path,
                    dry_run=True,
                )
            self.assertEqual(manifest["status"], "planned")
            self.assertEqual(manifest["qwen_calls"], 7)
            self.assertFalse(manifest["retry_on_invalid"])
            self.assertTrue(manifest_path.is_file())

    def test_literary_current_accepts_exactly_two_traits_from_model_essay(self):
        essay = (
            "Perspectiva narativă obiectivă este susținută de naratorul omniscient. "
            "Personajele tipice reprezintă categorii sociale bine definite."
        )
        payload = {
            "movement": {
                "name": "Realism",
                "definition": "Curent literar.",
                "work_classification": "Opera este realistă.",
            },
            "traits": [
                {
                    "title": "Perspectivă narativă obiectivă",
                    "explanation": "Narator obiectiv.",
                    "evidence_from_work": ["Narator omniscient."],
                    "essay_use": "Se argumentează obiectivitatea.",
                    "model_essay_excerpt": "Perspectiva narativă obiectivă este susținută de naratorul omniscient.",
                },
                {
                    "title": "Personaje tipice",
                    "explanation": "Personaje reprezentative.",
                    "evidence_from_work": ["Categorii sociale."],
                    "essay_use": "Se argumentează tipicitatea.",
                    "model_essay_excerpt": "Personajele tipice reprezintă categorii sociale bine definite.",
                },
            ],
            "bac_synthesis": "Sinteză.",
        }
        material, validation = literary_current_builder._normalize(payload, essay)
        self.assertEqual(len(material["traits"]), 2)
        self.assertTrue(validation["traits_from_model_essay_verified"])
        self.assertTrue(validation["valid"])

        payload["traits"].append(dict(payload["traits"][0]))
        _, invalid_validation = literary_current_builder._normalize(payload, essay)
        self.assertFalse(invalid_validation["valid"])

    def test_pipeline_disables_graph_enrichment(self):
        source = Path(builder.__file__).read_text(encoding="utf-8")
        self.assertIn("dry_run=False, enrich=False", source)
        self.assertNotIn("dry_run=False, enrich=True", source)

    def test_standalone_literary_current_does_not_enrich_by_default(self):
        self.assertFalse(
            literary_current_builder.generate_literary_current.__kwdefaults__["enrich"]
        )


if __name__ == "__main__":
    unittest.main()
