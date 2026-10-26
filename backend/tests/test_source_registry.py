"""T-4 / FR-3: registry YAML adalah satu-satunya sumber kebenaran.

Sebelum perbaikan, `keywords.py` dan `rss_collector.py` menyimpan salinan
manual dari `data/source_registry.yaml`, dan keduanya sudah menyimpang
(kode 15/22/17 kata vs YAML 9/8/8) sementara docstring mengaku bersumber
dari YAML.

Test di sini menjaga dua hal:
1. nilai yang dipakai kode benar-benar berasal dari YAML, bukan salinan;
2. mengubah YAML benar-benar mengubah perilaku — bukan hanya dokumentasi.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from backend.src.collect.news_api import keywords as kw
from backend.src.collect.rss_collector import _load_feeds

REGISTRY = Path("data/source_registry.yaml")


# ==========================================================
# Registry terbaca
# ==========================================================


def test_registry_is_the_actual_source():
    """Sumber yang dilaporkan harus registry, bukan fallback."""
    assert kw.REGISTRY_SOURCE.startswith("registry:"), kw.REGISTRY_SOURCE
    assert "fallback" not in kw.REGISTRY_SOURCE


def test_all_targets_have_keywords():
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    for target_id, spec in data["targets"].items():
        assert spec.get("keywords"), f"{target_id} tanpa kata kunci di YAML"
        assert kw.TARGET_KEYWORDS.get(target_id), f"{target_id} tidak terbaca kode"


def test_macro_keywords_present():
    assert len(kw.MACRO_KEYWORDS) > 0
    assert "fed" in kw.MACRO_KEYWORDS


# ==========================================================
# YAML benar-benar mengendalikan perilaku
# ==========================================================


def test_adding_keyword_to_yaml_changes_behaviour(tmp_path, monkeypatch):
    """Menambah kata kunci di YAML harus langsung mengubah hasil cocok.

    Inilah inti T-4: kalau test ini gagal, berarti kode masih memakai
    salinan sendiri dan YAML hanya jadi pajangan.
    """
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    data["targets"]["XAU"]["keywords"].append("logam mulia")
    reg = tmp_path / "reg.yaml"
    reg.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    target_kw, _, _ = kw._load_registry(reg)
    monkeypatch.setattr(kw, "TARGET_KEYWORDS", target_kw)

    teks = "Harga logam mulia naik tajam"
    assert "logam mulia" in target_kw["XAU"]
    assert kw.matches_target(teks, "XAU") is True


def test_removing_keyword_from_yaml_disables_match(tmp_path, monkeypatch):
    """Kebalikannya: kata kunci yang dibuang dari YAML tidak lagi cocok."""
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    data["targets"]["XAU"]["keywords"] = ["emas"]
    reg = tmp_path / "reg.yaml"
    reg.write_text(yaml.safe_dump(data), encoding="utf-8")

    target_kw, _, _ = kw._load_registry(reg)
    monkeypatch.setattr(kw, "TARGET_KEYWORDS", target_kw)

    assert kw.matches_target("Gold prices climb", "XAU") is False
    assert kw.matches_target("Harga emas naik", "XAU") is True


def test_feeds_come_from_yaml(tmp_path):
    """Feed juga dibaca dari registry, bukan dari dict di kode."""
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    data["targets"]["XAU"]["feeds"] = [
        {"name": "uji", "type": "rss", "url": "https://contoh.test/rss"}
    ]
    reg = tmp_path / "reg.yaml"
    reg.write_text(yaml.safe_dump(data), encoding="utf-8")

    feeds = _load_feeds(reg)
    assert feeds["XAU"] == [{"name": "uji", "url": "https://contoh.test/rss"}]


def test_non_rss_feed_entries_skipped(tmp_path):
    """Entri non-RSS (mis. deklarasi API) tidak boleh masuk daftar feed."""
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    data["targets"]["XAU"]["feeds"] = [
        {"name": "api_saja", "type": "api", "url": "https://contoh.test/api"},
        {"name": "rss_ok", "type": "rss", "url": "https://contoh.test/rss"},
    ]
    reg = tmp_path / "reg.yaml"
    reg.write_text(yaml.safe_dump(data), encoding="utf-8")

    feeds = _load_feeds(reg)
    assert [f["name"] for f in feeds["XAU"]] == ["rss_ok"]


# ==========================================================
# Cadangan saat registry hilang
# ==========================================================


def test_missing_registry_falls_back_and_says_so():
    """Registry hilang: program tetap hidup, tetapi jujur soal sumbernya."""
    target_kw, macro, source = kw._load_registry(Path("/tidak/ada/reg.yaml"))
    assert target_kw, "cadangan harus tidak kosong agar program tidak crash"
    assert macro
    assert "fallback" in source


def test_fallback_is_minimal_not_a_second_copy():
    """Cadangan harus jauh lebih kecil dari registry asli.

    Kalau cadangan sama panjangnya, ia akan jadi sumber kebenaran kedua yang
    lambat laun menyimpang lagi — persis masalah yang T-4 perbaiki.
    """
    fallback, _, _ = kw._load_registry(Path("/tidak/ada/reg.yaml"))
    for target_id, words in fallback.items():
        assert len(words) < len(kw.TARGET_KEYWORDS.get(target_id, ())) or not kw.TARGET_KEYWORDS.get(
            target_id
        ), f"cadangan {target_id} tidak lebih kecil dari registry"


def test_broken_yaml_falls_back(tmp_path):
    reg = tmp_path / "rusak.yaml"
    reg.write_text("targets: [ini: bukan: yaml", encoding="utf-8")
    target_kw, _, source = kw._load_registry(reg)
    assert target_kw
    assert "fallback" in source


# ==========================================================
# Tidak ada kata kunci yang hilang saat pindah ke YAML
# ==========================================================


@pytest.mark.parametrize("target", ["XAU", "RATE_UST", "SPX"])
def test_keyword_coverage_not_reduced(target):
    """Regresi: pindah ke YAML tidak boleh mengurangi cakupan routing.

    Daftar lama di kode (15/22/17 kata) harus tetap utuh; kalau ada yang
    hilang, berita yang dulu tertangkap akan lolos diam-diam.
    """
    assert len(kw.TARGET_KEYWORDS[target]) >= {"XAU": 15, "RATE_UST": 22, "SPX": 17}[target]


def test_keyword_dedup_and_lowercase(tmp_path):
    """YAML boleh berisi duplikat/huruf besar; loader merapikannya."""
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    data["targets"]["XAU"]["keywords"] = ["Gold", "gold", "GOLD", "emas"]
    reg = tmp_path / "reg.yaml"
    reg.write_text(yaml.safe_dump(data), encoding="utf-8")

    target_kw, _, _ = kw._load_registry(reg)
    assert target_kw["XAU"] == ("gold", "emas")
