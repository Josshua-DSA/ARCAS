"""Orkestrasi pipeline: raw_articles -> articles -> sentiments -> impacts -> daily_sentiment.

Modul ini adalah sambungan yang sebelumnya tidak ada (AUDIT K-1). Sebelumnya
setiap komponen berdiri sendiri dan hanya dipanggil dari test.

Alur per artikel:
    raw_articles (baca)
      -> ArticleCleaner.process_raw()   normalisasi, article_id, bahasa, tanggal bursa
      -> articles (tulis)
      -> TargetRouter.route_article()   target + arah + confidence + evidence
      -> BaselineTfidfSentiment         sentimen (model wajib terlatih)
      -> sentiments (tulis) + impacts (tulis) + article_targets (tulis)
      -> DailyAggregator                agregasi harian
      -> daily_sentiment (tulis)

Prinsip yang dipegang:
- **Tidak ada fallback senyap.** Model belum terlatih -> error, bukan angka karangan.
- **Idempoten.** Menjalankan ulang perintah yang sama tidak menggandakan baris.
- **Bisa dibatasi.** `--limit` dan `--dry-run` supaya bisa dicoba tanpa efek.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from backend.src.aggregate.daily import DailyAggregator
from backend.src.normalize.cleaner import ArticleCleaner
from backend.src.schema import Article, RawArticle, TargetImpact, TargetTag
from backend.src.store.db import Database
from backend.src.tagging.router import TargetRouter
from model.common.baseline import BaselineTfidfSentiment

DEFAULT_MODEL_PATH = Path("model/common/baseline_tfidf.joblib")
SENTIMENT_VERSION = "v1"


class PipelineError(RuntimeError):
    """Kesalahan yang membuat pipeline tidak boleh lanjut diam-diam."""


@dataclass
class PipelineStats:
    """Ringkasan satu kali jalan. Dipakai untuk laporan CLI."""

    raw_dibaca: int = 0
    artikel_tertulis: int = 0
    artikel_dilewati: int = 0
    sentimen_tertulis: int = 0
    impact_tertulis: int = 0
    target_tertulis: int = 0
    hari_agregat: int = 0
    tanpa_target: int = 0
    errors: list[str] = field(default_factory=list)

    def ringkas(self) -> str:
        return (
            f"raw dibaca        : {self.raw_dibaca}\n"
            f"artikel tertulis  : {self.artikel_tertulis}\n"
            f"artikel dilewati  : {self.artikel_dilewati}\n"
            f"sentimen tertulis : {self.sentimen_tertulis}\n"
            f"target tertulis   : {self.target_tertulis}\n"
            f"impact tertulis   : {self.impact_tertulis}\n"
            f"hari agregat      : {self.hari_agregat}\n"
            f"tanpa target      : {self.tanpa_target}\n"
            f"error             : {len(self.errors)}"
        )


def _row_to_raw_article(row: dict) -> RawArticle:
    """Mengubah baris `raw_articles` kembali menjadi kontrak RawArticle."""

    def _parse_dt(value) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        try:
            parsed = datetime.fromisoformat(str(value))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    published = _parse_dt(row.get("published_at"))
    fetched = _parse_dt(row.get("fetched_at")) or datetime.now(timezone.utc)

    return RawArticle(
        source=row["source"],
        url=row.get("url"),
        title=row["title"],
        body=row.get("body"),
        published_at=published,
        fetched_at=fetched,
        query_target=row.get("query_target"),
        vendor_sentiment=row.get("vendor_sentiment"),
    )


class Pipeline:
    """Menyambungkan komponen-komponen menjadi satu alur berjalan."""

    def __init__(
        self,
        db_path: Path | str = "data/finews.db",
        model_path: Path | str = DEFAULT_MODEL_PATH,
        aliases_path: Path | str = "data/universe/aliases.csv",
        impact_graph_path: Path | str = "data/impact_graph.yaml",
        asset_master_path: Path | str = "data/universe/asset_master.csv",
    ) -> None:
        self.db = Database(db_path)
        self.db.init_schema()
        self.router = TargetRouter(
            aliases_path=aliases_path, impact_graph_path=impact_graph_path
        )
        self.model_path = Path(model_path)
        self.model: Optional[BaselineTfidfSentiment] = None
        self.asset_master_path = Path(asset_master_path)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def seed_universe(self) -> dict[str, int]:
        """Mengisi asset_master & asset_aliases.

        Tanpa ini `/api/universe` mengembalikan `[]` (AUDIT K-6).
        """
        assets = self.db.seed_asset_master(self.asset_master_path)
        aliases = self.db.seed_aliases()
        return {"asset_master": assets, "asset_aliases": aliases}

    def load_model(self) -> BaselineTfidfSentiment:
        """Memuat model sentimen. Gagal keras bila tidak ada.

        AUDIT K-4: lebih baik berhenti daripada lanjut dengan angka kosong.
        """
        if self.model is not None:
            return self.model
        if not self.model_path.exists():
            raise PipelineError(
                f"Model sentimen tidak ditemukan: {self.model_path}\n"
                "Latih dulu:  python -m model.common.train_baseline"
            )
        self.model = BaselineTfidfSentiment.load(self.model_path)
        return self.model

    # ------------------------------------------------------------------
    # Tahap 1: normalisasi
    # ------------------------------------------------------------------
    def normalize_raw(
        self, limit: int = 100, dry_run: bool = False, stats: PipelineStats | None = None
    ) -> tuple[list[Article], PipelineStats]:
        """raw_articles -> Article, lalu tulis ke tabel `articles`."""
        stats = stats or PipelineStats()
        rows = self.db.query_raw_articles(limit=limit)
        stats.raw_dibaca = len(rows)

        articles: list[Article] = []
        seen: set[str] = set()
        for row in rows:
            raw = _row_to_raw_article(row)
            try:
                article = ArticleCleaner.process_raw(raw)
            except Exception as exc:  # noqa: BLE001 - satu baris buruk tidak boleh menghentikan batch
                stats.errors.append(f"normalize {row.get('raw_id')}: {exc}")
                continue

            # Dedup dalam-batch: dua raw bisa menghasilkan article_id sama.
            if article.article_id in seen:
                stats.artikel_dilewati += 1
                continue
            seen.add(article.article_id)
            articles.append(article)

        if articles and not dry_run:
            stats.artikel_tertulis = self.db.save_articles(articles)
        return articles, stats

    # ------------------------------------------------------------------
    # Tahap 2: skor sentimen + routing target
    # ------------------------------------------------------------------
    def score_and_route(
        self,
        articles: list[Article],
        dry_run: bool = False,
        stats: PipelineStats | None = None,
    ) -> tuple[list[TargetImpact], PipelineStats]:
        """Sentimen + impact untuk tiap artikel."""
        stats = stats or PipelineStats()
        model = self.load_model()

        all_impacts: list[TargetImpact] = []
        for article in articles:
            text = f"{article.title} {article.body or ''}".strip()
            if not text:
                stats.artikel_dilewati += 1
                continue

            try:
                sentiment = model.score_article(article.article_id, text)
                impacts = self.router.route_article(
                    article,
                    sentiment_score=sentiment.score,
                    model_version=SENTIMENT_VERSION,
                )
            except Exception as exc:  # noqa: BLE001
                stats.errors.append(f"score {article.article_id}: {exc}")
                continue

            if not impacts:
                stats.tanpa_target += 1

            if not dry_run:
                self.db.save_sentiment(sentiment)
                stats.sentimen_tertulis += len(sentiment.probs)
                for impact in impacts:
                    self.db.save_impact(impact)
                stats.impact_tertulis += len(impacts)

                tags = self._impacts_to_tags(impacts, article)
                if tags:
                    stats.target_tertulis += self.db.save_article_targets(
                        article.article_id, tags, article.effective_trading_date
                    )

            all_impacts.extend(impacts)

        return all_impacts, stats

    @staticmethod
    def _impacts_to_tags(impacts: list[TargetImpact], article: Article) -> list[TargetTag]:
        """TargetImpact -> TargetTag, membawa basis & kutipan bukti."""
        tags: list[TargetTag] = []
        for impact in impacts:
            quote = impact.evidence[0].quote if impact.evidence else None
            span = None
            if impact.evidence:
                span = (impact.evidence[0].start, impact.evidence[0].end)
            tags.append(
                TargetTag(
                    asset_id=impact.asset_id,
                    basis=impact.basis,
                    matched_text=quote,
                    span=span,
                    routed_from=impact.routed_from,
                )
            )
        return tags

    # ------------------------------------------------------------------
    # Tahap 3: agregasi harian
    # ------------------------------------------------------------------
    def aggregate(
        self,
        impacts: list[TargetImpact],
        articles: list[Article],
        dry_run: bool = False,
        stats: PipelineStats | None = None,
    ) -> PipelineStats:
        """impacts -> daily_sentiment."""
        stats = stats or PipelineStats()
        if not impacts:
            return stats

        # Tanggal efektif per artikel sudah dihitung normalizer; ambil yang
        # relevan untuk aset masing-masing impact.
        tanggal_per_aset: dict[tuple[str, str], date] = {}
        for article in articles:
            for asset_id, dt in article.effective_trading_date.items():
                tanggal_per_aset[(article.article_id, asset_id)] = dt

        # Kelompokkan impact per aset per tanggal bursa.
        grouped: dict[tuple[str, date], list[TargetImpact]] = defaultdict(list)
        source_by_article = {a.article_id: a.source for a in articles}
        for impact in impacts:
            tgl: date | None = tanggal_per_aset.get((impact.article_id, impact.asset_id))
            if tgl is None:
                # Fallback: pakai tanggal publikasi artikel bila tanggal bursa
                # tidak tersedia untuk aset ini.
                artikel = next((a for a in articles if a.article_id == impact.article_id), None)
                if artikel is None or artikel.published_at is None:
                    continue
                tgl = artikel.published_at.date()
            grouped[(impact.asset_id, tgl)].append(impact)

        daily_records = [
            DailyAggregator.aggregate_for_asset_date(
                asset_id=asset_id,
                trading_date=dt,
                impacts=group_impacts,
                version=SENTIMENT_VERSION,
                sources=[source_by_article.get(i.article_id, "") for i in group_impacts],
            )
            for (asset_id, dt), group_impacts in grouped.items()
        ]

        if not dry_run:
            for record in daily_records:
                self.db.save_daily_sentiment(record)
        stats.hari_agregat = len(daily_records)
        return stats

    # ------------------------------------------------------------------
    # Jalur lengkap
    # ------------------------------------------------------------------
    def run(
        self,
        limit: int = 100,
        dry_run: bool = False,
        seed: bool = True,
    ) -> PipelineStats:
        """Menjalankan seluruh alur sekali jalan."""
        stats = PipelineStats()
        if seed:
            self.seed_universe()

        articles, stats = self.normalize_raw(limit=limit, dry_run=dry_run, stats=stats)
        impacts, stats = self.score_and_route(articles, dry_run=dry_run, stats=stats)
        stats = self.aggregate(impacts, articles, dry_run=dry_run, stats=stats)
        return stats
