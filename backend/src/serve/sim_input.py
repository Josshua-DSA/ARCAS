"""Gerbang input Simulations: hanya berita atau rumor yang boleh dianalisis.

Halaman Simulations menerima teks bebas, dan teks bebas itu berbahaya: kalau
sistem menjawab apa pun, ia akan menjawab "halo" dengan angka pula. Modul ini
menolak lebih awal supaya apa pun yang lolos ke model dijamin berbentuk
laporan peristiwa, bukan pertanyaan atau obrolan.

Dua hal yang SENGAJA tidak dilakukan di sini:

1. Tidak menebak jenis input. Pengguna memilih sendiri Berita/Rumor; modul ini
   hanya memeriksa apakah teksnya pantas untuk jenis yang dipilih.
2. Tidak memakai LLM. Aturannya deterministik supaya hasilnya bisa diuji dan
   tidak berubah-ubah antar pemanggilan.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class InputKind(str, Enum):
    """Jenis input yang dipilih pengguna."""

    NEWS = "berita"
    RUMOR = "rumor"


#: Batas panjang. Terlalu pendek = bukan laporan; terlalu panjang = bukan
#: berita melainkan dokumen, dan model hanya membaca 512 token pertama.
#:
#: P3-2: ambang bawah dulu 40 karakter dan menolak judul finansial yang sah --
#: diukur pada dataset/, judul terpendek adalah "Federal Reserve issues FOMC
#: statement" (37 karakter, pernyataan FOMC asli). 40 juga tidak menjaga apa
#: pun: sapaan dan pertanyaan sudah ditolak aturan 1 dan 2, jadi ambang ini
#: hanya perlu memisahkan "frasa" dari "judul". 20 karakter menerima seluruh
#: judul pendek yang terukur (terpendek 21: "Gold hits record high") sambil
#: tetap menolak "Gold up" (7) dan "Fed statement" (13).
MIN_CHARS = 20
MAX_CHARS = 4000

#: Sapaan / obrolan. Hanya dipakai bila SELURUH teks terdiri dari kata-kata ini.
_SMALL_TALK_WORDS = frozenset({
    "halo", "hallo", "hello", "hi", "hai", "pagi", "siang", "sore", "malam",
    "terima", "kasih", "makasih", "thanks", "thank", "you", "oke", "ok", "sip",
    "tes", "test", "coba", "assalam", "salam", "kabar", "apa", "kamu", "anda",
    "p", "ya", "iya", "tidak", "nggak", "gak", "dong", "nih", "sih", "deh",
})

#: Kata kerja pelaporan / peristiwa. Satu saja cukup sebagai bukti bahwa teks
#: melaporkan sesuatu, bukan menanyakan sesuatu.
_REPORTING_CUES = (
    # Inggris: pelaporan
    "said", "says", "reported", "reports", "announced", "announces",
    "according to", "sources", "people familiar", "reportedly", "allegedly",
    "stated", "disclosed", "revealed", "confirmed", "denied",
    # Inggris: pergerakan pasar (istilah yang benar-benar dipakai judul berita)
    "rise", "rises", "rose", "rising", "fall", "falls", "fell", "falling",
    "gain", "gains", "gained", "drop", "drops", "dropped", "slide", "slides",
    "slid", "slip", "slips", "slipped", "climb", "climbs", "climbed",
    "surge", "surges", "surged", "jump", "jumps", "jumped", "soar", "soars",
    "plunge", "plunges", "plunged", "tumble", "tumbles", "tumbled",
    "retreat", "retreats", "retreated", "rebound", "rebounds", "rebounded",
    "steady", "steadies", "steadied", "edge", "edges", "edged",
    "drop", "sink", "sinks", "sank", "weaken", "weakens", "weakened",
    "strengthen", "strengthens", "strengthened", "pressure", "pressures",
    # Inggris: aksi korporasi / kebijakan
    "expects", "expected", "signals", "signalled", "signaled", "warns",
    "warned", "hike", "hikes", "cut", "cuts", "holds", "held", "plans",
    "planning", "agreed", "approved", "launched", "unveiled", "estimates",
    "forecasts", "beats", "misses", "issues", "releases", "requests",
    "finalizes", "extends", "turns away", "imposes", "sanctions", "bets",
    "betting", "watching", "weighs", "outweigh", "rout", "rallies", "rally",
    "sell-off", "selloff", "bounce", "bounces", "bounced", "tumbles",
    # Indonesia
    "kata", "ujar", "menurut", "melaporkan", "dilaporkan", "mengumumkan",
    "memperkirakan", "memprediksi", "sinyal", "memperingatkan", "naik",
    "turun", "menguat", "melemah", "melonjak", "anjlok", "stabil",
    "menahan", "memangkas", "berencana", "sepakat", "menyetujui",
    "merilis", "mencatat", "diperkirakan", "kabarnya", "isunya",
    "dikabarkan", "beredar", "menurut sumber",
)

#: Kata yang menandakan judul/berita, bukan pertanyaan. Judul berita sering
#: berupa frasa nominal tanpa kata kerja. Kehadiran satuan uang/angka/ticker,
#: atau kosakata pasar, sudah cukup memberi bukti bahwa ini laporan pasar.
_MARKET_MARKERS = re.compile(
    r"(\$|\bUSD\b|\bEUR\b|\bbps\b|\bpt\b|%|\bbasis points?\b|"
    r"\bQ[1-4]\b|\b20\d{2}\b|\b\d+[.,]\d+\b)"
)

#: Kosakata pasar. Bila sebuah kalimat memuat ini, hampir pasti ia berita
#: keuangan dan bukan obrolan -- sekalipun tanpa kata kerja pelaporan.
_MARKET_WORDS = (
    "stock", "stocks", "equit", "market", "markets", "trade", "trades",
    "trading", "earnings", "revenue", "profit", "investor", "investors",
    "wall street", "nasdaq", "s&p", "dow", "index", "indices", "yield",
    "yields", "bond", "bonds", "treasury", "central bank", "fed", "fomc",
    "ecb", "boj", "rate", "rates", "inflation", "gold", "silver", "oil",
    "crude", "dollar", "euro", "yen", "currency", "commodit", "bullion",
    "futures", "option", "options", "hedge", "portfolio", "valuation",
    "ipo", "merger", "acquisition", "guidance", "outlook", "forecast",
    "ekonomi", "pasar", "saham", "obligasi", "inflasi", "suku bunga",
    "komoditas", "investor", "bank sentral", "rupiah", "emas",
)

#: Penanda rumor. Hanya dipakai untuk memberi peringatan, bukan menolak --
#: pengguna sudah memilih jenisnya sendiri.
_RUMOR_CUES = (
    "rumor", "rumour", "kabar", "kabarnya", "isunya", "dikabarkan",
    "beredar", "katanya", "konon", "sumber", "unconfirmed", "belum pasti",
    "dengar-dengar", "sepertinya", "diduga", "spekulasi", "spekulatif",
    "menurut sumber", "people familiar", "reportedly", "allegedly",
)

#: Kata yang menandakan teks murni pertanyaan tanpa isi peristiwa.
_NUMERIC = re.compile(r"\d")


class InputRejected(ValueError):
    """Input bukan berita/rumor. Pesannya siap ditampilkan ke pengguna."""

    def __init__(self, message: str, *, code: str, contoh: list[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.contoh = contoh or [
            "IMF expects at least one more 25 bps ECB rate hike in 2026",
            "Gold steadies as dollar retreats from two-week high",
            "Fed officials signal patience on further easing",
        ]


@dataclass(frozen=True)
class ValidatedInput:
    """Hasil validasi yang sudah bersih dan siap diproses."""

    text: str
    kind: InputKind
    source: str | None
    is_rumor: bool
    """True bila jenisnya rumor ATAU teksnya mengandung penanda rumor."""
    had_rumor_cues: bool
    """True bila penanda rumor ditemukan (dipakai untuk menurunkan keyakinan)."""


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _looks_like_question(lowered: str, original: str) -> bool:
    """True bila teks ditujukan SEBAGAI pertanyaan kepada sistem.

    Judul berita kadang berbentuk tanya ("Gold Under Pressure: Is a Trend
    Reversal Near?"). Itu tetap berita, bukan permintaan jawaban. Bedanya:
    judul yang ditanya-kan tidak memakai kata sapa kepada lawan bicara
    ("menurutmu", "apakah Anda", "should I"), dan biasanya lebih panjang
    serta memuat penanda pasar.
    """
    # Ajakan bertanya kepada sistem: selalu ditolak.
    for sapaan in ("menurutmu", "menurut anda", "pendapatmu", "saranmu",
                   "should i", "what do you think", "do you think",
                   "bisakah anda", "boleh minta"):
        if sapaan in lowered:
            return True

    ada_tanda_tanya = "?" in original or "？" in original
    if not ada_tanda_tanya:
        # Tanpa tanda tanya, hanya kata tanya di awal kalimat yang menandakan
        # pertanyaan langsung.
        awal = lowered.strip()
        for pembuka in ("apakah ", "bagaimana ", "gimana ", "kenapa ", "mengapa ",
                        "kapan ", "berapa ", "siapa ", "bisakah ", "bolehkah "):
            if awal.startswith(pembuka):
                return True
        return False

    # Judul berita bertanya hampir selalu berkolon ("Topik: Pertanyaan?").
    # Pengguna tidak mengetik kolon sebelum bertanya.
    if ":" in original.split("?")[0]:
        return False

    # Bila setelah "?" masih ada kalimat panjang, ini artikel yang judulnya
    # bertanya, bukan pertanyaan kepada sistem.
    sesudah = original.rsplit("?", 1)[-1].strip()
    if len(sesudah) > 40:
        return False

    # Ada "?" di TENGAH yang diikuti lanjutan kalimat: itu gaya penulisan
    # artikel ("Obsessed with X? You're missing out..."), bukan pertanyaan.
    if sesudah and len(original.split()) > 8:
        return False

    # Pertanyaan pendek/utuh: hampir pasti ditujukan kepada sistem.
    if len(original.split()) <= 12:
        return True

    # Panjang, tanpa kolon, tanpa lanjutan: anggap pertanyaan pengguna.
    return True


def _is_small_talk(lowered: str) -> bool:
    """True hanya bila teks NYARIS SELURUHNYA kata sapaan/obrolan.

    Versi pertama fungsi ini membuang kata kecil lalu memeriksa sisanya, sehingga
    "Emas naik." (sisa "emasnaik" = 9 huruf) ikut terbuang sebagai obrolan.
    Sekarang: setiap kata harus cocok dengan daftar kecil, dan teks pendek.
    """
    kata = re.findall(r"[a-z]+", lowered)
    if not kata:
        return False
    if len(kata) > 5:
        # Kalimat panjang bukan sapaan, sekalipun ada kata "halo" di dalamnya.
        return False
    return all(k in _SMALL_TALK_WORDS for k in kata)



def _has_phrase(lowered: str, phrases) -> bool:
    """Cocokkan frasa pada batas kata, bukan substring.

    Pencocokan substring pernah membuat "p**rose**s" dianggap kata "rose" dan
    "g**old**en" dianggap "gold", sehingga teks sampah lolos sebagai berita.
    """
    for p in phrases:
        if " " in p:
            if p in lowered:
                return True
        elif re.search(r"\b" + re.escape(p) + r"\b", lowered):
            return True
    return False


def _has_reporting_cue(lowered: str, original: str) -> bool:
    """True bila teks terbaca sebagai laporan peristiwa.

    Tiga jalur, cukup salah satu:
    1. ada kata kerja pelaporan/pergerakan pasar ("rose", "said", "memangkas");
    2. ada penanda pasar berupa angka/uang/persentase ("$4,120", "25 bps", "Q3");
    3. bentuknya frasa nominal panjang tanpa kata tanya (judul berita seperti
       "Morning Bid: Elections, central banks and earnings on the menu").
    """
    if _has_phrase(lowered, _REPORTING_CUES):
        return True
    if _MARKET_MARKERS.search(original):
        return True
    if _has_phrase(lowered, _MARKET_WORDS):
        return True
    # Frasa nominal: >=6 kata, ada huruf besar di tengah (judul), tanpa "?".
    kata = lowered.split()
    if len(kata) >= 6 and "?" not in original:
        kapital_tengah = sum(1 for w in original.split()[1:] if w[:1].isupper())
        if kapital_tengah >= 1:
            return True
    return False


def _has_rumor_cues(lowered: str) -> bool:
    return any(cue in lowered for cue in _RUMOR_CUES)


def validate(text: str, kind: InputKind | str, source: str | None = None) -> ValidatedInput:
    """Validasi input. Melempar `InputRejected` bila bukan berita/rumor.

    Aturannya sengaja ketat dan sederhana: lebih baik menolak berita sah yang
    formatnya tidak biasa daripada menjawab "halo" dengan angka.
    """
    if isinstance(kind, str):
        try:
            kind = InputKind(kind)
        except ValueError as exc:
            raise InputRejected(
                "Jenis input harus 'berita' atau 'rumor'.",
                code="jenis_tidak_dikenal",
            ) from exc

    bersih = _normalize(text)
    lowered = bersih.lower()

    # 0. Kosong
    if not bersih:
        raise InputRejected(
            "Teks masih kosong. Tempel judul atau paragraf berita.",
            code="kosong",
        )

    # 1. Obrolan -- dicek sebelum panjang, supaya "halo" tidak dijawab dengan
    #    "terlalu pendek" yang menyesatkan.
    if _is_small_talk(lowered):
        raise InputRejected(
            "Itu sapaan atau obrolan, bukan berita. Halaman ini hanya menganalisis "
            "berita atau rumor.",
            code="obrolan",
        )

    # 2. Pertanyaan -- juga sebelum panjang. "Besok emas naik nggak?" harus
    #    ditolak sebagai pertanyaan, bukan disuruh dipanjangkan dulu.
    #    Dicek SEBELUM penanda pelaporan, karena "menurutmu harga emas akan
    #    naik?" memuat kata "naik" tetapi tetap pertanyaan.
    if _looks_like_question(lowered, bersih):
        raise InputRejected(
            "Itu pertanyaan, bukan berita. Halaman ini tidak menjawab pertanyaan; "
            "ia menganalisis teks berita atau rumor yang Anda tempel.",
            code="pertanyaan",
        )

    # 3. Panjang
    if len(bersih) < MIN_CHARS:
        raise InputRejected(
            f"Teks terlalu pendek ({len(bersih)} karakter, minimal {MIN_CHARS}). "
            "Tempel judul atau paragraf berita yang utuh.",
            code="terlalu_pendek",
        )
    if len(bersih) > MAX_CHARS:
        raise InputRejected(
            f"Teks terlalu panjang ({len(bersih)} karakter, maksimal {MAX_CHARS}). "
            "Tempel satu berita saja, bukan seluruh dokumen.",
            code="terlalu_panjang",
        )

    # 4. Harus ada penanda pelaporan/peristiwa
    if not _has_reporting_cue(lowered, bersih):
        raise InputRejected(
            "Teks ini tidak terbaca sebagai laporan peristiwa. Berita biasanya "
            "memuat kata seperti 'said', 'expects', 'naik', 'turun', atau 'menurut'.",
            code="bukan_laporan",
        )

    return ValidatedInput(
        text=bersih,
        kind=kind,
        source=(source or "").strip() or None,
        is_rumor=kind is InputKind.RUMOR,
        had_rumor_cues=_has_rumor_cues(lowered),
    )


def confidence_penalty(v: ValidatedInput) -> float:
    """Faktor pengali keyakinan untuk rumor.

    Rumor yang jelas ditandai sebagai rumor diturunkan lebih dalam daripada
    berita biasa. Angkanya tetap, bukan hasil tebakan, supaya bisa diuji.
    """
    if v.is_rumor:
        return 0.60
    if v.had_rumor_cues:
        # Berita yang teksnya sendiri memuat penanda rumor ("reportedly",
        # "menurut sumber") tetap diturunkan, tapi tidak sedalam rumor penuh.
        return 0.85
    return 1.0
