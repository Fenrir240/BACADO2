import unittest
from unittest import mock

from services.annotation_service import is_quote_annotation
from services.essay_quote_service import (
    ensure_quotes_present,
    quote_instructions,
    quotes_for_essay_section,
)


class EssayQuoteTests(unittest.TestCase):
    def test_recognizes_new_and_legacy_quote_annotations(self):
        self.assertTrue(
            is_quote_annotation(
                {"type": "underline", "color": "#2563eb", "purpose": "quote"}
            )
        )
        self.assertTrue(
            is_quote_annotation({"type": "underline", "color": "#8b5cf6"})
        )
        self.assertFalse(
            is_quote_annotation({"type": "underline", "color": "#2563eb"})
        )

    @mock.patch("services.essay_quote_service.get_scene_quotes")
    @mock.patch("services.essay_quote_service.load_relevant_sequences")
    def test_maps_generated_sequence_id_to_essay_section(
        self, load_sequences, get_quotes
    ):
        load_sequences.return_value = [
            {
                "id": "secventa_1_imprumutul",
                "title": "Împrumutul forțat",
            },
            {
                "id": "secventa_2_paste",
                "title": "Duminica de Paște",
            },
        ]
        get_quotes.return_value = ["Mi-ai luat liniștea sufletului."]
        sections = [
            {"id": "introducere", "kind": "introduction"},
            {"id": "secventa_1", "kind": "sequence"},
            {"id": "secventa_2", "kind": "sequence"},
        ]

        quotes = quotes_for_essay_section("moara_cu_noroc", sections[1], sections)

        self.assertEqual(quotes[0]["sequence_id"], "secventa_1_imprumutul")
        self.assertEqual(quotes[0]["text"], "Mi-ai luat liniștea sufletului.")
        get_quotes.assert_called_once_with(
            "moara_cu_noroc", "secventa_1_imprumutul"
        )

    def test_prompt_and_fallback_keep_selected_quote_verbatim(self):
        quotes = [
            {
                "sequence_id": "secventa_1",
                "sequence_title": "Secvența întâi",
                "text": "Fragment ales de elev",
            }
        ]
        self.assertIn("Fragment ales de elev", quote_instructions(quotes))
        result = ensure_quotes_present("Comentariu literar.", quotes)
        self.assertIn("„Fragment ales de elev”", result)
        self.assertEqual(
            ensure_quotes_present(result, quotes).count("Fragment ales de elev"), 1
        )

    @mock.patch("services.essay_quote_service.get_scene_quotes")
    @mock.patch("services.essay_quote_service.load_relevant_sequences")
    def test_keeps_legacy_ion_sequences_compatible(
        self, load_sequences, get_quotes
    ):
        load_sequences.side_effect = FileNotFoundError
        get_quotes.return_value = ["Cu o privire setoasă, Ion cuprinse tot locul."]
        sections = [
            {"id": "scena_cositul"},
            {"id": "scena_sarutarea"},
        ]

        quotes = quotes_for_essay_section("ion", sections[0], sections)

        self.assertEqual(quotes[0]["sequence_id"], "cositul")
        get_quotes.assert_called_once_with("ion", "cositul")


if __name__ == "__main__":
    unittest.main()
