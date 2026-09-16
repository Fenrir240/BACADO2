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

import build_essay_builder as essay_builder
from build_essay_builder import _find_reusable_result, _normalize_blueprint


MODEL_ESSAY = """
Introducerea stabilește opera, autorul și curentul literar.
Prima trăsătură dezvoltată este veridicitatea întâmplărilor din operă.
A doua trăsătură dezvoltată este caracterul tipologic al personajelor.
Tema analizată este legătura omului cu pământul.
Prima scenă relevantă este scena cositului din capitolul al doilea.
A doua scenă relevantă este sărutarea pământului din capitolul al nouălea.
În concluzie, opera rămâne un reper al literaturii române.
""".strip()


def raw_blueprint() -> dict:
    return {
        "movement": {"name": "Realism"},
        "introduction": {
            "title": "Introducere",
            "instructions": "Prezintă opera, autorul și curentul.",
            "checklist": ["opera", "autorul", "curentul"],
        },
        "traits": [
            {
                "title": "Veridicitatea întâmplărilor",
                "source_excerpt": "Prima trăsătură dezvoltată este veridicitatea întâmplărilor din operă.",
                "instructions": "Demonstrează veridicitatea.",
                "model_fragment": "Prima trăsătură dezvoltată este veridicitatea întâmplărilor din operă.",
            },
            {
                "title": "Caracterul tipologic al personajelor",
                "source_excerpt": "A doua trăsătură dezvoltată este caracterul tipologic al personajelor.",
                "instructions": "Demonstrează caracterul tipologic.",
                "model_fragment": "A doua trăsătură dezvoltată este caracterul tipologic al personajelor.",
            },
        ],
        "theme": {
            "title": "Legătura omului cu pământul",
            "source_excerpt": "Tema analizată este legătura omului cu pământul.",
            "instructions": "Prezintă tema.",
        },
        "sequences": [
            {
                "title": "Scena cositului",
                "chapter": "capitolul al doilea",
                "source_excerpt": "Prima scenă relevantă este scena cositului din capitolul al doilea.",
                "instructions": "Analizează prima scenă.",
            },
            {
                "title": "Sărutarea pământului",
                "chapter": "capitolul al nouălea",
                "source_excerpt": "A doua scenă relevantă este sărutarea pământului din capitolul al nouălea.",
                "instructions": "Analizează a doua scenă.",
            },
        ],
        "conclusion": {
            "title": "Concluzie",
            "source_excerpt": "În concluzie, opera rămâne un reper al literaturii române.",
            "instructions": "Formulează concluzia.",
        },
    }


class EssayBuilderTests(unittest.TestCase):
    def build(self, raw: dict) -> dict:
        return _normalize_blueprint(
            raw,
            work={"work_id": "test", "title": "Opera", "author": "Autor"},
            graph_path=Path("graph.json"),
            model_essay_path=Path("eseu.md"),
            model_essay=MODEL_ESSAY,
            expected_traits=2,
            generation={"attempts": 1, "retry_on_invalid": False},
        )

    def test_accepts_only_exact_model_essay_traits(self):
        result = self.build(raw_blueprint())
        self.assertTrue(result["validation"]["valid"])
        self.assertTrue(result["strict_trait_policy"]["reject_unlisted_traits"])
        self.assertEqual(
            result["strict_trait_policy"]["accepted_trait_titles"],
            ["Veridicitatea întâmplărilor", "Caracterul tipologic al personajelor"],
        )

    def test_rejects_trait_without_model_essay_evidence(self):
        raw = raw_blueprint()
        raw["traits"][1]["title"] = "Perspectiva narativă"
        raw["traits"][1]["source_excerpt"] = "Naratorul este omniscient."
        result = self.build(raw)
        self.assertFalse(result["validation"]["valid"])
        self.assertTrue(
            any("Fragmentul-sursă" in error for error in result["validation"]["errors"])
        )

    def test_rejects_invented_trait_title_even_with_real_excerpt(self):
        raw = raw_blueprint()
        raw["traits"][1]["title"] = "Perspectiva narativă"
        result = self.build(raw)
        self.assertFalse(result["validation"]["valid"])
        self.assertFalse(result["validation"]["trait_titles_verified"])
        self.assertTrue(
            any("Denumirea trăsăturii" in error for error in result["validation"]["errors"])
        )

    def test_repairs_near_exact_conclusion_without_relaxing_trait_policy(self):
        raw = raw_blueprint()
        raw["conclusion"]["source_excerpt"] = (
            "În concluzie, opera rămâne un reper al literatură române."
        )
        result = self.build(raw)
        self.assertTrue(result["validation"]["valid"])
        conclusion = next(
            section for section in result["sections"] if section["id"] == "concluzie"
        )
        self.assertEqual(
            conclusion["source_excerpt"],
            "În concluzie, opera rămâne un reper al literaturii române.",
        )
        self.assertEqual(len(result["validation"]["local_source_repairs"]), 1)

    def test_finds_existing_qwen_result_for_identical_packet(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            project = Path(temporary_directory)
            run = project / "runs" / "run-001"
            run.mkdir(parents=True)
            packet = {"task": "build_essay_ui_blueprint", "work": {"work_id": "test"}}
            (run / "packet.json").write_text(json.dumps(packet), encoding="utf-8")
            (run / "result.json").write_text(json.dumps(raw_blueprint()), encoding="utf-8")
            self.assertEqual(_find_reusable_result(project, packet), run / "result.json")

    def test_offline_pipeline_publishes_complete_ui_artifact(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            graph_path = root / "knowledge-graph.json"
            essay_path = root / "eseu-model.md"
            result_path = root / "qwen-result.json"
            graph_path.write_text(
                json.dumps(
                    {
                        "metadata": {"work": "Opera Test", "author": "Autor Test"},
                        "nodes": [
                            {"id": "work", "type": "Work", "label": "Opera Test"},
                            {"id": "author", "type": "Author", "label": "Autor Test"},
                        ],
                        "edges": [],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            essay_path.write_text(MODEL_ESSAY, encoding="utf-8")
            result_path.write_text(
                json.dumps(raw_blueprint(), ensure_ascii=False), encoding="utf-8"
            )

            with mock.patch.object(essay_builder, "ROOT_DIR", root):
                blueprint, output_path = essay_builder.generate_essay_blueprint(
                    graph_path,
                    essay_path,
                    input_result=result_path,
                )

            self.assertTrue(blueprint["validation"]["valid"])
            self.assertTrue(output_path.is_file())
            self.assertTrue(output_path.with_name("manifest.json").is_file())
            self.assertTrue(output_path.with_name("eseu-model.md").is_file())
            published = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(published["pipeline"], "construieste-eseu")
            self.assertEqual(len(published["sections"]), 10)
            self.assertEqual(
                published["strict_trait_policy"]["accepted_trait_titles"],
                ["Veridicitatea întâmplărilor", "Caracterul tipologic al personajelor"],
            )
            self.assertEqual(
                Path(published["source"]["model_essay"]),
                output_path.with_name("eseu-model.md"),
            )


if __name__ == "__main__":
    unittest.main()
