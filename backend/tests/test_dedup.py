"""Tests for T-6 / FR-2: near-duplicate detection.

Dedup sebelumnya hanya exact-hash, sehingga berita wire yang sama dari dua
feed masuk sebagai dua artikel. Test di bawah mengunci perilaku yang penting,
termasuk batas kemampuan metode leksikal ini.
"""

import shutil
from datetime import datetime
from pathlib import Path

import pytest

from backend.src.normalize.dedup import NearDuplicateDetector
from backend.src.schema import Article, Lang


def _article(aid, title, body="", source="s", published=None):
    return Article(
        article_id=aid,
        source=source,
        title=title,
        body=body,
        language=Lang.EN,
        published_at=published or datetime(2026, 10, 20, 10, 0),
        fetched_at=datetime(2026, 10, 20, 10, 5),
    )


# ---------------------------------------------------------------------------
# Deteksi dasar
# ---------------------------------------------------------------------------


def test_identical_articles_are_flagged():
    det = NearDuplicateDetector()
    out = det.mark_duplicates([
        _article("a", "Gold rises 2% on weaker dollar", "Bullion gained."),
        _article("b", "Gold rises 2% on weaker dollar", "Bullion gained."),
    ])
    assert out[1].duplicate_of == "a"
    assert out[0].duplicate_of is None


def test_different_topics_not_flagged():
    det = NearDuplicateDetector()
    out = det.mark_duplicates([
        _article("a", "Gold rises 2% on weaker dollar"),
        _article("b", "Oil slumps as OPEC raises output"),
    ])
    assert out[0].duplicate_of is None
    assert out[1].duplicate_of is None


def test_boilerplate_difference_still_flagged():
    """Badan berita beda di bagian 'Baca juga' tetap harus terdeteksi."""
    det = NearDuplicateDetector()
    out = det.mark_duplicates([
        _article("a", "Fed holds rates steady", "Powell spoke. Read also: X"),
        _article("b", "Fed holds rates steady", "Powell spoke. Read also: Y"),
    ])
    assert out[1].duplicate_of == "a"


def test_three_copies_point_to_single_original():
    """Tiga salinan -> satu asli + dua duplikat, bukan rantai saling menunjuk."""
    det = NearDuplicateDetector()
    arts = [
        _article("a", "Oil jumps after OPEC cuts output"),
        _article("b", "Oil jumps after OPEC cuts output"),
        _article("c", "Oil jumps after OPEC cuts output"),
    ]
    out = det.mark_duplicates(arts)
    assert out[0].duplicate_of is None
    assert out[1].duplicate_of == "a"
    assert out[2].duplicate_of == "a"


def test_earliest_publication_is_treated_as_original():
    det = NearDuplicateDetector()
    later = _article("later", "Gold rises 2%", published=datetime(2026, 10, 20, 12))
    earlier = _article("earlier", "Gold rises 2%", published=datetime(2026, 10, 20, 8))
    out = det.mark_duplicates([later, earlier])
    by_id = {a.article_id: a for a in out}
    assert by_id["earlier"].duplicate_of is None
    assert by_id["later"].duplicate_of == "earlier"


def test_history_match_against_db():
    det = NearDuplicateDetector()
    history = {"old1": "gold rises 2% gold rises 2% bullion gained"}
    out = det.mark_duplicates(
        [_article("new", "Gold rises 2%", "Bullion gained.")], history=history
    )
    assert out[0].duplicate_of == "old1"


# ---------------------------------------------------------------------------
# Batas metode: kasus yang TIDAK boleh digabung
# ---------------------------------------------------------------------------


def test_same_template_different_entity_not_merged():
    """Dua rilis Fed berbeda pemohon punya kalimat nyaris sama.

    Pada data nyata skornya 0.749. Menggabungkan keduanya akan menghilangkan
    berita yang sah, jadi harus masuk pita tinjauan, bukan digabung.
    """
    det = NearDuplicateDetector()
    out = det.mark_duplicates([
        _article("f1", "Federal Reserve Board announces approval of application by Isabella Bank"),
        _article("f2", "Federal Reserve Board announces approval of application by Fleur Capital"),
    ])
    assert out[1].duplicate_of is None, "entitas berbeda tidak boleh digabung"
    assert det.last_review, "kasus abu-abu harus dilaporkan untuk ditinjau"


def test_review_band_reports_without_merging():
    """Skor 0.55-0.85: dilaporkan, tidak digabung otomatis."""
    det = NearDuplicateDetector()
    det.mark_duplicates([
        _article("m", "Gold edges lower as investors weigh Fed rate signals - Reuters"),
        _article("n", "Gold steady as investors await fed rate signals - Reuters"),
    ])
    assert det.last_matches == []
    assert det.last_review
    assert 0.55 <= det.last_review[0][2] < 0.85


def test_empty_input_is_safe():
    det = NearDuplicateDetector()
    assert det.mark_duplicates([]) == []


def test_single_article_is_safe():
    det = NearDuplicateDetector()
    out = det.mark_duplicates([_article("only", "Whatever")])
    assert len(out) == 1
    assert out[0].duplicate_of is None


def test_missing_body_does_not_crash():
    det = NearDuplicateDetector()
    out = det.mark_duplicates([
        _article("a", "Gold rises", body=""),
        _article("b", "Gold rises", body=""),
    ])
    assert out[1].duplicate_of == "a"


# ---------------------------------------------------------------------------
# Integrasi pipeline
# ---------------------------------------------------------------------------


@pytest.fixture()
def pipeline_db(tmp_path):
    """Salin DB nyata bila ada, supaya uji memakai data sungguhan."""
    src = Path("data/finews.db")
    dst = tmp_path / "pipeline.db"
    if src.exists():
        shutil.copy(src, dst)
    return dst


def test_pipeline_never_self_references(pipeline_db):
    """Regresi: riwayat DB memuat batch yang sama -> artikel menunjuk dirinya."""
    from backend.src.pipeline.runner import Pipeline

    pipe = Pipeline(db_path=pipeline_db)
    articles, _ = pipe.normalize_raw(limit=100, dry_run=True)

    self_refs = [a for a in articles if a.duplicate_of == a.article_id]
    assert self_refs == [], "artikel tidak boleh dianggap duplikat dirinya sendiri"


def test_pipeline_reports_review_pairs(pipeline_db):
    from backend.src.pipeline.runner import Pipeline

    pipe = Pipeline(db_path=pipeline_db)
    pipe.normalize_raw(limit=100, dry_run=True)
    assert isinstance(pipe.last_duplicate_review, list)


def test_duplicates_are_excluded_from_scoring(pipeline_db):
    """Duplikat tidak boleh menambah hitungan pada tahap skor."""
    from backend.src.pipeline.runner import Pipeline

    pipe = Pipeline(db_path=pipeline_db)
    articles, _ = pipe.normalize_raw(limit=100, dry_run=True)
    dups = [a for a in articles if a.duplicate_of]
    if not dups:
        pytest.skip("data uji tidak punya duplikat")

    _, stats = pipe.score_and_route(articles, dry_run=True)
    assert stats.artikel_duplikat >= len(dups)


# ---------------------------------------------------------------------------
# FR-2 / AUDIT v3 §2: bukti end-to-end dengan fixture yang MENJAMIN duplikat.
#
# Test di atas bergantung pada `data/finews.db`, yang isinya berubah dan
# karenanya bisa tidak memuat duplikat -> `pytest.skip`. Skip bukan bukti:
# jalur `NearDuplicateDetector` di dalam `Pipeline` tidak pernah tereksekusi.
# Fixture di bawah deterministik dan selalu memuat satu pasangan duplikat.
# ---------------------------------------------------------------------------

#: Teks wire yang dipakai dua sumber berbeda.
_WIRE_BODY = (
    "Gold prices rose on Wednesday as the dollar weakened after the release of "
    "the Federal Reserve's minutes, which showed policymakers divided on the "
    "pace of future rate cuts. Spot gold gained 0.8% to $2,341 per ounce."
)
_WIRE_TITLE = "Gold rises as dollar weakens after Fed minutes"


@pytest.fixture
def seeded_pipeline_db(tmp_path):
    """DB berisi tepat 3 berita: sepasang duplikat + satu berita lain.

    Dibuat sintetis (bukan salinan `data/finews.db`) supaya hasilnya tidak
    bergantung pada isi database lokal.
    """
    from backend.src.store.db import Database

    db_path = tmp_path / "seeded.db"
    db = Database(db_path)
    db.init_schema()

    rows = [
        # (source, title, body, published_at)
        ("reuters", _WIRE_TITLE, _WIRE_BODY, "2026-10-20 10:00:00"),
        # Sumber lain, badan disunting sedikit + penanda media di judul.
        (
            "bloomberg",
            _WIRE_TITLE + " - Bloomberg",
            _WIRE_BODY.replace("rose", "climbed").replace("weakened", "fell"),
            "2026-10-20 10:30:00",
        ),
        # Topik sama sekali berbeda -- harus lolos.
        (
            "cnbc",
            "Oil slumps as OPEC signals higher output next quarter",
            "Crude benchmarks fell sharply after OPEC indicated it would raise "
            "production.",
            "2026-10-20 11:00:00",
        ),
    ]
    with db.get_connection() as conn:
        for source, title, body, published in rows:
            conn.execute(
                "INSERT INTO raw_articles "
                "(source, title, body, published_at, fetched_at) "
                "VALUES (?, ?, ?, ?, ?);",
                (source, title, body, published, "2026-10-20 12:00:00"),
            )
    return db_path


def test_pipeline_flags_duplicate_without_skipping(seeded_pipeline_db):
    """AUDIT v3 §2: jalur near-dup di Pipeline benar-benar dieksekusi.

    Sebelum perbaikan ini, test satu-satunya bergantung pada `data/finews.db`
    dan berakhir `pytest.skip` -- jadi tidak ada satu pun test yang membuktikan
    `duplicate_of` pernah terisi lewat `Pipeline`.
    """
    from backend.src.pipeline.runner import Pipeline

    pipe = Pipeline(db_path=seeded_pipeline_db)
    articles, stats = pipe.normalize_raw(limit=100, dry_run=True)

    assert len(articles) == 3, "ketiga berita harus lolos normalisasi"

    dups = [a for a in articles if a.duplicate_of]
    assert len(dups) == 1, (
        "harus tepat satu duplikat terdeteksi; "
        f"ditemukan {len(dups)} dari {len(articles)} artikel"
    )
    assert stats.artikel_duplikat == 1

    # Yang asli = terbit lebih awal (reuters 10:00), bukan yang lebih akhir.
    original = [a for a in articles if a.source == "reuters"][0]
    assert dups[0].source == "bloomberg"
    assert dups[0].duplicate_of == original.article_id
    assert dups[0].duplicate_of != dups[0].article_id, "tidak boleh menunjuk diri sendiri"

    # Berita topik lain tidak boleh ikut tertandai.
    oil = [a for a in articles if a.source == "cnbc"][0]
    assert oil.duplicate_of is None


def test_duplicate_does_not_increase_daily_article_count(seeded_pipeline_db, monkeypatch):
    """AUDIT v3 §2: duplikat tidak ikut diskor / menambah hitungan.

    Memakai model tiruan supaya test tidak bergantung pada artefak
    `model/common/baseline_tfidf.joblib`. Artefak itu sengaja tidak di-commit
    (terikat versi sklearn), jadi di checkout bersih/CI test ini akan gagal
    pada `load_model()` -- padahal yang diuji di sini adalah *pelewatan*
    duplikat, bukan kualitas sentimen.
    """
    from backend.src.pipeline.runner import Pipeline
    from backend.src.schema import ArticleSentiment, ModelProbs, Tone

    class _StubModel:
        """Model sentimen minimal: selalu netral."""

        def score_article(self, article_id: str, text: str) -> ArticleSentiment:
            return ArticleSentiment(
                article_id=article_id,
                tone=Tone.NEUTRAL,
                score=0.0,
                probs=[
                    ModelProbs(
                        model="stub",
                        p_pos=0.25,
                        p_neu=0.5,
                        p_neg=0.25,
                        model_version="stub",
                    )
                ],
            )

    pipe = Pipeline(db_path=seeded_pipeline_db)
    monkeypatch.setattr(pipe, "load_model", lambda: _StubModel())

    articles, _ = pipe.normalize_raw(limit=100, dry_run=True)
    _, stats = pipe.score_and_route(articles, dry_run=True)

    # Duplikat dilewati pada tahap skor; sisanya diproses.
    assert stats.artikel_duplikat == 1
    unik = [a for a in articles if not a.duplicate_of]
    assert len(unik) == len(articles) - 1
    assert stats.errors == [], f"tidak boleh ada error skor: {stats.errors}"


def test_detector_disabled_breaks_the_assertions(seeded_pipeline_db, monkeypatch):
    """Uji mutasi: tanpa detektor, duplikat lolos dan `duplicate_of` kosong.

    Ini yang membuktikan test di atas benar-benar menguji detektor, bukan
    kebetulan lolos karena fixture-nya.
    """
    from backend.src.normalize import dedup
    from backend.src.pipeline.runner import Pipeline

    # Matikan detektor: setiap artikel dianggap unik.
    monkeypatch.setattr(
        dedup.NearDuplicateDetector,
        "mark_duplicates",
        lambda self, articles, history=None: list(articles),
    )

    pipe = Pipeline(db_path=seeded_pipeline_db)
    articles, stats = pipe.normalize_raw(limit=100, dry_run=True)

    assert [a for a in articles if a.duplicate_of] == [], (
        "dengan detektor dimatikan tidak boleh ada yang tertandai duplikat"
    )
    assert stats.artikel_duplikat == 0


def test_true_paraphrase_lands_in_review_band_not_merged():
    """Batas jujur metode leksikal: parafrase sejati TIDAK digabung.

    Diukur pada `dedup.py` versi ini: badan yang diparafrase menyeluruh
    (sinonim + struktur kalimat berubah) menghasilkan cosine ~0.72, di bawah
    `NEAR_DUP_THRESHOLD=0.85`. Jadi artikel itu masuk `last_review` untuk
    ditinjau manusia, bukan digabung otomatis.

    Test ini mengunci perilaku tersebut supaya tidak ada yang mengira
    detektor ini menangkap parafrase semantik. Untuk itu perlu embedding
    (lihat AUDIT v3 §1).
    """
    det = NearDuplicateDetector()
    original = _article("o", _WIRE_TITLE, _WIRE_BODY)
    paraphrased = _article(
        "p",
        _WIRE_TITLE,
        "Gold prices climbed on Wednesday as the dollar dropped after the "
        "publication of the Federal Reserve's minutes, which showed officials "
        "split on the pace of upcoming rate cuts. Spot gold added 0.8% to "
        "$2,341 an ounce.",
    )

    out = det.mark_duplicates([original, paraphrased])

    assert out[1].duplicate_of is None, (
        "parafrase sejati tidak boleh digabung otomatis oleh metode leksikal"
    )
    assert det.last_review, "harus dilaporkan di pita tinjauan"
    score = det.last_review[0][2]
    assert 0.55 <= score < 0.85, f"skor parafrase {score:.4f} di luar pita tinjauan"
