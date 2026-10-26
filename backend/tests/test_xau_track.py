"""Test track FinBERT-EMAS (FR-6 / M2 + M6).

Fokus pada hal yang **tidak butuh PyTorch**: kontrak label, kebersihan data,
dan urutan probabilitas. Ketiganya adalah tempat bug paling mahal di track
ini karena semuanya gagal secara **senyap**:

- label terbalik  -> model melaporkan sentimen persis kebalikan, tanpa error,
- `none` ikut masuk -> model belajar "tidak bahas harga" = "harga stabil",
- urutan probabilitas salah -> protokol [pos, neu, neg] terisi nilai kelas lain.

Test yang membutuhkan bobot terlatih ditandai `skipif` supaya suite tetap
hijau di mesin tanpa artefak — tetapi test di file ini sendiri selalu jalan.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from model.xau.src.data_loader import (
    DEFAULT_TEST_PATH,
    DEFAULT_TRAIN_PATH,
    LABEL_TO_TONE,
    TONE_TO_LABEL,
    get_texts_and_labels,
    load_gold_test,
    load_gold_train,
    normalize_tone,
    sanitize_gold_df,
    split_train_val,
)

ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT_DIR = ROOT / "model/xau/weights/finbert_gold"


class TestLabelContract:
    """Mapping label harus cocok dengan protokol dan adapters backend."""

    def test_mapping_sesuai_kontrak(self) -> None:
        """README model/xau menetapkan Positive→2, Neutral→1, Negative→0."""
        assert TONE_TO_LABEL == {"positive": 2, "neutral": 1, "negative": 0}
        assert LABEL_TO_TONE == {2: "positive", 1: "neutral", 0: "negative"}

    def test_konsisten_dengan_adapters_backend(self) -> None:
        """Loader model dan jalur ingest harus memetakan tone dengan cara sama.

        Kalau keduanya menyimpang, model dilatih pada distribusi label yang
        berbeda dari yang ditemui saat inferensi — bug yang tak terlihat
        sampai metrik produksi aneh.
        """
        from backend.src.normalize.adapters import GOLD_TONE_MAP

        assert set(GOLD_TONE_MAP) == {"positive", "negative", "neutral"}
        assert set(GOLD_TONE_MAP) == set(TONE_TO_LABEL)

    @pytest.mark.parametrize(
        "raw,harapan",
        [
            ("positive", "positive"),
            ("Positive", "positive"),
            ("  NEGATIVE  ", "negative"),
            ("neutral", "neutral"),
            ("none", None),  # WAJIB dibuang, bukan jadi neutral
            ("", None),
            (None, None),
            ("entah", None),  # tak dikenal -> buang, jangan ditebak
        ],
    )
    def test_normalize_tone(self, raw: object, harapan: str | None) -> None:
        assert normalize_tone(raw) == harapan

    def test_none_tidak_digabung_ke_neutral(self) -> None:
        """Baris `none` harus hilang, bukan berubah jadi neutral."""
        df = pd.DataFrame(
            {
                "News": ["gold up", "gold flat?", "gold down"],
                "Price Sentiment": ["positive", "none", "negative"],
                "Dates": ["01-01-2015", "02-01-2015", "03-01-2015"],
            }
        )
        out = sanitize_gold_df(df)
        assert len(out) == 2
        assert "neutral" not in set(out["tone"])
        assert set(out["tone"]) == {"positive", "negative"}


class TestSanitize:
    """Kebersihan data nyata pada parquet lokal."""

    def test_parquet_ada(self) -> None:
        assert DEFAULT_TRAIN_PATH.exists(), "dataset/gold_sinha train hilang"
        assert DEFAULT_TEST_PATH.exists(), "dataset/gold_sinha test hilang"

    def test_train_bersih_dan_konsisten(self) -> None:
        df = load_gold_train()
        assert len(df) > 5000, f"train terlalu kecil setelah dibersihkan: {len(df)}"
        assert set(df["tone"]) == {"positive", "negative", "neutral"}
        assert df["label"].isin([0, 1, 2]).all()
        assert df["text"].str.len().gt(0).all()
        # label dan tone tidak boleh saling bertentangan
        assert (df["tone"].map(TONE_TO_LABEL) == df["label"]).all()

    def test_tidak_ada_teks_duplikat(self) -> None:
        """Duplikat antar-split akan membocorkan contoh test ke train."""
        tr, te = load_gold_train(), load_gold_test()
        irisan = set(tr["text"]) & set(te["text"])
        assert not irisan, f"{len(irisan)} teks muncul di train DAN test: {list(irisan)[:3]}"

    def test_teks_kosong_dibuang(self) -> None:
        df = pd.DataFrame(
            {
                "News": ["gold up", "   ", ""],
                "Price Sentiment": ["positive", "positive", "positive"],
                "Dates": ["01-01-2015"] * 3,
            }
        )
        assert len(sanitize_gold_df(df)) == 1

    def test_duplikat_dibuang(self) -> None:
        df = pd.DataFrame(
            {
                "News": ["gold up", "gold up"],
                "Price Sentiment": ["positive", "positive"],
                "Dates": ["01-01-2015", "02-01-2015"],
            }
        )
        assert len(sanitize_gold_df(df)) == 1

    def test_split_val_stratified(self) -> None:
        """Neutral hanya ~4%; stratifikasi menjamin ia hadir di validation."""
        tr, _ = split_train_val(load_gold_train(), val_fraction=0.15, seed=5768)
        val = split_train_val(load_gold_train(), val_fraction=0.15, seed=5768)[1]
        assert "neutral" in set(val["tone"]), "neutral hilang dari validation"
        assert len(set(tr["text"]) & set(val["text"])) == 0, "train/val bocor"

    def test_label_type_untuk_torch(self) -> None:
        texts, labels = get_texts_and_labels(load_gold_train())
        assert isinstance(texts[0], str)
        assert all(isinstance(y, int) for y in labels[:50])


class TestProbabilityOrder:
    """Urutan probabilitas harus [pos, neu, neg] sesuai protokol."""

    def test_konstanta_urutan_benar(self) -> None:
        from model.xau.src.model import _PROTOCOL_ORDER

        # label latih 0=neg,1=neu,2=pos -> protokol butuh indeks 2,1,0
        assert _PROTOCOL_ORDER == (2, 1, 0)

    def test_pembalikan_urutan_memberi_hasil_benar(self) -> None:
        """Simulasi: logits condong ke kelas 2 (positive) harus jadi p_pos tertinggi.

        Inilah bug senyap yang dikunci: bila `_PROTOCOL_ORDER` salah, model
        yang benar-benar memprediksi positif akan dilaporkan negatif.
        """
        from model.xau.src.model import _PROTOCOL_ORDER

        logits = np.array([[0.0, 0.0, 5.0]])  # kelas 2 menang
        z = np.exp(logits - logits.max(axis=1, keepdims=True))
        probs = z / z.sum(axis=1, keepdims=True)
        ordered = probs[0][list(_PROTOCOL_ORDER)]
        p_pos, p_neu, p_neg = ordered
        assert p_pos > p_neg and p_pos > p_neu
        assert abs(p_pos + p_neu + p_neg - 1.0) < 1e-6

    def test_tanpa_bobot_error_jelas(self, tmp_path: Path) -> None:
        """Tanpa artefak, error harus menuntun ke skrip latih, bukan segfault."""
        from model.xau.src.model import FinbertGoldSentiment

        m = FinbertGoldSentiment(
            checkpoint_dir=tmp_path / "tidak_ada",
            temperature_path=tmp_path / "t.json",
            metrics_path=tmp_path / "m.json",
        )
        assert not m.is_fitted
        with pytest.raises(FileNotFoundError, match="train_xau_finbert"):
            m.predict_probs(["gold rises"])


@pytest.mark.slow
@pytest.mark.skipif(
    not CHECKPOINT_DIR.exists(),
    reason="bobot FinBERT-EMAS belum dilatih di mesin ini",
)
class TestTrainedModel:
    """Dijalankan hanya bila artefak hasil latih tersedia.

    Ditandai `slow` (audit P2-6) karena memuat model 440 MB. Sebelumnya test
    ini lolos deteksi `device` otomatis di dalam `FinbertGoldSentiment`, yang
    memilih CUDA bila tersedia: di mesin dengan VRAM yang sudah terpakai, test
    gagal karena OOM -- kegagalan lingkungan, bukan logika. Karena itu device
    dipaksa "cpu" secara eksplisit di sini.
    """

    def test_protokol_terpenuhi(self) -> None:
        from model.xau.src.model import FinbertGoldSentiment

        # device="cpu" dipaksa: test ini menguji protokol [pos, neu, neg],
        # bukan performa. Tanpa ini, OOM di GPU bersama membuat test gagal
        # karena lingkungan, bukan karena kode (audit P2-6).
        m = FinbertGoldSentiment(device="cpu")
        probs = m.predict_probs(["gold prices rise sharply", "gold falls"])
        assert len(probs) == 2
        for p in probs:
            assert p.model == "finbert_gold"
            assert 0.0 <= p.p_pos <= 1.0
            total = p.p_pos + p.p_neu + p.p_neg
            assert abs(total - 1.0) < 1e-2

    def test_metrik_tersedia_dan_wajar(self) -> None:
        mp = ROOT / "model/xau/weights/metrics.json"
        assert mp.exists(), "metrics.json tidak ada setelah training"
        m = json.loads(mp.read_text(encoding="utf-8"))
        assert m["label_order"] == ["negative", "neutral", "positive"]
        assert 0.0 <= m["test_macro_f1"] <= 1.0
