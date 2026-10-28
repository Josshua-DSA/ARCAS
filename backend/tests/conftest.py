"""Fixture bersama untuk seluruh suite `backend/tests`.

Sebelumnya `temp_db` didefinisikan ulang di tiga berkas
(`test_db.py`, `test_xau_pipeline_integration.py`,
`test_fomc_pipeline_integration.py`) dengan isi yang nyaris identik. Selain
duplikasi, ada risiko nyata: satu salinan memakai `tempfile.TemporaryDirectory`
dan dua lainnya `tmp_path`, sehingga perilaku pembersihan berbeda antar test
tanpa alasan yang jelas.

Fixture di sini memakai `tmp_path` karena pytest sudah mengelola siklus
hidupnya (dibersihkan otomatis, unik per test, dan tidak bergantung pada
perilaku locking berkas di Windows).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.src.store.db import Database


@pytest.fixture()
def temp_db(tmp_path: Path) -> Database:
    """Database SQLite sementara dengan skema lengkap.

    Nama berkas memakai `tmp_path` yang unik per test, jadi tidak perlu
    membedakan nama per modul seperti sebelumnya (`test.db`,
    `test_xau_pipeline.db`, `test_fomc_pipeline.db`).
    """
    db = Database(tmp_path / "test.db")
    db.init_schema()
    return db


@pytest.fixture(autouse=True)
def _tanpa_scheduler_dan_warmup(monkeypatch):
    """Jangan pernah menyalakan scheduler atau memuat bobot 440 MB saat tes.

    Sebelum ini, `ARCAS_DISABLE_SCHEDULER` hanya diandalkan dari lingkungan
    pemanggil: kalau lupa di-set, setiap `TestClient(create_app(...))` akan
    menyalakan penjadwal -- yang bisa menembak eulerpool sungguhan -- dan
    sekarang juga akan menunggu warm-up model. Autouse membuat keduanya
    mustahil terjadi karena kelalaian.
    """
    monkeypatch.setenv("ARCAS_DISABLE_SCHEDULER", "1")
    monkeypatch.setenv("ARCAS_DISABLE_WARMUP", "1")
