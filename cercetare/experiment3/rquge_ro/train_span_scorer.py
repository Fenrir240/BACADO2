"""Antrenează regresorul 1–5 al RQUGE-Ro pe evaluări umane românești."""

from __future__ import annotations

import argparse
import inspect
import json
import math
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rquge_ro.data import (  # noqa: E402
    deterministic_group_split,
    format_span_input,
    read_jsonl,
    validate_rating_records,
)


DEFAULT_MODEL = "FacebookAI/xlm-roberta-base"
SPECIAL_TOKENS = ["<q>", "<r>", "<c>"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ratings_jsonl", type=Path)
    parser.add_argument("--validation-jsonl", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--base-model", default=DEFAULT_MODEL)
    parser.add_argument("--validation-fraction", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--epochs", type=float, default=4.0)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--eval-batch-size", type=int, default=4)
    parser.add_argument("--gradient-accumulation", type=int, default=4)
    parser.add_argument("--max-input-length", type=int, default=512)
    parser.add_argument("--fp16", action="store_true")
    parser.add_argument("--bf16", action="store_true")
    parser.add_argument("--gradient-checkpointing", action="store_true")
    parser.add_argument("--use-lora", action="store_true")
    parser.add_argument("--lora-r", type=int, default=8)
    parser.add_argument("--lora-alpha", type=int, default=16)
    parser.add_argument("--resume-from-checkpoint")
    return parser.parse_args()


def _rank(values: Any) -> Any:
    import numpy as np

    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    start = 0
    while start < len(values):
        end = start
        while end + 1 < len(values) and values[order[end + 1]] == values[order[start]]:
            end += 1
        ranks[order[start : end + 1]] = (start + end) / 2.0 + 1.0
        start = end + 1
    return ranks


def correlations(predictions: Any, labels: Any) -> dict[str, float]:
    import numpy as np

    predictions = np.asarray(predictions, dtype=float).reshape(-1)
    labels = np.asarray(labels, dtype=float).reshape(-1)
    error = predictions - labels

    def correlation(left: Any, right: Any) -> float:
        if len(left) < 2 or np.std(left) == 0 or np.std(right) == 0:
            return 0.0
        return float(np.corrcoef(left, right)[0, 1])

    return {
        "mae": float(np.mean(np.abs(error))),
        "rmse": float(math.sqrt(float(np.mean(error**2)))),
        "pearson": correlation(predictions, labels),
        "spearman": correlation(_rank(predictions), _rank(labels)),
    }


def main() -> None:
    args = parse_args()
    try:
        import torch
        from torch.utils.data import Dataset
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            DataCollatorWithPadding,
            Trainer,
            TrainingArguments,
        )
    except ImportError as exc:
        raise SystemExit(
            "Lipsesc dependențele ML. Instalează experiment3/rquge_ro/requirements.txt."
        ) from exc

    records = read_jsonl(args.ratings_jsonl)
    validate_rating_records(records)
    if args.validation_jsonl:
        validation_records = read_jsonl(args.validation_jsonl)
        validate_rating_records(validation_records)
        train_records = records
    else:
        train_records, validation_records = deterministic_group_split(
            records, ("question", "context"), args.validation_fraction, args.seed
        )

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, use_fast=True)
    tokenizer.add_special_tokens({"additional_special_tokens": SPECIAL_TOKENS})
    model = AutoModelForSequenceClassification.from_pretrained(
        args.base_model,
        num_labels=1,
        problem_type="regression",
    )
    model.resize_token_embeddings(len(tokenizer))
    if args.use_lora:
        try:
            from peft import LoraConfig, TaskType, get_peft_model
        except ImportError as exc:
            raise SystemExit("--use-lora necesită pachetul peft.") from exc
        target_modules = (
            ["q_lin", "v_lin"]
            if getattr(model.config, "model_type", "") == "distilbert"
            else ["query", "value"]
        )
        model = get_peft_model(
            model,
            LoraConfig(
                task_type=TaskType.SEQ_CLS,
                r=args.lora_r,
                lora_alpha=args.lora_alpha,
                lora_dropout=0.05,
                target_modules=target_modules,
                modules_to_save=["classifier"],
            ),
        )
        model.print_trainable_parameters()
    if args.gradient_checkpointing and hasattr(model, "enable_input_require_grads"):
        model.enable_input_require_grads()

    class RatingDataset(Dataset):
        def __init__(self, values: list[dict[str, Any]]) -> None:
            self.values = values

        def __len__(self) -> int:
            return len(self.values)

        def __getitem__(self, index: int) -> dict[str, Any]:
            record = self.values[index]
            encoded = tokenizer(
                format_span_input(
                    record["question"],
                    record["gold_answer"],
                    record["predicted_answer"],
                    record["context"],
                ),
                max_length=args.max_input_length,
                truncation=True,
            )
            encoded["labels"] = float(record["score"])
            return encoded

    def compute_metrics(evaluation: Any) -> dict[str, float]:
        predictions = evaluation.predictions
        if isinstance(predictions, tuple):
            predictions = predictions[0]
        return correlations(predictions, evaluation.label_ids)

    parameters = inspect.signature(TrainingArguments.__init__).parameters
    values: dict[str, Any] = {
        "output_dir": str(args.output_dir),
        "num_train_epochs": args.epochs,
        "learning_rate": args.learning_rate,
        "per_device_train_batch_size": args.batch_size,
        "per_device_eval_batch_size": args.eval_batch_size,
        "gradient_accumulation_steps": args.gradient_accumulation,
        "save_strategy": "epoch",
        "logging_steps": 25,
        "load_best_model_at_end": True,
        "metric_for_best_model": "spearman",
        "greater_is_better": True,
        "save_total_limit": 2,
        "report_to": [],
        "seed": args.seed,
        "fp16": args.fp16,
        "bf16": args.bf16,
        "gradient_checkpointing": args.gradient_checkpointing,
    }
    values["eval_strategy" if "eval_strategy" in parameters else "evaluation_strategy"] = "epoch"
    training_args = TrainingArguments(**values)
    trainer_values: dict[str, Any] = {
        "model": model,
        "args": training_args,
        "train_dataset": RatingDataset(train_records),
        "eval_dataset": RatingDataset(validation_records),
        "data_collator": DataCollatorWithPadding(tokenizer=tokenizer),
        "compute_metrics": compute_metrics,
    }
    trainer_parameters = inspect.signature(Trainer.__init__).parameters
    trainer_values["processing_class" if "processing_class" in trainer_parameters else "tokenizer"] = tokenizer
    trainer = Trainer(**trainer_values)
    trainer.train(resume_from_checkpoint=args.resume_from_checkpoint)
    trainer.save_model()
    tokenizer.save_pretrained(args.output_dir)
    (args.output_dir / "rquge_ro_training.json").write_text(
        json.dumps(
            {
                "component": "span_scorer",
                "base_model": args.base_model,
                "train_examples": len(train_records),
                "validation_examples": len(validation_records),
                "lora": args.use_lora,
                "seed": args.seed,
                "warning": "Valid doar după corelare pe un test românesc ținut separat.",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
