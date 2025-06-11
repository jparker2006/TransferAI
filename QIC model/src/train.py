"""Train a BERT‐based intent classifier on the V2 QIC dataset.

Usage
-----
python -m src.train  # assumes working directory = project root

Configuration is read from ``src/config.yaml`` and all major hyper-parameters
can be tweaked there. The script outputs the fine-tuned model, tokenizer, and a
pickled ``sklearn.preprocessing.LabelEncoder`` instance into
``<output_dir>/`` (see config).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict

import joblib
import pandas as pd
import torch
import yaml
from datasets import Dataset
from sklearn.metrics import f1_score
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
    EarlyStoppingCallback,
)

from .utils import encode_labels, load_dataset, set_seed, stratified_split

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def compute_metrics(eval_pred):  # type: ignore[override]
    """Compute weighted F1 for validation."""
    logits, labels = eval_pred
    preds = logits.argmax(axis=-1)
    f1 = f1_score(labels, preds, average="weighted", zero_division=0)
    return {"f1": f1}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:  # noqa: D401
    """Parse CLI args (currently only an optional path to the config)."""
    parser = argparse.ArgumentParser(description="Fine-tune BERT for intent classification")
    parser.add_argument(
        "--config",
        type=str,
        default=str(Path(__file__).parent / "config.yaml"),
        help="Path to YAML config file.",
    )
    return parser.parse_args()


def main() -> None:  # noqa: C901
    args = parse_args()
    config_path = Path(args.config)

    if not config_path.exists():
        raise FileNotFoundError(f"Config not found at {config_path}")

    cfg: Dict = yaml.safe_load(config_path.read_text())

    # Seed everything for deterministic training
    set_seed(cfg.get("random_seed", 42))

    output_dir = Path(cfg.get("output_dir", "outputs"))
    output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Data prep
    # ------------------------------------------------------------------
    dataset_path = Path(__file__).parent.parent / "data" / "V2 QIC Data.csv"
    if not dataset_path.exists():
        # Fallback to root location if user hasn't moved the file yet
        dataset_path = Path(__file__).parent.parent / "V2 QIC Data.csv"

    df = load_dataset(dataset_path)

    train_df, val_df = stratified_split(
        df, test_size=cfg.get("test_size", 0.15), seed=cfg.get("random_seed", 42)
    )

    train_df, label_encoder = encode_labels(train_df)
    val_df["label"] = label_encoder.transform(val_df["Intent"].tolist())

    tokenizer = AutoTokenizer.from_pretrained(cfg["model_name"], use_fast=True)

    def tokenize(batch: Dict[str, str]):  # type: ignore[type-arg]
        return tokenizer(
            batch["Query"],
            padding=False,
            truncation=True,
            max_length=cfg["max_length"],
        )

    train_dataset = Dataset.from_pandas(train_df)
    val_dataset = Dataset.from_pandas(val_df)

    train_dataset = train_dataset.map(tokenize, batched=False)
    val_dataset = val_dataset.map(tokenize, batched=False)

    # Remove original text columns (and index if present) for cleaner tensors
    cols_to_drop = [col for col in ["Intent", "Query", "__index_level_0__"] if col in train_dataset.column_names]
    if cols_to_drop:
        train_dataset = train_dataset.remove_columns(cols_to_drop)
    cols_to_drop_val = [col for col in ["Intent", "Query", "__index_level_0__"] if col in val_dataset.column_names]
    if cols_to_drop_val:
        val_dataset = val_dataset.remove_columns(cols_to_drop_val)

    num_labels = len(label_encoder.classes_)

    model = AutoModelForSequenceClassification.from_pretrained(
        cfg["model_name"], num_labels=num_labels
    )

    id2label = {i: l for i, l in enumerate(label_encoder.classes_)}
    label2id = {v: k for k, v in id2label.items()}
    model.config.id2label = id2label
    model.config.label2id = label2id

    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=cfg["num_epochs"],
        per_device_train_batch_size=cfg["batch_size"],
        per_device_eval_batch_size=cfg["batch_size"],
        learning_rate=float(cfg["learning_rate"]),
        weight_decay=float(cfg["weight_decay"]),
        eval_strategy="epoch",
        save_strategy="epoch",
        metric_for_best_model="f1",
        load_best_model_at_end=True,
        logging_dir=str(output_dir / "logs"),
        logging_strategy="epoch",
        warmup_ratio=cfg.get("warmup_ratio", 0.1),
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
        tokenizer=tokenizer,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )

    trainer.train()

    # Save artefacts ---------------------------------------------------
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    joblib.dump(label_encoder, output_dir / "label_encoder.pkl")

    # Persist run hyper-parameters without clobbering the model's own ``config.json``.
    (output_dir / "run_config.json").write_text(json.dumps(cfg, indent=2))
    metrics = trainer.evaluate()
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))

    print("\nTraining complete. Best model saved to:", output_dir.resolve())


if __name__ == "__main__":  # pragma: no cover
    main() 