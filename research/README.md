# research/ — Ringkasan Paper Terkait

> Folder `papers/` berisi 15 PDF primer dan pendukung (18 MB total, dilacak di repo).
> Disusun untuk mendukung usulan skripsi/TA: **Asosiasi Sentimen Berita Pasar terhadap 3 Target Makro (XAU/RATE_UST/SPX)**.

## 1. Paper Utama & Pendukung (Tersimpan di `research/papers/`)

| File PDF | Judul / Penulis | Metode & Target | Temuan Utama | Relevansi Proyek |
|---|---|---|---|---|
| `papers_phrasebank_malo2014.pdf` | *Good debt or bad debt: Detecting semantic orientations in economic texts* (Malo et al., 2014) | 4.840 kalimat finansial EN, 16 anotator, agreement 50–100% | Benchmark standar financial sentiment analysis | Rujukan metodologi tone finansial (folder lokal dihapus 2026-10-11, bukan makro) |
| `papers_finbert_original_araci2019.pdf` | *FinBERT: Financial Sentiment Analysis with Pre-trained Language Models* (Araci, 2019) | FinBERT vs BERT vs LSTM pada PhraseBank | FinBERT unggul transfer learning domain finansial | Arsitektur scorer EN utama di `DESIGN.md` §3.1 |
| `papers_indobert_indolem.pdf` | *Indo4B: Towards Benchmark Datasets for Indonesian NLP* / IndoLEM (Koto et al., 2020) | IndoBERT pretraining 4B token ID | Model dasar NLP bahasa Indonesia | Histori saja (Track A ID dicoret 2026-10-11, EN-only) |
| `papers_zenodo_indobert_cnbc.pdf` | *Fine-tuned IndoBERT for stock market sentiment analysis: evidence from CNBC Indonesia news* (2025) | IndoBERT-Large pada 9.819 headline CNBC ID 2024–2025 | Akurasi 78–81% | Histori saja (Track A ID dicoret 2026-10-11, EN-only) |
| `papers_fnspid_dataset.pdf` | *A Comprehensive Financial News Dataset in Time Series* (Dong et al., 2024 / FNSPID) | 15,7jt berita + 29,7jt harga, 4.775 emiten 1999–2023 | Sinyal sentimen menambah akurasi arah pasar; deret waktu terstruktur | Referensi arsitektur dataset EN historis (folder lokal dihapus 2026-10-11) |
| `papers_finbert_lstm.pdf` | *Financial sentiment analysis using FinBERT with application in predicting stock movement* (2023) | FinBERT (`ProsusAI/finbert`) → `SentimentScore = P(pos) - P(neg)` | Sentimen perbaiki akurasi vs baseline statistik murni | Dasar formulasi skor kontinu `[-1, 1]` di `SCHEMA.md` |
| `papers_finbert_famafrench.pdf` | *Dynamic Asset Pricing: Integrating FinBERT-Based Sentiment Quantification with Fama-French Five-Factor Model* (2025) | FinBERT indeks harian + rolling regression + event study | Sentimen time-varying; efek membesar saat volatilitas tinggi | Dasar event study & regresi kontrol makro di `DESIGN.md` §6 |
| `papers_stfa_semantictime.pdf` | *Using large models and time series forecasting for market reaction analysis* (PLOS ONE, 2025) | Delay-aware temporal alignment + bootstrap CI + Bonferroni | Temporal alignment krusial agar tidak ada lookahead bias | Penegasan aturan cut-off UTC di `RULES.md` & koreksi p-value |
| `papers_granger_news_return.pdf` | *The relation between news events and stock price jump* (Wang, 2013 / ANU) | Granger causality: sentimen berita → return saham (RavenPack) | Sentimen memicu Granger causality bagi return pasar | Rujukan metodologis uji Granger causality di `DESIGN.md` §6.3 |
| `papers_twitter_djia_eventstudy.pdf` | *The Effects of Twitter Sentiment on Stock Price Returns* (Bollen / PLOS ONE, 2015) | Event study: CAR (Cumulative Abnormal Returns) lonjakan sentimen | CAR terukur 1–2% pasca spike sentimen; korelasi normal rendah | Rujukan metodologi event study CAR di `DESIGN.md` §6.4 |
| `papers_wti_multidim_llm.pdf` | *Beyond Polarity: Multi-Dimensional Sentiment Signals for WTI Crude Oil Futures* (2026) | Berita komoditas minyak mentah (WTI) + FinBERT | Dinamika komoditas asimetris dibanding saham | Referensi histori saja (OIL/NG dicoret 2026-10-11, murni 3) |
| `papers_gold_commodity_news_sinha2020.pdf` | *Impact of News on the Commodity Market: Dataset and Results* (Sinha et al., 2020 / arXiv) | 11.412 headline teranotasi berita Emas (2000–2019) + causal impact | Informasi berita komoditas terbukti kausal mempengaruhi harga emas | Rujukan langsung target safe-haven Emas (`XAU`) |
| `papers_bert_vs_gpt_financial_2024.pdf` | *BERT vs GPT for financial engineering* (arXiv:2405.12990, 2024) | Benchmark Transformer domain komoditas & trading | Fine-tuned BERT unggul +10–16% F1 vs GPT, interpretabilitas tinggi tanpa risiko halusinasi | Landasan akademik pemilihan BERT & eliminasi LLM generatif |
| `papers_calibration_ece_guo2017.pdf` | *On Calibration of Modern Neural Networks* (Guo et al., ICML 2017) | Expected Calibration Error (ECE) + Temperature Scaling | Model deep modern overconfident; scaling suhu pulihkan kalibrasi | Dasar matematis kalibrasi probabilitas modul M5 & `SCHEMA.md` |
| `papers_epu_macro_baker2016.pdf` | *Measuring Economic Policy Uncertainty* (Baker, Bloom, Davis, QJE 2016) | Indeks ketidakpastian makroekonomi berbasis korpus berita koran | Teks berita efektif merefleksikan goncangan makroekonomi | Dasar teoretis agregasi teks ke tema makro (`impact_graph.yaml`) |

## 2. Sintesis untuk Sidang Skripsi / TA

1. **State of the Art & Pemilihan Model**:
   - `papers_bert_vs_gpt_financial_2024.pdf` membuktikan domain-specific encoder (BERT) lebih unggul dan aman dibanding LLM generatif untuk rekayasa finansial karena akurasi klasifikasi lebih tinggi dan bebas dari halusinasi.
   - `papers_calibration_ece_guo2017.pdf` memperkuat keharusan kalibrasi ECE di modul M5 agar probabilitas sentimen benar-benar mencerminkan tingkat keyakinan empiris.

2. **Celah Riset (Research Gap)**:
   - Mayoritas literatur berfokus sempit: saham individual AS saja (`FNSPID`), indeks saham domestik saja (`Zenodo CNBC`), atau satu komoditas terisolasi (`WTI 2026`, `Gold Sinha 2020`).
   - Proyek ini mengisi celah dengan menghubungkan **3 target makro** (`XAU` emas, `RATE_UST` yield obligasi US, `SPX`) dalam satu model transmisi terpadu (`impact_graph.yaml`, murni 3 v2026-10-11-p3).

3. **Integritas Metodologis**:
   - **Lookahead Bias Prevention**: Menghindari kebocoran data masa depan via cut-off UTC 00:00 tegas (`papers_stfa_semantictime.pdf`).
   - **Kausalitas & Event Abnormal**: Menguji hubungan arah kausal (`papers_granger_news_return.pdf`) dan respon abnormal jangka pendek (`papers_twitter_djia_eventstudy.pdf`).
