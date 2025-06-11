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
    train_df, val_df = train_test_split(
        df,
        test_size=test_size,
        stratify=df["Intent"],
        random_state=seed,
        shuffle=True,
    )
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