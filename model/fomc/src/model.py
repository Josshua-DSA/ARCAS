"""FOMC Sentiment Model: Baseline TF-IDF + LR and FOMC-RoBERTa wrapper.

Reference:
    Shah, A., Paturi, S., & Chava, S. (2023). "Trillion Dollar Words:
    A New Financial Dataset, Task & Market Analysis on Federal Reserve Communications",
    ACL 2023. Hugging Face checkpoint: gtfintechlab/FOMC-RoBERTa

Model Protocol:
    Implements model.common.protocol.BaseSentimentModel for backend integration.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional, Sequence

import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from backend.src.schema import ArticleSentiment, ModelProbs, Tone
from model.common.protocol import BaseSentimentModel
from model.common.sentiment_config import neutral_band
from model.fomc.src.calibrator import DEFAULT_TEMPERATURE_PATH, TemperatureScaler

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_FOMC_BASELINE_PATH = Path("model/fomc/weights/baseline_fomc.joblib")
DEFAULT_ROBERTA_CHECKPOINT = "gtfintechlab/FOMC-RoBERTa"
FALLBACK_ROBERTA_CHECKPOINT = "tim9510019/FOMC-RoBERTa"


def train_fomc_baseline(
    df_train: pd.DataFrame,
    out_path: Path | str = DEFAULT_FOMC_BASELINE_PATH,
    max_features: int = 5000,
    c_reg: float = 1.0,
    seed: int = 5768,
) -> tuple[TfidfVectorizer, LogisticRegression, Path]:
    """Trains Baseline TF-IDF + Logistic Regression on FOMC train set.

    Label mapping for baseline:
        0 = Dovish (Mapped to negative rate stance)
        1 = Hawkish (Mapped to positive rate stance)
        2 = Neutral (Mapped to neutral rate stance)
    """
    texts = df_train["sentence"].astype(str).tolist()
    labels = df_train["label"].astype(int).tolist()

    vectorizer = TfidfVectorizer(
        max_features=max_features,
        ngram_range=(1, 2),
        sublinear_tf=True,
    )
    X = vectorizer.fit_transform(texts)

    classifier = LogisticRegression(
        C=c_reg,
        max_iter=1000,
        class_weight="balanced",
        random_state=seed,
    )
    classifier.fit(X, labels)

    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"vectorizer": vectorizer, "classifier": classifier}, p)

    return vectorizer, classifier, p


class FOMCRoBERTaSentiment(BaseSentimentModel):
    """Wrapper for pre-trained gtfintechlab/FOMC-RoBERTa sequence classifier.

    Features:
        - Device-agnostic (automatic CPU / CUDA GPU selection).
        - Integrated temperature scaling probability calibration (M6).
        - Full compliance with BaseSentimentModel protocol and Pydantic invariants.
    """

    def __init__(
        self,
        checkpoint: str = DEFAULT_ROBERTA_CHECKPOINT,
        temperature_path: Optional[Path | str] = DEFAULT_TEMPERATURE_PATH,
        device: Optional[str] = None,
        lazy_load: bool = True,
        hf_token: Optional[str] = None,
    ):
        self._checkpoint = checkpoint
        self._model_version = "fomc-roberta-v1.0"
        self._device_str = device
        self._hf_token = hf_token
        self._tokenizer: Any = None
        self._model: Any = None
        self._torch: Any = None

        #: Ambang netral dari `data/sentiment_config.yaml` (RULES.md: tidak
        #: ada magic number). Nilai bawaan identik dengan literal `0.10`.
        self.neutral_band: float = neutral_band()

        # Load temperature scaler if available
        if temperature_path and Path(temperature_path).exists():
            try:
                self.calibrator = TemperatureScaler.load(temperature_path)
                logger.info("Loaded calibrated temperature T=%.4f from %s", self.calibrator.temperature, temperature_path)
            except Exception as exc:
                logger.warning("Could not load temperature from %s: %s. Using T=1.0", temperature_path, exc)
                self.calibrator = TemperatureScaler(temperature=1.0)
        else:
            self.calibrator = TemperatureScaler(temperature=1.0)

        if not lazy_load:
            self._ensure_loaded()

    @property
    def model_name(self) -> str:
        return "fomc_roberta"

    @property
    def model_version(self) -> str:
        return self._model_version

    def _ensure_loaded(self) -> None:
        """Loads Hugging Face tokenizer and model onto target device."""
        if self._model is not None:
            return

        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self._torch = torch

        token = self._hf_token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
        if self._device_str:
            device = torch.device(self._device_str)
        elif torch.cuda.is_available():
            # GPU kecil (<=8 GiB) tidak muat FOMC-RoBERTa (355M) berdampingan
            # dengan FinBERT-EMAS (440 MB bobot + aktivasi). Di rtx 4060 6 GiB
            # ini berujung CUDA OOM yang menjatuhkan seluruh suite. CPU lebih
            # lambat tetapi deterministik; set FOMC_DEVICE=cuda untuk memaksa.
            device = torch.device(os.environ.get("FOMC_DEVICE", "cpu"))
        else:
            device = torch.device("cpu")
        self._device = device
        logger.info("Loading FOMC-RoBERTa from %s onto %s...", self._checkpoint, device)
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(self._checkpoint, token=token)
            self._model = AutoModelForSequenceClassification.from_pretrained(
                self._checkpoint, token=token, use_safetensors=True
            ).to(device)
            self._model.eval()
        except Exception as exc:
            is_access_issue = any(k in str(exc).lower() for k in ["gated repo", "unauthorized", "401", "403", "awaiting a review"])
            if is_access_issue and self._checkpoint != FALLBACK_ROBERTA_CHECKPOINT:
                logger.warning(
                    "Checkpoint primer '%s' sedang dibatasi atau awaiting review. Beralih ke fallback mirror publik: '%s'...",
                    self._checkpoint,
                    FALLBACK_ROBERTA_CHECKPOINT,
                )
                try:
                    self._tokenizer = AutoTokenizer.from_pretrained(FALLBACK_ROBERTA_CHECKPOINT)
                    self._model = AutoModelForSequenceClassification.from_pretrained(
                        FALLBACK_ROBERTA_CHECKPOINT, use_safetensors=True
                    ).to(device)
                    self._model.eval()
                    self._checkpoint = FALLBACK_ROBERTA_CHECKPOINT
                    return
                except Exception as fallback_exc:
                    logger.error("Gagal memuat fallback checkpoint: %s", fallback_exc)

            if is_access_issue:
                raise PermissionError(
                    f"Model '{self._checkpoint}' memerlukan otentikasi Hugging Face (Gated Repo).\n"
                    "Langkah penyelesaian:\n"
                    "1. Buka https://huggingface.co/gtfintechlab/FOMC-RoBERTa dan klik 'Agree and access repository'.\n"
                    "2. Buat User Access Token di https://huggingface.co/settings/tokens.\n"
                    "3. Set environment variable: $env:HF_TOKEN='hf_xxx' (PowerShell) atau simpan di file .env."
                ) from exc
            raise exc

    def predict_raw_logits(self, texts: Sequence[str], batch_size: int = 16) -> np.ndarray:
        """Runs batched inference and returns unnormalized logits tensor of shape (N, 3)."""
        if not texts:
            return np.empty((0, 3), dtype=float)

        self._ensure_loaded()
        torch = self._torch
        assert self._tokenizer is not None
        assert self._model is not None
        assert torch is not None

        all_logits: list[np.ndarray] = []

        for i in range(0, len(texts), batch_size):
            batch = list(texts[i : i + batch_size])
            inputs = self._tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=256,
                return_tensors="pt",
            ).to(self._device)

            with torch.no_grad():
                outputs = self._model(**inputs)
                logits = outputs.logits.detach().cpu().numpy()
                all_logits.append(logits)

        return np.vstack(all_logits)

    def predict_probs(self, texts: Sequence[str]) -> list[ModelProbs]:
        """Returns 3-class calibrated probabilities [p_pos, p_neu, p_neg] summing to 1.0.

        Mapping from official RoBERTa labels to ModelProbs:
            LABEL_1 (Hawkish) -> p_pos (tightening / rates positive)
            LABEL_2 (Neutral) -> p_neu
            LABEL_0 (Dovish)  -> p_neg (easing / rates negative)
        """
        if not texts:
            return []

        raw_logits = self.predict_raw_logits(texts)
        # Apply temperature scaling
        cal_probs = self.calibrator.predict_proba(raw_logits)

        results: list[ModelProbs] = []
        for row in cal_probs:
            p_dovish = float(row[0])   # LABEL_0
            p_hawkish = float(row[1])  # LABEL_1
            p_neutral = float(row[2])  # LABEL_2

            # Re-normalize to guarantee exact 1.0 sum within tolerance
            total = p_hawkish + p_neutral + p_dovish
            if total > 0:
                p_pos = round(p_hawkish / total, 4)
                p_neu = round(p_neutral / total, 4)
                p_neg = round(1.0 - (p_pos + p_neu), 4)
            else:
                p_pos, p_neu, p_neg = 0.3333, 0.3334, 0.3333

            results.append(
                ModelProbs(
                    model=self.model_name,
                    model_version=self.model_version,
                    p_pos=p_pos,
                    p_neu=p_neu,
                    p_neg=p_neg,
                )
            )

        return results

    def score_article(
        self,
        article_id: str,
        text: str,
        translation_used: bool = False,
        translator_version: Optional[str] = None,
    ) -> ArticleSentiment:
        """Scores a single article text and outputs calibrated ArticleSentiment."""
        probs = self.predict_probs([text])
        prob = probs[0]
        score = round(prob.p_pos - prob.p_neg, 4)

        if score > self.neutral_band:
            tone = Tone.POSITIVE
        elif score < -self.neutral_band:
            tone = Tone.NEGATIVE
        else:
            tone = Tone.NEUTRAL

        return ArticleSentiment(
            article_id=article_id,
            tone=tone,
            score=score,
            probs=[prob],
            translation_used=translation_used,
            translator_version=translator_version,
        )
