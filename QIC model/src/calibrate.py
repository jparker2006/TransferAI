from __future__ import annotations

"""Learn a temperature scalar T on the validation set to calibrate model logits.

The script is invoked automatically from ``src.train`` after a successful run
(if ``calibration.enabled`` is true in *config.yaml*). It computes the optimal
T that minimises negative-log-likelihood (NLL) on the *validation* subset and
stores the value as plain text in ``<output_dir>/temperature.txt``.
"""

import sys
from pathlib import Path

import joblib
import torch
import torch.nn.functional as F
import yaml
from datasets import Dataset
from torch.optim import LBFGS
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# Local imports (relative) – safe because script is executed via ``python -m``
from .utils import load_dataset, stratified_split, encode_labels  # type: ignore


def _nll_criterion(logits: torch.Tensor, labels: torch.Tensor, temperature: torch.Tensor) -> torch.Tensor:  # noqa: D401
    """Negative log-likelihood with temperature scaling."""
    return F.cross_entropy(logits / temperature, labels)


def _learn_temperature(model, logits: torch.Tensor, labels: torch.Tensor) -> float:  # noqa: D401
    """Optimise temperature parameter using LBFGS (as in Guo et al., 2017)."""
    device = logits.device
    temperature = torch.ones(1, device=device) * 1.0
    temperature.requires_grad_()

    optimizer = LBFGS([temperature], lr=0.01, max_iter=50)

    def _eval():  # noqa: D401
        loss = _nll_criterion(logits, labels, temperature)
        optimizer.zero_grad()
        loss.backward()
        return loss

    optimizer.step(_eval)
    return float(temperature.detach().cpu().item())


def _collect_logits_and_labels(model, val_ds: Dataset, device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:  # noqa: D401
    """Forward pass over validation set to collect logits and labels."""
    model.to(device)
    model.eval()

    logits_list: list[torch.Tensor] = []
    label_list: list[int] = []

    for item in val_ds:
        # item contains keys: input_ids, attention_mask, label
        inputs = {
            "input_ids": torch.tensor(item["input_ids"]).unsqueeze(0).to(device),
            "attention_mask": torch.tensor(item["attention_mask"]).unsqueeze(0).to(device),
        }
        with torch.no_grad():
            logits = model(**inputs).logits.squeeze(0)
        logits_list.append(logits)
        label_list.append(int(item["label"]))

    logits_tensor = torch.stack(logits_list)  # (N, C)
    labels_tensor = torch.tensor(label_list, device=device)
    return logits_tensor, labels_tensor


def main() -> None:  # noqa: D401
    cfg_path = Path(__file__).parent / "config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())

    if not cfg.get("calibration", {}).get("enabled", False):
        print("[Calibration] Disabled – skipping.")
        return

    output_dir = Path(cfg.get("output_dir", "outputs"))
    if not output_dir.exists():
        print(f"[Calibration] Output dir {output_dir} not found – aborting.")
        return

    # ------------------------------------------------------------------
    # Load model & tokenizer saved by training script
    # ------------------------------------------------------------------
    model = AutoModelForSequenceClassification.from_pretrained(output_dir)
    tokenizer = AutoTokenizer.from_pretrained(output_dir)

    # ------------------------------------------------------------------
    # Recreate the validation split exactly as during training
    # ------------------------------------------------------------------
    dataset_csv = Path("data") / "V2 QIC Data.csv"
    if not dataset_csv.exists():
        dataset_csv = Path("V2 QIC Data.csv")
    df = load_dataset(dataset_csv)

    _, val_df = stratified_split(df, test_size=cfg.get("test_size", 0.15), seed=cfg.get("random_seed", 42))
    val_df, _ = encode_labels(val_df)

    # Tokenise
    def _tok(batch):  # noqa: D401
        return tokenizer(
            batch["Query"],
            truncation=True,
            padding="max_length",
            max_length=cfg.get("max_length", 128),
        )

    val_ds = Dataset.from_pandas(val_df)
    val_ds = val_ds.map(_tok, batched=False)
    # Keep only required columns
    keep_cols = {"input_ids", "attention_mask", "label"}
    drop_cols = [c for c in val_ds.column_names if c not in keep_cols]
    if drop_cols:
        val_ds = val_ds.remove_columns(drop_cols)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logits, labels = _collect_logits_and_labels(model, val_ds, device)

    temperature = _learn_temperature(model, logits, labels)

    (output_dir / "temperature.txt").write_text(f"{temperature:.6f}\n")
    print(f"[Calibration] Learned temperature: {temperature:.4f}")


if __name__ == "__main__":  # pragma: no cover
    main() 