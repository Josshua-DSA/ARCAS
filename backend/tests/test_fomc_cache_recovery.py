"""Tes untuk pemulihan checkpoint FOMC-RoBERTa yang rusak di cache.

Gejala aslinya di log server:

    Checkpoint primer 'gtfintechlab/FOMC-RoBERTa' sedang dibatasi ...
    Gagal memuat fallback checkpoint: Cannot copy out of meta tensor; no data!

Penyebabnya bukan model yang salah, melainkan unduhan yang terputus dan
menyisakan berkas *.incomplete di cache Hugging Face. transformers lalu
membangun model di `meta` device dan gagal mengisi bobotnya.

Tes di sini tidak mengunduh 1,4 GB: yang diuji adalah perilaku pemulihan
(hapus sisa -> coba lagi sekali), bukan kualitas model.
"""

from __future__ import annotations

import pytest

from model.fomc.src.model import (
    FALLBACK_ROBERTA_CHECKPOINT,
    FOMCRoBERTaSentiment,
    _bersihkan_cache_tidak_lengkap,
)


def test_pembersih_hanya_menyentuh_incomplete(tmp_path, monkeypatch):
    """Berkas sah tidak boleh ikut terhapus."""
    import huggingface_hub.constants as konst

    repo = tmp_path / "models--a--b"
    (repo / "blobs").mkdir(parents=True)
    (repo / "blobs" / "bobot.safetensors").write_bytes(b"asli")
    (repo / "blobs" / "bobot.bin.incomplete").write_bytes(b"setengah")

    monkeypatch.setattr(konst, "HF_HUB_CACHE", str(tmp_path), raising=False)

    dihapus = _bersihkan_cache_tidak_lengkap("a/b")

    assert dihapus == 1
    assert not (repo / "blobs" / "bobot.bin.incomplete").exists()
    assert (repo / "blobs" / "bobot.safetensors").exists(), "berkas sah ikut terhapus"


def test_pembersih_aman_saat_repo_tidak_ada(tmp_path, monkeypatch):
    import huggingface_hub.constants as konst

    monkeypatch.setattr(konst, "HF_HUB_CACHE", str(tmp_path), raising=False)
    assert _bersihkan_cache_tidak_lengkap("tidak/ada") == 0


def test_meta_tensor_dipulihkan_dan_model_siap(monkeypatch):
    """Sisa cache dibersihkan lalu muat ulang; hasilnya model terpakai."""
    import model.fomc.src.model as mod
    from transformers import AutoModelForSequenceClassification as AM
    from transformers import AutoTokenizer as AT

    class ModelPalsu:
        def to(self, device):
            return self

        def eval(self):
            return self

    dipanggil: list[int] = []
    dibersihkan: list[str] = []

    def from_pretrained_palsu(*a, **k):
        dipanggil.append(1)
        if len(dipanggil) == 1:
            raise RuntimeError("Cannot copy out of meta tensor; no data!")
        return ModelPalsu()

    monkeypatch.setattr(AM, "from_pretrained", staticmethod(from_pretrained_palsu))
    monkeypatch.setattr(AT, "from_pretrained", staticmethod(lambda *a, **k: object()))
    monkeypatch.setattr(
        mod, "_bersihkan_cache_tidak_lengkap", lambda cp: dibersihkan.append(cp) or 1
    )

    m = FOMCRoBERTaSentiment()
    m._ensure_loaded()

    assert dibersihkan, "pembersih cache tidak dipanggil saat meta tensor"
    assert len(dipanggil) == 2, f"harus tepat satu percobaan ulang, dapat {len(dipanggil)}"
    assert m._model is not None, "model tidak terpasang setelah pemulihan"


def test_tanpa_sisa_cache_tidak_mengulang(monkeypatch):
    """Bila tidak ada yang bisa dibersihkan, jangan buang waktu mengulang."""
    import model.fomc.src.model as mod
    from transformers import AutoModelForSequenceClassification as AM

    dipanggil: list[int] = []

    def from_pretrained_palsu(*a, **k):
        dipanggil.append(1)
        raise RuntimeError("Cannot copy out of meta tensor; no data!")

    monkeypatch.setattr(AM, "from_pretrained", staticmethod(from_pretrained_palsu))
    monkeypatch.setattr(mod, "_bersihkan_cache_tidak_lengkap", lambda cp: 0)

    m = FOMCRoBERTaSentiment()
    with pytest.raises(Exception):
        m._ensure_loaded()

    assert len(dipanggil) == 1, "tidak ada sisa cache, jadi tidak perlu mengulang"


def test_pemulihan_tidak_berulang_tanpa_henti(monkeypatch):
    """Percobaan ulang maksimal sekali per checkpoint, bukan tak terbatas."""
    import model.fomc.src.model as mod
    from transformers import AutoModelForSequenceClassification as AM
    from transformers import AutoTokenizer as AT

    dipanggil: list[int] = []

    def selalu_meta(*a, **k):
        dipanggil.append(1)
        raise RuntimeError("Cannot copy out of meta tensor; no data!")

    monkeypatch.setattr(AM, "from_pretrained", staticmethod(selalu_meta))
    monkeypatch.setattr(AT, "from_pretrained", staticmethod(lambda *a, **k: object()))
    monkeypatch.setattr(mod, "_bersihkan_cache_tidak_lengkap", lambda cp: 1)

    m = FOMCRoBERTaSentiment()
    with pytest.raises(Exception):
        m._ensure_loaded()

    # primer (1) + satu muat ulang (2) + fallback (3) + muat ulang fallback (4)
    assert len(dipanggil) <= 4, f"terlalu banyak percobaan: {len(dipanggil)}"


def test_galat_lain_tidak_memicu_pemulihan(monkeypatch):
    """Galat gated (401) bukan urusan cache; jangan hapus berkas apa pun."""
    import model.fomc.src.model as mod
    from transformers import AutoModelForSequenceClassification as AM

    dibersihkan: list[str] = []

    def gated(*a, **k):
        raise OSError("You are trying to access a gated repo. 401 Client Error")

    monkeypatch.setattr(AM, "from_pretrained", staticmethod(gated))
    monkeypatch.setattr(
        mod, "_bersihkan_cache_tidak_lengkap", lambda cp: dibersihkan.append(cp) or 1
    )

    m = FOMCRoBERTaSentiment()
    with pytest.raises(Exception):
        m._ensure_loaded()

    assert not dibersihkan, "galat gated tidak boleh menyentuh cache"
