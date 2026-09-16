from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RESEARCH_DIR = EXPERIMENT_DIR.parent
sys.path.insert(0, str(EXPERIMENT_DIR))

from text_profile import analyze_text, evaluate_profile  # noqa: E402


GOOD_SUMMARY = (
    "Satul Pripas prinde viaţă într-o zi de duminică, la hora satului, centrul "
    "vieţii sociale unde se dezvăluie clar ierarhiile şi conflictele mocnite. "
    "Hora are loc în curtea văduvei Todosia (soţia lui Maxim Oprea). Jocul este "
    "pătimaş, asudat, un ritm aprig susţinut de lăutarii Briceag, Holbea şi Gâvan, "
    "reprezentând o eliberare a energiilor acumulate peste săptămână. Aici se "
    "cristalizează drama centrală a eroului principal, Ion al Glanetaşului. Deşi "
    "este sărac, el o ignoră ostentativ pe Florica – o fată frumoasă, dar fără "
    "zestre, pe care o iubeşte cu adevărat – şi dansează aproape exclusiv cu Ana, "
    "fata urâţică dar bogată a lui Vasile Baciu. Planul lui Ion este să obţină "
    "pământurile lui Baciu prin căsătoria cu Ana. Totuşi, Vasile Baciu, venit beat "
    "la horă, îl insultă public pe flăcău, numindu-l „tâlhar”, „golan” şi "
    "„sărăntoc”, ameninţându-l că nu i-o va da niciodată pe Ana. Bătrânul îl "
    "preferă ca ginere pe chiaburul George Bulbuc. Acest afront naşte în inima lui "
    "Ion o dorinţă cruntă de răzbunare şi validare. Frustrarea lui Ion explodează "
    "seara, la cârciuma lui Avrum. Aici, Ion găseşte pretextul de a se lega de "
    "George Bulbuc pe tema plăţii lăutarilor. Ion îl loveşte cu brutalitate pe "
    "George cu un par, dovedindu-şi astfel superioritatea fizică, răzbunându-se "
    "indirect pe Baciu şi câştigând respectul celorlalţi flăcăi din sat."
)


class TextProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph_path = RESEARCH_DIR / "graf1" / "knowledge-graph.json"
        cls.manifest = json.loads(
            (EXPERIMENT_DIR / "inputs" / "summary-manifest.json").read_text(
                encoding="utf-8"
            )
        )

    def test_reference_fragment_profile_is_reproducible(self) -> None:
        profile = analyze_text(GOOD_SUMMARY, self.graph_path)
        self.assertEqual(profile["word_count"], 212)
        self.assertEqual(profile["sentence_count"], 12)
        self.assertAlmostEqual(profile["average_sentence_length"], 17.667, places=3)
        self.assertEqual(profile["discourse_connector_count"], 5)
        self.assertAlmostEqual(profile["discourse_connector_ratio"], 5 / 212, places=6)
        self.assertEqual(profile["filler_phrase_count"], 0)
        self.assertEqual(profile["preposition_count"], 29)
        self.assertEqual(profile["character_name_token_count"], 24)

    def test_reference_fragment_passes_wide_style_margins(self) -> None:
        profile = analyze_text(GOOD_SUMMARY, self.graph_path)
        evaluation = evaluate_profile(profile, self.manifest["style_constraints"])
        self.assertTrue(evaluation["all_rules_passed"])
        self.assertEqual(evaluation["compliance"], 1.0)

    def test_filler_heavy_text_is_penalized(self) -> None:
        text = "În continuare, Ion acționează. De asemenea, Ion răspunde. " * 20
        profile = analyze_text(text, self.graph_path)
        evaluation = evaluate_profile(profile, self.manifest["style_constraints"])
        self.assertFalse(evaluation["rules"]["filler_phrases"]["passed"])
        self.assertLess(evaluation["compliance"], 1.0)


if __name__ == "__main__":
    unittest.main()
