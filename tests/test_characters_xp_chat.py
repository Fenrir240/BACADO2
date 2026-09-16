import unittest
from unittest.mock import patch
import json

from components.learning_path_ui import (
    _answer_characters_question,
    _has_substantive_characters_answer,
    _parse_characters_teacher_turn,
    _remove_xp_question_from_history,
    _replace_malformed_characters_response,
    _split_assistant_xp_message,
)
from services.ai_service import answer_characters_teacher_turn
from services.openrouter_provider import OpenRouterProvider
from services.progress_service import (
    _normalize_deferred_questions,
    update_characters_ai_progress,
)


class _CapturingProvider:
    def __init__(self):
        self.prompt = ""
        self.chat_generator_used = False

    def generate_text(self, prompt: str) -> str:
        self.prompt = prompt
        return "ok"

    def generate_chat_text(self, prompt: str) -> str:
        self.chat_generator_used = True
        return self.generate_text(prompt)


class _FakeHttpResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class CharactersXpChatTests(unittest.TestCase):
    def test_enigma_prompt_requires_followup_and_uses_three_point_rubric(self):
        provider = _CapturingProvider()
        with patch("services.ai_service.get_ai_provider", return_value=provider):
            answer_characters_teacher_turn(
                work_title="Enigma Otiliei",
                work_author="George Călinescu",
                user_message="De ce este Otilia enigmatică?",
                context_text="Otilia este un personaj central.",
                require_xp_followup=True,
                max_xp_per_answer=3,
            )

        self.assertIn("Dupa FIECARE raspuns", provider.prompt)
        self.assertIn("intre 0 si 3 XP", provider.prompt)
        self.assertIn("complexitatea ideilor", provider.prompt)
        self.assertIn("limbaj precis, matur si expresiv", provider.prompt)
        self.assertIn("3-6 propozitii complete", provider.prompt)
        self.assertTrue(provider.chat_generator_used)

    def test_parser_clamps_xp_and_adds_a_fallback_question(self):
        message, earned_xp, next_question = _parse_characters_teacher_turn(
            """
<message>Otilia este construită prin perspective diferite.</message>
<xp>5</xp>
<next_question>NONE</next_question>
""",
            max_xp=3,
            require_xp_followup=True,
        )

        self.assertEqual(earned_xp, 3)
        self.assertIsNotNone(next_question)
        self.assertTrue(next_question.endswith("(+XP)"))
        self.assertTrue(message.endswith(next_question))

    def test_parser_recovers_question_from_message_when_tag_is_missing(self):
        message, earned_xp, next_question = _parse_characters_teacher_turn(
            "Ai explicat coerent. Cum influențează Felix alegerile Otiliei? (+XP)",
            max_xp=3,
            require_xp_followup=True,
        )

        self.assertEqual(earned_xp, 0)
        self.assertEqual(
            next_question,
            "Cum influențează Felix alegerile Otiliei? (+XP)",
        )
        self.assertEqual(message.count("(+XP)"), 1)

    def test_empty_message_tags_do_not_produce_a_direct_fallback_question(self):
        message, earned_xp, next_question = _parse_characters_teacher_turn(
            """
<message></message>
<xp>0</xp>
<next_question>NONE</next_question>
""",
            max_xp=3,
            require_xp_followup=True,
        )

        self.assertEqual(message, "")
        self.assertEqual(earned_xp, 0)
        self.assertIsNone(next_question)

    def test_enigma_chat_retries_when_model_returns_only_format_tags(self):
        malformed = "<message></message><xp>0</xp><next_question>NONE</next_question>"
        repaired = """
<message>Otilia este atrasă de artă deoarece aceasta îi exprimă firea liberă și sensibilă. De ce arta îi accentuează independența? (+XP)</message>
<xp>0</xp>
<next_question>De ce arta îi accentuează independența? (+XP)</next_question>
"""
        with patch(
            "components.learning_path_ui.answer_characters_teacher_turn",
            side_effect=[malformed, repaired],
        ) as teacher_turn:
            message, earned_xp, next_question = _answer_characters_question(
                {
                    "id": "enigma_otiliei",
                    "title": "Enigma Otiliei",
                    "author": "George Călinescu",
                },
                "De ce este Otilia interesată de artă?",
                "Otilia este sensibilă și atrasă de muzică.",
                "",
                0,
            )

        self.assertEqual(teacher_turn.call_count, 2)
        self.assertFalse(teacher_turn.call_args_list[0].kwargs["format_retry"])
        self.assertTrue(teacher_turn.call_args_list[1].kwargs["format_retry"])
        self.assertIn("Otilia este atrasă de artă", message)
        self.assertEqual(earned_xp, 0)
        self.assertEqual(
            next_question,
            "De ce arta îi accentuează independența? (+XP)",
        )

    def test_truncated_sentence_is_not_accepted_as_a_complete_answer(self):
        self.assertFalse(
            _has_substantive_characters_answer(
                "Întrebarea surprinde una dintre cele mai interesante dinam",
                None,
            )
        )
        self.assertTrue(
            _has_substantive_characters_answer(
                "Întrebarea surprinde una dintre cele mai interesante dinamici.",
                None,
            )
        )

    def test_openrouter_chat_uses_larger_budget_and_low_reasoning(self):
        provider = OpenRouterProvider.__new__(OpenRouterProvider)
        provider.api_key = "test-key"
        provider.model = "test-model"
        provider.timeout = 30
        captured_payload = {}

        def fake_urlopen(request, timeout):
            captured_payload.update(json.loads(request.data.decode("utf-8")))
            return _FakeHttpResponse(
                {
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {"content": "Răspuns complet."},
                        }
                    ]
                }
            )

        with patch("services.openrouter_provider.urllib.request.urlopen", fake_urlopen):
            result = provider.generate_chat_text("prompt")

        self.assertEqual(result, "Răspuns complet.")
        self.assertEqual(captured_payload["max_tokens"], 6000)
        self.assertEqual(captured_payload["reasoning"]["effort"], "low")

    def test_deferred_question_normalization_removes_blanks_and_duplicates(self):
        self.assertEqual(
            _normalize_deferred_questions(["  Întrebarea 1? (+XP) ", "", "Întrebarea 1? (+XP)"]),
            ["Întrebarea 1? (+XP)"],
        )

    def test_progress_update_persists_queue_and_applies_only_new_xp(self):
        progress = {
            "score": 10,
            "characters_ai_xp": 1,
            "characters_ai_xp_applied_to_score": 1,
            "characters_ai_pending_question": "",
            "characters_ai_deferred_questions": [],
            "essay_unlocked": False,
            "current_step": "Personaje",
        }
        with (
            patch(
                "services.progress_service.get_work_progress",
                return_value=progress,
            ),
            patch("services.progress_service._save_progress") as save_progress,
        ):
            update_characters_ai_progress(
                "enigma_otiliei",
                3,
                "Întrebare nouă? (+XP)",
                [" Întrebare veche? (+XP) ", "Întrebare veche? (+XP)"],
            )

        self.assertEqual(progress["score"], 12)
        self.assertEqual(progress["characters_ai_xp"], 3)
        self.assertEqual(
            progress["characters_ai_deferred_questions"],
            ["Întrebare veche? (+XP)"],
        )
        save_progress.assert_called_once_with("enigma_otiliei", progress)

    def test_assistant_question_is_split_from_explanation_for_boxed_rendering(self):
        question = "Cum este caracterizată Otilia de Felix? (+XP)"
        answer_text, xp_question = _split_assistant_xp_message(
            {
                "role": "assistant",
                "content": f"Otilia este prezentată din perspective multiple.\n\n{question}",
                "xp_question": question,
            }
        )

        self.assertEqual(
            answer_text,
            "Otilia este prezentată din perspective multiple.",
        )
        self.assertEqual(xp_question, question)

    def test_ignoring_question_removes_it_from_conversation_history(self):
        question = "De ce rămâne Otilia enigmatică? (+XP)"
        history = [
            {
                "role": "assistant",
                "content": f"Explicația profesorului.\n\n{question}",
                "xp_question": question,
            }
        ]

        _remove_xp_question_from_history(history, question)

        self.assertEqual(history[0]["content"], "Explicația profesorului.")
        self.assertNotIn("xp_question", history[0])

    def test_existing_malformed_response_loses_its_direct_question(self):
        question = "Ce trăsătură a personajului poți justifica? (+XP)"
        history = [
            {
                "role": "assistant",
                "content": f"<message>\n\n{question}",
                "xp_question": question,
            }
        ]

        replaced = _replace_malformed_characters_response(history, question)

        self.assertTrue(replaced)
        self.assertNotIn(question, history[0]["content"])
        self.assertNotIn("<message>", history[0]["content"])
        self.assertNotIn("xp_question", history[0])


if __name__ == "__main__":
    unittest.main()
