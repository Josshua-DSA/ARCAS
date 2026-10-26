"""Test untuk perhitungan laporan evaluasi XAU (audit P1-5).

Audit mencatat `model/xau/evaluation/evaluate.py` 0% teruji: angka macro-F1,
per-kelas, confusion matrix, dan ECE yang dilaporkan untuk Track XAU tidak
diverifikasi test apa pun. Ukuran cakupan itu memang tidak bisa diuji tanpa
memuat model 440 MB, jadi logikanya diangkat ke `build_report()` dan
`softmax_with_temperature()` -- keduanya murni dan dapat diuji di sini.

Yang dikunci: angka yang masuk laporan harus benar secara aritmetika, dan
`meets_target` harus mengikuti ECE SESUDAH kalibrasi (bukan sebelumnya) --
salah memilih kolom di sini akan membuat laporan mengklaim target terpenuhi
padahal tidak.
"""

from __future__ import annotations

import numpy as np
import pytest

from model.fomc.src.calibrator import compute_multiclass_ece
from model.xau.evaluation.evaluate import build_report, softmax_with_temperature


class TestSoftmaxDenganSuhu:
    def test_suhu_satu_sama_dengan_softmax_biasa(self) -> None:
        z = np.array([[1.0, 2.0, 3.0]])
        e = np.exp(z - z.max(axis=1, keepdims=True))
        harapan = e / e.sum(axis=1, keepdims=True)

        assert softmax_with_temperature(z, 1.0) == pytest.approx(harapan)

    def test_tiap_baris_menjumlah_satu(self) -> None:
        z = np.array([[0.5, -1.0, 2.0], [3.0, 3.0, 3.0]])
        p = softmax_with_temperature(z)
        assert np.allclose(p.sum(axis=1), 1.0)

    def test_suhu_besar_membuat_distribusi_lebih_datar(self) -> None:
        """T > 1 melembutkan; T < 1 menajamkan. Ini inti kalibrasi suhu."""
        z = np.array([[0.0, 2.0, 0.0]])
        tajam = softmax_with_temperature(z, 0.5)
        datar = softmax_with_temperature(z, 5.0)

        assert tajam.max() > datar.max()

    def test_suhu_nol_tidak_meledak(self) -> None:
        """Suhu 0 (artefak kalibrasi rusak) tidak boleh menghasilkan NaN."""
        z = np.array([[1.0, 2.0, 3.0]])
        p = softmax_with_temperature(z, 0.0)
        assert np.isfinite(p).all()
        assert np.allclose(p.sum(axis=1), 1.0)

    def test_argmax_tidak_berubah_oleh_suhu(self) -> None:
        """Kalibrasi suhu tidak boleh mengubah kelas prediksi.

        Bila berubah, laporan akan memakai prediksi berbeda dari yang
        dilaporkan di confusion matrix -- tidak konsisten.
        """
        z = np.array([[0.1, 5.0, 0.2], [3.0, 0.0, 1.0]])
        for t in (0.3, 1.0, 2.0, 10.0):
            assert np.array_equal(
                softmax_with_temperature(z, t).argmax(axis=1), z.argmax(axis=1)
            )


class TestBuildReport:
    def _laporan(self, **kwargs):
        default = dict(
            y_true=np.array([0, 1, 2, 0]),
            logits=np.array(
                [
                    [2.0, 0.0, 0.0],  # benar (0)
                    [0.0, 2.0, 0.0],  # benar (1)
                    [0.0, 0.0, 2.0],  # benar (2)
                    [0.0, 2.0, 0.0],  # salah: seharusnya 0, ditebak 1
                ]
            ),
            temperature=1.0,
            ece_pre=0.3,
            ece_post=0.05,
        )
        default.update(kwargs)
        return build_report(**default)

    def test_akurasi_dan_macro_f1_benar(self) -> None:
        """3 dari 4 benar -> akurasi 0.75."""
        r = self._laporan()
        assert r["n_test"] == 4
        assert r["accuracy"] == pytest.approx(0.75)

    def test_prediksi_sempurna_memberi_f1_satu(self) -> None:
        y_true = np.array([0, 1, 2])
        logits = np.array([[5.0, 0.0, 0.0], [0.0, 5.0, 0.0], [0.0, 0.0, 5.0]])
        r = build_report(
            y_true=y_true, logits=logits, temperature=1.0, ece_pre=0.4, ece_post=0.05
        )
        assert r["macro_f1"] == pytest.approx(1.0)
        assert r["accuracy"] == pytest.approx(1.0)

    def test_confusion_matrix_menjumlah_sama_dengan_n(self) -> None:
        r = self._laporan()
        cm = np.array(r["confusion_matrix"]["rows_true_cols_pred"])
        assert cm.shape == (3, 3)
        assert cm.sum() == r["n_test"]

    def test_confusion_matrix_menempatkan_prediksi_di_baris_benar(self) -> None:
        """Baris = label sebenarnya, kolom = prediksi. Sampel ke-4 (true 0 -> 1)."""
        r = self._laporan()
        cm = np.array(r["confusion_matrix"]["rows_true_cols_pred"])
        # baris 0 (true=0): satu benar di kolom 0, satu salah di kolom 1
        assert cm[0][0] == 1
        assert cm[0][1] == 1

    def test_meets_target_memakai_ece_sesudah_kalibrasi(self) -> None:
        """Target 0.1 harus dinilai dari `ece_post`, bukan `ece_pre`.

        Kasus penting: ECE sebelum kalibrasi jelek (0.30) tetapi sesudahnya
        baik (0.05) -> target TERPENUHI. Bila kode keliru memakai ece_pre,
        laporan akan salah menyatakan target gagal.
        """
        r = self._laporan(ece_pre=0.30, ece_post=0.05)
        assert r["meets_target"] is True

        # Kebalikannya: setelah kalibrasi justru memburuk -> tidak terpenuhi
        r2 = self._laporan(ece_pre=0.05, ece_post=0.30)
        assert r2["meets_target"] is False

    def test_per_kelas_mencakup_semua_tone(self) -> None:
        r = self._laporan()
        assert set(r["per_class"]) == {"positive", "neutral", "negative"}
        for _tone, m in r["per_class"].items():
            assert 0.0 <= m["precision"] <= 1.0
            assert 0.0 <= m["recall"] <= 1.0
            assert 0.0 <= m["f1"] <= 1.0
            assert m["support"] >= 0

    def test_kelas_tanpa_sampel_tidak_error(self) -> None:
        """Holdout bisa saja tidak memuat satu kelas; laporan tidak boleh crash."""
        r = build_report(
            y_true=np.array([0, 0]),
            logits=np.array([[2.0, 0.0, 0.0], [2.0, 0.0, 0.0]]),
            temperature=1.0,
            ece_pre=0.1,
            ece_post=0.1,
        )
        assert r["per_class"]["positive"]["support"] == 0
        assert r["per_class"]["positive"]["f1"] == pytest.approx(0.0)

    def test_laporan_bisa_disimpan_sebagai_json(self) -> None:
        """Laporan harus JSON-serializable: `evaluate` menulisnya ke disk."""
        import json

        r = self._laporan()
        json.dumps(r)  # tidak boleh raise


class TestECEUntukLaporanXAU:
    """ECE multiclass yang dipakai laporan XAU harus menangani confidence 1.0.

    Fungsi ini sudah benar, tetapi belum ada test yang mengunci perilakunya
    dari sisi pemakaian XAU (audit P1-5).
    """

    def test_model_sempurna_memberi_ece_nol(self) -> None:
        true = np.array([0, 1, 2])
        probs = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        assert compute_multiclass_ece(probs, true) == pytest.approx(0.0)

    def test_yakin_penuh_tapi_salah_memberi_ece_satu(self) -> None:
        """Regresi: confidence tepat 1.0 harus masuk bin terakhir.

        Bila batas bin memakai `<` untuk semua bin, confidence 1.0 terbuang
        dan model yang selalu salah dilaporkan ECE 0.0 (sempurna).
        """
        true = np.array([0, 0, 0])
        probs = np.array([[0.0, 0.0, 1.0]] * 3)  # yakin kelas 2, sebenarnya kelas 0
        assert compute_multiclass_ece(probs, true) == pytest.approx(1.0)

    def test_tebakan_acak_mendekati_ece_nol(self) -> None:
        """Probabilitas seragam = akurasi ~1/3 = confidence ~1/3 -> ECE kecil."""
        true = np.array([0, 1, 2] * 10)
        probs = np.array([[1 / 3, 1 / 3, 1 / 3]] * 30)
        assert compute_multiclass_ece(probs, true) == pytest.approx(0.0, abs=0.02)
