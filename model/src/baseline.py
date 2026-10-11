"""M1 Baseline Model: TF-IDF + Logistic Regression."""

from typing import Optional, Sequence
import numpy as np

try:
    from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
    from sklearn.linear_model import LogisticRegression  # type: ignore
except ImportError:
    TfidfVectorizer = None  # type: ignore
    LogisticRegression = None  # type: ignore

from backend.src.schema import ArticleSentiment, ModelProbs, Tone
from model.src.protocol import BaseSentimentModel


class BaselineTfidfSentiment(BaseSentimentModel):
    """TF-IDF + Logistic Regression baseline for 3-class financial sentiment."""

    def __init__(self, model_version: str = "tfidf-lr-v0.5.0"):
        self._model_version = model_version
        self.vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2)) if TfidfVectorizer else None
        self.classifier = LogisticRegression(max_iter=1000) if LogisticRegression else None
        self.is_fitted = False

    @property
    def model_name(self) -> str:
        return "tfidf_lr"

    @property
    def model_version(self) -> str:
        return self._model_version

    def fit(self, texts: Sequence[str], labels: Sequence[int]) -> "BaselineTfidfSentiment":
        """
        Fits baseline model.
        labels: 0 for negative, 1 for neutral, 2 for positive
        """
        if self.vectorizer is None or self.classifier is None:
            raise RuntimeError("scikit-learn is required to train the baseline model.")

        X = self.vectorizer.fit_transform(texts)
        self.classifier.fit(X, labels)
        self.is_fitted = True
        return self

    def predict_probs(self, texts: Sequence[str]) -> list[ModelProbs]:
        """Infers 3-class probabilities. Falls back to neutral prior if unfitted."""
        if not texts:
            return []

        if not self.is_fitted or self.classifier is None or self.vectorizer is None:
            # Neutral baseline prior [0.20, 0.60, 0.20]
            return [
                ModelProbs(
                    model=self.model_name,
                    model_version=self.model_version,
                    p_pos=0.20,
                    p_neu=0.60,
                    p_neg=0.20,
                )
                for _ in texts
            ]

        X = self.vectorizer.transform(texts)
        proba_matrix = self.classifier.predict_proba(X)
        probs_list: list[ModelProbs] = []

        for row in proba_matrix:
            # Classes assume [negative (0), neutral (1), positive (2)]
            p_neg = float(row[0])
            p_neu = float(row[1]) if len(row) > 2 else 0.0
            p_pos = float(row[2]) if len(row) > 2 else float(row[1])

            # Guarantee sum == 1.0 within tolerance
            total = p_neg + p_neu + p_pos
            if total > 0:
                p_neg, p_neu, p_pos = p_neg / total, p_neu / total, p_pos / total

            probs_list.append(
                ModelProbs(
                    model=self.model_name,
                    model_version=self.model_version,
                    p_pos=round(p_pos, 4),
                    p_neu=round(p_neu, 4),
                    p_neg=round(p_neg, 4),
                )
            )

        return probs_list

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
