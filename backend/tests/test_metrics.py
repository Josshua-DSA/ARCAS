"""Test untuk metrik evaluasi bersama (`model/common/metrics.py`).

Audit P1-5 mencatat bahwa angka ECE, p-value McNemar, dan CI bootstrap yang
dilaporkan untuk Track XAU tidak pernah diverifikasi: fungsi McNemar/bootstrap
hanya hidup di dalam skrip evaluasi FOMC, sehingga padanan XAU tidak teruji.

Test di sini mengunci perilaku metrik tersebut lewat nilai yang dapat dihitung
manual, bukan sekadar "tidak crash".

CATATAN PENTING tentang `compute_ece` (single-label):
Fungsi ini menerima `probs` lalu MENGABAIKANNYA. Ia memakai `confidences`
sebagai keyakinan dan `true_labels` sebagai IND A TOR biner benar/salah
(0 = salah, 1 = benar) -- bukan label kelas. Kontrak itu tidak terdokumentasi
dan bertentangan dengan `compute_multiclass_ece` di
`model/fomc/src/calibrator.py`, yang menerima probabilitas per kelas dan label
kelas. Karena itu fungsi ini TIDAK dipakai di mana pun dalam produksi
(diverifikasi: nol pemanggil) dan berada di jalur deprecated.

Test di bawah mengunci perilaku yang ada sekarang agar tidak berubah diam-diam,
sekaligus mendokumentasikan keanehannya.
"""

from __future__ import annotations

import pytest

from model.common.metrics import (
    compute_bootstrap_ci,
    compute_ece,
    compute_mcnemar_test,
    evaluate_predictions,
)


class TestMcNemar:
    """Uji McNemar dengan koreksi kontinuitas Edwards."""

    def test_kasus_manual_terhitung_benar(self) -> None:
        """Angka chi2 dan p dihitung manual dari tabel kontingensi.

        Skenario 10 sampel: roberta benar di 10 posisi, baseline benar di 6
        (posisi 2..7).
          n01 (baseline salah, roberta benar) = 4
          n10 (baseline benar, roberta salah) = 0
          n11 (keduanya benar) = 6
          n00 (keduanya salah) = 0        total 4+0+6+0 = 10

        Edwards: chi2 = (|n01-n10| - 1)^2 / (n01+n10) = (4-1)^2/4 = 2.25
        p = chi2.sf(2.25, df=1) = 0.1336
        """
        y_true = [0, 0, 1, 1, 2, 2, 0, 1, 2, 0]
        y_pred_roberta = [0, 0, 1, 1, 2, 2, 0, 1, 2, 0]  # 10 benar
        y_pred_base = [1, 1, 1, 1, 2, 2, 0, 1, 1, 1]      # 6 benar

        r = compute_mcnemar_test(y_true, y_pred_base, y_pred_roberta)
        t = r["contingency_table"]

        assert t["roberta_correct_baseline_wrong_n01"] == 4
        assert t["baseline_correct_roberta_wrong_n10"] == 0
        assert t["both_correct_n11"] == 6
        assert t["both_wrong_n00"] == 0
        assert r["chi2_statistic"] == pytest.approx(2.25, abs=1e-4)
        assert r["p_value"] == pytest.approx(0.1336, abs=1e-3)
        assert r["significant_p_05"] is False

    def test_komponen_diadopsi_hanya_bila_signif_dan_lebih_baik(self) -> None:
        """`component_adopted` mensyaratkan p<0.05 DAN n01>n10.

        Signifikansi saja tidak cukup: bila roberta justru lebih sering salah
        (n10 > n01), komponen tidak boleh diadopsi walau p kecil.
        """
        y_true = [0] * 40
        y_pred_roberta = [0] * 40           # semua benar
        y_pred_base = [1] * 20 + [0] * 20   # salah di 20 pertama

        r = compute_mcnemar_test(y_true, y_pred_base, y_pred_roberta)
        assert r["significant_p_05"] is True
        assert r["component_adopted"] is True

        # Kebalikannya: roberta lebih buruk -> harus TIDAK diadopsi
        r_balik = compute_mcnemar_test(y_true, y_pred_roberta, y_pred_base)
        assert r_balik["significant_p_05"] is True
        assert r_balik["component_adopted"] is False

    def test_tanpa_selisih_tidak_signifikan(self) -> None:
        """Bila kedua model identik, tabel diskordan nol -> p=1.0."""
        y_true = [0, 1, 2, 0, 1]
        sama = [0, 1, 2, 0, 1]

        r = compute_mcnemar_test(y_true, sama, sama)

        assert r["chi2_statistic"] == 0.0
        assert r["p_value"] == 1.0
        assert r["significant_p_05"] is False
        assert r["component_adopted"] is False

    def test_tabel_kontingensi_konsisten_dengan_jumlah_sampel(self) -> None:
        """Keempat sel harus berjumlah sama dengan jumlah sampel."""
        y_true = [0, 1, 2, 0, 1, 2, 0, 1]
        y_b = [0, 0, 2, 1, 1, 2, 0, 0]
        y_r = [0, 1, 2, 0, 1, 2, 1, 1]

        r = compute_mcnemar_test(y_true, y_b, y_r)
        t = r["contingency_table"]
        total = (t["both_correct_n11"] + t["both_wrong_n00"]
                 + t["baseline_correct_roberta_wrong_n10"]
                 + t["roberta_correct_baseline_wrong_n01"])

        assert total == len(y_true)
        assert t["both_correct_n11"] == sum(
            1 for a, b, c in zip(y_true, y_b, y_r) if a == b and a == c
        )


class TestBootstrapCI:
    def test_reproducible_dengan_seed_sama(self) -> None:
        """Seed yang sama harus menghasilkan angka identik."""
        y_true = [0, 1, 2] * 20
        y_b = [0, 1, 2] * 10 + [0, 0, 0] * 10
        y_r = [0, 1, 2] * 20

        a = compute_bootstrap_ci(y_true, y_b, y_r, n_bootstraps=200)
        b = compute_bootstrap_ci(y_true, y_b, y_r, n_bootstraps=200)

        assert a == b

    def test_model_lebih_baik_memberi_ci_positif(self) -> None:
        """Bila roberta jauh lebih baik, batas bawah CI harus > 0."""
        y_true = [0, 1, 2] * 30
        y_b = [0, 0, 0] * 30      # baseline selalu salah
        y_r = [0, 1, 2] * 30      # roberta selalu benar

        r = compute_bootstrap_ci(y_true, y_b, y_r, n_bootstraps=200)

        assert r["ci_95_lower"] > 0
        assert r["ci_strictly_positive"] is True
        assert r["ci_95_lower"] <= r["ci_95_upper"]

    def test_model_identik_memberi_selisih_nol(self) -> None:
        """Dua model identik -> selisih 0, CI memuat 0 (tidak signifikan)."""
        y_true = [0, 1, 2] * 20
        sama = [0, 1, 2] * 20

        r = compute_bootstrap_ci(y_true, sama, sama, n_bootstraps=200)

        assert r["mean_delta_macro_f1"] == pytest.approx(0.0, abs=1e-9)
        assert r["ci_strictly_positive"] is False

    def test_seed_berbeda_memberi_hasil_sedikit_berbeda(self) -> None:
        """Sanity check: seed benar-benar dipakai, bukan diabaikan."""
        y_true = [0, 1, 2] * 20
        y_b = [0, 1, 2] * 10 + [0, 0, 0] * 10
        y_r = [0, 1, 2] * 20

        a = compute_bootstrap_ci(y_true, y_b, y_r, n_bootstraps=200, seed=1)
        b = compute_bootstrap_ci(y_true, y_b, y_r, n_bootstraps=200, seed=2)

        assert a["ci_95_lower"] != b["ci_95_lower"]


class TestECE:
    """`compute_ece` (single-label, deprecated) -- lihat catatan modul.

    Kontrak sebenarnya: `true_labels` adalah indikator biner benar(1)/salah(0),
    dan argumen `probs` diabaikan sepenuhnya.
    """

    def test_kosong_mengembalikan_nol(self) -> None:
        assert compute_ece([], [], []) == 0.0

    def test_konfiden_sempurna_dan_semua_benar_memberi_nol(self) -> None:
        # confidence 1.0 harus masuk bin terakhir (batas atas inklusif)
        assert compute_ece([1.0] * 3, [1.0] * 3, [1, 1, 1]) == pytest.approx(0.0)

    def test_konfiden_sempurna_dan_semua_salah_memberi_satu(self) -> None:
        """Model yakin 1.0 tetapi semua salah -> ECE mendekati 1.0.

        Regresi yang dijaga: versi lama memakai `<` pada batas atas bin
        sehingga confidence tepat 1.0 terbuang dan ECE dilaporkan 0.0
        (seolah sempurna) -- false negative terburuk untuk metrik kalibrasi.
        """
        assert compute_ece([1.0] * 4, [1.0] * 4, [0, 0, 0, 0]) == pytest.approx(1.0)

    def test_separuh_benar_memberi_setengah(self) -> None:
        # 2 dari 4 benar pada confidence 1.0 -> |0.5 - 1.0| = 0.5
        assert compute_ece([1.0] * 4, [1.0] * 4, [1, 1, 0, 0]) == pytest.approx(0.5)

    def test_argumen_probs_diabaikan(self) -> None:
        """Mendokumentasikan keanehan: `probs` tidak memengaruhi hasil."""
        a = compute_ece([0.1] * 4, [1.0] * 4, [1, 0, 1, 0])
        b = compute_ece([0.9] * 4, [1.0] * 4, [1, 0, 1, 0])
        assert a == b


class TestEvaluatePredictions:
    def test_kosong_tidak_error(self) -> None:
        r = evaluate_predictions([], [])
        assert r == {"f1_macro": 0.0, "accuracy": 0.0, "kappa": 0.0}

    def test_prediksi_sempurna(self) -> None:
        r = evaluate_predictions([0, 1, 2, 0], [0, 1, 2, 0])
        assert r["f1_macro"] == pytest.approx(1.0)
        assert r["accuracy"] == pytest.approx(1.0)
