"""SQLite database repository adhering to SCHEMA v0.5.0."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Generator, Optional

from backend.src.schema import (
    Article,
    ArticleSentiment,
    DailySentiment,
    PriceRecord,
    RawArticle,
    StatResult,
    TargetImpact,
    TargetTag,
)

DEFAULT_DB_PATH = Path("data/finews.db")


DDL_SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_articles (
  raw_id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  url TEXT,
  title TEXT NOT NULL,
  body TEXT,
  published_at TIMESTAMP,
  fetched_at TIMESTAMP NOT NULL,
  query_target TEXT,
  vendor_sentiment REAL,
  payload_json TEXT
);

CREATE TABLE IF NOT EXISTS articles (
  article_id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  url TEXT,
  title TEXT NOT NULL,
  body TEXT,
  language TEXT NOT NULL,
  published_at TIMESTAMP,
  fetched_at TIMESTAMP NOT NULL,
  duplicate_of TEXT,
  market_relevant BOOLEAN
);

CREATE TABLE IF NOT EXISTS article_targets (
  article_id TEXT NOT NULL REFERENCES articles(article_id),
  asset_id TEXT NOT NULL,
  basis TEXT NOT NULL,
  matched_text TEXT,
  routed_from TEXT,
  effective_trading_date DATE,
  PRIMARY KEY (article_id, asset_id)
);

CREATE TABLE IF NOT EXISTS sentiments (
  article_id TEXT NOT NULL REFERENCES articles(article_id),
  model TEXT NOT NULL,
  model_version TEXT NOT NULL,
  p_pos REAL NOT NULL,
  p_neu REAL NOT NULL,
  p_neg REAL NOT NULL,
  translation_used BOOLEAN DEFAULT 0,
  translator_version TEXT,
  created_at TIMESTAMP NOT NULL,
  PRIMARY KEY (article_id, model, model_version)
);

CREATE TABLE IF NOT EXISTS impacts (
  article_id TEXT NOT NULL,
  asset_id TEXT NOT NULL,
  direction TEXT NOT NULL,
  score REAL NOT NULL,
  confidence REAL NOT NULL,
  basis TEXT NOT NULL,
  themes_json TEXT,
  causal_path_json TEXT,
  rationale TEXT,
  evidence_json TEXT,
  flags_json TEXT,
  news_horizon TEXT,
  model_version TEXT NOT NULL,
  routed_from TEXT,
  route_score REAL,
  universe_version TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL,
  PRIMARY KEY (article_id, asset_id, model_version)
);

CREATE TABLE IF NOT EXISTS daily_sentiment (
  asset_id TEXT NOT NULL,
  date DATE NOT NULL,
  score_mean REAL,
  score_weighted REAL,
  n_articles INTEGER NOT NULL,
  n_sources INTEGER NOT NULL,
  has_news BOOLEAN NOT NULL,
  version TEXT NOT NULL,
  PRIMARY KEY (asset_id, date, version)
);

CREATE TABLE IF NOT EXISTS prices (
  asset_id TEXT NOT NULL,
  date DATE NOT NULL,
  open REAL,
  high REAL,
  low REAL,
  close REAL,
  adj_close REAL,
  volume REAL,
  PRIMARY KEY (asset_id, date)
);

CREATE TABLE IF NOT EXISTS stat_results (
  run_id TEXT NOT NULL,
  asset_id TEXT NOT NULL,
  test TEXT NOT NULL,
  market_metric TEXT NOT NULL,
  lag INTEGER,
  estimate REAL NOT NULL,
  ci_low REAL,
  ci_high REAL,
  p_value REAL NOT NULL,
  p_adjusted REAL,
  n_obs INTEGER NOT NULL,
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  params_json TEXT NOT NULL,
  code_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS labels (
  article_id TEXT NOT NULL,
  asset_id TEXT NOT NULL,
  annotator TEXT NOT NULL,
  label TEXT NOT NULL,
  labeled_at TIMESTAMP NOT NULL,
  PRIMARY KEY (article_id, asset_id, annotator)
);

CREATE TABLE IF NOT EXISTS asset_master (
  asset_id TEXT PRIMARY KEY,
  asset_class TEXT NOT NULL,
  track TEXT NOT NULL,
  name TEXT NOT NULL,
  price_ticker TEXT NOT NULL,
  exchange TEXT,
  country TEXT,
  sector TEXT,
  timezone TEXT NOT NULL,
  session_close TEXT NOT NULL,
  valid_from DATE NOT NULL,
  valid_to DATE,
  active BOOLEAN NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS asset_aliases (
  asset_id TEXT NOT NULL,
  alias TEXT NOT NULL,
  lang TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alloc_profiles (
  profile_id TEXT NOT NULL,
  alloc_class TEXT NOT NULL,
  base_pct REAL NOT NULL,
  min_pct REAL NOT NULL,
  max_pct REAL NOT NULL,
  PRIMARY KEY (profile_id, alloc_class)
);

CREATE TABLE IF NOT EXISTS alloc_suggestions (
  article_id TEXT NOT NULL,
  profile_id TEXT NOT NULL,
  alloc_class TEXT NOT NULL,
  baseline_pct REAL NOT NULL,
  new_pct REAL NOT NULL,
  delta_pp REAL NOT NULL,
  confidence REAL NOT NULL,
  rationale TEXT,
  no_change BOOLEAN NOT NULL DEFAULT 0,
  params_version TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL,
  PRIMARY KEY (article_id, profile_id, alloc_class, params_version)
);

CREATE TABLE IF NOT EXISTS persona_views (
  article_id TEXT NOT NULL,
  persona_id TEXT NOT NULL,
  target TEXT NOT NULL,
  stance TEXT NOT NULL,
  strength REAL NOT NULL,
  news_horizon TEXT NOT NULL,
  raw_value REAL NOT NULL,
  confidence REAL NOT NULL,
  rationale TEXT,
  params_version TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL,
  PRIMARY KEY (article_id, persona_id, target, params_version)
);


-- Status preload berita (job 07:00 WIB). Menyimpan jejak setiap tarikan
-- terjadwal supaya:
--   1. GUI bisa menyatakan "data per <waktu>" saat API mati (tidak mengarang).
--   2. Job yang terlewat (aplikasi mati semalaman) bisa "mengejar" sekali saat
--      startup, lalu lanjut jadwal normal -- dibedakan lewat status.
CREATE TABLE IF NOT EXISTS ingest_runs (
  run_id INTEGER PRIMARY KEY AUTOINCREMENT,
  trigger TEXT NOT NULL,              -- 'schedule' | 'startup_catchup' | 'manual'
  status TEXT NOT NULL,               -- 'running' | 'ok' | 'partial' | 'failed'
  started_at TIMESTAMP NOT NULL,
  finished_at TIMESTAMP,
  scheduled_for TIMESTAMP,            -- slot 07:00 WIB yang diwakili run ini
  raw_new INTEGER NOT NULL DEFAULT 0,
  articles_clean INTEGER NOT NULL DEFAULT 0,
  impacts_new INTEGER NOT NULL DEFAULT 0,
  detail TEXT
);


-- T-3: riwayat kesehatan sumber. Satu baris per (sumber, pemeriksaan).
-- `is_failure` sengaja disimpan sebagai kolom agar query alert tidak perlu
-- mengulang logika "status apa saja yang dianggap gagal" di banyak tempat.
CREATE TABLE IF NOT EXISTS source_health (
  source TEXT NOT NULL,
  checked_at TIMESTAMP NOT NULL,
  status TEXT NOT NULL,
  is_failure BOOLEAN NOT NULL DEFAULT 0,
  usable BOOLEAN NOT NULL DEFAULT 0,
  latency_ms REAL,
  detail TEXT,
  sample_size INTEGER NOT NULL DEFAULT 0,
  consecutive_failures INTEGER NOT NULL DEFAULT 0
);


-- Jejak setiap /api/simulate (P1-7).
--
-- Tanpa ini, teks yang dianalisis, model yang terpilih, dan skor yang
-- dihasilkan hanya hidup selama satu request. Kalau pengguna melaporkan
-- "kemarin hasilnya bullish", tidak ada cara memeriksa ulang -- bahkan tidak
-- bisa membuktikan teks masukannya sama. Itu melemahkan prinsip Explainable
-- di halaman yang paling menonjol.
--
-- `text` disimpan lengkap (keputusan pemilik repo) agar analisis bisa
-- dijalankan ULANG, bukan sekadar dikenali; `text_hash` disimpan berdampingan
-- supaya duplikat bisa dicari tanpa membandingkan teks penuh. Retensi dibatasi
-- RETAIN_DAYS lewat `purge_sim_runs`, jadi data pengguna tidak menumpuk
-- selamanya.
CREATE TABLE IF NOT EXISTS sim_runs (
  run_id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TIMESTAMP NOT NULL,
  text_hash TEXT NOT NULL,
  text TEXT NOT NULL,
  input_kind TEXT NOT NULL,
  is_rumor BOOLEAN NOT NULL DEFAULT 0,
  source TEXT,
  target TEXT NOT NULL,
  tone TEXT NOT NULL,
  score REAL NOT NULL,
  confidence REAL NOT NULL,
  confidence_raw REAL NOT NULL,
  penalty REAL NOT NULL DEFAULT 0,
  direction TEXT NOT NULL,
  horizon TEXT,
  model_version TEXT NOT NULL,
  warnings TEXT,          -- JSON list
  degraded TEXT           -- JSON list
);

"""

# P3-5: indeks dibuat SETELAH migrasi kolom, bukan sebelumnya.
#
# Sebelumnya indeks berada di dalam DDL_SCHEMA yang dijalankan lebih dulu.
# Pada DB lama, `CREATE INDEX ... ON ingest_runs(finished_at)` dievaluasi saat
# kolom `finished_at` belum ada -> OperationalError sebelum migrasi sempat
# berjalan. Akibatnya DB lama tidak bisa dinaikkan sama sekali: semua kolom
# sudah ada di katalog, tapi proses migrasi belum pernah sampai ke sana.
#
# Dipisah ke sini supaya `init_schema` bisa memakai urutan yang benar:
#   DDL tabel -> migrasi kolom -> DDL indeks -> seed
DDL_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_impacts_asset ON impacts(asset_id, created_at);
CREATE INDEX IF NOT EXISTS idx_daily_asset_date ON daily_sentiment(asset_id, date);
CREATE INDEX IF NOT EXISTS idx_prices_asset_date ON prices(asset_id, date);
CREATE INDEX IF NOT EXISTS idx_ingest_runs_finished ON ingest_runs(finished_at);
CREATE INDEX IF NOT EXISTS idx_source_health_source
  ON source_health(source, checked_at);
CREATE INDEX IF NOT EXISTS idx_sim_runs_created ON sim_runs(created_at);
CREATE INDEX IF NOT EXISTS idx_sim_runs_hash ON sim_runs(text_hash);
"""


class Database:
    """Manages SQLite connections and queries for FInews."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_schema(self) -> None:
        """Initializes tables and indexes, lalu migrasi kolom yang menyusul.

        Urutannya penting dan sengaja tidak boleh ditukar:
          1. DDL_SCHEMA  -- tabel baru muncul
          2. _migrate    -- tabel LAMA dilengkapi kolomnya
          3. DDL_INDEXES -- indeks dibuat, setelah kolomnya pasti ada
          4. seed        -- baris wajib, tanpa menimpa data pengguna

        Langkah 3 harus setelah 2: pada DB lama, indeks di atas kolom yang
        belum dimigrasi akan menggagalkan seluruh proses.
        """
        with self.get_connection() as conn:
            conn.executescript(DDL_SCHEMA)
            self._migrate(conn)
            conn.executescript(DDL_INDEXES)
            self._seed_schema_data(conn)

    # -- P3-5: versi skema ---------------------------------------------------
    #: Versi skema yang diharapkan kode ini. Naikkan setiap kali ada perubahan
    #: struktur yang butuh migrasi, lalu tambahkan langkahnya di `MIGRATIONS`.
    #: Tanpa angka ini, DB lama dan baru tidak bisa dibedakan sama sekali.
    SCHEMA_VERSION: int = 1

    # -- P3-5: deskripsi kolom yang WAJIB ada --------------------------------
    #: Peta tabel -> {kolom: DDL}. Dipakai dua arah: `init_schema` melengkapi
    #: kolom yang hilang, dan `skema_tidak_lengkap()` melaporkan selisih tanpa
    #: mengubah apa pun (untuk `fi check-schema`).
    #:
    #: Sebelumnya hanya tabel `impacts` yang punya jalur upgrade, dan DDL-nya
    #: ditulis ulang manual di `_migrate`. Akibatnya kolom baru pada tabel lain
    #: tidak pernah masuk ke DB lama: `CREATE TABLE IF NOT EXISTS` tidak
    #: menyentuh tabel yang sudah ada, jadi query-nya gagal saat runtime --
    #: atau lebih buruk, berjalan dengan data yang tidak lengkap.
    KOLOM_WAJIB: dict[str, dict[str, str]] = {
        "impacts": {
            "routed_from": "TEXT",
            "route_score": "REAL",
            # S-5: horizon berita harus tersimpan agar bisa dibaca kembali,
            # bukan hanya hidup di memori selama satu pemanggilan.
            "news_horizon": "TEXT",
        },
        "raw_articles": {
            "query_target": "TEXT",
            "vendor_sentiment": "REAL",
            "payload_json": "TEXT",
        },
        "articles": {
            "duplicate_of": "TEXT",
            "market_relevant": "BOOLEAN",
        },
        # Tabel-tabel ini lahir belakangan; DB yang dibuat sebelum itu tidak
        # memilikinya. `NOT NULL DEFAULT` dipakai bila DDL aslinya NOT NULL,
        # supaya baris lama tetap valid setelah kolom ditambahkan.
        # Nama kolom di bawah diambil langsung dari DDL_SCHEMA, bukan ditebak.
        "ingest_runs": {
            "finished_at": "TIMESTAMP",
            "scheduled_for": "TIMESTAMP",
            "raw_new": "INTEGER NOT NULL DEFAULT 0",
            "articles_clean": "INTEGER NOT NULL DEFAULT 0",
            "impacts_new": "INTEGER NOT NULL DEFAULT 0",
            "detail": "TEXT",
        },
        "source_health": {
            "status": "TEXT NOT NULL DEFAULT 'unknown'",
            "is_failure": "BOOLEAN NOT NULL DEFAULT 0",
            "usable": "BOOLEAN NOT NULL DEFAULT 0",
            "latency_ms": "REAL",
            "sample_size": "INTEGER NOT NULL DEFAULT 0",
            "consecutive_failures": "INTEGER NOT NULL DEFAULT 0",
        },
        "sim_runs": {
            "is_rumor": "BOOLEAN NOT NULL DEFAULT 0",
            "warnings": "TEXT",
            "degraded": "TEXT",
        },
    }

    # -- P3-5: seed yang tidak boleh menimpa data -----------------------------
    #: Universe terkunci yang harus selalu ada di `asset_master`.
    #:
    #: Nilainya diambil dari `data/universe/asset_master.csv` dan
    #: `LOCKED_UNIVERSE` (XAU, RATE_UST, SPX) -- bukan dikarang. `price_ticker`
    #: NOT NULL di DDL, jadi tidak boleh None.
    #:
    #: Hanya diisi bila BELUM ada (ON CONFLICT DO NOTHING), sehingga tidak
    #: pernah menimpa nama/harga/status yang sudah diubah lewat seed CSV.
    SEED_ASSET_MASTER: tuple[tuple, ...] = (
        # (asset_id, asset_class, track, name, price_ticker, exchange,
        #  country, sector, timezone, session_close, valid_from, valid_to,
        #  active)
        ("XAU", "commodity", "B", "Gold", "GC=F", "CME", "US", "",
         "America/New_York", "17:00", "2026-10-12-core3", None, 1),
        ("RATE_UST", "rate", "B", "US 10-Year Treasury Yield", "^TNX", "CBOE",
         "US", "", "America/New_York", "15:00", "2026-10-12-core3", None, 1),
        ("SPX", "index", "B", "S&P 500", "^GSPC", "SNP", "US", "",
         "America/New_York", "16:00", "2026-10-12-core3", None, 1),
    )

    @classmethod
    def versi_skema(cls, conn: sqlite3.Connection) -> int:
        """Baca versi skema DB dari `PRAGMA user_version`.

        Sengaja TIDAK menebak dari keberadaan tabel. Percobaan pertama saya
        memakai `sqlite_master` untuk menilai "DB ini sudah v1", dan hasilnya
        salah: DB lama yang semua tabelnya ada tetapi belum punya kolom susulan
        dinilai v1 -- persis bug yang P3-5 perbaiki.
        `user_version` disetel `_migrate` hanya SETELAH migrasi selesai, jadi
        nol berarti "belum pernah dimigrasi oleh kode ini". Itu satu-satunya
        sinyal yang tidak bisa menipu.
        """
        return int(conn.execute("PRAGMA user_version;").fetchone()[0])

    @classmethod
    def skema_tidak_lengkap(cls, conn: sqlite3.Connection) -> list[str]:
        """Daftar kolom yang hilang, tanpa mengubah apa pun.

        Dipakai `fi check-schema` supaya masalah ini bisa dideteksi SEBELUM
        query gagal di produksi, bukan sesudahnya.
        """
        hilang: list[str] = []
        for tabel, kolom in cls.KOLOM_WAJIB.items():
            info = conn.execute(f"PRAGMA table_info({tabel});").fetchall()
            if not info:
                hilang.append(f"{tabel} (tabel tidak ada)")
                continue
            ada = {r["name"] for r in info}
            for nama in kolom:
                if nama not in ada:
                    hilang.append(f"{tabel}.{nama}")
        return hilang

    @staticmethod
    def _tambah_kolom(conn: sqlite3.Connection, tabel: str, kolom: str, ddl: str) -> bool:
        """Tambahkan satu kolom bila belum ada. True bila benar-benar ditambah."""
        info = conn.execute(f"PRAGMA table_info({tabel});").fetchall()
        if not info:  # tabel belum ada; DDL akan membuatnya lengkap
            return False
        if kolom in {r["name"] for r in info}:
            return False
        conn.execute(f"ALTER TABLE {tabel} ADD COLUMN {kolom} {ddl};")
        return True

    @classmethod
    def _migrate(cls, conn: sqlite3.Connection) -> None:
        """Lengkapi kolom yang hilang pada tabel yang sudah ada.

        Idempoten dan aman diulang. Mencakup SEMUA tabel di `KOLOM_WAJIB`,
        bukan hanya `impacts` seperti sebelumnya.
        """
        for tabel, kolom in cls.KOLOM_WAJIB.items():
            for nama, ddl in kolom.items():
                cls._tambah_kolom(conn, tabel, nama, ddl)
        conn.execute(f"PRAGMA user_version = {int(cls.SCHEMA_VERSION)};")

    @classmethod
    def _seed_schema_data(cls, conn: sqlite3.Connection) -> None:
        """Isi baris wajib bila belum ada. Tidak pernah menimpa data pengguna."""
        for baris in cls.SEED_ASSET_MASTER:
            conn.execute(
                """
                INSERT INTO asset_master (
                    asset_id, asset_class, track, name, price_ticker, exchange,
                    country, sector, timezone, session_close, valid_from,
                    valid_to, active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(asset_id) DO NOTHING;
                """,
                baris,
            )

    @staticmethod
    def _migrate_versi_lama(conn: sqlite3.Connection) -> None:
        """Placeholder: langkah migrasi per-versi ditambahkan di sini.

        Disengaja kosong untuk v1. Saat `SCHEMA_VERSION` naik, tambahkan
        langkah yang mengubah struktur (bukan sekadar menambah kolom) di sini,
        lalu panggil dari `_migrate`.
        """

    # --- Status preload berita (job 07:00 WIB) ------------------------------
    #: Batas waktu klaim slot (detik). Proses yang mati di tengah jalan tidak
    #: boleh mengunci slot selamanya, jadi klaim yang lebih tua dari ini
    #: dianggap kedaluwarsa dan boleh diambil alih.
    CLAIM_TIMEOUT_SECONDS: int = 15 * 60

    def claim_ingest_slot(
        self,
        trigger: str,
        scheduled_for: str | None,
        timeout_seconds: int | None = None,
    ) -> int | None:
        """Klaim satu slot secara ATOMIK; None bila slot sudah diklaim proses lain.

        Kenapa perlu: `start_ingest_run` hanya INSERT, lalu `run_preload`
        langsung menembak eulerpool. Dua proses (mis. uvicorn --workers 2, atau
        proses lama yang belum mati saat restart) sama-sama INSERT berstatus
        'running', sama-sama lanjut menarik data, dan kuota harian terbakar dua
        kali. Kunci di level DB harus diambil SEBELUM panggilan jaringan.

        Satu-satunya statement INSERT...SELECT di bawah berjalan atomik di
        SQLite (satu transaksi tulis), sehingga hanya satu pemanggil yang bisa
        menyisipkan baris untuk slot yang sama. Klaim yang lebih tua dari
        `timeout_seconds` dianggap milik proses yang sudah mati dan boleh
        diambil alih, supaya crash tidak mengunci slot selamanya.
        """
        batas_detik = (
            self.CLAIM_TIMEOUT_SECONDS if timeout_seconds is None else int(timeout_seconds)
        )
        batas = (datetime.now() - timedelta(seconds=batas_detik)).isoformat()
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO ingest_runs (trigger, status, started_at, scheduled_for)
                SELECT ?, 'running', ?, ?
                WHERE NOT EXISTS (
                    SELECT 1 FROM ingest_runs
                    WHERE scheduled_for IS ?
                      AND status = 'running'
                      AND started_at > ?
                );
                """,
                (trigger, datetime.now().isoformat(), scheduled_for, scheduled_for, batas),
            )
            if cur.rowcount == 0:
                return None
            return int(cur.lastrowid or 0)

    def start_ingest_run(
        self,
        trigger: str,
        scheduled_for: str | None = None,
    ) -> int:
        """Catat awal satu run preload; kembalikan run_id untuk diakhiri nanti.

        Tidak mengklaim slot -- dipakai untuk run manual yang memang boleh
        berjalan berdampingan. Untuk job terjadwal pakai `claim_ingest_slot`.
        """
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO ingest_runs (trigger, status, started_at, scheduled_for)
                VALUES (?, 'running', ?, ?);
                """,
                (trigger, datetime.now().isoformat(), scheduled_for),
            )
            return int(cur.lastrowid or 0)

    def finish_ingest_run(
        self,
        run_id: int,
        status: str,
        *,
        raw_new: int = 0,
        articles_clean: int = 0,
        impacts_new: int = 0,
        detail: str | None = None,
    ) -> None:
        """Tutup run preload. status: 'ok' | 'partial' | 'failed'."""
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE ingest_runs
                   SET status = ?, finished_at = ?, raw_new = ?,
                       articles_clean = ?, impacts_new = ?, detail = ?
                 WHERE run_id = ?;
                """,
                (status, datetime.now().isoformat(), raw_new, articles_clean,
                 impacts_new, detail, run_id),
            )

    def has_run_for_slot(self, scheduled_for: str) -> bool:
        """True bila slot ini sudah punya run yang membawa data (ok/no_new).

        Dipakai scheduler saat startup: tanpa ini, setiap restart aplikasi
        akan mengulang tarikan untuk slot yang sama dan membakar kuota harian
        eulerpool. Run 'failed'/'partial' sengaja TIDAK dihitung, supaya
        kegagalan tetap bisa dicoba ulang.
        """
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT 1 FROM ingest_runs
                 WHERE scheduled_for = ?
                   AND status IN ('ok', 'no_new')
                 LIMIT 1;
                """,
                (scheduled_for,),
            ).fetchone()
            return row is not None

    def last_ingest_run(self) -> dict | None:
        """Run terakhir yang selesai (status != 'running'), untuk cap waktu GUI.

        Mengembalikan None bila belum pernah ada preload. GUI memakai ini untuk
        menyatakan "data per <waktu>", bukan mengarang saat API mati.
        """
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM ingest_runs
                 WHERE status != 'running'
                 ORDER BY finished_at DESC
                 LIMIT 1;
                """
            ).fetchone()
            return dict(row) if row else None

    def seed_asset_master(self, csv_path: Path | str = Path("data/universe/asset_master.csv")) -> int:
        """Seeds the 3 core locked assets from asset_master.csv."""
        csv_file = Path(csv_path)
        if not csv_file.exists():
            return 0

        inserted = 0
        import csv
        with open(csv_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            with self.get_connection() as conn:
                for row in reader:
                    conn.execute(
                        """
                        INSERT INTO asset_master (
                            asset_id, asset_class, track, name, price_ticker, exchange,
                            country, sector, timezone, session_close, valid_from, valid_to, active
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(asset_id) DO UPDATE SET
                            name = excluded.name,
                            price_ticker = excluded.price_ticker,
                            session_close = excluded.session_close,
                            active = excluded.active;
                        """,
                        (
                            row["asset_id"],
                            row["asset_class"],
                            row["track"],
                            row["name"],
                            row["price_ticker"],
                            row["exchange"] or None,
                            row["country"] or None,
                            row["sector"] or None,
                            row["timezone"],
                            row["session_close"],
                            row["valid_from"],
                            row["valid_to"] or None,
                            1 if row["active"].lower() in ("true", "1") else 0,
                        ),
                    )
                    inserted += 1
                # Deactivate retired assets missing from the CSV so existing
                # databases transition cleanly to the pruned universe.
                with open(csv_file, mode="r", encoding="utf-8") as f2:
                    keep = {r["asset_id"] for r in csv.DictReader(f2)}
                if keep:
                    placeholders = ",".join("?" for _ in keep)
                    conn.execute(
                        f"UPDATE asset_master SET active = 0 WHERE asset_id NOT IN ({placeholders});",
                        tuple(keep),
                    )
        return inserted

    def seed_aliases(self, csv_path: Path | str = Path("data/universe/aliases.csv")) -> int:
        """Seeds asset aliases from aliases.csv."""
        csv_file = Path(csv_path)
        if not csv_file.exists():
            return 0

        import csv
        inserted = 0
        with open(csv_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            with self.get_connection() as conn:
                conn.execute("DELETE FROM asset_aliases;")
                for row in reader:
                    conn.execute(
                        "INSERT INTO asset_aliases (asset_id, alias, lang) VALUES (?, ?, ?);",
                        (row["asset_id"], row["alias"].strip().lower(), row["lang"]),
                    )
                    inserted += 1
        return inserted

    def save_impact(self, impact: TargetImpact) -> None:
        """Stores a TargetImpact record."""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO impacts (
                    article_id, asset_id, direction, score, confidence, basis,
                    themes_json, causal_path_json, rationale, evidence_json, flags_json,
                    news_horizon, model_version, routed_from, route_score, universe_version,
                    schema_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    impact.article_id,
                    impact.asset_id,
                    impact.direction.value,
                    impact.score,
                    impact.confidence,
                    impact.basis.value,
                    json.dumps(impact.themes),
                    json.dumps(impact.causal_path) if impact.causal_path else None,
                    impact.rationale,
                    json.dumps([e.model_dump() for e in impact.evidence]),
                    json.dumps(impact.flags),
                    impact.news_horizon.value
                    if hasattr(impact.news_horizon, "value")
                    else str(impact.news_horizon),
                    impact.model_version,
                    impact.routed_from,
                    impact.route_score,
                    impact.universe_version,
                    impact.schema_version,
                    impact.created_at.isoformat(),
                ),
            )

    def save_daily_sentiment(self, daily: DailySentiment) -> None:
        """Stores daily aggregate sentiment for an asset."""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO daily_sentiment (
                    asset_id, date, score_mean, score_weighted,
                    n_articles, n_sources, has_news, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    daily.asset_id,
                    daily.date.isoformat(),
                    daily.score_mean,
                    daily.score_weighted,
                    daily.n_articles,
                    daily.n_sources,
                    1 if daily.has_news else 0,
                    daily.version,
                ),
            )

    def save_price(self, price: PriceRecord) -> None:
        """Stores a daily asset price."""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO prices (
                    asset_id, date, open, high, low, close, adj_close, volume
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    price.asset_id,
                    price.date.isoformat(),
                    price.open,
                    price.high,
                    price.low,
                    price.close,
                    price.adj_close,
                    price.volume,
                ),
            )

    # ==========================================================
    # CRUD: raw_articles — berita mentah dari API/RSS
    # ==========================================================

    def save_raw_article(
        self, raw: RawArticle, payload: dict | None = None
    ) -> int:
        """Stores a raw (unnormalized) article. Returns raw_id.

        Deduplikasi memakai (source, url) bila URL tersedia, selain itu
        (source, title). Baris identik tidak digandakan.
        """
        with self.get_connection() as conn:
            if raw.url:
                existing = conn.execute(
                    "SELECT raw_id FROM raw_articles WHERE source = ? AND url = ? LIMIT 1;",
                    (raw.source, raw.url),
                ).fetchone()
            else:
                existing = conn.execute(
                    "SELECT raw_id FROM raw_articles WHERE source = ? AND title = ? LIMIT 1;",
                    (raw.source, raw.title),
                ).fetchone()
            if existing:
                return int(existing["raw_id"])

            cur = conn.execute(
                """
                INSERT INTO raw_articles (
                    source, url, title, body, published_at, fetched_at,
                    query_target, vendor_sentiment, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    raw.source,
                    raw.url,
                    raw.title,
                    raw.body,
                    raw.published_at.isoformat() if raw.published_at else None,
                    raw.fetched_at.isoformat(),
                    raw.query_target,
                    raw.vendor_sentiment,
                    json.dumps(payload) if payload else None,
                ),
            )
            return int(cur.lastrowid or 0)

    def save_raw_articles(
        self, items: list[tuple[RawArticle, dict | None]]
    ) -> int:
        """Bulk insert. Returns jumlah baris baru."""
        inserted = 0
        with self.get_connection() as conn:
            for raw, payload in items:
                if raw.url:
                    existing = conn.execute(
                        "SELECT 1 FROM raw_articles WHERE source = ? AND url = ? LIMIT 1;",
                        (raw.source, raw.url),
                    ).fetchone()
                else:
                    existing = conn.execute(
                        "SELECT 1 FROM raw_articles WHERE source = ? AND title = ? LIMIT 1;",
                        (raw.source, raw.title),
                    ).fetchone()
                if existing:
                    continue
                conn.execute(
                    """
                    INSERT INTO raw_articles (
                        source, url, title, body, published_at, fetched_at,
                        query_target, vendor_sentiment, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        raw.source,
                        raw.url,
                        raw.title,
                        raw.body,
                        raw.published_at.isoformat() if raw.published_at else None,
                        raw.fetched_at.isoformat(),
                        raw.query_target,
                        raw.vendor_sentiment,
                        json.dumps(payload) if payload else None,
                    ),
                )
                inserted += 1
        return inserted

    def query_raw_articles(
        self, source: str | None = None, limit: int = 100
    ) -> list[dict]:
        """Returns raw articles, terbaru dulu."""
        query = "SELECT * FROM raw_articles"
        params: list = []
        if source:
            query += " WHERE source LIKE ?"
            params.append(f"{source}%")
        query += " ORDER BY fetched_at DESC LIMIT ?;"
        params.append(limit)
        with self.get_connection() as conn:
            return [dict(r) for r in conn.execute(query, params).fetchall()]

    def count_raw_articles(self) -> int:
        with self.get_connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM raw_articles;").fetchone()
            return int(row["n"]) if row else 0

    # ==========================================================
    # CRUD: articles — berita ternormalisasi (punya article_id)
    # ==========================================================

    def save_article(self, article: Article) -> None:
        """Stores a normalized article."""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO articles (
                    article_id, source, url, title, body, language,
                    published_at, fetched_at, duplicate_of, market_relevant
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    article.article_id,
                    article.source,
                    article.url,
                    article.title,
                    article.body,
                    article.language.value,
                    article.published_at.isoformat() if article.published_at else None,
                    article.fetched_at.isoformat(),
                    article.duplicate_of,
                    None if article.market_relevant is None else (1 if article.market_relevant else 0),
                ),
            )

    def save_articles(self, articles: list[Article]) -> int:
        """Bulk insert normalized articles. Returns jumlah baris ditulis."""
        with self.get_connection() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO articles (
                    article_id, source, url, title, body, language,
                    published_at, fetched_at, duplicate_of, market_relevant
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                [
                    (
                        a.article_id,
                        a.source,
                        a.url,
                        a.title,
                        a.body,
                        a.language.value,
                        a.published_at.isoformat() if a.published_at else None,
                        a.fetched_at.isoformat(),
                        a.duplicate_of,
                        None if a.market_relevant is None else (1 if a.market_relevant else 0),
                    )
                    for a in articles
                ],
            )
        return len(articles)

    def get_article(self, article_id: str) -> dict | None:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM articles WHERE article_id = ?;", (article_id,)
            ).fetchone()
            return dict(row) if row else None

    def article_exists(self, article_id: str) -> bool:
        with self.get_connection() as conn:
            return (
                conn.execute(
                    "SELECT 1 FROM articles WHERE article_id = ? LIMIT 1;", (article_id,)
                ).fetchone()
                is not None
            )

    def query_articles(
        self, limit: int = 100, since: date | None = None
    ) -> list[dict]:
        query = "SELECT * FROM articles"
        params: list = []
        if since:
            query += " WHERE date(fetched_at) >= ?"
            params.append(since.isoformat())
        query += " ORDER BY fetched_at DESC LIMIT ?;"
        params.append(limit)
        with self.get_connection() as conn:
            return [dict(r) for r in conn.execute(query, params).fetchall()]

    def count_articles(self) -> int:
        with self.get_connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM articles;").fetchone()
            return int(row["n"]) if row else 0

    # ==========================================================
    # CRUD: article_targets — pemetaan berita ke target universe
    # ==========================================================

    def save_article_target(
        self,
        article_id: str,
        tag: TargetTag,
        effective_trading_date: date | None = None,
    ) -> None:
        """Stores one article→target mapping."""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO article_targets (
                    article_id, asset_id, basis, matched_text, routed_from,
                    effective_trading_date
                ) VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    article_id,
                    tag.asset_id,
                    tag.basis.value,
                    tag.matched_text,
                    tag.routed_from,
                    effective_trading_date.isoformat() if effective_trading_date else None,
                ),
            )

    def save_article_targets(
        self,
        article_id: str,
        tags: list[TargetTag],
        effective_dates: dict[str, date] | None = None,
    ) -> int:
        """Bulk insert mappings untuk satu artikel. Returns jumlah baris."""
        dates = effective_dates or {}
        with self.get_connection() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO article_targets (
                    article_id, asset_id, basis, matched_text, routed_from,
                    effective_trading_date
                ) VALUES (?, ?, ?, ?, ?, ?);
                """,
                [
                    (
                        article_id,
                        t.asset_id,
                        t.basis.value,
                        t.matched_text,
                        t.routed_from,
                        dates[t.asset_id].isoformat() if t.asset_id in dates else None,
                    )
                    for t in tags
                ],
            )
        return len(tags)

    def query_article_targets(self, article_id: str) -> list[dict]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM article_targets WHERE article_id = ?;", (article_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def query_articles_by_target(
        self, asset_id: str, limit: int = 50
    ) -> list[dict]:
        """Berita untuk satu target, join ke tabel articles."""
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT a.*, t.basis, t.matched_text, t.effective_trading_date
                FROM article_targets t
                JOIN articles a ON a.article_id = t.article_id
                WHERE t.asset_id = ?
                ORDER BY a.published_at DESC, a.fetched_at DESC
                LIMIT ?;
                """,
                (asset_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    # ==========================================================
    # CRUD: sentiments — keluaran model per artikel
    # ==========================================================

    def save_sentiment(self, sentiment: ArticleSentiment) -> None:
        """Stores all ModelProbs for an article (satu baris per model)."""
        with self.get_connection() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO sentiments (
                    article_id, model, model_version, p_pos, p_neu, p_neg,
                    translation_used, translator_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                [
                    (
                        sentiment.article_id,
                        p.model,
                        p.model_version,
                        p.p_pos,
                        p.p_neu,
                        p.p_neg,
                        1 if sentiment.translation_used else 0,
                        sentiment.translator_version,
                        datetime.now().isoformat(),
                    )
                    for p in sentiment.probs
                ],
            )

    def query_sentiments(self, article_id: str) -> list[dict]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM sentiments WHERE article_id = ?;", (article_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    # ==========================================================
    # CRUD: labels — anotasi manusia (untuk Cohen's kappa)
    # ==========================================================

    def save_label(
        self,
        article_id: str,
        asset_id: str,
        annotator: str,
        label: str,
        labeled_at: datetime | None = None,
    ) -> None:
        """Stores one human annotation."""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO labels (
                    article_id, asset_id, annotator, label, labeled_at
                ) VALUES (?, ?, ?, ?, ?);
                """,
                (
                    article_id,
                    asset_id,
                    annotator,
                    label,
                    (labeled_at or datetime.now()).isoformat(),
                ),
            )

    def save_labels(self, rows: list[dict]) -> int:
        """Bulk insert labels. Each dict: article_id, asset_id, annotator, label."""
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO labels (
                    article_id, asset_id, annotator, label, labeled_at
                ) VALUES (?, ?, ?, ?, ?);
                """,
                [
                    (
                        r["article_id"],
                        r["asset_id"],
                        r["annotator"],
                        r["label"],
                        r.get("labeled_at", now),
                    )
                    for r in rows
                ],
            )
        return len(rows)

    def query_labels(
        self, asset_id: str | None = None, annotator: str | None = None
    ) -> list[dict]:
        query = "SELECT * FROM labels"
        clauses: list[str] = []
        params: list = []
        if asset_id:
            clauses.append("asset_id = ?")
            params.append(asset_id)
        if annotator:
            clauses.append("annotator = ?")
            params.append(annotator)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY labeled_at DESC;"
        with self.get_connection() as conn:
            return [dict(r) for r in conn.execute(query, params).fetchall()]

    def count_labels(self) -> int:
        with self.get_connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM labels;").fetchone()
            return int(row["n"]) if row else 0

    def get_active_universe(self) -> list[dict]:
        """Returns all 3 active core universe assets."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM asset_master WHERE active = 1 ORDER BY asset_id ASC;"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_meta_summary(self) -> dict:
        """Returns real provenance facts for GET /api/meta.

        Everything comes from a table count or version column, so the GUI
        provenance bar can show fresh vs stale data without guessing.
        """
        with self.get_connection() as conn:
            universe = conn.execute(
                "SELECT asset_id, valid_from FROM asset_master WHERE active = 1 ORDER BY asset_id ASC;"
            ).fetchall()
            universe_versions = sorted({r["valid_from"] for r in universe if r["valid_from"]})

            def scalar(sql: str) -> object:
                return conn.execute(sql).fetchone()[0]

            last_price = scalar("SELECT MAX(date) FROM prices;")
            last_sentiment = scalar("SELECT MAX(date) FROM daily_sentiment;")
            last_impact = scalar("SELECT MAX(created_at) FROM impacts;")
            stamp = max(
                [str(last_price or ""), str(last_sentiment or ""), str(last_impact or "")] or [""]
            )
            return {
                "universe_count": len(universe),
                "targets": [r["asset_id"] for r in universe],
                "universe_version": universe_versions[0] if len(universe_versions) == 1 else (universe_versions[0] if universe_versions else None),
                "articles": scalar("SELECT COUNT(*) FROM articles;"),
                "sources": scalar("SELECT COUNT(DISTINCT source) FROM articles;"),
                "days_with_news": scalar("SELECT COUNT(DISTINCT date) FROM daily_sentiment WHERE has_news = 1;"),
                "last_price_date": str(last_price) if last_price else None,
                "last_news_date": str(last_sentiment) if last_sentiment else None,
                "last_impact_at": str(last_impact) if last_impact else None,
                "updated_at": stamp or None,
                "params_version": scalar("SELECT MAX(params_version) FROM persona_views;"),
                "model_version": scalar("SELECT MAX(model_version) FROM impacts;"),
                "schema_version": scalar("SELECT MAX(schema_version) FROM impacts;"),
            }

    def is_valid_target(self, target: str) -> bool:
        """Checks if a target belongs to the 3 core locked universe."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM asset_master WHERE asset_id = ? AND active = 1;", (target,)
            ).fetchone()
            if row:
                return True
            # Fallback if DB not seeded yet
            locked = {"XAU", "RATE_UST", "SPX"}
            return target in locked

    def query_daily_sentiment(
        self, asset_id: str, start_date: date, end_date: date
    ) -> list[DailySentiment]:
        """Queries daily sentiment records between dates."""
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT asset_id, date, score_mean, score_weighted, n_articles, n_sources, has_news, version
                FROM daily_sentiment
                WHERE asset_id = ? AND date >= ? AND date <= ?
                ORDER BY date ASC;
                """,
                (asset_id, start_date.isoformat(), end_date.isoformat()),
            ).fetchall()

            res: list[DailySentiment] = []
            for r in rows:
                res.append(
                    DailySentiment(
                        asset_id=r["asset_id"],
                        date=date.fromisoformat(r["date"]),
                        score_mean=r["score_mean"],
                        score_weighted=r["score_weighted"],
                        n_articles=r["n_articles"],
                        n_sources=r["n_sources"],
                        has_news=bool(r["has_news"]),
                        version=r["version"],
                    )
                )
            return res

    def query_prices(
        self, asset_id: str, start_date: date, end_date: date
    ) -> list[PriceRecord]:
        """Queries price records between dates."""
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT asset_id, date, open, high, low, close, adj_close, volume
                FROM prices
                WHERE asset_id = ? AND date >= ? AND date <= ?
                ORDER BY date ASC;
                """,
                (asset_id, start_date.isoformat(), end_date.isoformat()),
            ).fetchall()

            res: list[PriceRecord] = []
            for r in rows:
                res.append(
                    PriceRecord(
                        asset_id=r["asset_id"],
                        date=date.fromisoformat(r["date"]),
                        open=r["open"],
                        high=r["high"],
                        low=r["low"],
                        close=r["close"],
                        adj_close=r["adj_close"],
                        volume=r["volume"],
                    )
                )
            return res

    def query_impacts(self, asset_id: str, limit: int = 50) -> list[TargetImpact]:
        """Queries recent target impacts, terbaru menurut waktu terbit.

        Diurutkan menurut `articles.published_at`, bukan `impacts.created_at`.
        `created_at` adalah kapan baris ditulis (kapan pipeline jalan): saat
        beberapa hari berita di-ingest sekaligus, seluruh backlog mendapat
        `created_at` yang hampir sama sehingga urutannya jadi urutan ingest,
        bukan urutan terbit. Akibatnya berita tertua bisa muncul paling atas.

        `published_at` NULL (sumber tanpa tanggal) ditaruh paling bawah;
        SQLite menganggap NULL lebih kecil dari nilai apa pun, jadi ia natural
        terlempar ke akhir pada DESC. `created_at` jadi pemecah seri agar
        urutan tetap deterministik.
        """
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT i.* FROM impacts i
                LEFT JOIN articles a ON a.article_id = i.article_id
                WHERE i.asset_id = ?
                ORDER BY a.published_at DESC, i.created_at DESC
                LIMIT ?;
                """,
                (asset_id, limit),
            ).fetchall()

            res: list[TargetImpact] = []
            for r in rows:
                from backend.src.schema import Basis, Direction, EvidenceSpan
                themes = json.loads(r["themes_json"]) if r["themes_json"] else []
                causal = json.loads(r["causal_path_json"]) if r["causal_path_json"] else None
                evidence_raw = json.loads(r["evidence_json"]) if r["evidence_json"] else []
                flags = json.loads(r["flags_json"]) if r["flags_json"] else []

                evidence = [EvidenceSpan(**e) for e in evidence_raw]

                res.append(
                    TargetImpact(
                        article_id=r["article_id"],
                        asset_id=r["asset_id"],
                        direction=Direction(r["direction"]),
                        score=r["score"],
                        confidence=r["confidence"],
                        basis=Basis(r["basis"]),
                        themes=themes,
                        causal_path=causal,
                        rationale=r["rationale"],
                        evidence=evidence,
                        flags=flags,
                        model_version=r["model_version"],
                        routed_from=r["routed_from"],
                        route_score=r["route_score"],
                        universe_version=r["universe_version"],
                        schema_version=r["schema_version"],
                        created_at=datetime.fromisoformat(r["created_at"]),
                    )
                )
            return res

    def query_impact_time_audit(self, asset_id: str, limit: int = 50) -> list[dict]:
        """Joins impacts with article metadata, session cut-off, and model probs.

        Feeds UI-02 time auditing and UI-03 evidence provenance: a reader can
        trace each impact from published_at to its market session bucket, and
        from the score back to per-model class probabilities.
        """
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT i.article_id, a.published_at, a.language, a.title, a.source, a.url,
                       CASE WHEN a.body IS NULL THEN 1 ELSE 0 END AS headline_only,
                       t.effective_trading_date, m.session_close, m.timezone
                FROM impacts i
                LEFT JOIN articles a
                    ON a.article_id = i.article_id
                LEFT JOIN article_targets t
                    ON t.article_id = i.article_id AND t.asset_id = i.asset_id
                JOIN asset_master m
                    ON m.asset_id = i.asset_id
                WHERE i.asset_id = ?
                ORDER BY a.published_at DESC, i.created_at DESC
                LIMIT ?;
                """,
                (asset_id, limit),
            ).fetchall()
            out = [dict(r) for r in rows]
            ids = [r["article_id"] for r in out]
            probs: dict[str, list] = {}
            if ids:
                marks = ",".join("?" for _ in ids)
                srows = conn.execute(
                    f"""
                    SELECT article_id, model, model_version, p_pos, p_neu, p_neg, translation_used
                    FROM sentiments
                    WHERE article_id IN ({marks});
                    """,
                    ids,
                ).fetchall()
                for s in srows:
                    probs.setdefault(s["article_id"], []).append(dict(s))
            for r in out:
                r["probs"] = probs.get(r["article_id"], [])
            return out

    def save_stat(self, stat: StatResult) -> None:
        """Stores econometric test result."""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO stat_results (
                    run_id, asset_id, test, market_metric, lag, estimate,
                    ci_low, ci_high, p_value, p_adjusted, n_obs,
                    period_start, period_end, params_json, code_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    stat.run_id,
                    stat.asset_id,
                    stat.test,
                    stat.market_metric,
                    stat.lag,
                    stat.estimate,
                    stat.ci_low,
                    stat.ci_high,
                    stat.p_value,
                    stat.p_adjusted,
                    stat.n_obs,
                    stat.period_start.isoformat(),
                    stat.period_end.isoformat(),
                    stat.params_json,
                    stat.code_version,
                ),
            )

    def query_stats(self, asset_id: str) -> list[StatResult]:
        """Queries recent econometric results for asset."""
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM stat_results
                WHERE asset_id = ?
                ORDER BY rowid DESC
                LIMIT 50;
                """,
                (asset_id,),
            ).fetchall()

            res: list[StatResult] = []
            for r in rows:
                res.append(
                    StatResult(
                        run_id=r["run_id"],
                        asset_id=r["asset_id"],
                        test=r["test"],
                        market_metric=r["market_metric"],
                        lag=r["lag"],
                        estimate=r["estimate"],
                        ci_low=r["ci_low"],
                        ci_high=r["ci_high"],
                        p_value=r["p_value"],
                        p_adjusted=r["p_adjusted"],
                        n_obs=r["n_obs"],
                        period_start=date.fromisoformat(r["period_start"]),
                        period_end=date.fromisoformat(r["period_end"]),
                        params_json=r["params_json"],
                        code_version=r["code_version"],
                    )
                )
            return res

    # ------------------------------------------------------------------
    # S-2: persist hasil persona & alokasi agar bisa diaudit ulang
    # ------------------------------------------------------------------

    def save_persona_views(self, views: list) -> int:
        """Simpan PersonaView ke tabel `persona_views`.

        NFR reproducibility: hasil yang hanya dikembalikan lewat API lalu
        dibuang tidak bisa diperiksa ulang atau direproduksi.
        """
        if not views:
            return 0
        rows = [
            (
                v.article_id,
                v.persona_id,
                v.target,
                v.stance.value if hasattr(v.stance, "value") else str(v.stance),
                float(v.strength),
                (
                    v.news_horizon.value
                    if hasattr(v.news_horizon, "value")
                    else str(v.news_horizon)
                ),
                float(v.raw_value),
                float(v.confidence),
                getattr(v, "rationale", None),
                getattr(v, "params_version", "unknown"),
                datetime.now().isoformat(sep=" ", timespec="seconds"),
            )
            for v in views
        ]
        with self.get_connection() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO persona_views (
                    article_id, persona_id, target, stance, strength,
                    news_horizon, raw_value, confidence, rationale,
                    params_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                rows,
            )
        return len(rows)

    def save_alloc_suggestion(self, suggestion) -> int:
        """Simpan AllocationSuggestion beserta seluruh barisnya.

        `article_id` pada tabel adalah kunci simpanan; untuk tilt pasar
        (bukan artikel) dipakai penanda seperti ``current_market``.
        """
        created = getattr(suggestion, "created_at", None) or datetime.now()
        if hasattr(created, "isoformat"):
            created_s = created.isoformat(sep=" ", timespec="seconds")
        else:
            created_s = str(created)

        rows = [
            (
                suggestion.article_id,
                line.alloc_class.value
                if hasattr(line.alloc_class, "value")
                else str(line.alloc_class),
                suggestion.profile_id,
                float(line.baseline_pct),
                float(line.new_pct),
                float(line.delta_pp),
                float(line.confidence),
                getattr(line, "rationale", None),
                1 if getattr(line, "no_change", False) else 0,
                suggestion.params_version,
                created_s,
            )
            for line in suggestion.lines
        ]
        with self.get_connection() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO alloc_suggestions (
                    article_id, alloc_class, profile_id, baseline_pct, new_pct,
                    delta_pp, confidence, rationale, no_change,
                    params_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                rows,
            )
        return len(rows)

    def get_persona_views(self, article_id: str, target: str | None = None) -> list[dict]:
        """Baca kembali persona_views yang tersimpan (untuk audit)."""
        q = "SELECT * FROM persona_views WHERE article_id = ?"
        params: list = [article_id]
        if target:
            q += " AND target = ?"
            params.append(target)
        q += " ORDER BY persona_id ASC;"
        with self.get_connection() as conn:
            return [dict(r) for r in conn.execute(q, params).fetchall()]

    def get_alloc_suggestions(self, article_id: str) -> list[dict]:
        """Baca kembali alloc_suggestions yang tersimpan (untuk audit)."""
        with self.get_connection() as conn:
            return [
                dict(r)
                for r in conn.execute(
                    "SELECT * FROM alloc_suggestions WHERE article_id = ? "
                    "ORDER BY alloc_class ASC;",
                    (article_id,),
                ).fetchall()
            ]

    def get_impact_for_article(self, article_id: str, asset_id: str) -> dict | None:
        """Dampak satu artikel pada satu aset, atau None bila tidak ada.

        Dipakai endpoint persona: angka yang ditampilkan harus berasal dari
        analisis yang tercatat, bukan nilai bawaan fungsi.
        """
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT article_id, asset_id, direction, score, confidence, basis,
                       news_horizon
                FROM impacts WHERE article_id = ? AND asset_id = ?
                ORDER BY confidence DESC LIMIT 1;
                """,
                (article_id, asset_id),
            ).fetchone()
            return dict(row) if row else None

    def get_daily_series(self, asset_id: str, start_date: Optional[date] = None) -> list[dict]:
        """Retrieves joint sentiment and price series for a target."""
        query = """
            SELECT
                p.date,
                p.close,
                p.volume,
                d.score_mean,
                d.n_articles,
                d.has_news
            FROM prices p
            LEFT JOIN daily_sentiment d ON p.asset_id = d.asset_id AND p.date = d.date
            WHERE p.asset_id = ?
        """
        params: list[str] = [asset_id]
        if start_date:
            query += " AND p.date >= ?"
            params.append(start_date.isoformat())
        query += " ORDER BY p.date ASC;"

        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # T-3: kesehatan sumber (FR-18)
    # ------------------------------------------------------------------

    #: Status yang dianggap gagal. `no_key` TIDAK dihitung gagal: itu kondisi
    #: konfigurasi yang disengaja, bukan sumber yang mati.
    FAILURE_STATUSES = frozenset({"unauthorized", "rate_limited", "error"})

    def save_source_health(
        self,
        source: str,
        status: str,
        detail: str = "",
        latency_ms: float | None = None,
        sample_size: int = 0,
        usable: bool = False,
        checked_at: datetime | None = None,
    ) -> int:
        """Catat satu hasil pemeriksaan kesehatan sumber.

        Mengembalikan jumlah kegagalan BERTURUT-TURUT untuk sumber ini
        (0 bila pemeriksaan ini berhasil). Nilai itu yang dipakai untuk
        memutuskan kapan alert perlu berbunyi.
        """
        ts = (checked_at or datetime.now()).replace(microsecond=0)
        is_failure = status in self.FAILURE_STATUSES

        with self.get_connection() as conn:
            if is_failure:
                row = conn.execute(
                    """
                    SELECT consecutive_failures FROM source_health
                    WHERE source = ? ORDER BY checked_at DESC LIMIT 1;
                    """,
                    (source,),
                ).fetchone()
                streak = (int(row["consecutive_failures"]) if row else 0) + 1
            else:
                streak = 0

            conn.execute(
                """
                INSERT INTO source_health (
                    source, checked_at, status, is_failure, usable,
                    latency_ms, detail, sample_size, consecutive_failures
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    source,
                    ts.isoformat(sep=" "),
                    status,
                    1 if is_failure else 0,
                    1 if usable else 0,
                    latency_ms,
                    detail[:500] if detail else None,
                    int(sample_size),
                    streak,
                ),
            )
        return streak

    def latest_source_health(self) -> list[dict]:
        """Status terakhir tiap sumber, satu baris per sumber.

        Memakai `rowid` sebagai pemecah seri: `checked_at` beresolusi detik,
        sehingga beberapa pemeriksaan dalam detik yang sama akan membuat
        `MAX(checked_at)` cocok ke banyak baris sekaligus.
        """
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT h.* FROM source_health h
                JOIN (
                    SELECT source, MAX(rowid) AS mx FROM source_health GROUP BY source
                ) t ON t.mx = h.rowid
                ORDER BY h.source ASC;
                """
            ).fetchall()
            return [dict(r) for r in rows]

    def sources_needing_alert(self, threshold: int = 3) -> list[dict]:
        """Sumber yang SEDANG gagal `threshold` kali berturut-turut.

        Hanya keadaan TERAKHIR yang diperiksa. Kegagalan lama tidak boleh
        membuat alert terus berbunyi setelah sumber pulih.
        """
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT source, status, detail, consecutive_failures, checked_at
                FROM source_health h
                WHERE h.is_failure = 1
                  AND h.consecutive_failures >= ?
                  AND h.rowid = (
                      SELECT MAX(rowid) FROM source_health WHERE source = h.source
                  )
                ORDER BY consecutive_failures DESC, source ASC;
                """,
                (int(threshold),),
            ).fetchall()
            return [dict(r) for r in rows]

    # -- jejak simulasi (P1-7) -------------------------------------------
    #: Retensi jejak simulasi. Teks yang dianalisis adalah data pengguna, jadi
    #: umurnya dibatasi; angka ini dipakai `purge_sim_runs`.
    RETAIN_DAYS: int = 90

    @staticmethod
    def hash_text(text: str | None) -> str:
        """SHA-256 dari teks yang sudah dinormalkan spasi.

        Dipakai sebagai kunci duplikat di `sim_runs`; normalkan spasi supaya
        teks yang sama dengan spasi berbeda menghasilkan hash yang sama.
        """
        import hashlib

        bersih = " ".join((text or "").split())
        return hashlib.sha256(bersih.encode("utf-8")).hexdigest()

    def save_sim_run(self, hasil) -> int:
        """Simpan satu hasil `SimulationService.analyze` ke `sim_runs`.

        NFR reproducibility: hasil yang hanya dikembalikan lewat API lalu
        dibuang tidak bisa diperiksa ulang. Mengembalikan `run_id` supaya
        pemanggil bisa merujuk baris yang sama.
        """
        rows = (
            datetime.now().isoformat(),
            self.hash_text(hasil.text),
            hasil.text,
            hasil.input_kind,
            1 if hasil.is_rumor else 0,
            hasil.source,
            hasil.target,
            hasil.tone,
            float(hasil.score),
            float(hasil.confidence),
            float(hasil.confidence_raw),
            float(hasil.penalty),
            hasil.direction,
            hasil.horizon,
            hasil.model_version,
            json.dumps(list(hasil.warnings or [])),
            json.dumps(list(hasil.degraded or [])),
        )
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO sim_runs (
                    created_at, text_hash, text, input_kind, is_rumor, source,
                    target, tone, score, confidence, confidence_raw, penalty,
                    direction, horizon, model_version, warnings, degraded
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);
                """,
                rows,
            )
            return int(cur.lastrowid or 0)

    def get_sim_run(self, run_id: int) -> Optional[dict]:
        """Ambil satu jejak simulasi. None bila tidak ada (bukan galat)."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM sim_runs WHERE run_id = ?;", (int(run_id),)
            ).fetchone()
        if row is None:
            return None
        data = dict(row)
        for kolom in ("warnings", "degraded"):
            try:
                data[kolom] = json.loads(data[kolom] or "[]")
            except (TypeError, ValueError):
                data[kolom] = []
        return data

    def purge_sim_runs(self, days: int | None = None) -> int:
        """Hapus jejak simulasi lebih tua dari `days`. Kembalikan jumlah baris.

        Dipanggil dari lifespan saat startup. Idempoten: memanggil berulang
        tidak menghapus apa pun yang belum kedaluwarsa.
        """
        batas_hari = self.RETAIN_DAYS if days is None else int(days)
        batas = (datetime.now() - timedelta(days=batas_hari)).isoformat()
        with self.get_connection() as conn:
            cur = conn.execute("DELETE FROM sim_runs WHERE created_at < ?;", (batas,))
            return int(cur.rowcount or 0)
