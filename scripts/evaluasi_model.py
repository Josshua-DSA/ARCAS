"""Tulis docs/EVALUASI-MODEL.md dari artefak evaluasi yang tersimpan.

Angka TIDAK dihitung ulang di sini: semuanya dibaca dari berkas hasil
pelatihan/evaluasi, supaya laporan tidak bisa berbeda dari yang dipakai model.
Satu-satunya yang dihitung langsung adalah akurasi router, karena itu memang
tidak pernah disimpan sebagai artefak.

Jalankan: python scripts/evaluasi_model.py
"""

from __future__ import annotations

import json
import random
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
XAU_EVAL = ROOT / "model/xau/evaluation/eval_report.json"
XAU_META = ROOT / "model/xau/weights/metrics.json"
FOMC_META = ROOT / "model/fomc/weights/metrics.json"
KELUARAN = ROOT / "docs/EVALUASI-MODEL.md"

GOLD = ROOT / "dataset/gold_sinha/data/train-00000-of-00001.parquet"
FOMC_DATA = ROOT / "dataset/fomc/train/lab-manual-split-combine-train-5768.xlsx"


def baca(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def angka(v, digit: int = 4) -> str:
    """Format angka; None jadi 'tidak tersedia', bukan 0 yang menyesatkan."""
    if v is None:
        return "tidak tersedia"
    if isinstance(v, float):
        return f"{v:.{digit}f}"
    return str(v)


def akurasi_router(n: int = 200) -> dict[str, float | None]:
    """Ukur akurasi routing pada sampel dataset nyata."""
    hasil: dict[str, float | None] = {"gold": None, "fomc": None, "n": n}
    try:
        from backend.src.tagging.model_router import ModelRouter

        router = ModelRouter()
    except Exception:
        return hasil

    if GOLD.exists():
        import pandas as pd

        teks = pd.read_parquet(GOLD)["News"].dropna()
        random.seed(0)
        sampel = random.sample(list(teks), min(n, len(teks)))
        hasil["gold"] = sum(
            1 for t in sampel if router.route(t)[0] == ["finbert_emas"]
        ) / len(sampel)

    if FOMC_DATA.exists():
        import pandas as pd

        teks = pd.read_excel(FOMC_DATA)["sentence"].dropna()
        random.seed(0)
        sampel = random.sample(list(teks), min(n, len(teks)))
        hasil["fomc"] = sum(
            1 for t in sampel if router.route(t)[0] == ["fomc_roberta"]
        ) / len(sampel)

    return hasil


def bagian_xau(ev: dict, meta: dict) -> str:
    if not ev and not meta:
        return (
            "## Emas (FinBERT-EMAS)\n\n"
            "**Metrik tidak tersedia.** Artefak evaluasi belum ada di mesin ini.\n"
        )

    baris = [
        "## Emas (FinBERT-EMAS)\n",
    ]
    if meta:
        baris.append(
            f"- Model: `{meta.get('model_version', 'tidak tersedia')}`\n"
            f"- Basis: `{meta.get('base_checkpoint', 'tidak tersedia')}`\n"
            f"- Pembagian data: latih {meta.get('n_train')}, "
            f"validasi {meta.get('n_val')}, uji {meta.get('n_test')}\n"
            f"- Seed: {meta.get('seed')} · epoch {meta.get('epochs')} · "
            f"lr {meta.get('lr')} · batch {meta.get('batch_size')}\n"
        )

    baris.append("\n### Ringkasan pada set uji\n\n")
    baris.append("| Metrik | Nilai |\n|---|---|\n")
    for label, nilai in (
        ("Sampel uji", ev.get("n_test")),
        ("Akurasi", ev.get("accuracy")),
        ("Macro F1", ev.get("macro_f1")),
        ("ECE sebelum kalibrasi", ev.get("ece_pre")),
        ("ECE sesudah kalibrasi", ev.get("ece_post")),
        ("Ambang ECE", ev.get("ece_target")),
    ):
        if nilai is not None:
            baris.append(f"| {label} | {angka(nilai)} |\n")

    if ev.get("ece_pre") is not None and ev.get("ece_post") is not None:
        turun = (1 - ev["ece_post"] / ev["ece_pre"]) * 100
        baris.append(
            f"\nKalibrasi suhu menurunkan ECE {turun:.0f}%, dari "
            f"{angka(ev['ece_pre'])} ke {angka(ev['ece_post'])}.\n"
        )

    per_kelas = ev.get("per_class") or {}
    if per_kelas:
        baris.append("\n### Per kelas\n\n")
        baris.append("| Kelas | Precision | Recall | F1 | Support |\n|---|---|---|---|---|\n")
        for k, v in per_kelas.items():
            baris.append(
                f"| {k} | {angka(v.get('precision'))} | {angka(v.get('recall'))} | "
                f"{angka(v.get('f1'))} | {v.get('support', '—')} |\n"
            )

    cm = ev.get("confusion_matrix") or {}
    if cm.get("rows_true_cols_pred"):
        labels = cm.get("labels") or []
        baris.append("\n### Matriks konfusi\n\nBaris = aktual, kolom = prediksi.\n\n")
        baris.append("| aktual \\ prediksi | " + " | ".join(labels) + " |\n")
        baris.append("|---" * (len(labels) + 1) + "|\n")
        for i, row in enumerate(cm["rows_true_cols_pred"]):
            nama = labels[i] if i < len(labels) else str(i)
            baris.append(f"| **{nama}** | " + " | ".join(str(n) for n in row) + " |\n")

    return "".join(baris)


def bagian_fomc(meta: dict) -> str:
    if not meta:
        return (
            "## FOMC (RoBERTa)\n\n"
            "**Metrik tidak tersedia.** `model/fomc/weights/metrics.json` belum ada: "
            "bobot hasil pelatihan tidak ikut ter-clone (`.gitignore`), dan skrip "
            "evaluasi FOMC belum menulis ringkasan metrik.\n\n"
            "Untuk melengkapinya: jalankan `python scripts/fetch_weights.py` lalu "
            "`model/fomc/evaluation/evaluate_holdout.py`, dan simpan hasilnya ke "
            "`model/fomc/weights/metrics.json`.\n"
        )
    baris = ["## FOMC (RoBERTa)\n\n", "| Metrik | Nilai |\n|---|---|\n"]
    for label, kunci in (
        ("Sampel uji", "n_test"),
        ("Akurasi", "accuracy"),
        ("Macro F1", "macro_f1"),
        ("ECE", "ece_post"),
    ):
        if meta.get(kunci) is not None:
            baris.append(f"| {label} | {angka(meta[kunci])} |\n")
    return "".join(baris)


def main() -> int:
    ev_xau = baca(XAU_EVAL)
    meta_xau = baca(XAU_META)
    meta_fomc = baca(FOMC_META)
    router = akurasi_router()

    isi = [
        "# Evaluasi Model ARCAS\n\n",
        f"Digenerate: {date.today().isoformat()} · oleh `scripts/evaluasi_model.py`\n\n",
        "Semua angka di bawah dibaca dari artefak evaluasi yang tersimpan di disk. "
        "Tidak ada yang dihitung ulang saat laporan dibuat, supaya angka di dokumen "
        "ini tidak bisa berbeda dari angka yang dipakai model.\n\n",
        "Evaluasi ini mengukur **kualitas model membaca teks**, bukan profit trading. "
        "Sesuai `context/RULES.md` §11.9, fitur tidak dinilai dari untung-rugi.\n\n",
        "---\n\n",
        bagian_xau(ev_xau, meta_xau),
        "\n",
        bagian_fomc(meta_fomc),
        "\n",
        "---\n\n## Router: pemilihan model spesialis\n\n",
    ]

    if router["gold"] is None and router["fomc"] is None:
        isi.append(
            "**Tidak tersedia.** Dataset atau centroid router tidak ada di mesin ini.\n"
        )
    else:
        isi.append(
            f"Diukur langsung pada {router['n']} sampel acak per dataset "
            "(seed 0). Teks emas harus dirutekan ke `finbert_emas`, teks FOMC ke "
            "`fomc_roberta`.\n\n| Dataset | Akurasi routing |\n|---|---|\n"
        )
        if router["gold"] is not None:
            isi.append(f"| Emas (gold_sinha) | {router['gold']:.2%} |\n")
        if router["fomc"] is not None:
            isi.append(f"| FOMC | {router['fomc']:.2%} |\n")

    isi.append(
        "\n---\n\n## Yang belum dievaluasi\n\n"
        "- **Asosiasi sentimen ↔ harga**: dihitung terpisah oleh `cli stats` "
        "(OLS-HAC, Granger, CAR) dan disimpan di tabel `stat_results`. "
        "Belum ada yang signifikan setelah koreksi Benjamini-Hochberg.\n"
        "- **Konsistensi persona**: uji monotonisitas yang dijanjikan "
        "`context/DESIGN.md` §12.4 belum diimplementasikan.\n"
        "- **Kepatuhan alokasi**: total 100% dan batas min/max dijaga oleh tes, "
        "tetapi belum dilaporkan sebagai metrik.\n"
    )

    KELUARAN.parent.mkdir(parents=True, exist_ok=True)
    KELUARAN.write_text("".join(isi), encoding="utf-8")
    print(f"Ditulis: {KELUARAN} ({KELUARAN.stat().st_size:,} byte)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
