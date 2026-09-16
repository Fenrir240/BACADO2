from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "run_qwen_packets.py"
SPEC = importlib.util.spec_from_file_location("run_qwen_packets_tested", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


class PacketRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.specs = runner.build_task_specs()

    def test_default_model_is_qwen_3_7_flash(self) -> None:
        self.assertEqual(runner.DEFAULT_MODEL, "qwen/qwen3.7-flash")

    def test_question_defaults_enable_reasoning_without_validation_retries(self) -> None:
        self.assertEqual(runner.DEFAULT_QUESTION_REASONING_EFFORT, "medium")
        self.assertFalse(hasattr(runner, "DEFAULT_QUESTION_MAX_ATTEMPTS"))
        self.assertEqual(runner.DEFAULT_SUMMARY_REASONING_EFFORT, "medium")
        self.assertEqual(runner.DEFAULT_SUMMARY_MAX_ATTEMPTS, 1)

    def valid_simple_payload(self, spec, packet):
        questions = []
        for index, slot in enumerate(packet["selection"]["question_slots"], start=1):
            required_nodes = list(dict.fromkeys(slot["event_ids"] + slot["anchor_node_ids"]))
            questions.append(
                {
                    "question_id": slot["slot_id"],
                    "status": "generated",
                    "question_text": f"Care este informația verificată pentru slotul {index}?",
                    "answer": {"text": "răspuns", "node_ids": required_nodes[:1], "ordered_node_ids": []},
                    "evidence": {
                        "node_ids": required_nodes,
                        "edge_ids": [],
                        "paths": [],
                        "attribute_paths": [],
                        "chapter_ids": slot["chapter_ids"],
                    },
                    "hop_profile": {
                        "class": "lowhop",
                        "total_edge_hops": 0,
                        "longest_continuous_path_hops": 0,
                        "distinct_evidence_nodes": len(required_nodes),
                        "chapters_involved": len(slot["chapter_ids"]),
                    },
                    "declared_difficulty": 1,
                }
            )
        return {
            "task": "question_generation",
            "category_id": spec.expected_id,
            "graph_version": packet["metadata"]["version"],
            "questions": questions,
        }

    def test_discovers_all_tasks_in_expected_order(self) -> None:
        self.assertEqual(len(self.specs), 24)
        self.assertEqual([spec.task_type for spec in self.specs[:8]], ["questions"] * 8)
        self.assertEqual([spec.task_type for spec in self.specs[8:21]], ["summaries"] * 13)
        self.assertEqual([spec.task_type for spec in self.specs[21:]], ["compositions"] * 3)
        self.assertEqual(self.specs[0].expected_id, "SIMPLE_FACT_LOWHOP")
        self.assertEqual(self.specs[20].expected_id, "CH_13")
        self.assertEqual(self.specs[-1].expected_id, "CONFLICT")

    def test_every_prompt_is_rendered_once_without_placeholder(self) -> None:
        for spec in self.specs:
            prompt, packet = runner.render_prompt(spec)
            self.assertNotIn("{{GRAPH_PACKET}}", prompt)
            self.assertIn(str((packet.get("metadata") or {}).get("packet_id")), prompt)

    def test_reasoning_request_asks_for_internal_validation(self) -> None:
        payload, applied = runner.build_request(
            "qwen/test",
            {
                "id": "qwen/test",
                "supported_parameters": ["reasoning", "temperature"],
                "reasoning": {"supported_efforts": ["none", "medium"]},
            },
            "prompt",
            max_tokens=1000,
            reasoning_effort="medium",
            allow_provider_fallbacks=True,
            provider_order=None,
        )
        self.assertEqual(payload["reasoning"], {"effort": "medium", "exclude": True})
        self.assertEqual(applied["reasoning"], {"effort": "medium", "exclude": True})
        self.assertIn("verifică intern", payload["messages"][0]["content"])

    def test_invalid_question_result_does_not_become_retry_feedback(self) -> None:
        spec = self.specs[1]
        latest = {
            "attempt": 1,
            "status": "invalid",
            "validation_errors": [
                "questions[0].evidence nu acoperă ancorele slotului: ['EV_058']."
            ],
        }
        feedback = runner.build_validator_retry_feedback(spec, latest)
        self.assertIsNone(feedback)

    def test_invalid_summary_result_does_not_become_retry_feedback(self) -> None:
        spec = self.specs[8]
        latest = {
            "attempt": 1,
            "status": "invalid",
            "validation_errors": [
                "coverage.excluded_event_ids nu reproduce exact excluded_event_sequence."
            ],
        }
        feedback = runner.build_validator_retry_feedback(spec, latest)
        self.assertIsNone(feedback)

    def test_manifest_has_hashes_and_token_estimates(self) -> None:
        manifest = runner.build_manifest(self.specs)
        self.assertEqual(manifest["task_count"], 24)
        self.assertTrue(all(item["estimated_prompt_tokens"] > 0 for item in manifest["tasks"]))
        self.assertTrue(all(len(item["rendered_prompt_sha256"]) == 64 for item in manifest["tasks"]))

    def test_multiple_legacy_runs_count_as_one_historical_batch(self) -> None:
        original_runs_dir = runner.RUNS_DIR
        try:
            with tempfile.TemporaryDirectory() as temporary:
                runner.RUNS_DIR = Path(temporary)
                for name in ("run-old-1", "run-old-2"):
                    run_dir = runner.RUNS_DIR / name
                    run_dir.mkdir()
                    runner.save_json(
                        run_dir / "manifest.json",
                        {
                            "tasks": [
                                {"task_type": "questions", "packet_path": "legacy.packet.json"}
                            ]
                        },
                    )
                used, sources, maximum_batch = runner.question_selection_history()
            expected = set()
            for spec in self.specs[:8]:
                expected.update(runner.question_event_ids(runner.read_json(spec.packet_path)))
            self.assertEqual(used, expected)
            self.assertEqual(maximum_batch, 1)
            self.assertEqual(len(sources), 2)
        finally:
            runner.RUNS_DIR = original_runs_dir

    def test_global_question_archive_accumulates_runs_without_duplicate_rebuilds(self) -> None:
        original_runs_dir = runner.RUNS_DIR
        try:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                runner.RUNS_DIR = root / "rulari"
                spec = self.specs[0]
                for batch in (1, 2):
                    run_dir = runner.RUNS_DIR / "model" / f"run-{batch}"
                    attempt_dir = runner.task_dir(run_dir, spec) / "attempts" / "attempt-001"
                    attempt_dir.mkdir(parents=True)
                    questions = [
                        {"question_text": f"Întrebarea {batch}-{index}?"}
                        for index in range(1, 4)
                    ]
                    runner.save_json(
                        attempt_dir / "result.json",
                        {"category_id": spec.expected_id, "questions": questions},
                    )
                    runner.save_json(
                        runner.task_dir(run_dir, spec) / "latest.json",
                        {
                            "status": "succeeded",
                            "validation_passed": batch == 1,
                            "attempt_dir": str(attempt_dir.relative_to(run_dir)),
                        },
                    )
                    runner.save_json(
                        run_dir / "metadata.json",
                        {
                            "run_id": f"run-{batch}",
                            "timestamp_utc": f"2026-08-2{batch}T00:00:00+00:00",
                            "requested_model": "qwen/test",
                            "question_batch_number": batch,
                        },
                    )
                output = root / "toate.txt"
                runner.write_global_questions_archive(output)
                first = output.read_text(encoding="utf-8")
                runner.write_global_questions_archive(output)
                second = output.read_text(encoding="utf-8")
                json_output = root / "toate.json"
                runner.write_global_questions_json(json_output)
                cumulative = json.loads(json_output.read_text(encoding="utf-8"))
            self.assertEqual(first, second)
            self.assertIn("Total întrebări păstrate: 6", first)
            self.assertEqual(first.count("Întrebarea 1-1?"), 1)
            self.assertEqual(first.count("Întrebarea 2-3?"), 1)
            self.assertIn("Lot 2 | run-2", first)
            self.assertEqual(cumulative["question_count"], 6)
            self.assertEqual(cumulative["run_count"], 2)
            self.assertEqual(cumulative["categories"][0]["questions"][0]["source"]["batch_number"], 1)
        finally:
            runner.RUNS_DIR = original_runs_dir

    def test_previous_21_task_manifest_remains_verifiable(self) -> None:
        previous_specs = self.specs[:21]
        manifest = runner.build_manifest(previous_specs)
        runner.verify_manifest_inputs(manifest, previous_specs)

    def test_summary_packets_expose_only_source_grounded_facts(self) -> None:
        for spec in self.specs[8:21]:
            packet = runner.read_json(spec.packet_path)
            self.assertNotIn("nodes", packet)
            self.assertNotIn("edges", packet)
            self.assertNotIn("boundary_context", packet)
            verified_ids = [event["id"] for event in packet["verified_events"]]
            excluded_ids = [event["id"] for event in packet["excluded_events"]]
            self.assertEqual(verified_ids, packet["chapter"]["verified_event_sequence"])
            self.assertEqual(excluded_ids, packet["chapter"]["excluded_event_sequence"])
            self.assertEqual(
                set(verified_ids) | set(excluded_ids),
                set(packet["chapter"]["source_event_sequence"]),
            )
            for event in packet["verified_events"]:
                self.assertEqual(event["provenance"]["status"], "verified_primary")
                self.assertTrue(
                    event["provenance"].get("pdf_page")
                    or event["provenance"].get("source_locator")
                )
                self.assertTrue(event["provenance"]["evidence_quote"])
                self.assertNotIn("participants", event)
                self.assertNotIn("location", event)

    def test_corrected_chapter_boundaries_are_preserved(self) -> None:
        summaries = {
            spec.expected_id: runner.read_json(spec.packet_path)
            for spec in self.specs[8:21]
        }
        facts = {
            chapter_id: {event["id"]: event["fact"] for event in packet["verified_events"]}
            for chapter_id, packet in summaries.items()
        }
        self.assertIn("jumătate din locuri", facts["CH_08"]["EV_076"])
        self.assertIn("tuturor pământurilor", facts["CH_09"]["EV_084"])
        self.assertIn("se căsătorește", facts["CH_10"]["EV_090"])
        self.assertIn("se întoarce", facts["CH_12"]["EV_109"])
        self.assertIn("își revine", facts["CH_13"]["EV_111"])
        self.assertIn("așteptând judecata", facts["CH_13"]["EV_122"])

    def test_question_validator_accepts_three_grounded_questions(self) -> None:
        spec = self.specs[0]
        packet = runner.read_json(spec.packet_path)
        payload = self.valid_simple_payload(spec, packet)
        validation = runner.validate_payload(spec, payload, packet)
        self.assertTrue(validation["valid"], validation["errors"])

    def test_summary_validator_checks_canonical_coverage(self) -> None:
        spec = self.specs[8]
        packet = runner.read_json(spec.packet_path)
        events = packet["chapter"]["verified_event_sequence"]
        excluded = packet["chapter"]["excluded_event_sequence"]
        verified = {event["id"]: event for event in packet["verified_events"]}
        sentences = [str(verified[event_id]["fact"]).rstrip(".") + "." for event_id in events]
        payload = {
            "task": "chapter_summary",
            "chapter_id": spec.expected_id,
            "status": "generated",
            "summary": " ".join(sentences),
            "sentence_evidence": [
                {
                    "sentence_index": index,
                    "sentence_text": sentences[index - 1],
                    "event_ids": [event_id],
                }
                for index, event_id in enumerate(events, start=1)
            ],
            "coverage": {
                "covered_event_ids": events,
                "excluded_event_ids": excluded,
                "event_count_expected": len(events),
                "event_count_covered": len(events),
            },
            "style": {
                "word_count": runner.count_words(" ".join(sentences)),
                "paragraph_count": 1,
            },
        }
        validation = runner.validate_payload(spec, payload, packet)
        self.assertTrue(validation["valid"], validation["errors"])
        payload["coverage"]["covered_event_ids"] = events[:-1]
        self.assertFalse(runner.validate_payload(spec, payload, packet)["valid"])

    def test_summary_validator_rejects_unsupported_intensifier(self) -> None:
        spec = self.specs[8]
        packet = runner.read_json(spec.packet_path)
        event = packet["verified_events"][0]
        sentence = str(event["fact"]).rstrip(".") + " instantaneu."
        payload = {
            "task": "chapter_summary",
            "chapter_id": spec.expected_id,
            "status": "generated",
            "summary": sentence,
            "sentence_evidence": [
                {
                    "sentence_index": 1,
                    "sentence_text": sentence,
                    "event_ids": [event["id"]],
                }
            ],
            "coverage": {
                "covered_event_ids": packet["chapter"]["verified_event_sequence"],
                "excluded_event_ids": packet["chapter"]["excluded_event_sequence"],
                "event_count_expected": len(packet["chapter"]["verified_event_sequence"]),
                "event_count_covered": len(packet["chapter"]["verified_event_sequence"]),
            },
            "style": {"word_count": runner.count_words(sentence), "paragraph_count": 1},
        }
        validation = runner.validate_payload(spec, payload, packet)
        self.assertFalse(validation["valid"])
        self.assertTrue(any("intensificări nesusținute" in error for error in validation["errors"]))

    def test_composition_validator_distinguishes_graph_and_research_brief(self) -> None:
        spec = self.specs[21]
        packet = runner.read_json(spec.packet_path)
        node_id = packet["nodes"][0]["id"]
        brief_ids = [item["brief_id"] for item in packet["researcher_brief"]]
        idea_number = 0
        sections = []
        for section_number in range(1, 5):
            ideas = []
            for local_number in range(1, 3):
                idea_number += 1
                brief_id = brief_ids[idea_number - 1] if idea_number <= len(brief_ids) else None
                ideas.append(
                    {
                        "key_idea": f"Ideea {idea_number}",
                        "explanation": "Explicație susținută.",
                        "basis": ["graph", "researcher_brief"] if brief_id else ["graph"],
                        "node_ids": [node_id],
                        "edge_ids": [],
                        "attribute_paths": [],
                        "brief_ids": [brief_id] if brief_id else [],
                    }
                )
            sections.append(
                {
                    "section_id": f"SECTION_{section_number:02d}",
                    "heading": f"Secțiunea {section_number}",
                    "ideas": ideas,
                }
            )
        payload = {
            "task": "composition_element_schema",
            "element_id": spec.expected_id,
            "element_name": spec.label,
            "status": "generated",
            "central_thesis": "Titlul organizează interpretarea.",
            "schema": sections,
            "bac_synthesis": "O sinteză scurtă, dar validă structural.",
            "memory_formula": ["titlu", "tipologie", "pământ"],
            "validation": {
                "used_node_ids": [node_id],
                "used_edge_ids": [],
                "used_brief_ids": brief_ids,
                "unsupported_claims": [],
            },
        }
        validation = runner.validate_payload(spec, payload, packet)
        self.assertTrue(validation["valid"], validation["errors"])
        payload["schema"][0]["ideas"][0]["brief_ids"] = []
        self.assertFalse(runner.validate_payload(spec, payload, packet)["valid"])

    def test_consolidation_keeps_valid_results_and_counts_usage(self) -> None:
        spec = self.specs[0]
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            attempt_dir = runner.task_dir(run_dir, spec) / "attempts" / "attempt-001"
            attempt_dir.mkdir(parents=True)
            result = {
                "task": "question_generation",
                "category_id": spec.expected_id,
                "questions": [{"question_id": str(i)} for i in range(3)],
            }
            runner.save_json(attempt_dir / "result.json", result)
            metadata = {
                "task_key": spec.key,
                "attempt": 1,
                "status": "succeeded",
                "duration_seconds": 1.5,
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 20,
                    "total_tokens": 120,
                    "cost": 0.01,
                },
            }
            runner.save_json(attempt_dir / "task-metadata.json", metadata)
            runner.save_json(
                runner.task_dir(run_dir, spec) / "latest.json",
                {**metadata, "json_valid": True, "attempt_dir": str(attempt_dir.relative_to(run_dir))},
            )
            summary = runner.write_consolidated_results(run_dir, self.specs)
            self.assertEqual(summary["questions_retained"], 3)
            self.assertEqual(summary["billable_all_attempt_totals"]["total_tokens"], 120)
            self.assertEqual(summary["question_set_cost"]["api_attempts"], 1)
            self.assertEqual(summary["question_set_cost"]["cost_usd"], 0.01)
            self.assertTrue((run_dir / "token-usage.csv").is_file())
            self.assertTrue((run_dir / "questions-cost-report.json").is_file())
            self.assertTrue((run_dir / "summaries-cost-report.json").is_file())
            questions_text = (run_dir / "intrebari-pe-categorii.txt").read_text(
                encoding="utf-8"
            )
            self.assertIn("ULTIMA VARIANTĂ PE CATEGORII", questions_text)
            self.assertIn("3/24", questions_text)
            self.assertEqual(json.loads((run_dir / "questions.all.json").read_text(encoding="utf-8"))["question_count"], 3)

    def test_questions_text_file_marks_invalid_latest_result(self) -> None:
        spec = self.specs[0]
        packet = runner.read_json(spec.packet_path)
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            attempt_dir = runner.task_dir(run_dir, spec) / "attempts" / "attempt-001"
            attempt_dir.mkdir(parents=True)
            result = self.valid_simple_payload(spec, packet)
            runner.save_json(attempt_dir / "result.json", result)
            latest = {
                "task_key": spec.key,
                "attempt": 1,
                "status": "invalid",
                "attempt_dir": str(attempt_dir.relative_to(run_dir)),
            }
            runner.save_json(runner.task_dir(run_dir, spec) / "latest.json", latest)

            path = runner.write_questions_text_file(run_dir, self.specs)
            text = path.read_text(encoding="utf-8")
            self.assertIn("RESPINSĂ DE VALIDATOR, încercarea 1", text)
            self.assertIn(result["questions"][0]["question_text"], text)
            self.assertIn("Întrebări validate: 0/24", text)

    def test_question_cost_report_includes_invalid_attempts_and_retries(self) -> None:
        spec = self.specs[0]
        packet = runner.read_json(spec.packet_path)
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            statuses = ("invalid", "invalid", "succeeded")
            for number, status in enumerate(statuses, start=1):
                attempt_dir = runner.task_dir(run_dir, spec) / "attempts" / f"attempt-{number:03d}"
                attempt_dir.mkdir(parents=True)
                metadata = {
                    "task_key": spec.key,
                    "attempt": number,
                    "status": status,
                    "duration_seconds": 1.0,
                    "usage": {
                        "prompt_tokens": 100,
                        "completion_tokens": 20,
                        "total_tokens": 120,
                        "cost": 0.01,
                        "completion_tokens_details": {"reasoning_tokens": 5},
                    },
                }
                runner.save_json(attempt_dir / "task-metadata.json", metadata)
                if status == "succeeded":
                    runner.save_json(
                        attempt_dir / "result.json",
                        self.valid_simple_payload(spec, packet),
                    )
                    runner.save_json(
                        runner.task_dir(run_dir, spec) / "latest.json",
                        {
                            **metadata,
                            "json_valid": True,
                            "attempt_dir": str(attempt_dir.relative_to(run_dir)),
                        },
                    )

            report_path = runner.write_question_cost_report(run_dir, self.specs)
            data = json.loads(
                (run_dir / "questions-cost-report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(data["api_attempts"], 3)
            self.assertEqual(data["retries"], 2)
            self.assertEqual(data["invalid_attempts"], 2)
            self.assertEqual(data["total_tokens"], 360)
            self.assertEqual(data["reasoning_tokens"], 15)
            self.assertEqual(data["cost_usd"], 0.03)
            self.assertEqual(data["categories"][0]["api_attempts"], 3)
            self.assertIn("0,03000000 USD", report_path.read_text(encoding="utf-8"))

    def test_consolidation_writes_plain_summary_files(self) -> None:
        spec = self.specs[8]
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            attempt_dir = runner.task_dir(run_dir, spec) / "attempts" / "attempt-001"
            attempt_dir.mkdir(parents=True)
            result = {
                "task": "chapter_summary",
                "chapter_id": spec.expected_id,
                "chapter_title": spec.label,
                "summary": "Acesta este textul complet al rezumatului.",
            }
            runner.save_json(attempt_dir / "result.json", result)
            metadata = {
                "task_key": spec.key,
                "attempt": 1,
                "status": "succeeded",
                "duration_seconds": 1.0,
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }
            runner.save_json(attempt_dir / "task-metadata.json", metadata)
            runner.save_json(
                runner.task_dir(run_dir, spec) / "latest.json",
                {**metadata, "json_valid": True, "attempt_dir": str(attempt_dir.relative_to(run_dir))},
            )

            runner.write_consolidated_results(run_dir, self.specs)

            expected = "Acesta este textul complet al rezumatului."
            self.assertEqual(
                (runner.task_dir(run_dir, spec) / "summary.txt").read_text(encoding="utf-8").strip(),
                expected,
            )
            self.assertEqual((attempt_dir / "summary.txt").read_text(encoding="utf-8").strip(), expected)
            aggregate = (run_dir / "summaries.all.txt").read_text(encoding="utf-8")
            self.assertIn(spec.label, aggregate)
            self.assertIn(expected, aggregate)
            validated = (run_dir / "summaries.validated.txt").read_text(encoding="utf-8")
            self.assertIn(spec.label, validated)
            self.assertIn(expected, validated)
            all_chapters = (run_dir / "rezumate-pe-capitole.txt").read_text(
                encoding="utf-8"
            )
            self.assertIn(f"{spec.label} ({spec.expected_id})", all_chapters)
            self.assertIn("Statut: VALIDAT, încercarea 1", all_chapters)
            self.assertIn(expected, all_chapters)

            cost_data = json.loads(
                (run_dir / "summaries-cost-report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(cost_data["api_attempts"], 1)
            self.assertEqual(cost_data["validated_chapters"], 1)
            self.assertEqual(cost_data["total_tokens"], 15)

    def test_summary_cost_report_includes_invalid_attempt_and_retry(self) -> None:
        spec = self.specs[8]
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            for number, status in enumerate(("invalid", "succeeded"), start=1):
                attempt_dir = runner.task_dir(run_dir, spec) / "attempts" / f"attempt-{number:03d}"
                attempt_dir.mkdir(parents=True)
                metadata = {
                    "task_key": spec.key,
                    "attempt": number,
                    "status": status,
                    "duration_seconds": 1.0,
                    "usage": {
                        "prompt_tokens": 100,
                        "completion_tokens": 50,
                        "total_tokens": 150,
                        "cost": 0.02,
                        "completion_tokens_details": {"reasoning_tokens": 20},
                    },
                }
                runner.save_json(attempt_dir / "task-metadata.json", metadata)
                if status == "succeeded":
                    runner.save_json(
                        attempt_dir / "result.json",
                        {
                            "task": "chapter_summary",
                            "chapter_id": spec.expected_id,
                            "summary": "Rezumat valid.",
                        },
                    )
                    runner.save_json(
                        runner.task_dir(run_dir, spec) / "latest.json",
                        {
                            **metadata,
                            "attempt_dir": str(attempt_dir.relative_to(run_dir)),
                        },
                    )

            report_path = runner.write_summary_cost_report(run_dir, self.specs)
            data = json.loads(
                (run_dir / "summaries-cost-report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(data["api_attempts"], 2)
            self.assertEqual(data["retries"], 1)
            self.assertEqual(data["invalid_attempts"], 1)
            self.assertEqual(data["total_tokens"], 300)
            self.assertEqual(data["reasoning_tokens"], 40)
            self.assertEqual(data["cost_usd"], 0.04)
            self.assertIn("0,04000000 USD", report_path.read_text(encoding="utf-8"))

    def test_summaries_text_file_keeps_latest_invalid_piece(self) -> None:
        spec = self.specs[8]
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            attempt_dir = runner.task_dir(run_dir, spec) / "attempts" / "attempt-001"
            attempt_dir.mkdir(parents=True)
            result = {
                "task": "chapter_summary",
                "chapter_id": spec.expected_id,
                "chapter_title": spec.label,
                "summary": "Bucată de rezumat încă nevalidată.",
            }
            runner.save_json(attempt_dir / "result.json", result)
            latest = {
                "task_key": spec.key,
                "attempt": 1,
                "status": "invalid",
                "attempt_dir": str(attempt_dir.relative_to(run_dir)),
            }
            runner.save_json(runner.task_dir(run_dir, spec) / "latest.json", latest)

            path = runner.write_summaries_text_file(run_dir, self.specs)
            text = path.read_text(encoding="utf-8")
            self.assertIn(f"{spec.label} ({spec.expected_id})", text)
            self.assertIn("RESPINS DE VALIDATOR, încercarea 1", text)
            self.assertIn(result["summary"], text)
            self.assertIn("Bucăți de rezumat afișate: 1/13", text)
            all_summaries = (run_dir / "summaries.all.txt").read_text(encoding="utf-8")
            self.assertIn("RESPINS DE VALIDATOR, încercarea 1", all_summaries)
            self.assertIn(result["summary"], all_summaries)

            consolidated = runner.write_consolidated_results(run_dir, self.specs)
            self.assertEqual(consolidated["chapter_summaries_completed"], 1)
            payload = json.loads((run_dir / "summaries.all.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["chapter_count"], 1)
            self.assertEqual(payload["summaries"][0]["summary"], result["summary"])
            self.assertEqual(
                (runner.task_dir(run_dir, spec) / "summary.txt").read_text(encoding="utf-8").strip(),
                result["summary"],
            )
            self.assertEqual(
                (run_dir / "summaries.validated.txt").read_text(encoding="utf-8"),
                "",
            )

    def test_run_one_task_persists_provider_usage_immediately(self) -> None:
        spec = self.specs[0]
        packet = runner.read_json(spec.packet_path)
        payload = self.valid_simple_payload(spec, packet)
        response = {
            "id": "gen-test",
            "model": "qwen/test",
            "provider": "Alibaba",
            "choices": [{"message": {"content": json.dumps(payload, ensure_ascii=False)}}],
            "usage": {
                "prompt_tokens": 1000,
                "completion_tokens": 250,
                "total_tokens": 1250,
                "cost": 0.0125,
            },
        }
        original_api_json = runner.api_json
        runner.api_json = lambda *args, **kwargs: response
        try:
            with tempfile.TemporaryDirectory() as temporary:
                run_dir = Path(temporary)
                latest = runner.run_one_task(
                    spec,
                    run_dir,
                    api_key="not-saved",
                    model_id="qwen/test",
                    model_info={"id": "qwen/test", "supported_parameters": []},
                    max_tokens=1000,
                    timeout=5,
                    reasoning_effort="none",
                    allow_provider_fallbacks=True,
                    provider_order=None,
                )
                self.assertEqual(latest["status"], "succeeded")
                self.assertEqual(latest["usage"]["total_tokens"], 1250)
                attempt = run_dir / latest["attempt_dir"]
                self.assertTrue((attempt / "response.openrouter.json").is_file())
                self.assertTrue((attempt / "validation.json").is_file())
                self.assertNotIn("not-saved", (attempt / "request.json").read_text(encoding="utf-8"))
        finally:
            runner.api_json = original_api_json

    def test_semantically_invalid_questions_are_kept_without_retry_status(self) -> None:
        spec = self.specs[0]
        packet = runner.read_json(spec.packet_path)
        payload = self.valid_simple_payload(spec, packet)
        payload["category_id"] = "CATEGORIE_GRESITA"
        response = {
            "id": "gen-invalid-but-kept",
            "model": "qwen/test",
            "provider": "Alibaba",
            "choices": [{"message": {"content": json.dumps(payload, ensure_ascii=False)}}],
            "usage": {"total_tokens": 10},
        }
        original_api_json = runner.api_json
        runner.api_json = lambda *args, **kwargs: response
        try:
            with tempfile.TemporaryDirectory() as temporary:
                run_dir = Path(temporary)
                latest = runner.run_one_task(
                    spec,
                    run_dir,
                    api_key="not-saved",
                    model_id="qwen/test",
                    model_info={"id": "qwen/test", "supported_parameters": []},
                    max_tokens=1000,
                    timeout=5,
                    reasoning_effort="none",
                    allow_provider_fallbacks=True,
                    provider_order=None,
                )
                self.assertEqual(latest["status"], "succeeded")
                self.assertFalse(latest["validation_passed"])
                self.assertTrue(latest["json_valid"])
                self.assertTrue((run_dir / latest["attempt_dir"] / "result.json").is_file())
        finally:
            runner.api_json = original_api_json

    def test_run_one_task_ignores_retry_feedback_for_questions(self) -> None:
        spec = self.specs[0]
        packet = runner.read_json(spec.packet_path)
        response = {
            "id": "gen-retry-test",
            "model": "qwen/test",
            "provider": "Alibaba",
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            self.valid_simple_payload(spec, packet), ensure_ascii=False
                        )
                    }
                }
            ],
            "usage": {"total_tokens": 10},
        }
        original_api_json = runner.api_json
        runner.api_json = lambda *args, **kwargs: response
        try:
            with tempfile.TemporaryDirectory() as temporary:
                run_dir = Path(temporary)
                latest = runner.run_one_task(
                    spec,
                    run_dir,
                    api_key="not-saved",
                    model_id="qwen/test",
                    model_info={"id": "qwen/test", "supported_parameters": []},
                    max_tokens=1000,
                    timeout=5,
                    reasoning_effort="none",
                    allow_provider_fallbacks=True,
                    provider_order=None,
                    retry_feedback="EROARE TEST: lipsește EV_001",
                    retry_source_attempt=1,
                )
                attempt = run_dir / latest["attempt_dir"]
                prompt = (attempt / "prompt.txt").read_text(encoding="utf-8")
                metadata = json.loads((attempt / "task-metadata.json").read_text(encoding="utf-8"))
                self.assertNotIn("EROARE TEST", prompt)
                self.assertFalse(metadata["validator_feedback_applied"])
                self.assertIsNone(metadata["retry_source_attempt"])
        finally:
            runner.api_json = original_api_json


if __name__ == "__main__":
    unittest.main()
