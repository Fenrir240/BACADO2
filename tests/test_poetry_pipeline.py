from __future__ import annotations

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_complete_work
from services.composition_service import (
    infer_composition_element_ids,
    load_composition_schemas,
    selected_elements_for_essay,
)
from services.essay_builder_service import load_essay_blueprint
from services.exercise_bank_service import (
    EXERCISE_FILES,
    load_prebuilt_exercises,
    quick_testing_available,
)
from services.work_artifact_validation_service import validate_poetry_artifacts


WORK_ID = "floare_albastra"
GRAPH_PATH = ROOT / "grafuri" / WORK_ID / "knowledge-graph.json"
ESSAY_PATH = ROOT / "modele_eseuri" / "floare_albastra.md"


class PoetryArtifactContractTests(unittest.TestCase):
    def setUp(self) -> None:
        load_prebuilt_exercises.cache_clear()

    def test_current_floare_bundle_is_publishable(self) -> None:
        graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
        report = validate_poetry_artifacts(ROOT, WORK_ID, graph)
        self.assertTrue(report["valid"])

    def test_all_quick_testing_banks_match_ui_contracts(self) -> None:
        self.assertTrue(quick_testing_available(WORK_ID))
        for exercise_type in EXERCISE_FILES:
            with self.subTest(exercise_type=exercise_type):
                self.assertGreater(len(load_prebuilt_exercises(WORK_ID, exercise_type)), 0)

        chronology = load_prebuilt_exercises(WORK_ID, "Ordine cronologică")
        self.assertTrue(
            all(item.get("event_id") for exercise in chronology for item in exercise["items"])
        )

    def test_qwen_composition_schema_is_visible_to_ui(self) -> None:
        elements = load_composition_schemas(WORK_ID)["elements"]
        self.assertEqual(len(elements), 2)
        for element in elements:
            self.assertTrue(element["central_idea"])
            self.assertTrue(element["essay_paragraph"])
            self.assertTrue(element["memory_formula"])
            self.assertTrue(all(branch["key_idea"] for branch in element["branches"]))
            self.assertTrue(all(branch["explanation"] for branch in element["branches"]))

    def test_essay_composition_ids_resolve_to_real_sections(self) -> None:
        self.assertEqual(
            infer_composition_element_ids(ESSAY_PATH.read_text(encoding="utf-8")),
            ["title", "semantic_figures"],
        )
        blueprint = load_essay_blueprint(WORK_ID)
        sections = {section["id"] for section in blueprint["sections"]}
        elements = selected_elements_for_essay(WORK_ID, {})
        self.assertEqual([item["id"] for item in elements], ["title", "semantic_figures"])
        self.assertTrue({item["section_id"] for item in elements}.issubset(sections))
        self.assertTrue(all(section.get("instructions") for section in blueprint["sections"]))


class PoetryPipelineControlTests(unittest.TestCase):
    def test_dry_run_does_not_call_generator_or_register_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            with (
                mock.patch.object(build_complete_work, "ROOT_DIR", temp_root),
                mock.patch.object(build_complete_work, "register_work") as register_work,
                mock.patch.dict(
                    sys.modules,
                    {
                        "creeaza_opera_poezie": types.SimpleNamespace(
                            generate_poetic_work_complete=mock.Mock(
                                side_effect=AssertionError("Generatorul nu trebuie apelat în dry-run")
                            )
                        )
                    },
                ),
            ):
                manifest, manifest_path = build_complete_work.build_complete_work(
                    GRAPH_PATH,
                    model_essay_path=ESSAY_PATH,
                    dry_run=True,
                )
            self.assertEqual(manifest["status"], "planned")
            self.assertEqual(manifest["executed_qwen_calls"], 0)
            self.assertTrue(manifest_path.is_file())
            register_work.assert_not_called()
            self.assertFalse((temp_root / "data" / "works.json").exists())

    def test_invalid_staging_bundle_is_never_registered(self) -> None:
        def produce_invalid_bundle(*args, output_root: Path, **kwargs):
            target = output_root / "data" / "generated_works" / WORK_ID / "intelegere-opera"
            target.mkdir(parents=True, exist_ok=True)
            (target / "toata-opera.json").write_text("{}", encoding="utf-8")
            return {"usage": {"api_calls": 0}, "usage_by_section": {}}

        fake_generator = types.SimpleNamespace(generate_poetic_work_complete=produce_invalid_bundle)
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            with (
                mock.patch.object(build_complete_work, "ROOT_DIR", temp_root),
                mock.patch.object(build_complete_work, "register_work") as register_work,
                mock.patch.dict(sys.modules, {"creeaza_opera_poezie": fake_generator}),
            ):
                with self.assertRaises(ValueError):
                    build_complete_work.build_complete_work(
                        GRAPH_PATH,
                        model_essay_path=ESSAY_PATH,
                    )
            register_work.assert_not_called()
            self.assertFalse((temp_root / "data" / "works.json").exists())

    def test_valid_existing_bundle_is_adopted_without_api_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            fake_generator = types.SimpleNamespace(
                generate_poetic_work_complete=mock.Mock(
                    side_effect=AssertionError("Un bundle valid existent nu trebuie regenerat")
                )
            )
            with (
                mock.patch.object(build_complete_work, "ROOT_DIR", temp_root),
                mock.patch(
                    "services.work_artifact_validation_service.validate_poetry_artifacts",
                    return_value={"schema_version": 1, "work_id": WORK_ID, "valid": True, "errors": []},
                ),
                mock.patch.object(
                    build_complete_work,
                    "register_work",
                    return_value=({"id": WORK_ID, "type": "poezie"}, False),
                ),
                mock.patch.dict(sys.modules, {"creeaza_opera_poezie": fake_generator}),
            ):
                manifest, manifest_path = build_complete_work.build_complete_work(
                    GRAPH_PATH,
                    model_essay_path=ESSAY_PATH,
                )
            self.assertEqual(manifest["status"], "ready")
            self.assertTrue(manifest["adopted_existing_artifacts"])
            self.assertEqual(manifest["executed_qwen_calls"], 0)
            self.assertTrue(manifest_path.is_file())
            fake_generator.generate_poetic_work_complete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
