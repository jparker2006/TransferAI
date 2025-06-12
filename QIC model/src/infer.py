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
import numpy as np

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

    # ------------------------------------------------------------------
    # Prefer the best checkpoint (highest eval F1) if Trainer artifacts exist
    # ------------------------------------------------------------------
    import json

    ckpt_state_files = list(output_dir.glob("checkpoint-*/trainer_state.json"))
    best_dir: Path | None = None
    if ckpt_state_files:
        try:
            # Any trainer_state.json contains the key we need
            with ckpt_state_files[0].open() as f:
                trainer_state = json.load(f)
            best_rel = trainer_state.get("best_model_checkpoint")
            if best_rel:
                best_dir = (output_dir / Path(best_rel).name).resolve()
                if not best_dir.exists():
                    best_dir = None
        except Exception:
            best_dir = None

    model_dir = best_dir if best_dir is not None else output_dir

    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    label_encoder = joblib.load(output_dir / "label_encoder.pkl")

    onnx_path = model_dir / "onnx" / "model.onnx"
    if onnx_path.exists():
        import onnxruntime as ort

        session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])

        def onnx_predict(query: str) -> str:  # noqa: D401
            tokens = tokenizer(
                query,
                return_tensors="np",
                padding="max_length",
                truncation=True,
                max_length=128,
            )
            # ort requires numpy arrays
            inputs = {k: v for k, v in tokens.items()}
            logits = session.run(None, inputs)[0]
            pred_id = int(np.argmax(logits, axis=-1))
            return label_encoder.inverse_transform([pred_id])[0]

        return cfg, tokenizer, onnx_predict, label_encoder, None

    # Fallback to PyTorch model
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    return cfg, tokenizer, model, label_encoder, device


def predict_intent(query: str, tokenizer, model_or_fn, label_encoder, device):  # type: ignore[valid-type]
    """Device-aware prediction that supports ONNX or HF model."""
    # If we received a callable (ONNX path), delegate directly
    if callable(model_or_fn) and device is None:
        return model_or_fn(query)

    # Else use PyTorch model
    inputs = tokenizer(
        query,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=128,
    ).to(device)

    with torch.no_grad():
        logits = model_or_fn(**inputs).logits
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

    _, tokenizer, model_pt_or_fn, label_encoder, device = load_artefacts(config_path)

    intent = predict_intent(args.query, tokenizer, model_pt_or_fn, label_encoder, device)
    print(intent)


if __name__ == "__main__":  # pragma: no cover
    main() 