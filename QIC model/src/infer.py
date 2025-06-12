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
import json
from typing import Any, Tuple

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

        # Keep the ONNX runtime session to compute logits later
        return cfg, tokenizer, session, label_encoder, None

    # Fallback to PyTorch model
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    return cfg, tokenizer, model, label_encoder, device


def _softmax_np(logits: np.ndarray) -> np.ndarray:
    """Numerically stable softmax for numpy arrays."""
    e = np.exp(logits - logits.max())
    return e / e.sum(axis=-1, keepdims=True)


def predict_intent(
    query: str,
    tokenizer,
    model_or_session: Any,
    label_encoder,
    device,
    cfg: dict,
    *,
    return_probs: bool = False,
) -> Tuple[str, float, np.ndarray] | str:  # type: ignore[override]
    """Return predicted intent, optionally with confidence & full distribution.

    Works transparently for both PyTorch *and* ONNX inference sessions.
    """

    # ------------------------------------------------------------------
    # 1️⃣  Generate logits
    # ------------------------------------------------------------------
    if device is None and hasattr(model_or_session, "run"):
        # ONNX path
        tokens = tokenizer(
            query,
            return_tensors="np",
            padding="max_length",
            truncation=True,
            max_length=128,
        )
        logits = model_or_session.run(None, {k: v for k, v in tokens.items()})[0].squeeze()
        logits_np = logits.astype(np.float32)
    else:
        # PyTorch path
        inputs = tokenizer(
            query,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=128,
        ).to(device)

        with torch.no_grad():
            logits_t = model_or_session(**inputs).logits.squeeze()
        logits_np = logits_t.cpu().numpy()

    # ------------------------------------------------------------------
    # 2️⃣  Temperature scaling (if calibrated)
    # ------------------------------------------------------------------
    temperature = 1.0
    temp_path = Path(cfg.get("output_dir", "outputs")) / "temperature.txt"
    if temp_path.exists():
        try:
            temperature = float(temp_path.read_text().strip()) or 1.0
        except Exception:
            temperature = 1.0

    logits_np /= temperature

    # ------------------------------------------------------------------
    # 3️⃣  Softmax → probabilities
    # ------------------------------------------------------------------
    probs = _softmax_np(logits_np)
    top_idx = int(probs.argmax())
    top_prob = float(probs[top_idx])

    predicted_intent = label_encoder.inverse_transform([top_idx])[0]

    # ------------------------------------------------------------------
    # 4️⃣  Threshold fallback logic
    # ------------------------------------------------------------------
    threshold = float(cfg.get("confidence_threshold", 0.65))
    if top_prob < threshold:
        predicted_intent = cfg.get("fallback_intent", "clarify")

    if return_probs:
        return predicted_intent, top_prob, probs  # type: ignore[return-value]
    return predicted_intent  # type: ignore[return-value]


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
    parser.add_argument(
        "--show-probs",
        action="store_true",
        help="Print JSON with confidence & full probability distribution.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = Path(args.config)

    if not config_path.exists():
        raise FileNotFoundError(config_path)

    cfg, tokenizer, model_obj, label_encoder, device = load_artefacts(config_path)

    if args.show_probs:
        intent, conf, dist = predict_intent(
            args.query,
            tokenizer,
            model_obj,
            label_encoder,
            device,
            cfg,
            return_probs=True,
        )

        distribution = {lbl: float(prob) for lbl, prob in zip(label_encoder.classes_, dist)}
        output = {"intent": intent, "confidence": conf, "distribution": distribution}
        print(json.dumps(output, indent=2))
    else:
        intent = predict_intent(
            args.query, tokenizer, model_obj, label_encoder, device, cfg, return_probs=False
        )
        print(intent)


if __name__ == "__main__":  # pragma: no cover
    main() 