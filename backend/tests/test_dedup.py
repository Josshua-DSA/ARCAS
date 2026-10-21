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
