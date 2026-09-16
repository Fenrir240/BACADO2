"""Fine-tuning mT5 pentru modulul QA generativ din RQUGE-Ro."""

from __future__ import annotations

import argparse
import inspect
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rquge_ro.data import (  # noqa: E402
    deterministic_group_split,
    format_qa_input,
    normalized_exact_match,
    read_jsonl,
    token_f1,
    validate_qa_records,
)


DEFAULT_MODEL = "google/mt5-small"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("train_jsonl", type=Path)
    parser.add_argument("--validation-jsonl", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--base-model", default=DEFAULT_MODEL)
    parser.add_argument("--validation-fraction", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--epochs", type=float, default=3.0)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--eval-batch-size", type=int, default=2)
    parser.add_argument("--gradient-accumulation", type=int, default=8)
    parser.add_argument("--max-input-length", type=int, default=512)
    parser.add_argument("--max-answer-length", type=int, default=128)
    parser.add_argument("--fp16", action="store_true")
    parser.add_argument("--bf16", action="store_true")
    parser.add_argument("--gradient-checkpointing", action="store_true")
    parser.add_argument("--use-lora", action="store_true")
    parser.add_argument("--lora-r", type=int, default=8)
    parser.add_argument("--lora-alpha", type=int, default=16)
    parser.add_argument("--resume-from-checkpoint")
    return parser.parse_args()


def _training_arguments(cls: type[Any], args: argparse.Namespace) -> Any:
    parameters = inspect.signature(cls.__init__).parameters
    values: dict[str, Any] = {
        "output_dir": str(args.output_dir),
        "num_train_epochs": args.epochs,
        "learning_rate": args.learning_rate,
        "per_device_train_batch_size": args.batch_size,
        "per_device_eval_batch_size": args.eval_batch_size,
        "gradient_accumulation_steps": args.gradient_accumulation,
        "predict_with_generate": True,
        "generation_max_length": args.max_answer_length,
        "save_strategy": "epoch",
        "logging_steps": 25,
        "load_best_model_at_end": True,
        "metric_for_best_model": "token_f1",
        "greater_is_better": True,
        "save_total_limit": 2,
        "report_to": [],
        "seed": args.seed,
        "fp16": args.fp16,
        "bf16": args.bf16,
        "gradient_checkpointing": args.gradient_checkpointing,
    }
    values["eval_strategy" if "eval_strategy" in parameters else "evaluation_strategy"] = "epoch"
    return cls(**values)


def main() -> None:
    args = parse_args()
    try:
        import numpy as np
        import torch
        from torch.utils.data import Dataset
        from transformers import (
            AutoModelForSeq2SeqLM,
            AutoTokenizer,
            DataCollatorForSeq2Seq,
            Seq2SeqTrainer,
            Seq2SeqTrainingArguments,
        )
    except ImportError as exc:
        raise SystemExit(
            "Lipsesc dependențele ML. Instalează experiment3/rquge_ro/requirements.txt."
        ) from exc

    train_records = read_jsonl(args.train_jsonl)
    validate_qa_records(train_records)
    if args.validation_jsonl:
        validation_records = read_jsonl(args.validation_jsonl)
        validate_qa_records(validation_records)
    else:
        train_records, validation_records = deterministic_group_split(
            train_records, ("context",), args.validation_fraction, args.seed
        )

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, use_fast=False)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.base_model)
    if args.use_lora:
        try:
            from peft import LoraConfig, TaskType, get_peft_model
        except ImportError as exc:
            raise SystemExit("--use-lora necesită pachetul peft.") from exc
        model = get_peft_model(
            model,
            LoraConfig(
                task_type=TaskType.SEQ_2_SEQ_LM,
                r=args.lora_r,
                lora_alpha=args.lora_alpha,
                lora_dropout=0.05,
                target_modules=["q", "v"],
            ),
        )
        model.print_trainable_parameters()
    if args.gradient_checkpointing and hasattr(model, "enable_input_require_grads"):
        model.enable_input_require_grads()
    model.config.use_cache = False

    class QADataset(Dataset):
        def __init__(self, records: list[dict[str, Any]]) -> None:
            self.records = records

        def __len__(self) -> int:
            return len(self.records)

        def __getitem__(self, index: int) -> dict[str, Any]:
            record = self.records[index]
            encoded = tokenizer(
                format_qa_input(record["question"], record["context"]),
                max_length=args.max_input_length,
                truncation=True,
            )
            labels = tokenizer(
                text_target=str(record["answer"]),
                max_length=args.max_answer_length,
                truncation=True,
            )
            encoded["labels"] = labels["input_ids"]
            return encoded

    def compute_metrics(evaluation: Any) -> dict[str, float]:
        predictions = evaluation.predictions
        if isinstance(predictions, tuple):
            predictions = predictions[0]
        labels = np.where(evaluation.label_ids != -100, evaluation.label_ids, tokenizer.pad_token_id)
        decoded_predictions = tokenizer.batch_decode(predictions, skip_special_tokens=True)
        decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)
        return {
            "exact_match": float(
                np.mean(
                    [
                        normalized_exact_match(prediction, reference)
                        for prediction, reference in zip(decoded_predictions, decoded_labels)
                    ]
                )
            ),
            "token_f1": float(
                np.mean(
                    [
                        token_f1(prediction, reference)
                        for prediction, reference in zip(decoded_predictions, decoded_labels)
                    ]
                )
            ),
        }

    training_args = _training_arguments(Seq2SeqTrainingArguments, args)
    trainer_values: dict[str, Any] = {
        "model": model,
        "args": training_args,
        "train_dataset": QADataset(train_records),
        "eval_dataset": QADataset(validation_records),
        "data_collator": DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model),
        "compute_metrics": compute_metrics,
    }
    trainer_parameter = inspect.signature(Seq2SeqTrainer.__init__).parameters
    trainer_values["processing_class" if "processing_class" in trainer_parameter else "tokenizer"] = tokenizer
    trainer = Seq2SeqTrainer(**trainer_values)
    trainer.train(resume_from_checkpoint=args.resume_from_checkpoint)
    trainer.save_model()
    tokenizer.save_pretrained(args.output_dir)
    (args.output_dir / "rquge_ro_training.json").write_text(
        json.dumps(
            {
                "component": "qa",
                "base_model": args.base_model,
                "train_examples": len(train_records),
                "validation_examples": len(validation_records),
                "lora": args.use_lora,
                "seed": args.seed,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
