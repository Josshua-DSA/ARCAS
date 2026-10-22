"""FR-2 / T-6: deteksi artikel near-duplicate.

Dedup yang ada sebelumnya hanya *exact*: `sha256(norm(title)+norm(body))[:16]`.
Akibatnya rilis yang sama dari dua feed -- dengan satu kata berbeda, atau
dengan boilerplate "Baca juga:" yang beda -- masuk sebagai dua artikel, lalu
menghitung ganda di `daily_sentiment`.

Pendekatan di sini: TF-IDF karakter (3-5 gram) + cosine similarity. Dipilih
karena (a) sudah tersedia lewat scikit-learn, (b) deterministik sehingga
hasilnya reproducible (NFR), (c) tidak butuh model eksternal.

BATASAN YANG DISENGAJA:
Metode leksikal ini menangkap duplikasi *permukaan* (berita wire yang sama
disalin ulang dengan suntingan kecil). Ia **tidak** menangkap parafrase yang
mengganti kata dengan sinonim ("Gold rises" vs "Gold climbs") karena tidak ada
model embedding yang terpasang. Ambang `NEAR_DUP_THRESHOLD` karena itu
dipilih konservatif: lebih baik melewatkan duplikat daripada salah
menggabungkan dua berita berbeda.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Sequence

if TYPE_CHECKING:  # pragma: no cover
    from backend.src.schema import Article

#: Ambang penggabungan otomatis.
#:
#: Nilai ini dipilih dari pengukuran pada 67 artikel nyata di `data/finews.db`,
#: bukan tebakan. Distribusinya:
#:   1.000  -> 13 pasangan, semuanya salinan persis lintas-feed (aman digabung)
#:   0.749  -> DUA rilis Fed BERBEDA ("...application by Isabella Ba..." vs
#:             "...by Fleur Capit..."). Template kalimatnya sama, entitasnya
#:             beda. Menggabungkan ini akan MENGHILANGKAN berita nyata.
#:   0.563  -> satu berita Reuters yang sama disindikasi ke dua feed
#:             (finnhub & eulerpool), seharusnya digabung.
#:
#: Karena 0.563 (harus gabung) < 0.749 (tidak boleh gabung), TIDAK ADA satu
#: ambang global yang benar untuk keduanya dengan metode leksikal ini. Maka
#: 0.85 dipakai sebagai batas aman: hanya menangkap duplikasi yang jelas,
#: dan kasus 0.56 sengaja DIBIARKAN lolos ke pita tinjauan (lihat di bawah).
NEAR_DUP_THRESHOLD = 0.85

#: Batas bawah pita tinjauan. Pasangan dengan skor di antara nilai ini dan
#: `NEAR_DUP_THRESHOLD` TIDAK digabung otomatis, hanya dilaporkan agar bisa
#: diperiksa manusia. Ini konsekuensi langsung dari data di atas: pada rentang
#: itu ada kandidat benar (0.563) sekaligus kandidat salah (0.749), sehingga
#: keputusan otomatis di rentang tersebut tidak bisa dipertanggungjawabkan.
REVIEW_THRESHOLD = 0.55

#: Berapa banyak artikel lama (dari DB) yang ikut dibandingkan. Dibatasi agar
#: biaya tetap wajar saat riwayat sudah panjang.
MAX_HISTORY = 500


def _compose(article: "Article") -> str:
    """Teks pembanding: judul diberi bobot lebih dengan cara diulang.

    Badan berita sering memuat boilerplate yang sama antar-sumber, sedangkan
    judul adalah penanda topik yang paling kuat. Mengulang judul membuat
    kemiripan judul mendominasi skor.
    """
    title = (article.title or "").strip().lower()
    body = (article.body or "").strip().lower()
    return f"{title} {title} {body}".strip()


class NearDuplicateDetector:
    """Menandai artikel yang mirip dengan artikel lain via `duplicate_of`."""

    def __init__(
        self,
        threshold: float = NEAR_DUP_THRESHOLD,
        max_history: int = MAX_HISTORY,
        review_threshold: float = REVIEW_THRESHOLD,
    ) -> None:
        self.threshold = threshold
        self.max_history = max_history
        self.review_threshold = review_threshold
        #: Pasangan (id_baru, id_asal, skor) yang DIGABUNG.
        self.last_matches: list[tuple[str, str, float]] = []
        #: Pasangan (id_baru, id_asal, skor) yang perlu DIPERIKSA MANUSIA.
        self.last_review: list[tuple[str, str, float]] = []

    # ------------------------------------------------------------------
    def similarity_matrix(self, texts: Sequence[str]):
        """Matriks cosine similarity antar teks. Mengembalikan None bila kosong."""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
        except ImportError:  # pragma: no cover - sklearn ada di requirements
            return None

        if len(texts) < 2:
            return None
        # char_wb: tahan terhadap perbedaan spasi/tanda baca; ngram 3-5
        # menangkap frasa pendek sekaligus variasi kata.
        vectorizer = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(3, 5), min_df=1, sublinear_tf=True
        )
        matrix = vectorizer.fit_transform(list(texts))
        return cosine_similarity(matrix)

    # ------------------------------------------------------------------
    def mark_duplicates(
        self,
        articles: Sequence["Article"],
        history: Optional[dict[str, str]] = None,
    ) -> list["Article"]:
        """Kembalikan daftar artikel dengan `duplicate_of` terisi bila perlu.

        `history` berisi {article_id: teks} artikel lama dari database. Artikel
        baru dibandingkan terhadap riwayat DAN terhadap artikel baru lain yang
        lebih dulu lolos (supaya tiga salinan cerita yang sama menghasilkan
        satu artikel asli + dua duplikat, bukan tiga-duanya saling menunjuk).
        """
        if not articles:
            return list(articles)

        history = history or {}
        hist_items = list(history.items())[: self.max_history]
        hist_ids = [h[0] for h in hist_items]
        hist_texts = [h[1] for h in hist_items]

        new_texts = [_compose(a) for a in articles]

        # Urutkan berdasarkan waktu terbit agar "asli" = yang paling awal.
        order = sorted(
            range(len(articles)),
            key=lambda i: (articles[i].published_at is None, articles[i].published_at),
        )

        # Korpus gabungan: riwayat dulu, lalu artikel baru pada urutan waktu.
        texts = hist_texts + [new_texts[i] for i in order]
        sim = self.similarity_matrix(texts)
        if sim is None:
            return list(articles)

        n_hist = len(hist_texts)
        result = {i: articles[i] for i in range(len(articles))}
        #: indeks korpus yang sudah "dipakai" sebagai artikel asli
        kept_corpus: list[int] = list(range(n_hist))
        self.last_matches = []
        self.last_review = []

        for position, idx in enumerate(order):
            corpus_idx = n_hist + position
            best_score = 0.0
            best_id: Optional[str] = None

            for cand in kept_corpus:
                score = float(sim[corpus_idx, cand])
                if score > best_score:
                    best_score = score
                    best_id = (
                        hist_ids[cand]
                        if cand < n_hist
                        else articles[order[cand - n_hist]].article_id
                    )

            if best_id is not None and best_score >= self.threshold:
                # Salinan: jangan jadikan kandidat pembanding berikutnya.
                result[idx] = articles[idx].model_copy(
                    update={"duplicate_of": best_id}
                )
                self.last_matches.append((articles[idx].article_id, best_id, best_score))
            else:
                if best_id is not None and best_score >= self.review_threshold:
                    # Abu-abu: tidak digabung, tapi dicatat untuk diperiksa.
                    self.last_review.append(
                        (articles[idx].article_id, best_id, best_score)
                    )
                kept_corpus.append(corpus_idx)

        return [result[i] for i in range(len(articles))]
