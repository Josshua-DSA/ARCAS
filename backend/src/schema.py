"""Data contracts and validation models (SCHEMA v0.5.0)."""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, model_validator


# ==========================================
# 1. ENUMS
# ==========================================

class Tone(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class Direction(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class AssetClass(str, Enum):
    COMMODITY = "commodity"    # XAU, OIL, CU, NG
    CRYPTO = "crypto"          # BTC
    INDEX = "index"            # SPX, IHSG
    FX = "fx"                  # USDIDR, DXY
    RATE = "rate"              # RATE_UST
    VOLATILITY = "volatility"  # VIX
    BOND = "bond"              # Allocation target
    MUTUAL_FUND = "mutual_fund"
    ETF = "etf"


class Track(str, Enum):
    A_IDX = "A"
    B_GLOBAL = "B"


class Basis(str, Enum):
    EXPLICIT = "explicit"
    MACRO_FACTOR = "macro_factor"
    SECTOR_INFERRED = "sector_inferred"  # Dropped from MVP


class Lang(str, Enum):
    ID = "id"
    EN = "en"
    OTHER = "other"


class AllocClass(str, Enum):
    BOND = "bond"
    MUTUAL_FUND = "mutual_fund"
    STOCK = "stock"
    ETF = "etf"
    BTC = "btc"
    GOLD = "gold"
    CASH = "cash"


class Stance(str, Enum):
    BUY = "buy"    # Green
    HOLD = "hold"  # Gray
    SELL = "sell"  # Red


class NewsHorizon(str, Enum):
    INTRADAY = "intraday"
    SHORT = "short"    # 1-5 days
    MEDIUM = "medium"  # 1-4 weeks
    LONG = "long"      # > 1 month


# ==========================================
# 2. PIPELINE MODELS
# ==========================================

class RawArticle(BaseModel):
    source: str
    url: Optional[str] = None
    title: str
    body: Optional[str] = None
    published_at: Optional[datetime] = None  # UTC
    fetched_at: datetime
    query_target: Optional[str] = None
    vendor_sentiment: Optional[float] = None


class Article(BaseModel):
    article_id: str  # sha256(norm(title)+norm(body))[:16]
    source: str
    url: Optional[str] = None
    title: str
    body: Optional[str] = None
    language: Lang
    published_at: Optional[datetime] = None
    fetched_at: datetime
    effective_trading_date: dict[str, date] = {}
    duplicate_of: Optional[str] = None
    market_relevant: Optional[bool] = None


class TargetTag(BaseModel):
    asset_id: str
    basis: Basis
    matched_text: Optional[str] = None
    span: Optional[tuple[int, int]] = None
    routed_from: Optional[str] = None


class ModelProbs(BaseModel):
    model: str  # tfidf_lr | indobert | finbert_mt | finbert | fusion
    p_pos: float = Field(ge=0.0, le=1.0)
    p_neu: float = Field(ge=0.0, le=1.0)
    p_neg: float = Field(ge=0.0, le=1.0)
    model_version: str

    @model_validator(mode="after")
    def validate_probabilities(self) -> "ModelProbs":
        total = self.p_pos + self.p_neu + self.p_neg
        if abs(total - 1.0) > 1e-2:
            raise ValueError(f"Probabilities must sum to 1.0, got {total:.4f}")
        return self


class ArticleSentiment(BaseModel):
    article_id: str
    tone: Tone
    score: float = Field(ge=-1.0, le=1.0)
    probs: list[ModelProbs]
    translation_used: bool = False
    translator_version: Optional[str] = None


class EvidenceSpan(BaseModel):
    quote: str = Field(max_length=300)
    start: int
    end: int


class TargetImpact(BaseModel):
    article_id: str
    asset_id: str
    direction: Direction
    score: float = Field(ge=-1.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    basis: Basis
    themes: list[str] = []
    causal_path: Optional[list[str]] = None
    rationale: Optional[str] = Field(default=None, max_length=500)
    evidence: list[EvidenceSpan] = []
    flags: list[str] = []
    news_horizon: NewsHorizon = NewsHorizon.SHORT
    model_version: str = "fusion-v1"
    universe_version: str = "2026-10-12-core3"
    schema_version: str = "0.5.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def validate_basis_confidence_and_evidence(self) -> "TargetImpact":
        # Rule 1.2 & Invariant 5: Cap per basis
        caps = {
            Basis.EXPLICIT: 1.00,
            Basis.MACRO_FACTOR: 0.85,
            Basis.SECTOR_INFERRED: 0.60,
        }
        cap = caps.get(self.basis, 1.00)
        if self.confidence > cap + 1e-4:
            raise ValueError(
                f"Confidence {self.confidence} exceeds cap {cap} for basis {self.basis}"
            )

        # Rule 1.3 & Invariant 4: Explicit basis must have evidence
        if self.basis == Basis.EXPLICIT and len(self.evidence) < 1:
            raise ValueError("TargetImpact with basis=explicit requires at least 1 evidence span")

        return self


class DailySentiment(BaseModel):
    asset_id: str
    date: date
    score_mean: Optional[float] = None
    score_weighted: Optional[float] = None
    n_articles: int = Field(ge=0)
    n_sources: int = Field(ge=0)
    has_news: bool
    version: str = "v1"

    @model_validator(mode="after")
    def validate_empty_day_nan(self) -> "DailySentiment":
        # Invariant 6: n_articles == 0 => score_mean IS NULL and has_news == False
        if self.n_articles == 0:
            if self.score_mean is not None:
                raise ValueError("score_mean must be None (NaN) when n_articles == 0")
            if self.has_news:
                raise ValueError("has_news must be False when n_articles == 0")
        return self


class PriceRecord(BaseModel):
    asset_id: str
    date: date
    open: float
    high: float
    low: float
    close: float
    adj_close: float
    volume: float


class StatResult(BaseModel):
    run_id: str
    asset_id: str
    test: str  # pearson | spearman | ols | granger | event_study
    market_metric: str  # return | abnormal_return | volatility | volume_change
    lag: Optional[int] = None
    estimate: float
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None
    p_value: float
    p_adjusted: Optional[float] = None
    n_obs: int
    period_start: date
    period_end: date
    params_json: str
    code_version: str


# ==========================================
# 3. ALLOCATION & PERSONA MODELS
# ==========================================

class ClassScore(BaseModel):
    alloc_class: AllocClass
    score: float = Field(ge=-1.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    sources: list[str] = []


class AllocationLine(BaseModel):
    alloc_class: AllocClass
    baseline_pct: float
    new_pct: float
    delta_pp: float
    confidence: float
    rationale: Optional[str] = None
    no_change: bool = False


class AllocationSuggestion(BaseModel):
    article_id: str
    profile_id: str  # conservative | moderate | aggressive | custom
    lines: list[AllocationLine]
    params_version: str = "2026-10-09"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    disclaimer: str = "Simulasi analitis. Bukan nasihat investasi."

    @model_validator(mode="after")
    def validate_sum_100(self) -> "AllocationSuggestion":
        total_new = sum(line.new_pct for line in self.lines)
        if abs(total_new - 100.0) > 1e-3:
            raise ValueError(f"Allocation lines must sum to 100.0%, got {total_new:.4f}%")
        return self


class PersonaView(BaseModel):
    article_id: str
    persona_id: str  # retail | day_trader | fund_manager | pension | risk_manager
    target: str
    stance: Stance
    strength: float = Field(ge=0.0, le=1.0)
    news_horizon: NewsHorizon
    raw_value: float
    confidence: float
    rationale: str = Field(max_length=300)
    params_version: str = "2026-10-09"
    disclaimer: str = "Simulasi sudut pandang. Bukan nasihat investasi."
