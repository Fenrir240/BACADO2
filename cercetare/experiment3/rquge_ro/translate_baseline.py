"""Traduce setul de scorare română→engleză pentru baseline-ul RQUGE original."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rquge_ro.data import read_jsonl, write_jsonl  # noqa: E402


DEFAULT_MODEL = "Helsinki-NLP/opus-mt-roa-en"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_jsonl", type=Path)
    parser.add_argument("output_jsonl", type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--max-input-length", type=int, default=512)
    parser.add_argument("--batch-size", type=int, default=8)
    return parser.parse_args()


def chunk_text(text: str, tokenizer: Any, max_length: int) -> list[str]:
    """Taie conservator la granițe de cuvinte, fără a pierde text."""

    words = text.split()
    chunks: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join([*current, word])
        length = len(tokenizer(candidate, add_special_tokens=True, truncation=False)["input_ids"])
        if current and length > max_length:
            chunks.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        chunks.append(" ".join(current))
    return chunks or [""]


def main() -> None:
    args = parse_args()
    try:
        import torch
        from transformers import MarianMTModel, MarianTokenizer
    except ImportError as exc:
        raise SystemExit(
            "Lipsesc dependențele ML. Instalează experiment3/rquge_ro/requirements.txt."
        ) from exc
    device_name = args.device
    if device_name == "auto":
        device_name = "cuda" if torch.cuda.is_available() else "cpu"
    device = torch.device(device_name)
    tokenizer = MarianTokenizer.from_pretrained(args.model)
    model = MarianMTModel.from_pretrained(args.model).to(device).eval()

    def translate(value: str) -> str:
        chunks = chunk_text(value, tokenizer, args.max_input_length)
        translated: list[str] = []
        for start in range(0, len(chunks), args.batch_size):
            batch = tokenizer(
                chunks[start : start + args.batch_size],
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=args.max_input_length,
            )
            batch = {key: tensor.to(device) for key, tensor in batch.items()}
            with torch.inference_mode():
                generated = model.generate(**batch, max_new_tokens=args.max_input_length)
            translated.extend(tokenizer.batch_decode(generated, skip_special_tokens=True))
        return " ".join(translated).strip()

    output: list[dict[str, Any]] = []
    for record in read_jsonl(args.input_jsonl):
        translated_record = dict(record)
        translated_record["source_language"] = "ro"
        translated_record["target_language"] = "en"
        translated_record["translation_model"] = args.model
        for field in ("question", "context", "gold_answer", "answer"):
            if field in record and str(record[field]).strip():
                translated_record[f"source_{field}"] = record[field]
                translated_record[field] = translate(str(record[field]))
        output.append(translated_record)
    write_jsonl(args.output_jsonl, output)
    print(f"Am tradus {len(output)} înregistrări în {args.output_jsonl}.")


if __name__ == "__main__":
    main()
