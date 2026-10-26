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

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

from backend.src.aggregate.daily import DailyAggregator
from backend.src.normalize.cleaner import ArticleCleaner
from backend.src.schema import Article, Lang, RawArticle, TargetImpact, TargetTag
from backend.src.store.db import Database
from backend.src.tagging.model_router import ModelRouter
from backend.src.tagging.router import TargetRouter
from model.common.baseline import BaselineTfidfSentiment

logger = logging.getLogger(__name__)

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
    #: T-6: jumlah artikel yang ditandai near-duplicate (tidak ikut agregasi).
    artikel_duplikat: int = 0
    #: Jumlah artikel yang dilewati karena bahasanya bukan Inggris.
    #:
    #: Terjemahan ID->EN MATI 2026-10-11 (DESIGN.md §3.1 #4), sedangkan
    #: FinBERT-EMAS dan FOMC-RoBERTa hanya dilatih pada teks Inggris. Teks
    #: Indonesia yang dipaksa masuk terbukti menghasilkan skor tak bermakna:
    #: "Harga emas anjlok tajam..." diskor positive +0.231. Melewati artikel
    #: ini lebih jujur daripada memasukkan sinyal palsu ke agregasi harian.
    artikel_bukan_inggris: int = 0
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
            f"near-duplicate    : {self.artikel_duplikat}\n"
            f"bukan Inggris     : {self.artikel_bukan_inggris}\n"
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


def _row_to_article(row: dict) -> Article:
    """Mengubah baris tabel `articles` kembali menjadi `Article`.

    Pasangan dari `_row_to_raw_article`, dipakai `Pipeline.load_articles()`
    supaya tahap `score` benar-benar memakai hasil tahap `clean`.
    """

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

    return Article(
        article_id=row["article_id"],
        source=row["source"],
        url=row.get("url"),
        title=row["title"],
        body=row.get("body"),
        language=Lang(row["language"]),
        published_at=_parse_dt(row.get("published_at")),
        fetched_at=_parse_dt(row.get("fetched_at")) or datetime.now(timezone.utc),
        duplicate_of=row.get("duplicate_of"),
        market_relevant=(
            None if row.get("market_relevant") is None else bool(row["market_relevant"])
        ),
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
        self.model_router = ModelRouter()
        self.model_path = Path(model_path)
        self.model: Optional[BaselineTfidfSentiment] = None
        self.fomc_model: Optional[Any] = None
        self.xau_model: Optional[Any] = None
        self.asset_master_path = Path(asset_master_path)
        #: T-6: pasangan mirip yang perlu ditinjau manusia (tidak digabung).
        self.last_duplicate_review: list[tuple[str, str, float]] = []
        #: Peringatan non-fatal (mis. riwayat dedup tak terbaca).
        self.last_warnings: list[str] = []

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

    def load_xau_model(self) -> Optional[Any]:
        """Memuat model spesialis FinBERT-EMAS secara lazy (FR-6).

        Mengembalikan ``None`` bila PyTorch/Transformers tidak terpasang
        atau bobot hasil latih belum ada. Tanpa pemeriksaan bobot, pipeline
        akan gagal di setiap artikel emas pada mesin yang belum melatih;
        dengan pemeriksaan ini, jalur turun ke baseline TF-IDF seperti
        perilaku sebelum FR-6 terpasang.
        """
        if self.xau_model is not None:
            return self.xau_model
        try:
            import importlib.util

            if not (importlib.util.find_spec("torch") and importlib.util.find_spec("transformers")):
                logger.info("PyTorch / Transformers tidak terpasang. Fallback ke baseline.")
                return None

            from model.xau.src.model import DEFAULT_CHECKPOINT_DIR, FinbertGoldSentiment

            if not Path(DEFAULT_CHECKPOINT_DIR).exists():
                logger.info(
                    "Bobot FinBERT-EMAS belum ada di %s. Fallback ke baseline. "
                    "Latih dulu: python -m scripts.train_xau_finbert",
                    DEFAULT_CHECKPOINT_DIR,
                )
                return None

            self.xau_model = FinbertGoldSentiment()
            return self.xau_model
        except Exception as exc:
            logger.warning("Gagal memuat model FinBERT-EMAS (%s). Fallback ke baseline.", exc)
            return None

    def load_fomc_model(self) -> Optional[Any]:
        """Memuat model spesialis FOMC-RoBERTa secara lazy."""
        if self.fomc_model is not None:
            return self.fomc_model
        try:
            import importlib.util

            if not (importlib.util.find_spec("torch") and importlib.util.find_spec("transformers")):
                logger.info("PyTorch / Transformers tidak terpasang. Fallback ke baseline.")
                return None
            from model.fomc.src.model import FOMCRoBERTaSentiment

            self.fomc_model = FOMCRoBERTaSentiment()
            return self.fomc_model
        except Exception as exc:
            logger.warning("FOMC-RoBERTa gagal dimuat: %s. Fallback ke baseline.", exc)
            return None

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

        # T-6 / FR-2: dedup exact saja tidak cukup. Berita wire yang sama
        # sering muncul dari beberapa feed dengan suntingan kecil; tanpa
        # langkah ini keduanya dihitung di `daily_sentiment`.
        if articles:
            articles, dup_stats = self._mark_near_duplicates(articles)
            stats.artikel_duplikat += dup_stats["digabung"]

        if articles and not dry_run:
            stats.artikel_tertulis = self.db.save_articles(articles)
        return articles, stats

    def load_articles(self, limit: int = 100) -> list[Article]:
        """Baca kembali `Article` dari tabel `articles`.

        S-4: `cmd_score` dulu memanggil `normalize_raw(dry_run=True)`, sehingga
        tahap `score` mengolah ulang `raw_articles` dan bukan memakai hasil
        `clean`. Akibatnya `clean` praktis opsional, dan menjalankan `score`
        tanpa `clean` lebih dulu gagal dengan `FOREIGN KEY constraint failed`
        dari SQLite -- pesan yang tidak memberi tahu apa yang harus dilakukan.
        """
        hasil: list[Article] = []
        for row in self.db.query_articles(limit=limit):
            try:
                hasil.append(_row_to_article(row))
            except Exception:  # noqa: BLE001 - satu baris rusak tidak menghentikan batch
                continue
        return hasil

    def _mark_near_duplicates(self, articles: list[Article]) -> tuple[list[Article], dict]:
        """Tandai near-duplicate terhadap riwayat DB dan sesama batch.

        Artikel duplikat tetap disimpan (dengan `duplicate_of` terisi) agar
        jejaknya bisa diaudit, tetapi tidak ikut dihitung pada agregasi.
        """
        from backend.src.normalize.dedup import NearDuplicateDetector

        history: dict[str, str] = {}
        try:
            with self.db.get_connection() as conn:
                rows = conn.execute(
                    "SELECT article_id, title, body FROM articles "
                    "WHERE duplicate_of IS NULL ORDER BY published_at DESC LIMIT 500;"
                ).fetchall()
            history = {
                r["article_id"]: f"{(r['title'] or '').lower()} "
                f"{(r['title'] or '').lower()} {(r['body'] or '').lower()}"
                for r in rows
            }
        except Exception as exc:  # noqa: BLE001 - dedup tidak boleh menggagalkan pipeline
            history = {}
            self.last_warnings.append(f"near-dup: riwayat tidak terbaca ({exc})")

        detector = NearDuplicateDetector()
        # Riwayat tidak boleh memuat artikel dari batch ini sendiri: kalau
        # tidak, tiap artikel akan "mirip 100%" dengan dirinya sendiri dan
        # `duplicate_of` menunjuk ke dirinya sendiri -- seluruh artikel
        # dianggap duplikat dan agregasi menjadi kosong.
        batch_ids = {a.article_id for a in articles}
        history = {k: v for k, v in history.items() if k not in batch_ids}

        result = detector.mark_duplicates(articles, history=history)
        self.last_duplicate_review = list(detector.last_review)
        return result, {"digabung": len(detector.last_matches)}

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
        baseline_model: Optional[BaselineTfidfSentiment] = None

        all_impacts: list[TargetImpact] = []
        for article in articles:
            # T-6: salinan near-duplicate tidak ikut diskor/dihitung. Kalau
            # ikut, satu berita yang tersindikasi ke tiga feed akan muncul
            # tiga kali di `daily_sentiment` dan menggeser rata-rata.
            if article.duplicate_of is not None:
                stats.artikel_duplikat += 1
                continue

            text = f"{article.title} {article.body or ''}".strip()
            if not text:
                stats.artikel_dilewati += 1
                continue

            # Terjemahan ID->EN MATI 2026-10-11 (DESIGN.md §3.1 #4) dan kedua
            # model spesialis hanya dilatih pada teks Inggris. Memaksa teks
            # non-Inggris lewat model EN menghasilkan skor yang menyesatkan
            # (terbukti: kalimat emas negatif berbahasa Indonesia diskor
            # positive). Artikel tetap tersimpan di tabel `articles`; yang
            # dilewati hanya scoring sentimen + impact.
            if article.language is not Lang.EN:
                stats.artikel_bukan_inggris += 1
                logger.debug(
                    "Lewati scoring non-Inggris (%s): %s", article.language, article.article_id
                )
                continue

            try:
                selected_model = None
                model_version = SENTIMENT_VERSION

                routed_models, _reason, _score = self.model_router.route(
                    text, source=article.source or ""
                )
                if "fomc_roberta" in routed_models:
                    fomc = self.load_fomc_model()
                    if fomc is not None:
                        selected_model = fomc
                        model_version = getattr(fomc, "model_version", "fomc-roberta-v1.0")

                if "finbert_emas" in routed_models:
                    # FR-6: router sudah lama menunjuk `finbert_emas`, tetapi
                    # pipeline belum pernah memuatnya, sehingga artikel emas
                    # tetap diskor baseline TF-IDF generik. Tanpa bobot
                    # terlatih, `load_xau_model` mengembalikan None dan
                    # pemilihan jatuh ke baseline seperti sebelumnya.
                    xau = self.load_xau_model()
                    if xau is not None:
                        selected_model = xau
                        model_version = getattr(xau, "model_version", "finbert-gold-v1.0")

                if selected_model is None:
                    if baseline_model is None:
                        baseline_model = self.load_model()
                    selected_model = baseline_model

                try:
                    sentiment = selected_model.score_article(article.article_id, text)
                except Exception as model_exc:
                    if selected_model is not baseline_model:
                        logger.warning(
                            "Model spesialis gagal scoring (%s): %s. Fallback ke baseline.",
                            model_version,
                            model_exc,
                        )
                        if baseline_model is None:
                            baseline_model = self.load_model()
                        selected_model = baseline_model
                        model_version = SENTIMENT_VERSION
                        sentiment = selected_model.score_article(article.article_id, text)
                    else:
                        raise

                impacts = self.router.route_article(
                    article,
                    sentiment_score=sentiment.score,
                    model_version=model_version,
                    model_router=self.model_router,
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
