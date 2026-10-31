"""Regresi: siaran pers FOMC harus ter-tag ke RATE_UST.

Konteks kegagalan yang dicegah test ini:

`daily_sentiment` untuk RATE_UST hanya mencakup 2026-10-15..2026-10-23 (7 hari),
padahal `prices` sudah 84 hari. Akibatnya OLS (butuh >=10 hari berpasangan) dan
Granger (>=20) tidak pernah bisa dihitung.

Penyebabnya bukan jumlah berita, melainkan alias: teks siaran pers Fed menulis
"federal funds rate" dan "Federal Open Market Committee", sedangkan
`aliases.csv` hanya memuat "fed funds rate". Kata "FOMC" tidak ada sama sekali.
Dokumen paling relevan untuk suku bunga justru tidak ter-tag.

Test di bawah mengunci perilaku itu: kalimat FOMC yang menyebut kenaikan
target range harus menghasilkan impact RATE_UST.
"""

from datetime import datetime, timezone

from backend.src.schema import Article, Lang
from backend.src.tagging.router import TargetRouter

FOMC_TEXT = (
    "The Federal Open Market Committee approved the following statement for "
    "release by a 12-0 vote: The Committee decided to raise the target range "
    "for the federal funds rate by 1/4 percentage point to 3-3/4 to 4 percent."
)


def _article(title: str, body: str) -> Article:
    return Article(
        article_id="uji-fomc-0001",
        source="rss:fed_press",
        url="https://www.federalreserve.gov/newsevents/pressreleases/monial.htm",
        title=title,
        body=body,
        published_at=datetime(2026, 9, 16, 18, 0, tzinfo=timezone.utc),
        fetched_at=datetime(2026, 9, 16, 18, 0, tzinfo=timezone.utc),
        language=Lang.EN,
        market_relevant=True,
    )


def _targets(router: TargetRouter, article: Article) -> set[str]:
    return {impact.asset_id for impact in router.route_article(article, 0.0)}


def test_fomc_statement_ter_tag_ke_rate_ust():
    """Siaran pers FOMC harus menghasilkan impact RATE_UST."""
    router = TargetRouter()
    targets = _targets(router, _article("Federal Reserve issues FOMC statement", FOMC_TEXT))
    assert "RATE_UST" in targets, (
        "Siaran pers FOMC tidak ter-tag ke RATE_UST. Periksa aliases.csv: "
        "harus memuat 'fomc', 'federal funds rate', dan "
        "'federal open market committee'."
    )


def test_frasa_federal_funds_rate_dikenali():
    """Teks Fed menulis 'federal funds rate', bukan 'fed funds rate'."""
    router = TargetRouter()
    article = _article(
        "Federal Reserve Board and FOMC",
        "The Committee decided to raise the target range for the federal funds rate.",
    )
    assert "RATE_UST" in _targets(router, article)


def test_siaran_pers_non_pasar_tidak_dipaksa_ter_tag():
    """Persetujuan/enforcement bukan berita pasar: jangan dipaksa punya target.

    Ini menjaga agar perbaikan alias tidak menjadi terlalu longgar — setiap
    siaran pers Fed tidak otomatis dianggap sinyal RATE_UST.
    """
    router = TargetRouter()
    article = _article(
        "Federal Reserve Board announces approval of application",
        "The Federal Reserve Board on Thursday announced its approval of the "
        "application by an individual to become a member of a state bank.",
    )
    assert "RATE_UST" not in _targets(router, article)
