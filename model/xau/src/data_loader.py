"""Loader korpus `dataset/gold_sinha/` → teks + label tone 3 kelas.

Kontrak label mengikuti `model/xau/README.md` dan `GOLD_TONE_MAP` di
`backend/src/normalize/adapters.py`:

    Positive → 2
    Neutral  → 1
    Negative → 0
    none     → DIBUANG (bukan digabung ke neutral)

Pembuangan `none` bukan pilihan gaya: baris itu adalah headline tanpa sinyal
harga, dan menggabungkannya ke `neutral` akan mengajari model bahwa "tidak
membahas harga" sama dengan "harga stabil" — dua hal berbeda. `adapters.py`
sudah memutuskan hal yang sama untuk jalur ingest, jadi loader ini harus
konsisten dengannya, kalau tidak model dilatih pada distribusi yang berbeda
dari yang ditemui saat inferensi.

Modul ini sengaja TIDAK mengimpor torch/transformers: ia hanya membaca dan
membersihkan data, sehingga bisa dipakai skrip evaluasi ringan maupun test
tanpa memasang PyTorch.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TRAIN_PATH = ROOT / "dataset/gold_sinha/data/train-00000-of-00001.parquet"
DEFAULT_TEST_PATH = ROOT / "dataset/gold_sinha/data/test-00000-of-00001.parquet"

#: Label tone → id integer. Urutan ini WAJIB cocok dengan urutan probabilitas
#: `[p_pos, p_neu, p_neg]` di `model/common/protocol.py`; kalau dibalik, model
#: akan melaporkan sentimen terbalik tanpa error apa pun.
TONE_TO_LABEL: dict[str, int] = {"positive": 2, "neutral": 1, "negative": 0}
LABEL_TO_TONE: dict[int, str] = {v: k for k, v in TONE_TO_LABEL.items()}

#: Nama kolom di parquet. Dikumpulkan di satu tempat karena parquet ini
#: berasal dari re-upload pihak ketiga; bila sumbernya berganti nama kolom,
#: hanya daftar ini yang perlu disentuh.
TEXT_COL = "News"
TONE_COL = "Price Sentiment"
DATE_COL = "Dates"


def normalize_tone(raw: object) -> str | None:
    """Petakan nilai `Price Sentiment` mentah ke tone baku, atau None.

    None berarti baris harus dibuang (`none`, kosong, atau nilai tak dikenal).
    Nilai tak dikenal dibuang, bukan ditebak jadi neutral: menebak akan
    menyuntikkan label palsu ke data latih.
    """
    if raw is None:
        return None
    key = str(raw).strip().lower()
    return key if key in TONE_TO_LABEL else None


def sanitize_gold_df(df: pd.DataFrame) -> pd.DataFrame:
    """Bersihkan korpus mentah → kolom `text`, `label`, `tone`, `date`.

    Baris dibuang bila:
    - `Price Sentiment` tidak memetakan ke tone (termasuk `none`),
    - teks kosong / hanya spasi,
    - teks duplikat persis (korpus ini berisi headline berulang dari
      beberapa hari; duplikat di train membuat metrik validasi terlalu
      optimistis, dan bila bocor ke test, evaluasi jadi tidak sah).
    """
    df = df.copy()
    df["tone"] = df[TONE_COL].map(normalize_tone)
    df["text"] = df[TEXT_COL].astype("string").str.strip()

    mask = df["tone"].notna() & df["text"].notna()
    df = df[mask]
    df = df[df["text"].str.len() > 0]
    df = df.copy()

    df["label"] = df["tone"].map(TONE_TO_LABEL).astype(int)
    df["date"] = pd.to_datetime(df[DATE_COL], format="%d-%m-%Y", errors="coerce")

    df = df.drop_duplicates(subset=["text"], keep="first")
    out: pd.DataFrame = df.loc[:, ["text", "label", "tone", "date"]].reset_index(drop=True)
    return out


def load_gold_train_raw(path: Path | str = DEFAULT_TRAIN_PATH) -> pd.DataFrame:
    """Baca split train mentah (sebelum dibersihkan)."""
    return pd.read_parquet(path)


def load_gold_test_holdout(path: Path | str = DEFAULT_TEST_PATH) -> pd.DataFrame:
    """Baca split test mentah (holdout; jangan dipakai untuk memilih model)."""
    return pd.read_parquet(path)


def load_gold_train(path: Path | str = DEFAULT_TRAIN_PATH) -> pd.DataFrame:
    """Split train bersih, siap dilatih."""
    return sanitize_gold_df(load_gold_train_raw(path))


def load_gold_test(path: Path | str = DEFAULT_TEST_PATH) -> pd.DataFrame:
    """Split test bersih, hanya untuk evaluasi akhir."""
    return sanitize_gold_df(load_gold_test_holdout(path))


def split_train_val(
    df: pd.DataFrame,
    val_fraction: float = 0.15,
    seed: int = 5768,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pisahkan validation dari train untuk early stopping + temperature.

    Stratified agar kelas minoritas (`neutral` hanya ~4% korpus) tetap
    terwakili di validation; tanpa stratifikasi, satu fold bisa kehilangan
    kelas itu seluruhnya dan early stopping jadi buta terhadapnya.

    Split test TIDAK disentuh di sini — ia holdout murni.
    """
    from sklearn.model_selection import train_test_split

    train_df, val_df = train_test_split(
        df,
        test_size=val_fraction,
        random_state=seed,
        stratify=df["label"],
    )
    return train_df.reset_index(drop=True), val_df.reset_index(drop=True)


def get_texts_and_labels(df: pd.DataFrame) -> tuple[list[str], list[int]]:
    """Ambil pasangan (teks, label) siap umpan ke tokenizer."""
    return df["text"].astype(str).tolist(), df["label"].astype(int).tolist()
