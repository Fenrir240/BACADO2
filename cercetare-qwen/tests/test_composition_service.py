import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services import composition_service as service


class CompositionServiceTests(unittest.TestCase):
    def test_infers_only_elements_explicitly_developed_in_model_essay(self):
        essay = """
În ceea ce privește elementele de compoziție, acestea susțin viziunea operei.

Un prim element compozițional este titlul operei și semnificația sa.

Un alt element compozițional este relația dintre incipit și final.
"""
        self.assertEqual(
            service.infer_composition_element_ids(essay),
            ["title", "incipit_final"],
        )

    def test_empty_progress_uses_blueprint_defaults_for_future_works(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            composition_path = root / "elemente.json"
            blueprint_path = root / "eseu.json"
            composition_path.write_text(
                json.dumps(
                    {
                        "elements": [
                            {"id": "incipit_final", "title": "Relația incipit–final"},
                            {"id": "conflict", "title": "Conflictul"},
                            {"id": "title", "title": "Titlul"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            blueprint_path.write_text(
                json.dumps(
                    {"default_composition_element_ids": ["title", "incipit_final"]}
                ),
                encoding="utf-8",
            )
            with (
                mock.patch.object(service, "composition_path", return_value=composition_path),
                mock.patch.object(service, "essay_blueprint_path", return_value=blueprint_path),
            ):
                elements = service.selected_elements_for_essay("opera_noua", {})
            self.assertEqual([item["id"] for item in elements], ["title", "incipit_final"])

    def test_manual_selection_has_priority_and_is_completed_safely(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            composition_path = root / "elemente.json"
            blueprint_path = root / "eseu.json"
            composition_path.write_text(
                json.dumps(
                    {
                        "elements": [
                            {"id": "incipit_final"},
                            {"id": "conflict"},
                            {"id": "title"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            blueprint_path.write_text(
                json.dumps(
                    {"default_composition_element_ids": ["title", "incipit_final"]}
                ),
                encoding="utf-8",
            )
            with (
                mock.patch.object(service, "composition_path", return_value=composition_path),
                mock.patch.object(service, "essay_blueprint_path", return_value=blueprint_path),
            ):
                elements = service.selected_elements_for_essay(
                    "opera_noua", {"composition_selected_elements": ["conflict"]}
                )
            self.assertEqual([item["id"] for item in elements], ["conflict", "title"])


if __name__ == "__main__":
    unittest.main()
