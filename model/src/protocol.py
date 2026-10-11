"""Abstract base protocol for sentiment inference models."""

from abc import ABC, abstractmethod
from typing import Sequence

from backend.src.schema import ArticleSentiment, ModelProbs


class BaseSentimentModel(ABC):
    """Protocol for financial sentiment classifiers."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the model architecture."""
        ...

    @property
    @abstractmethod
    def model_version(self) -> str:
        """Version identifier."""
        ...

    @abstractmethod
    def predict_probs(self, texts: Sequence[str]) -> list[ModelProbs]:
        """Returns 3-class probabilities [p_pos, p_neu, p_neg] summing to 1.0."""
        ...

    @abstractmethod
    def score_article(
        self,
        article_id: str,
        text: str,
        translation_used: bool = False,
        translator_version: str | None = None,
    ) -> ArticleSentiment:
        """Returns structured ArticleSentiment."""
        ...
