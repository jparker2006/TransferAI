"""Utility helpers for the Query Intent Classifier (QIC).

This module centralises common tasks such as:
1. Loading the CSV dataset as a ``pandas.DataFrame``.
2. Creating a stratified train/validation split.
3. Encoding the string intent labels into integer ids.
4. Seeding all relevant RNGs to guarantee reproducibility.

Author: TransferAI
"""
from __future__ import annotations

import random
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from collections import Counter
import re


def load_dataset(csv_path: str | Path) -> pd.DataFrame:
    """Load the raw CSV dataset.

    Parameters
    ----------
    csv_path: str | Path
        Location of the ``V2 QIC Data.csv`` file.

    Returns
    -------
    pd.DataFrame
        A dataframe with *at least* the columns ``["Intent", "Query"]``.
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset not found at {csv_path.resolve()}")

    df = pd.read_csv(csv_path)

    # Basic sanity-check for expected columns
    expected_cols = {"Intent", "Query"}
    if not expected_cols.issubset(df.columns):
        raise ValueError(
            f"Dataset missing required columns {expected_cols}. Found: {set(df.columns)}"
        )

    # Drop duplicates & reset index for cleaner downstream processing
    df = df.drop_duplicates().reset_index(drop=True)

    # ------------------------------------------------------------------
    # Oversample minority classes with lightweight augmentation
    # ------------------------------------------------------------------
    MIN_SAMPLES = 50
    augmented_rows = []
    counts = df["Intent"].value_counts().to_dict()

    for intent, cnt in counts.items():
        deficit = max(0, MIN_SAMPLES - cnt)
        if deficit == 0:
            continue
        subset = df[df["Intent"] == intent]
        for _ in range(deficit):
            row = subset.sample(1, replace=True, random_state=random.randint(0, 1_000_000)).iloc[0]
            augmented_rows.append({
                "Intent": intent,
                "Query": augment_text(row["Query"]),
                "_aug": True,
            })

    df["_aug"] = False
    if augmented_rows:
        df = pd.concat([df, pd.DataFrame(augmented_rows)], ignore_index=True)

    return df


def stratified_split(
    df: pd.DataFrame, *, test_size: float = 0.15, seed: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split ``df`` into train and validation sets while preserving label ratios.

    Parameters
    ----------
    df: pd.DataFrame
        Full dataset.
    test_size: float, default ``0.15``
        Fraction of rows to allocate to the validation set.
    seed: int, default ``42``
        RNG seed for deterministic splits.

    Returns
    -------
    Tuple[pd.DataFrame, pd.DataFrame]
        ``train_df``, ``val_df`` (in that order).
    """
    # Use only *original* rows for validation to avoid leakage
    orig_df = df[df["_aug"] == False]  # noqa: E712

    train_orig, val_df = train_test_split(
        orig_df,
        test_size=test_size,
        stratify=orig_df["Intent"],
        random_state=seed,
        shuffle=True,
    )

    # Training set gets originals + all augmented rows
    train_df = pd.concat([train_orig, df[df["_aug"] == True]], ignore_index=True)  # noqa: E712

    return train_df.reset_index(drop=True), val_df.reset_index(drop=True)


def encode_labels(df: pd.DataFrame) -> Tuple[pd.DataFrame, LabelEncoder]:
    """Encode the ``Intent`` column to ``label`` integers.

    The new integer IDs are stored under a fresh ``label`` column which is
    *explicitly* named to match what 🤗 Transformers expects.

    Parameters
    ----------
    df: pd.DataFrame
        Input dataframe containing an ``Intent`` column.

    Returns
    -------
    Tuple[pd.DataFrame, LabelEncoder]
        DataFrame with a new ``label`` column *and* the fitted encoder so that
        the mapping can later be persisted & reused during inference.
    """
    encoder = LabelEncoder()
    df = df.copy()
    df["label"] = encoder.fit_transform(df["Intent"].tolist())
    return df, encoder


def set_seed(seed: int) -> None:
    """Seed Python, NumPy & PyTorch for full reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

    # The below settings make CuDNN deterministic but *may* impact performance.
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def compute_class_weights(labels: list[int]) -> torch.Tensor:
    """Return weights = 1/sqrt(freq) normalised to mean=1."""
    counts = Counter(labels)
    weights = {c: 1.0 / (count ** 0.5) for c, count in counts.items()}
    w = torch.tensor([weights[i] for i in range(len(counts))], dtype=torch.float)
    return w / w.mean()


# ---------------------------------------------------------------------------
#  Text augmentation helpers (very light-weight, CPU-only)
# ---------------------------------------------------------------------------

_SYNONYM_MAP = {
    "transfer": "move",
    "course": "class",
    "gpa": "gradepoint",
    "units": "credits",
    "professor": "instructor",
    "requirement": "req",
}


def augment_text(text: str) -> str:  # noqa: D401
    """Return a weakly-augmented variant of *text* (synonym swap + tiny typo).

    Designed to increase minority-class support without complex NLP libs.
    """
    words = text.split()
    # 1) synonym replacement (30 % chance per word if in map)
    for i, word in enumerate(words):
        key = word.lower()
        if key in _SYNONYM_MAP and random.random() < 0.3:
            # Preserve capitalisation roughly
            repl = _SYNONYM_MAP[key]
            words[i] = repl.capitalize() if word[0].isupper() else repl

    # 2) Optional trivial typo (swap final char)
    if len(words) > 0 and random.random() < 0.1:
        j = random.randrange(len(words))
        words[j] = re.sub(r"(.)(?!.*.)", r"\\1x", words[j])
    return " ".join(words)


# ---------------------------------------------------------------------------
#  Focal-loss (multiclass) implementation
# ---------------------------------------------------------------------------


class FocalLoss(torch.nn.Module):
    """Weighted focal loss for multiclass classification.

    Parameters
    ----------
    gamma: float
        Focusing parameter γ; 2.0 is standard.
    weight: torch.Tensor | None
        Class-wise weights (same semantics as for CrossEntropyLoss).
    """

    def __init__(self, gamma: float = 2.0, *, weight: torch.Tensor | None = None):
        super().__init__()
        self.gamma = gamma
        self.register_buffer("weight", weight if weight is not None else None)

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:  # noqa: D401
        import torch.nn.functional as F

        log_p = F.log_softmax(logits, dim=-1)
        p = torch.exp(log_p)
        focal_factor = (1 - p) ** self.gamma
        loss = F.nll_loss(focal_factor * log_p, targets, weight=self.weight, reduction="mean")
        return loss


def oversample_intents(df: pd.DataFrame, intents: list[str], factor: int = 3) -> pd.DataFrame:
    """Return a new DataFrame where rows matching *intents* are duplicated *factor* times.

    The original distribution of all other intents is preserved. The returned
    dataframe is shuffled implicitly by ``pd.concat`` so that boosted samples
    are not grouped together.

    Parameters
    ----------
    df: pd.DataFrame
        Input dataframe **before** label encoding.
    intents: list[str]
        List of intent names to up-sample.
    factor: int, default ``3``
        Total replication factor (``factor=3`` → each selected row appears
        three times in the returned dataframe).

    Returns
    -------
    pd.DataFrame
        A new dataframe containing the over-sampled training examples.
    """
    if factor < 1:
        raise ValueError("factor must be >= 1")

    # Rows to keep as-is
    keep = df[~df["Intent"].isin(intents)]

    if factor == 1:
        return keep.copy().reset_index(drop=True)

    # Rows to boost (duplicated to reach the desired factor)
    boost = df[df["Intent"].isin(intents)]
    if boost.empty:
        # No matching intent rows – nothing to oversample.
        return df.reset_index(drop=True)

    boosted_parts = [boost] * factor  # original + (factor-1) clones
    df_boosted = pd.concat([keep, *boosted_parts], ignore_index=True)
    return df_boosted 