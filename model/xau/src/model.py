"""FinBERT-EMAS: inference wrapper untuk track XAU (M2) + trainer (M6).

Mengimplementasikan `model.common.protocol.BaseSentimentModel`, sehingga
pipeline memperlakukan model ini sama seperti `FOMCRoBERTaSentiment` dan
`BaselineTfidfSentiment`.

Dua hal yang mudah salah dan sengaja dikunci di sini:

1. **Urutan probabilitas.** Protokol mewajibkan `[p_pos, p_neu, p_neg]`.
   Label latih kita `positive=2, neutral=1, negative=0` (lihat
   `data_loader.TONE_TO_LABEL`). Artinya logits dari model harus DIBALIK
   urutannya sebelum keluar sebagai probabilitas — kalau tidak, model akan
   melaporkan sentimen persis terbalik tanpa satu pun error.

2. **Artefak tidak di-commit.** Bobot (~440 MB) tidak masuk git; `weights/`
   hanya menyimpan metadata kecil (metrik, temperature), dan model dapat
   dilatih ulang lewat `scripts/train_xau_finbert.py`.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional, Sequence

import numpy as np

from backend.src.schema import ArticleSentiment, ModelProbs
from model.common.protocol import BaseSentimentModel
from model.common.sentiment_config import neutral_band

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_WEIGHTS_DIR = ROOT / "model/xau/weights"
DEFAULT_CHECKPOINT_DIR = DEFAULT_WEIGHTS_DIR / "finbert_gold"
DEFAULT_TEMPERATURE_PATH = DEFAULT_WEIGHTS_DIR / "temperature.json"
DEFAULT_METRICS_PATH = DEFAULT_WEIGHTS_DIR / "metrics.json"

#: Checkpoint dasar. `finbert-tone` dilatih pada 10-K/10-Q + analis, dan
#: merupakan titik awal yang dipakai mayoritas pekerjaan sentimen emas.
BASE_CHECKPOINT = "yiyanghkust/finbert-tone"

#: Panjang token. Headline emas di korpus ini pendek (median < 20 token);
#: 96 sudah lapang dan memotong biaya komputasi dibanding 512.
MAX_LENGTH = 96

#: Urutan label latih: 0=negative, 1=neutral, 2=positive.
#: Protokol butuh [pos, neu, neg] → indeks 2, 1, 0.
_PROTOCOL_ORDER = (2, 1, 0)


class FinbertGoldSentiment(BaseSentimentModel):
    """FinBERT yang di-fine-tune pada korpus berita emas Sinha."""

    def __init__(
        self,
        checkpoint_dir: Path | str = DEFAULT_CHECKPOINT_DIR,
        temperature_path: Path | str = DEFAULT_TEMPERATURE_PATH,
        metrics_path: Path | str = DEFAULT_METRICS_PATH,
        device: Optional[str] = None,
        sentiment_config_path: Path | str | None = None,
    ) -> None:
        self.checkpoint_dir = Path(checkpoint_dir)
        self.temperature_path = Path(temperature_path)
        self.metrics_path = Path(metrics_path)
        self._device_pref = device
        self._model: Any = None
        self._tokenizer: Any = None
        self._torch: Any = None
        self.temperature: float = 1.0
        self.metrics: dict[str, Any] = {}
        #: Ambang netral dari `data/sentiment_config.yaml` (RULES.md: tidak
        #: ada magic number). Nilai bawaan identik dengan literal `0.10`
        #: yang sebelumnya ditulis di sini.
        self.neutral_band: float = neutral_band(sentiment_config_path)
        self._load_metadata()

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------
    def _load_metadata(self) -> None:
        if self.temperature_path.exists():
            try:
                payload = json.loads(self.temperature_path.read_text(encoding="utf-8"))
                self.temperature = float(payload.get("temperature", 1.0))
                logger.info("Temperature T=%.4f dari %s", self.temperature, self.temperature_path)
            except (ValueError, OSError) as exc:  # pragma: no cover - jalur rusak
                logger.warning("Gagal baca temperature %s: %s. Pakai T=1.0", self.temperature_path, exc)
                self.temperature = 1.0

        if self.metrics_path.exists():
            try:
                self.metrics = json.loads(self.metrics_path.read_text(encoding="utf-8"))
            except (ValueError, OSError) as exc:  # pragma: no cover
                logger.warning("Gagal baca metrics %s: %s", self.metrics_path, exc)

    # ------------------------------------------------------------------
    # Protokol
    # ------------------------------------------------------------------
    @property
    def model_name(self) -> str:
        return "finbert_gold"

    @property
    def model_version(self) -> str:
        """Versi dari metrics.json bila ada, agar dapat diaudit per-artefak."""
        ver = self.metrics.get("model_version") if self.metrics else None
        return str(ver) if ver else "unversioned"

    @property
    def is_fitted(self) -> bool:
        return self.checkpoint_dir.exists() and any(self.checkpoint_dir.iterdir())

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        if not self.is_fitted:
            raise FileNotFoundError(
                f"Bobot FinBERT-EMAS tidak ada di {self.checkpoint_dir}. "
                "Latih dulu: python -m scripts.train_xau_finbert"
            )

        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self._torch = torch
        device = self._device_pref or ("cuda" if torch.cuda.is_available() else "cpu")
        self._device = device
        self._tokenizer = AutoTokenizer.from_pretrained(str(self.checkpoint_dir))
        model = AutoModelForSequenceClassification.from_pretrained(
            str(self.checkpoint_dir), use_safetensors=True
        )
        self._model = model.to(device).eval()

    def predict_probs(self, texts: Sequence[str]) -> list[ModelProbs]:
        """Kembalikan probabilitas terkalibrasi, urutan `[pos, neu, neg]`."""
        if not texts:
            return []
        self._ensure_loaded()
        torch = self._torch

        enc = self._tokenizer(
            list(texts),
            truncation=True,
            max_length=MAX_LENGTH,
            padding=True,
            return_tensors="pt",
        ).to(self._device)

        with torch.no_grad():
            logits = self._model(**enc).logits
            scaled = logits / max(self.temperature, 1e-6)
            probs = torch.softmax(scaled, dim=-1).cpu().numpy()

        out: list[ModelProbs] = []
        for row in probs:
            ordered = row[list(_PROTOCOL_ORDER)]
            p = ordered / ordered.sum()  # jaga-jaga pembulatan float
            out.append(
                ModelProbs(
                    model=self.model_name,
                    model_version=self.model_version,
                    p_pos=float(p[0]),
                    p_neu=float(p[1]),
                    p_neg=float(p[2]),
                )
            )
        return out

    def predict_logits(self, texts: Sequence[str]) -> np.ndarray:
        """Logits mentah (untuk temperature scaling saat kalibrasi).

        Urutan kolom mengikuti label latih: `[neg, neu, pos]`.
        """
        if not texts:
            return np.zeros((0, 3), dtype=float)
        self._ensure_loaded()
        torch = self._torch
        enc = self._tokenizer(
            list(texts),
            truncation=True,
            max_length=MAX_LENGTH,
            padding=True,
            return_tensors="pt",
        ).to(self._device)
        with torch.no_grad():
            logits = self._model(**enc).logits
        return logits.cpu().numpy()

    def score_article(
        self,
        article_id: str,
        text: str,
        translation_used: bool = False,
        translator_version: Optional[str] = None,
    ) -> ArticleSentiment:
        """Skor satu artikel → ArticleSentiment terkalibrasi.

        Ambang ±0.10 sama dengan `FOMCRoBERTaSentiment` supaya kedua track
        memakai definisi "netral" yang sama; kalau berbeda, fusion akan
        menerima sinyal yang tidak sebanding.
        """
        from backend.src.schema import ArticleSentiment, Tone

        prob = self.predict_probs([text])[0]
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
