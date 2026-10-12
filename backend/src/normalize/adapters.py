"""DRAFT utensil referensi (chat planning) — bukan klaim final.
Per-source adapters: raw benchmark dumps -> RawArticle/Article contract (SCHEMA.md).

Sitasi:
- Gold: Sinha & Khandait 2020, arXiv:2009.04202 (India Gold Policy Centre grant
  1815012). HF: SaguaroCapital/sentiment-analysis-in-commodity-market-gold,
  lisensi cc-by-nc-nd-4.0. Raw immutable di dataset/gold_sinha/.
- FOMC: Shah, Paturi & Chava 2023, https://aclanthology.org/2023.acl-long.368/,
  model gtfintechlab/FOMC-RoBERTa. Repo gtfintechlab/fomc-hawkish-dovish,
  lisensi CC BY-NC 4.0. Varian terkunci: split-combine seed 5768 saja.

Keputusan beku 2026-10-11 (DESIGN §3.4): kolom `none` gold = DROP (bukan gabung
ke neutral). Bukti: semua 1574 train + 394 test `none` punya
Up=0/Constant=0/Down=0 (tanpa arah harga); sampel isi promosi/irrelevan
(medali Olimpiade, "Bitcoin the new gold", basket komoditas). Gabung ke
neutral cemari kelas Constant murni (301 train). Drop ~18% demi distribusi jujur.
"""

from datetime import datetime, timezone
from typing import Optional

import pandas as pd

from backend.src.normalize.cleaner import ArticleCleaner
from backend.src.schema import RawArticle

GOLD_SOURCE = "sinha_gold"
FOMC_SOURCE = "fomc_split_combine_5768"

GOLD_TONE_MAP = {
    "positive": "positive",
    "negative": "negative",
    "neutral": "neutral",
    # "none" -> DROP (return None)
}

# Paper/repo mapping (non-obvious, jangan tebak urutan):
# LABEL_2 = Neutral, LABEL_1 = Hawkish, LABEL_0 = Dovish.
FOMC_LABEL_TO_STANCE = {2: "neutral", 1: "hawkish", 0: "dovish"}

# Satu stance layani 2 target polaritas berlawanan (tanpa label baru).
FOMC_STANCE_TO_TONE = {
    ("hawkish", "RATE_UST"): "positive",
    ("hawkish", "SPX"): "negative",
    ("dovish", "RATE_UST"): "negative",
    ("dovish", "SPX"): "positive",
    ("neutral", "RATE_UST"): "neutral",
    ("neutral", "SPX"): "neutral",
}


def gold_tone(price_sentiment: str) -> Optional[str]:
    """Price Sentiment -> tone. `none` -> None (DROP)."""
    if not isinstance(price_sentiment, str):
        return None
    return GOLD_TONE_MAP.get(price_sentiment.strip().lower())


def fomc_stance(label: int) -> str:
    return FOMC_LABEL_TO_STANCE[int(label)]


def fomc_tone(stance: str, asset_id: str) -> str:
    return FOMC_STANCE_TO_TONE[(stance, asset_id)]


def _gold_parse_date(s) -> Optional[datetime]:
    try:
        dt = pd.to_datetime(s, format="%d-%m-%Y", errors="coerce")
    except Exception:
        return None
    if pd.isna(dt):
        return None
    return dt.to_pydatetime().replace(tzinfo=timezone.utc)


def gold_to_raw(df: pd.DataFrame, fetched_at: Optional[datetime] = None) -> pd.DataFrame:
    """Parquet Sinha -> RawArticle + tone XAU. Baris `none` dibuang.

    Input kolom: Dates/URL/News/Price Direction Up/Constant/Down/
    Asset Comparision/Past Information/Future Information/Price Sentiment.
    Kolom eksplorasi (*_clean/dll) tidak ada di sumber ini; kolom biner
    Up/Constant/Down hanya dipakai audit putus-none, tidak masuk DB.
    """
    now = fetched_at or datetime.now(timezone.utc)
    rows = []
    for _, r in df.iterrows():
        tone = gold_tone(str(r.get("Price Sentiment") or ""))
        if tone is None:
            continue  # DROP none
        title = str(r.get("News") or "").strip()
        if not title:
            continue
        url = r.get("URL") or None
        raw = RawArticle(
            source=GOLD_SOURCE,
            url=url,
            title=title,
            body=None,
            published_at=_gold_parse_date(r.get("Dates")),
            fetched_at=now,
            query_target="XAU",
        )
        art = ArticleCleaner.process_raw(raw)
        rows.append(
            {
                "article_id": art.article_id,
                "source": GOLD_SOURCE,
                "url": url,
                "title": art.title,
                "body": None,
                "language": art.language.value,
                "published_at": art.published_at,
                "query_target": "XAU",
                "asset_id": "XAU",
                "tone": tone,
            }
        )
    out = pd.DataFrame(rows)
    if len(out):
        out = out.drop_duplicates("article_id", keep="first").reset_index(drop=True)
    return out


def fomc_to_raw(df: pd.DataFrame, fetched_at: Optional[datetime] = None) -> pd.DataFrame:
    """XLSX split-combine-5768 -> RawArticle + stance dual-target.

    Input kolom: index/sentence/year/label/orig_index. Pola single-sentence:
    title=body=sentence, published_at=None (hanya tahun, tanpa timestamp;
    split ikut berkas, bukan temporal). year dipertahankan sebagai kolom audit.
    """
    now = fetched_at or datetime.now(timezone.utc)
    rows = []
    for _, r in df.iterrows():
        sent = str(r.get("sentence") or "").strip()
        if not sent:
            continue
        stance = fomc_stance(int(r.get("label")))
        raw = RawArticle(
            source=FOMC_SOURCE,
            url=None,
            title=sent,
            body=sent,
            published_at=None,
            fetched_at=now,
            query_target=None,
        )
        art = ArticleCleaner.process_raw(raw)
        year_val = r.get("year")
        try:
            year = int(year_val) if year_val is not None and str(year_val) != "nan" else None
        except (TypeError, ValueError):
            year = None
        rows.append(
            {
                "article_id": art.article_id,
                "source": FOMC_SOURCE,
                "url": None,
                "title": art.title,
                "body": art.body,
                "language": art.language.value,
                "published_at": None,
                "year": year,
                "orig_index": r.get("orig_index"),
                "stance": stance,
                "tone_RATE_UST": fomc_tone(stance, "RATE_UST"),
                "tone_SPX": fomc_tone(stance, "SPX"),
            }
        )
    out = pd.DataFrame(rows)
    if len(out):
        out = out.drop_duplicates("article_id", keep="first").reset_index(drop=True)
    return out
