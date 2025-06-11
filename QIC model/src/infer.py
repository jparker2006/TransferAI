"""Command-line inference for the Query Intent Classifier.

Example
-------
$ python src/infer.py "how many units do I need to transfer?"
→ unit_requirements_transfer
"""
from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import torch
import yaml
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def load_artefacts(config_path: Path):
    cfg = yaml.safe_load(config_path.read_text())
    output_dir = Path(cfg.get("output_dir", "outputs"))

    if not output_dir.exists():
        raise FileNotFoundError(
            f"Output directory {output_dir} does not exist. Have you trained the model?"
        )

    tokenizer = AutoTokenizer.from_pretrained(output_dir)
    model = AutoModelForSequenceClassification.from_pretrained(output_dir)
    label_encoder = joblib.load(output_dir / "label_encoder.pkl")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    return cfg, tokenizer, model, label_encoder, device


def predict_intent(query: str, tokenizer, model, label_encoder, device):  # type: ignore[valid-type]
    inputs = tokenizer(
        query,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=128,
    ).to(device)

    with torch.no_grad():
        logits = model(**inputs).logits
        pred_id = logits.argmax(dim=-1).cpu().item()
    intent = label_encoder.inverse_transform([pred_id])[0]
    return intent


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():  # noqa: D401
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Run inference with the QIC model")
    parser.add_argument("query", type=str, help="Input query string")
    parser.add_argument(
        "--config",
        type=str,
        default=str(Path(__file__).parent / "config.yaml"),
        help="Path to the YAML config used during training.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = Path(args.config)

    if not config_path.exists():
        raise FileNotFoundError(config_path)

    _, tokenizer, model, label_encoder, device = load_artefacts(config_path)

    intent = predict_intent(args.query, tokenizer, model, label_encoder, device)
    print(intent)


if __name__ == "__main__":  # pragma: no cover
    main() 