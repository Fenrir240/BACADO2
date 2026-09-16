import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class ProgressDisplayTests(unittest.TestCase):
    def test_opera_page_displays_persisted_progress_without_work_specific_override(self):
        source = (ROOT / "pages" / "opera_page.py").read_text(encoding="utf-8")

        self.assertIn("progress = get_work_progress(work_id)", source)
        self.assertIn("render_progress_panel(work_id, progress)", source)
        self.assertNotIn('if work_id == "enigma_otiliei"', source)
        self.assertNotIn('"score": 70', source)

    def test_essay_page_is_not_blocked_by_progress_score(self):
        source = (ROOT / "components" / "essay_ui.py").read_text(encoding="utf-8")

        self.assertIn('initialize_essay_state(work["id"])', source)
        self.assertNotIn('if not progress["essay_unlocked"]', source)
        self.assertNotIn("Eseul este blocat momentan", source)
        self.assertNotIn("minimum 70/100", source)


if __name__ == "__main__":
    unittest.main()
