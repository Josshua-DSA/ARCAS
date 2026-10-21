"""M1 Baseline Model: TF-IDF + Logistic Regression.

Kontrak penting (perbaikan AUDIT K-4): model yang belum dilatih TIDAK boleh
diam-diam mengembalikan distribusi prior. Itu membuat test hijau padahal
prediksi tidak berarti apa-apa. Semua prediksi melempar `ModelNotFittedError`
sampai `fit()` atau `load()` berhasil dipanggil.
"""

from pathlib import Path
from typing import Any, Optional, Sequence

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression

    SKLEARN_AVAILABLE = True
except ImportError:  # pragma: no cover - lingkungan tanpa sklearn
    TfidfVectorizer = None
    LogisticRegression = None
    SKLEARN_AVAILABLE = False

from backend.src.schema import ArticleSentiment, ModelProbs, Tone
from model.common.protocol import BaseSentimentModel

# Label -> indeks kelas. Dipakai bersama oleh training & inference.
LABEL_TO_INT = {"negative": 0, "neutral": 1, "positive": 2}
INT_TO_LABEL = {v: k for k, v in LABEL_TO_INT.items()}


class ModelNotFittedError(RuntimeError):
    """Dilempar saat prediksi diminta dari model yang belum dilatih.

    Sengaja berupa error, bukan fallback: lihat AUDIT K-4 — fallback senyap
    membuat pipeline menghasilkan angka tanpa makna.
    """


class BaselineTfidfSentiment(BaseSentimentModel):
    """TF-IDF + Logistic Regression baseline for 3-class financial sentiment."""

    def __init__(self, model_version: str = "tfidf-lr-v0.5.0"):
        self._model_version = model_version
        self.vectorizer: Any = None
        self.classifier: Any = None
        self.is_fitted = False

    @property
    def model_name(self) -> str:
        return "tfidf_lr"

    @property
    def model_version(self) -> str:
        return self._model_version

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------
    def fit(self, texts: Sequence[str], labels: Sequence[int]) -> "BaselineTfidfSentiment":
        """Melatih baseline.

        labels: 0 = negative, 1 = neutral, 2 = positive
        """
        if not SKLEARN_AVAILABLE:
            raise RuntimeError(
                "scikit-learn tidak terpasang. Baseline TF-IDF tidak bisa dilatih. "
                "Pasang dengan: pip install scikit-learn"
            )
        if not texts:
            raise ValueError("fit() butuh minimal satu teks.")
        if len(texts) != len(labels):
            raise ValueError(f"jumlah teks ({len(texts)}) != jumlah label ({len(labels)})")

        # Import lokal: satu-satunya jalur yang butuh sklearn, dan di sini mypy
        # melihat simbol sebagai kelas nyata (bukan `None` dari blok except).
        from sklearn.feature_extraction.text import TfidfVectorizer as _Vec
        from sklearn.linear_model import LogisticRegression as _LR

        self.vectorizer = _Vec(max_features=5000, ngram_range=(1, 2))
        self.classifier = _LR(max_iter=1000)

        X = self.vectorizer.fit_transform(texts)
        self.classifier.fit(X, labels)
        self.is_fitted = True
        return self

    # ------------------------------------------------------------------
    # Persistence — supaya training tidak diulang tiap pipeline run
    # ------------------------------------------------------------------
    def save(self, path: Path | str) -> Path:
        """Menyimpan model terlatih ke disk (joblib)."""
        if not self.is_fitted:
            raise ModelNotFittedError("Tidak ada model terlatih untuk disimpan.")
        import joblib

        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "vectorizer": self.vectorizer,
                "classifier": self.classifier,
                "model_version": self._model_version,
            },
            target,
        )
        return target

    @classmethod
    def load(cls, path: Path | str) -> "BaselineTfidfSentiment":
        """Memuat model terlatih dari disk."""
        import joblib

        source = Path(path)
        if not source.exists():
            raise FileNotFoundError(f"Model tidak ditemukan: {source}")
        blob = joblib.load(source)
        model = cls(model_version=blob.get("model_version", "tfidf-lr-v0.5.0"))
        model.vectorizer = blob["vectorizer"]
        model.classifier = blob["classifier"]
        model.is_fitted = True
        return model

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------
    def _require_fitted(self) -> None:
        if not self.is_fitted or self.classifier is None or self.vectorizer is None:
            raise ModelNotFittedError(
                "Baseline TF-IDF belum dilatih. Panggil fit() atau load() lebih dulu. "
                "Tidak ada fallback prior — prediksi tanpa model akan menyesatkan."
            )

    def predict_probs(self, texts: Sequence[str]) -> list[ModelProbs]:
        """3-class probabilities. Melempar bila model belum dilatih."""
        if not texts:
            return []
        self._require_fitted()

        X = self.vectorizer.transform(texts)
        proba = self.classifier.predict_proba(X)
        # Urutkan kolom sesuai kelas yang dikenal classifier (bisa tidak lengkap
        # bila satu kelas absen di data latih).
        classes = list(self.classifier.classes_)
        out: list[ModelProbs] = []
        for row in proba:
            by_class = {int(c): float(p) for c, p in zip(classes, row)}
            out.append(
                ModelProbs(
                    model=self.model_name,
                    model_version=self.model_version,
                    p_pos=by_class.get(LABEL_TO_INT["positive"], 0.0),
                    p_neu=by_class.get(LABEL_TO_INT["neutral"], 0.0),
                    p_neg=by_class.get(LABEL_TO_INT["negative"], 0.0),
                )
            )
        return out

    def score_article(
        self,
        article_id: str,
        text: str,
        translation_used: bool = False,
        translator_version: Optional[str] = None,
    ) -> ArticleSentiment:
        """Scores a single article text and outputs ArticleSentiment."""
        probs = self.predict_probs([text])
        prob = probs[0]
        score = round(prob.p_pos - prob.p_neg, 4)

        if score > 0.1:
            tone = Tone.POSITIVE
        elif score < -0.1:
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
