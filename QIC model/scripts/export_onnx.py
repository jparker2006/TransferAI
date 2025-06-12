"""Export a fine-tuned QIC model to quantized ONNX format.

Usage
-----
python scripts/export_onnx.py [--config src/config.yaml]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml
from transformers import AutoModelForSequenceClassification


def parse_args():
    parser = argparse.ArgumentParser(description="Export QIC model to ONNX")
    parser.add_argument(
        "--config",
        default=str(Path(__file__).parent.parent / "src" / "config.yaml"),
        help="Path to YAML config used during training.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    cfg_path = Path(args.config)
    cfg = yaml.safe_load(cfg_path.read_text())
    output_dir = Path(cfg["output_dir"])
    onnx_dir = output_dir / "onnx"

    if not output_dir.exists():
        raise SystemExit(f"Trained model not found in {output_dir}. Train first.")

    try:
        from optimum.onnxruntime import ORTOptimizer
    except ImportError as e:
        raise SystemExit("optimum not installed. Install with pip install optimum[onnxruntime]") from e

    print("Loading fine-tuned model from", output_dir)
    model = AutoModelForSequenceClassification.from_pretrained(output_dir)
    print("Exporting quantized ONNX to", onnx_dir)
    ORTOptimizer.from_pretrained(model).export(onnx_dir, fp16=False, quantize=True)
    print("Done ✔️")


if __name__ == "__main__":
    main() 