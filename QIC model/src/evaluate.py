"""Batch inference & evaluation for the Query Intent Classifier (QIC).

This script loads the fine-tuned model (as specified in ``src/config.yaml``) and
runs predictions over a CSV file that contains a ``Query`` column. If an
``Intent`` ground-truth column is also present, weighted-F1 and a full
classification report are printed.

Example
-------
python -m src.evaluate QIC_inference_test.csv --output results.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sklearn.metrics import classification_report, f1_score
from tqdm import tqdm

from .infer import load_artefacts, predict_intent


def parse_args() -> argparse.Namespace:  # noqa: D401
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Evaluate QIC model on a test CSV")
    parser.add_argument("csv_path", type=str, help="Path to CSV with a 'Query' column")
    parser.add_argument(
        "--config",
        type=str,
        default=str(Path(__file__).parent / "config.yaml"),
        help="YAML config used during training (so we can locate outputs/).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="predictions.csv",
        help="Where to save CSV with added Predicted_Intent column.",
    )
    return parser.parse_args()


def run_inference(df: pd.DataFrame, cfg_path: Path) -> pd.DataFrame:
    """Add a *Predicted_Intent* column to *df* by running the model."""
    cfg, tokenizer, model, label_encoder, device = load_artefacts(cfg_path)

    preds: list[str] = []
    for query in tqdm(df["Query"].tolist(), desc="Predicting", unit="q"):
        intent = predict_intent(query, tokenizer, model, label_encoder, device, cfg)
        preds.append(intent)

    df = df.copy()
    df["Predicted_Intent"] = preds
    return df


def main() -> None:  # pragma: no cover
    args = parse_args()
    csv_path = Path(args.csv_path)
    cfg_path = Path(args.config)

    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    df = pd.read_csv(csv_path)
    if "Query" not in df.columns:
        raise ValueError("Input CSV must contain a 'Query' column.")

    df_with_preds = run_inference(df, cfg_path)

    # Save predictions CSV
    out_path = Path(args.output)
    df_with_preds.to_csv(out_path, index=False)
    print(f"\nPredictions saved to {out_path.resolve()}")

    # If ground-truth labels exist, compute metrics
    if "Intent" in df_with_preds.columns:
        y_true = df_with_preds["Intent"].tolist()
        y_pred = df_with_preds["Predicted_Intent"].tolist()
        weighted_f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0)
        print(f"\nWeighted F1: {weighted_f1:.4f}\n")
        print(classification_report(y_true, y_pred, zero_division=0))


if __name__ == "__main__":
    main() 