# dataset/ — Katalog Data

> Dilacak git (total 3,8 MB). Status: 2026-10-12. Murni 3 (`XAU/RATE_UST/SPX`). Scope chat ini planning + `context/` + utensil draft; eksekusi baseline ML di chat lain.

| Folder | Isi | Lisensi | Status |
|---|---|---|---|
| `gold_sinha/` 976K | `SaguaroCapital/sentiment-analysis-in-commodity-market-gold` — train 8.456 + test 2.114 parquet (10 kolom: `Dates/URL/News/Price Direction Up/Constant/Down/Asset Comparision/Past Information/Future Information/Price Sentiment`) | `cc-by-nc-nd-4.0` | ✅ lokal |
| `fomc/` 2,9M | `gtfintechlab/fomc-hawkish-dovish` (Shah et al. ACL 2023) — 24 xlsx train + 24 test, seed 5768/78516/944601 | `CC BY-NC 4.0` | ✅ lokal |

## Mapping label (beku)
- Gold→`XAU`: `Price Direction Up→positive`, `Down→negative`, `Constant→neutral`. Kolom `none` (train 1.574) diputus di DESIGN §3.4 sebelum train.
- FOMC→`RATE_UST`: `Hawkish(LABEL_1)→positive`, `Dovish(LABEL_0)→negative`, `Neutral(LABEL_2)→neutral`.
- FOMC→`SPX`: arah balik, `Hawkish→negative`, `Dovish→positive`, `Neutral→neutral`. Tanpa label baru.
- Pilih 1 seed FOMC saja (rekomendasi `split-combine` 5768); 3 seed hash beda = split beda.

## Dihapus 2026-10-11
- `financial_phrasebank/` (2,7 MB, AllAgree 2.264) — bukan makro.
- `ihsg_indobert/` (18 MB, 556 baris nol label) — seiring coret `IHSG`.
- `fnspid_reduced/` (3,1 GB, mikro single-ticker) + `fnspid_full/` (kosong).
- Kaggle `daittan/gold-commodity-news-and-dimensions` 404 mati — jangan pakai; pakai HF `SaguaroCapital/...`.
- `TheFinAI/finben-fomc` test saja 496 rows — jangan train.

## Sitasi
- Sinha & Khandait 2020 (`arXiv:2009.04202`), didanai India Gold Policy Centre grant 1815012.
- Shah, Paturi & Chava 2023 (`https://aclanthology.org/2023.acl-long.368/`), model `gtfintechlab/FOMC-RoBERTa`.
