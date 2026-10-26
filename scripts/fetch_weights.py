#!/usr/bin/env python3
"""Unduh dan verifikasi bobot model inferensi (audit P1-1).

Masalah yang diselesaikan
-------------------------
Bobot tidak di-vendor di repo (`.gitignore` mengecualikan `*.bin`,
`*.safetensors`, `*.pt`, `*.onnx`). Akibatnya:

- Mesin baru tidak punya bobot FOMC-RoBERTa, sehingga `load_fomc_model()`
  mengembalikan `None` dan pipeline DIAM-DIAM jatuh ke baseline TF-IDF
  (57,98%) alih-alih RoBERTa (86,87%).
- Tidak ada yang membedakan "sengaja fallback" dari "gagal karena masalah".

Skrip ini membuat unduhan menjadi eksplisit dan terverifikasi: setiap berkas
dicek SHA256-nya, dan kegagalan checksum adalah error keras, bukan peringatan.

Pemakaian
---------
    # Unduh semua model (FOMC + XAU) dengan verifikasi checksum
    python scripts/fetch_weights.py --all

    # Hanya FOMC-RoBERTa
    python scripts/fetch_weights.py --model fomc

    # Verifikasi ulang tanpa jaringan (untuk CI / sebelum menjalankan pipeline)
    python scripts/fetch_weights.py --all --verify-only

    # Cetak checksum aktual (untuk memperbarui manifest setelah upgrade)
    python scripts/fetch_weights.py --model fomc --print-checksums

Catatan tentang sumber FOMC
---------------------------
Checkpoint primer `gtfintechlab/FOMC-RoBERTa` (rujukan paper ACL 2023) sedang
dibatasi di HuggingFace. Kode sudah punya jalur fallback ke mirror
`tim9510019/FOMC-RoBERTa`, dan manifest di bawah memakai mirror tersebut
karena itulah bobot yang benar-benar dipakai inferensi saat ini. Bila akses
ke checkpoint primer pulih, perbarui `CHECKSUMS` dengan menjalankan
`--print-checksums`.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Manifest checksum. Setiap entri: target direktori lokal -> daftar berkas.
#:
#: Nilai SHA256 di bawah diambil dari bobot yang SUDAH TERBUKTI dipakai dan
#: lulus smoke test (`backend/tests/test_fomc_roberta_real.py`), bukan dari
#: dokumentasi pihak ketiga. Untuk XAU, checksum diisi saat bobot tersedia di
#: mesin pengembang; bila kosong, verifikasi hanya memeriksa keberadaan berkas
#: dan ukurannya (lihat `--verify-only`).
CHECKSUMS: dict[str, dict[str, Any]] = {
    "fomc": {
        "kind": "hf",
        "repo_id": "tim9510019/FOMC-RoBERTa",
        "local_dir": "model/fomc/weights/roberta",
        "files": {
            "config.json": {
                "sha256": "2922246d05e484441ed64d410854491aa52f4fd4f93fe8cf35ada59c12fd4979",
                "size": 903,
            },
            "pytorch_model.bin": {
                "sha256": "4f7a4f60ae60e639c3c1450257f6da04fee50f55c25f8cf9f227b38819fdd5ae",
                "size": 1421581361,
            },
            "tokenizer.json": {
                "sha256": "cfdd8e06b322eb64e234d00f479dd0939a39ce8e2f139814b48de8adf4448277",
                "size": 2108872,
            },
            "vocab.json": {
                "sha256": "ed19656ea1707df69134c4af35c8ceda2cc9860bf2c3495026153a133670ab5e",
                "size": 798293,
            },
        },
    },
    "xau": {
        "kind": "local",
        "local_dir": "model/xau/weights/finbert_gold",
        "files": {
            "config.json": {
                "sha256": "5ece7a4aaa9cf540c5894eb2d1059a70ce49d72c2633d4134bc87cfa2a544c0c",
                "size": 804,
            },
            "model.safetensors": {
                "sha256": "cbe75f3305766daa8327fdd48cee4ea5cfd7d29ffd87cba4f46bed71d8cfb437",
                "size": 439039996,
            },
            "tokenizer.json": {
                "sha256": "88d0fe9f83314699047419763d5927a447bd8d0113c0e69bd1b0f3081e9c1d52",
                "size": 712338,
            },
            "vocab.txt": {
                "sha256": "85f2481b4e3c25a7ece5e0e4930631a75c1a5fe2d31b0ecd9b5d51136ab98de8",
                "size": 226122,
            },
        },
    },
}


def sha256_of(path: Path, chunk: int = 1 << 20) -> str:
    """Hitung SHA256 tanpa memuat seluruh berkas (bobot bisa >1 GB)."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def verify_local(name: str, spec: dict[str, Any]) -> list[str]:
    """Verifikasi bobot yang sudah ada di disk. Kembalikan daftar masalah."""
    problems: list[str] = []
    local_dir = REPO_ROOT / spec["local_dir"]

    if not local_dir.exists():
        return [f"[{name}] direktori tidak ada: {local_dir}"]

    for filename, meta in spec["files"].items():
        f = local_dir / filename
        if not f.exists():
            problems.append(f"[{name}] berkas hilang: {filename}")
            continue

        actual_size = f.stat().st_size
        if meta.get("size") and actual_size != meta["size"]:
            problems.append(
                f"[{name}] {filename}: ukuran {actual_size} != {meta['size']} (berkas rusak/berbeda versi)"
            )
            continue

        expected = meta.get("sha256")
        if expected:
            actual = sha256_of(f)
            if actual != expected:
                problems.append(
                    f"[{name}] {filename}: SHA256 tidak cocok\n"
                    f"    diharapkan: {expected}\n"
                    f"    aktual   : {actual}"
                )

    return problems


def download_hf(name: str, spec: dict[str, Any]) -> None:
    """Unduh dari HuggingFace Hub lalu pindahkan ke direktori lokal."""
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print(
            "ERROR: huggingface_hub tidak terpasang. Jalankan:\n"
            "    pip install huggingface_hub",
            file=sys.stderr,
        )
        raise SystemExit(2) from None

    local_dir = REPO_ROOT / spec["local_dir"]
    local_dir.mkdir(parents=True, exist_ok=True)

    print(f"[{name}] mengunduh {spec['repo_id']} -> {local_dir}")
    for filename in spec["files"]:
        print(f"  - {filename} ...", end=" ", flush=True)
        cached = hf_hub_download(repo_id=spec["repo_id"], filename=filename)
        dest = local_dir / filename
        if dest.exists() and dest.resolve() == Path(cached).resolve():
            print("sudah ada (tertaut)")
            continue
        # Salin (bukan symlink) agar direktori bobot mandiri dan bisa dipindah.
        with Path(cached).open("rb") as src, dest.open("wb") as out:
            for block in iter(lambda: src.read(1 << 20), b""):
                out.write(block)
        print("selesai")


def print_checksums(name: str, spec: dict[str, Any]) -> None:
    """Cetak SHA256 + ukuran aktual, dalam format siap-tempel untuk manifest."""
    local_dir = REPO_ROOT / spec["local_dir"]
    print(f"# {name}: {spec['local_dir']}")
    entries = {}
    for filename in spec["files"]:
        f = local_dir / filename
        if not f.exists():
            print(f"#   {filename}: TIDAK ADA")
            continue
        entries[filename] = {
            "sha256": sha256_of(f),
            "size": f.stat().st_size,
        }
        print(f'    "{filename}": {{')
        print(f'        "sha256": "{entries[filename]["sha256"]}",')
        print(f'        "size": {entries[filename]["size"]},')
        print("    },")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Unduh & verifikasi bobot model (audit P1-1)")
    p.add_argument("--model", choices=sorted(CHECKSUMS), help="model yang diproses")
    p.add_argument("--all", action="store_true", help="semua model")
    p.add_argument(
        "--verify-only",
        action="store_true",
        help="jangan unduh; hanya verifikasi bobot yang sudah ada (exit 1 bila ada masalah)",
    )
    p.add_argument(
        "--print-checksums",
        action="store_true",
        help="cetak SHA256 aktual untuk memperbarui manifest",
    )
    args = p.parse_args(argv)

    if not args.all and not args.model:
        p.error("pilih --model <nama> atau --all")
    names = sorted(CHECKSUMS) if args.all else [args.model]

    if args.print_checksums:
        for name in names:
            print_checksums(name, CHECKSUMS[name])
        return 0

    if not args.verify_only:
        for name in names:
            spec = CHECKSUMS[name]
            if spec["kind"] == "hf":
                download_hf(name, spec)
            else:
                print(f"[{name}] bobot lokal: unduhan tidak tersedia, verifikasi saja")

    print()
    all_problems: list[str] = []
    for name in names:
        problems = verify_local(name, CHECKSUMS[name])
        if problems:
            all_problems.extend(problems)
        else:
            print(f"[{name}] OK -- semua berkas ada dan checksum cocok")

    if all_problems:
        print("\nGAGAL verifikasi:", file=sys.stderr)
        for problem in all_problems:
            print(f"  {problem}", file=sys.stderr)
        print(
            "\nTanpa bobot yang terverifikasi, pipeline akan DIAM-DIAM memakai "
            "baseline TF-IDF (akurasi lebih rendah) alih-alih model spesialis.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
