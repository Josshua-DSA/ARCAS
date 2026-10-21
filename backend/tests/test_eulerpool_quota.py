"""Test penjaga kuota harian & adapter Eulerpool."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from backend.src.collect.news_api.quota import (
    HARD_CAP_PER_DAY,
    DailyQuota,
    QuotaExceeded,
)


def test_kuota_awal_nol(tmp_path: Path) -> None:
    q = DailyQuota(tmp_path / "q.db", "eulerpool", limit_per_day=10)
    st = q.status()
    assert st.used == 0
    assert st.remaining == 10
    assert not st.exhausted


def test_reserve_mengurangi_sisa(tmp_path: Path) -> None:
    q = DailyQuota(tmp_path / "q.db", "eulerpool", limit_per_day=10)
    q.reserve(3)
    st = q.status()
    assert st.used == 3
    assert st.remaining == 7


def test_kuota_habis_melempar(tmp_path: Path) -> None:
    q = DailyQuota(tmp_path / "q.db", "eulerpool", limit_per_day=2)
    q.reserve(2)
    with pytest.raises(QuotaExceeded):
        q.reserve(1)


def test_tidak_bisa_melewati_batas(tmp_path: Path) -> None:
    """Pagar inti: permintaan yang membuat total melewati limit harus ditolak."""
    q = DailyQuota(tmp_path / "q.db", "eulerpool", limit_per_day=5)
    q.reserve(4)
    with pytest.raises(QuotaExceeded):
        q.reserve(2)  # 4+2 > 5
    # Yang gagal tidak boleh memakan jatah.
    assert q.status().used == 4


def test_pagar_keras_100(tmp_path: Path) -> None:
    """limit_per_day di atas 100 ditolak sejak awal."""
    with pytest.raises(ValueError, match="pagar keras"):
        DailyQuota(tmp_path / "q.db", "eulerpool", limit_per_day=HARD_CAP_PER_DAY + 1)
    # Tepat 100 masih boleh.
    DailyQuota(tmp_path / "q.db", "eulerpool", limit_per_day=HARD_CAP_PER_DAY)


def test_persisten_lintas_instance(tmp_path: Path) -> None:
    """Kuota harus bertahan walau proses/objek baru — inti desainnya."""
    path = tmp_path / "q.db"
    DailyQuota(path, "eulerpool", limit_per_day=10).reserve(4)
    # Objek baru, database sama: pemakaian tetap terlihat.
    assert DailyQuota(path, "eulerpool", limit_per_day=10).status().used == 4


def test_vendor_terpisah(tmp_path: Path) -> None:
    path = tmp_path / "q.db"
    DailyQuota(path, "eulerpool", limit_per_day=5).reserve(3)
    assert DailyQuota(path, "finnhub", limit_per_day=5).status().used == 0


def test_refund_mengembalikan_slot(tmp_path: Path) -> None:
    q = DailyQuota(tmp_path / "q.db", "eulerpool", limit_per_day=5)
    q.reserve(2)
    q.refund(1)
    assert q.status().used == 1
    # Refund tidak boleh membuat negatif.
    q.refund(99)
    assert q.status().used == 0


def test_tabel_kuota_dibuat(tmp_path: Path) -> None:
    path = tmp_path / "q.db"
    q = DailyQuota(path, "eulerpool", limit_per_day=10)
    q.reserve(1)
    with sqlite3.connect(path) as conn:
        n = conn.execute("SELECT count(*) FROM api_quota_usage;").fetchone()[0]
    assert n == 1


# ---------------- adapter (tanpa jaringan) ----------------


def test_adapter_tanpa_kunci_tidak_terkonfigurasi(tmp_path: Path) -> None:
    from backend.src.collect.news_api.eulerpool import EulerpoolAdapter

    a = EulerpoolAdapter(key="")
    assert not a.is_configured()
    report = a.probe()
    assert "tidak diset" in report.detail


def test_fetch_target_di_luar_universe_ditolak() -> None:
    from backend.src.collect.news_api.eulerpool import EulerpoolAdapter

    a = EulerpoolAdapter(key="dummy")
    with pytest.raises(ValueError, match="di luar universe"):
        a.fetch("BTC", limit=5)


def test_adapter_gagal_jaringan_mengembalikan_kuota(tmp_path: Path) -> None:
    """Bila request gagal sebelum terkirim, slot kuota harus dikembalikan."""
    from backend.src.collect.news_api.base import ApiStatus
    from backend.src.collect.news_api.client import ApiError
    from backend.src.collect.news_api.eulerpool import EulerpoolAdapter

    class ClientGagal:
        def get_json(self, *a, **k):
            raise ApiError(ApiStatus.ERROR, "jaringan mati")

    q = DailyQuota(tmp_path / "q.db", "eulerpool", limit_per_day=5)
    a = EulerpoolAdapter(client=ClientGagal(), key="dummy", quota=q)

    with pytest.raises(ApiError):
        a.fetch_all()
    assert q.status().used == 0, "kegagalan lokal tidak boleh memakan kuota"


def test_adapter_menghitung_satu_request_untuk_semua_target(tmp_path: Path) -> None:
    """fetch_all harus 1 request, bukan 3 — inti efisiensi kuota."""
    from backend.src.collect.news_api.eulerpool import EulerpoolAdapter

    class ClientPalsu:
        def __init__(self) -> None:
            self.panggilan = 0

        def get_json(self, url, params=None, headers=None):
            self.panggilan += 1
            return (
                [
                    {
                        "headline": "Gold rises as Fed signals rate cut, S&P 500 gains",
                        "source": "Reuters",
                        "url": "https://example.com/a",
                        "summary": "Gold and stocks rally",
                        "category": "business",
                        "datetime": 1792543800,
                    }
                ],
                12.0,
            )

    client = ClientPalsu()
    q = DailyQuota(tmp_path / "q.db", "eulerpool", limit_per_day=5)
    a = EulerpoolAdapter(client=client, key="dummy", quota=q)

    hasil = a.fetch_all()
    assert client.panggilan == 1, "tiga target tidak boleh jadi tiga request"
    assert q.status().used == 1
    assert set(hasil) == {"XAU", "RATE_UST", "SPX"}
