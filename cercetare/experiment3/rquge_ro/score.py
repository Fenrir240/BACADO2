"""Calculează scoruri RQUGE-Ro cu două checkpointuri locale/Hugging Face."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rquge_ro.data import (  # noqa: E402
    clamp_score,
    format_qa_input,
    format_span_input,
    normalized_exact_match,
    read_jsonl,
    summary_statistics,
    token_f1,
    write_jsonl,
)


class RQuGERoScorer:
    """Implementare inferență; modelele sunt încărcate o singură dată."""

    def __init__(
        self,
        qa_model: str,
        span_model: str,
        *,
        device: str = "auto",
        qa_adapter: bool = False,
        span_adapter: bool = False,
        max_input_length: int = 512,
        max_answer_length: int = 128,
    ) -> None:
        try:
            import torch
            from transformers import (
                AutoModelForSeq2SeqLM,
                AutoModelForSequenceClassification,
                AutoTokenizer,
            )
        except ImportError as exc:
            raise RuntimeError(
                "Lipsesc dependențele ML. Instalează experiment3/rquge_ro/requirements.txt."
            ) from exc

        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.torch = torch
        self.device = torch.device(device)
        self.qa_model_name = qa_model
        self.span_model_name = span_model
        self.max_input_length = max_input_length
        self.max_answer_length = max_answer_length

        self.qa_tokenizer = AutoTokenizer.from_pretrained(qa_model, use_fast=False)
        self.span_tokenizer = AutoTokenizer.from_pretrained(span_model, use_fast=True)
        if qa_adapter:
            try:
                from peft import AutoPeftModelForSeq2SeqLM
            except ImportError as exc:
                raise RuntimeError("Checkpointul QA LoRA necesită pachetul peft.") from exc
            self.qa_model = AutoPeftModelForSeq2SeqLM.from_pretrained(qa_model)
        else:
            self.qa_model = AutoModelForSeq2SeqLM.from_pretrained(qa_model)
        if span_adapter:
            try:
                from peft import AutoPeftModelForSequenceClassification
            except ImportError as exc:
                raise RuntimeError("Checkpointul span LoRA necesită pachetul peft.") from exc
            self.span_model = AutoPeftModelForSequenceClassification.from_pretrained(span_model)
        else:
            self.span_model = AutoModelForSequenceClassification.from_pretrained(span_model)
        self.qa_model.to(self.device).eval()
        self.span_model.to(self.device).eval()

    def _move(self, encoded: dict[str, Any]) -> dict[str, Any]:
        return {key: value.to(self.device) for key, value in encoded.items()}

    def predict_answer(self, question: str, context: str) -> str:
        encoded = self._move(
            self.qa_tokenizer(
                format_qa_input(question, context),
                return_tensors="pt",
                max_length=self.max_input_length,
                truncation=True,
            )
        )
        with self.torch.inference_mode():
            generated = self.qa_model.generate(
                **encoded,
                max_new_tokens=self.max_answer_length,
                num_beams=1,
            )
        return self.qa_tokenizer.decode(generated[0], skip_special_tokens=True).strip()

    def score(
        self,
        question: str,
        context: str,
        gold_answer: str,
    ) -> dict[str, Any]:
        predicted_answer = self.predict_answer(question, context)
        encoded = self._move(
            self.span_tokenizer(
                format_span_input(question, gold_answer, predicted_answer, context),
                return_tensors="pt",
                max_length=self.max_input_length,
                truncation=True,
            )
        )
        with self.torch.inference_mode():
            raw_score = float(self.span_model(**encoded).logits.reshape(-1)[0].item())
        return {
            "predicted_answer": predicted_answer,
            "raw_score": raw_score,
            "score": clamp_score(raw_score),
            "answer_exact_match": normalized_exact_match(predicted_answer, gold_answer),
            "answer_token_f1": token_f1(predicted_answer, gold_answer),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_jsonl", type=Path)
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path)
    parser.add_argument("--qa-model", required=True)
    parser.add_argument("--span-model", required=True)
    parser.add_argument("--qa-adapter", action="store_true")
    parser.add_argument("--span-adapter", action="store_true")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--max-input-length", type=int, default=512)
    parser.add_argument("--max-answer-length", type=int, default=128)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = read_jsonl(args.input_jsonl)
    scorer = RQuGERoScorer(
        args.qa_model,
        args.span_model,
        device=args.device,
        qa_adapter=args.qa_adapter,
        span_adapter=args.span_adapter,
        max_input_length=args.max_input_length,
        max_answer_length=args.max_answer_length,
    )
    results: list[dict[str, Any]] = []
    for index, record in enumerate(records, 1):
        for field in ("question", "context", "gold_answer"):
            if not str(record.get(field, "")).strip():
                raise ValueError(f"Înregistrarea {index} nu conține {field!r}.")
        result = scorer.score(record["question"], record["context"], record["gold_answer"])
        results.append(
            {
                "id": record.get("id", index),
                "question": record["question"],
                "gold_answer": record["gold_answer"],
                **result,
            }
        )
    write_jsonl(args.output_jsonl, results)
    summary = {
        "metric": "RQUGE-Ro-KG",
        "status": "experimental_unvalidated",
        "qa_model": args.qa_model,
        "span_model": args.span_model,
        "scores": summary_statistics([float(result["score"]) for result in results]),
        "answer_token_f1": summary_statistics(
            [float(result["answer_token_f1"]) for result in results]
        ),
    }
    summary_path = args.summary_json or args.output_jsonl.with_suffix(".summary.json")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
