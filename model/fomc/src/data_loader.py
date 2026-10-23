"""Data loader and stratified partitioner for FOMC hawkish-dovish dataset.

Dataset reference:
    Shah, A., Paturi, S., & Chava, S. (2023). "Trillion Dollar Words:
    A New Financial Dataset, Task & Market Analysis on Federal Reserve Communications",
    ACL 2023. https://aclanthology.org/2023.acl-long.368/

Locked variant:
    dataset/fomc/train/lab-manual-split-combine-train-5768.xlsx (1.939 sentences)
    dataset/fomc/test/lab-manual-split-combine-test-5768.xlsx (495 sentences)

Label taxonomy:
    0 = Dovish
    1 = Hawkish
    2 = Neutral
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence, Tuple

import pandas as pd
from sklearn.model_selection import train_test_split

DEFAULT_FOMC_TRAIN_PATH = Path("dataset/fomc/train/lab-manual-split-combine-train-5768.xlsx")
DEFAULT_FOMC_TEST_PATH = Path("dataset/fomc/test/lab-manual-split-combine-test-5768.xlsx")

LABEL_TO_STANCE: dict[int, str] = {
    0: "dovish",
    1: "hawkish",
    2: "neutral",
}

STANCE_TO_LABEL: dict[str, int] = {v: k for k, v in LABEL_TO_STANCE.items()}

# Dual-target inverse transmission mapping (locked in SCHEMA & adapters.py)
STANCE_TO_TONE: dict[tuple[str, str], str] = {
    ("hawkish", "RATE_UST"): "positive",
    ("hawkish", "SPX"): "negative",
    ("dovish", "RATE_UST"): "negative",
    ("dovish", "SPX"): "positive",
    ("neutral", "RATE_UST"): "neutral",
    ("neutral", "SPX"): "neutral",
}


def sanitize_fomc_df(df: pd.DataFrame) -> pd.DataFrame:
    """Sanitizes text and validates essential columns in FOMC DataFrame.

    Retains numbers, percentages, and financial markers ($ and bps) as they carry
    critical monetary policy signal.
    """
    required_cols = {"sentence", "label"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in FOMC dataset: {missing}")

    clean_df = df.copy()
    clean_df["sentence"] = clean_df["sentence"].fillna("").astype(str).str.strip()
    clean_df = clean_df[clean_df["sentence"].str.len() > 0].copy()

    # Deduplicate sentences (lowercased) following DESIGN.md §3.4
    # (train: 1.984 -> 1.939 unique; test: 496 -> 495 unique)
    clean_df["_dedup_key"] = clean_df["sentence"].str.lower()
    clean_df = clean_df.drop_duplicates(subset=["_dedup_key"], keep="first").drop(columns=["_dedup_key"]).reset_index(drop=True)

    # Ensure label is valid integer
    clean_df["label"] = clean_df["label"].astype(int)
    invalid_labels = set(clean_df["label"].unique()) - {0, 1, 2}
    if invalid_labels:
        raise ValueError(f"Invalid labels found in dataset: {invalid_labels}. Expected {0, 1, 2}")

    # Map stance and tones
    clean_df["stance"] = clean_df["label"].map(LABEL_TO_STANCE)
    clean_df["tone_RATE_UST"] = clean_df["stance"].apply(lambda s: STANCE_TO_TONE[(s, "RATE_UST")])
    clean_df["tone_SPX"] = clean_df["stance"].apply(lambda s: STANCE_TO_TONE[(s, "SPX")])

    return clean_df.reset_index(drop=True)


def load_fomc_train_raw(path: Path | str = DEFAULT_FOMC_TRAIN_PATH) -> pd.DataFrame:
    """Loads and sanitizes raw FOMC training set."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"FOMC train dataset not found at: {p}")
    raw_df = pd.read_excel(p)
    return sanitize_fomc_df(raw_df)


def load_fomc_test_holdout(path: Path | str = DEFAULT_FOMC_TEST_PATH) -> pd.DataFrame:
    """Loads and sanitizes the official 495-sample unseen test holdout set.

    IMPORTANT: This dataset must only be used for final model benchmarking (Phase 5).
    Never tune hyperparameters or calibrate temperature on this set (Anti-Leakage).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"FOMC test dataset not found at: {p}")
    raw_df = pd.read_excel(p)
    return sanitize_fomc_df(raw_df)


def load_fomc_train_val_split(
    path: Path | str = DEFAULT_FOMC_TRAIN_PATH,
    val_ratio: float = 0.10,
    seed: int = 5768,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Loads FOMC train dataset and creates a stratified train/validation split.

    Args:
        path: Path to FOMC train excel file.
        val_ratio: Proportion of train data allocated to validation (default: 0.10 ~ 194 samples).
        seed: Random seed for stratified splitting (default: 5768).

    Returns:
        (df_train, df_val): Stratified DataFrames.
            - df_train (90% ~ 1.745 samples): Used to fit Baseline TF-IDF + Logistic Regression.
            - df_val (10% ~ 194 samples): Used for Baseline regularizer tuning & Temperature Scaling.
    """
    df_all_train = load_fomc_train_raw(path)

    df_train, df_val = train_test_split(
        df_all_train,
        test_size=val_ratio,
        random_state=seed,
        stratify=df_all_train["label"],
    )

    return df_train.reset_index(drop=True), df_val.reset_index(drop=True)


def get_fomc_texts_and_labels(df: pd.DataFrame) -> tuple[list[str], list[int]]:
    """Extracts texts and integer labels from FOMC DataFrame."""
    texts = df["sentence"].tolist()
    labels = df["label"].tolist()
    return texts, labels
