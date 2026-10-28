"""Endpoint simulasi: berita/rumor -> skor model -> stance persona.

Alur ini SENGAJA tidak memakai LLM. Setiap angka berasal dari bobot model atau
dari ambang di berkas konfigurasi, sehingga hasilnya dapat diuji ulang dan
dipertanggungjawabkan.

Alur lengkap:
    teks -> sim_input.validate()      (tolak obrolan/pertanyaan)
         -> model.score_article()     (FOMC-RoBERTa / FinBERT)
         -> TargetRouter.route_article()  (arah per aset + confidence)
         -> PersonaEngine.evaluate_all()  (5 stance)
         -> SimResult

Paragraf penjelas disusun dari templat yang hanya memakai angka di atas.
Kalimat tidak pernah menambahkan fakta yang tidak ada di data.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from backend.src.serve.sim_input import (
    InputKind,
    InputRejected,
    ValidatedInput,
    confidence_penalty,
    validate,
)
from backend.src.tagging.router import LOCKED_UNIVERSE

logger = logging.getLogger(__name__)

#: Batas keyakinan minimum supaya hasil tidak dilebih-lebihkan. Rumor yang
#: sudah diturunkan 0.60 lalu ditimpa batas ini akan tampil apa adanya.
MIN_CONFIDENCE_WARNING = 0.35


@dataclass
class SimStance:
    persona_id: str
    persona_name: str
    stance: str
    strength: float
    rationale: str


@dataclass
class SimResult:
    """Hasil lengkap satu analisis, siap dirender GUI."""

    input_kind: str
    is_rumor: bool
    source: Optional[str]
    text: str
    target: str
    tone: str
    score: float
    confidence: float
    confidence_raw: float
    """Sebelum penalti rumor. Ditampilkan agar penurunan bisa diaudit."""
    penalty: float
    horizon: str
    direction: str
    model_version: str
    stances: list[SimStance] = field(default_factory=list)
    summary: str = ""
    warnings: list[str] = field(default_factory=list)
    degraded: list[str] = field(default_factory=list)
    """Model yang gagal dimuat, beserta alasannya. Kosong = semua normal."""
    disclaimer: str = "Simulasi sudut pandang. Bukan nasihat investasi."


def _nama_persona() -> dict[str, str]:
    """Nama tampilan persona dari berkas konfigurasi, bukan hardcode di GUI."""
    import yaml

    hasil: dict[str, str] = {}
    for kandidat in ("data/personas.yaml", "config/personas.yaml"):
        p = Path(kandidat)
        if not p.exists():
            continue
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except Exception:  # pragma: no cover - konfigurasi rusak
            continue
        for pid, cfg in (data.get("personas") or data).items():
            if isinstance(cfg, dict):
                hasil[str(pid)] = str(cfg.get("name") or pid)
    return hasil


def _susun_ringkasan(
    v: ValidatedInput,
    target: str,
    tone: str,
    arah_target: str,
    score: float,
    confidence: float,
    penalti: float,
    stances: list[SimStance],
) -> str:
    """Paragraf penjelas yang hanya memakai angka dari hasil perhitungan.

    Tidak ada LLM di sini: kalimat disusun dari templat supaya tidak mungkin
    memunculkan fakta atau angka yang tidak ada di data.
    """
    arah = {"positive": "naik", "negative": "turun", "neutral": "netral"}.get(tone, tone)
    jumlah_beli = sum(1 for s in stances if s.stance == "buy")
    jumlah_jual = sum(1 for s in stances if s.stance == "sell")
    jumlah_tahan = sum(1 for s in stances if s.stance == "hold")

    bagian = [
        f"Teks ini terbaca sebagai {'rumor' if v.is_rumor else 'berita'} dan "
        f"menghasilkan arah {arah_target} untuk {target} dengan skor {score:+.2f} "
        f"dan keyakinan {confidence:.2f}."
    ]

    if penalti < 1.0:
        bagian.append(
            f"Keyakinan sudah diturunkan dari {confidence / penalti:.2f} menjadi "
            f"{confidence:.2f} karena input berupa rumor"
            + (" (sumber tidak dicantumkan)." if not v.source else ".")
        )

    bagian.append(
        f"Dari lima persona, {jumlah_beli} memilih beli, {jumlah_jual} memilih "
        f"jual, dan {jumlah_tahan} memilih tahan."
    )

    if jumlah_tahan and jumlah_beli:
        tahan = [s for s in stances if s.stance == "hold"]
        bagian.append(
            "Yang menahan diri: "
            + "; ".join(f"{s.persona_name} ({s.rationale.rstrip('.')})" for s in tahan)
            + "."
        )

    return " ".join(bagian)


def _conf_label(conf: float) -> str:
    if conf < MIN_CONFIDENCE_WARNING:
        return "keyakinan rendah"
    if conf < 0.6:
        return "keyakinan sedang"
    return "keyakinan tinggi"


class SimulationService:
    """Pemegang model. Dimuat sekali, dipakai berkali-kali."""

    def __init__(
        self,
        db_path: Path | str = "data/finews.db",
        model_path: str = "model/fomc/weights/roberta",
        xau_model_path: str = "model/xau/weights/finbert_gold",
    ) -> None:
        self.db_path = Path(db_path)
        self.model_path = model_path
        self.xau_model_path = xau_model_path
        self._model = None
        self._router = None
        self._cache: dict[str, Any] = {}
        self._model_router = None
        self._degraded: list[str] = []  # catatan warm-up, bukan per-request
        # P1-9: status kesiapan model. `None` = belum dicoba, True = siap,
        # False = pemuatan gagal. Dipakai endpoint untuk menjawab 503 alih-alih
        # menggantung 3,33 detik pada request pertama.
        self._siap: bool | None = None
        self._alasan_belum_siap: str | None = None

    # -- kesiapan model (P1-9) ------------------------------------------
    @property
    def siap(self) -> bool | None:
        """True/False bila sudah dicoba dimuat, None bila belum."""
        return self._siap

    @property
    def alasan_belum_siap(self) -> str | None:
        return self._alasan_belum_siap

    def warm_up(self) -> bool:
        """Muat model yang tersedia tanpa memproses teks apa pun.

        Dipanggil dari lifespan supaya request pertama tidak menanggung
        pemuatan bobot: FinBERT-EMAS (440 MB) dan FOMC-RoBERTa (1,42 GB/berkas).
        Ukuran berbeda jauh, jadi jangan disamakan -- '440 MB' hanya benar
        untuk FinBERT-EMAS. Konkurensi aman: `_cache` diisi sebelum
        `_siap` disetel, dan pemanggil yang datang bersamaan tetap mendapat
        jalur lambat yang benar (memuat sendiri) bila belum siap.

        Tidak pernah melempar: kegagalan dicatat sebagai `_siap=False` sehingga
        API bisa menjawab 503 dengan alasan yang jelas, bukan 500.
        """
        from backend.src.tagging.model_router import ModelRouter

        try:
            if self._model_router is None:
                self._model_router = ModelRouter()
            dimuat: list[str] = []
            gagal: list[str] = []
            for nama, pemuat, _space in self.PRIORITAS:
                if self._cache.get(nama) is not None:
                    dimuat.append(nama)
                    continue
                try:
                    model = getattr(self, pemuat)()
                except Exception as exc:
                    gagal.append(f"{nama}: {type(exc).__name__}: {exc}")
                    continue
                if model is None:
                    gagal.append(f"{nama}: bobot tidak ditemukan")
                    continue
                self._cache[nama] = model
                dimuat.append(nama)
            if not dimuat:
                self._siap = False
                self._alasan_belum_siap = (
                    "tidak ada model yang bisa dimuat: " + "; ".join(gagal)
                )
                logger.warning("Warm-up model gagal: %s", self._alasan_belum_siap)
                return False
            self._siap = True
            self._degraded = gagal
            logger.info("Warm-up model selesai; siap: %s", ", ".join(dimuat))
            return True
        except Exception as exc:  # pragma: no cover - router rusak
            self._siap = False
            self._alasan_belum_siap = f"{type(exc).__name__}: {exc}"
            logger.warning("Warm-up model gagal: %s", exc)
            return False

    #: Urutan prioritas sama dengan pipeline (MODEL_PRIORITY di runner.py).
    #: Kolom: (nama router, method pemuat, score_space).
    PRIORITAS = (
        ("fomc_roberta", "_muat_fomc", "stance"),
        ("finbert_emas", "_muat_xau", "price"),
    )

    def _pilih_model(self, text: str):
        """Pilih model untuk SATU teks lewat ModelRouter, lalu muat.

        Memilih satu model untuk semua input adalah kesalahan: FOMC-RoBERTa
        dilatih pada bahasa Fed, jadi skornya berarti hawkish/dovish (skor
        positif = hawkish = emas TURUN). FinBERT-EMAS dilatih pada harga emas,
        jadi skor positif = emas NAIK. Memakai satu model untuk keduanya
        membuat arah terbalik.

        Mengembalikan (model, score_space, catatan_degradasi).
        """
        from backend.src.tagging.model_router import ModelRouter

        if self._model_router is None:
            self._model_router = ModelRouter()
        ditunjuk, alasan, _ = self._model_router.route(text)
        catatan: list[str] = []

        for nama, pemuat, space in self.PRIORITAS:
            if nama not in ditunjuk:
                continue
            cached = self._cache.get(nama)
            if cached is not None:
                return cached, space, catatan
            try:
                model = getattr(self, pemuat)()
            except Exception as exc:
                catatan.append(f"{nama}: {type(exc).__name__}: {exc}")
                logger.warning("Model %s gagal dimuat: %s", nama, exc)
                continue
            if model is None:
                catatan.append(f"{nama}: bobot tidak ditemukan")
                continue
            self._cache[nama] = model
            return model, space, catatan

        # Tidak ada model yang ditunjuk router DAN tersedia: pakai apa pun yang
        # bisa dimuat, tetapi laporkan penyimpangannya.
        for nama, pemuat, space in self.PRIORITAS:
            if nama in self._cache:
                return self._cache[nama], space, catatan
            try:
                model = getattr(self, pemuat)()
            except Exception as exc:
                catatan.append(f"{nama}: {type(exc).__name__}: {exc}")
                continue
            if model is not None:
                self._cache[nama] = model
                catatan.append(
                    f"Router menunjuk {ditunjuk or 'tanpa model'}; memakai {nama} "
                    "sebagai cadangan."
                )
                return model, space, catatan

        raise InputRejected(
            "Tidak ada bobot model yang dapat dimuat, jadi analisis tidak bisa "
            "dijalankan. Rincian: " + "; ".join(catatan),
            code="model_tidak_ada",
        )

    def _muat_fomc(self):
        from model.fomc.src.model import FOMCRoBERTaSentiment

        path = Path(self.model_path)
        if not (path / "config.json").exists():
            return None
        model = FOMCRoBERTaSentiment(checkpoint=str(path))
        model.predict_probs(["uji muat"])  # paksa pemuatan bobot sekarang
        return model

    def _muat_xau(self):
        from model.xau.src.model import FinbertGoldSentiment

        path = Path(self.xau_model_path)
        if not (path / "config.json").exists():
            return None
        model = FinbertGoldSentiment(checkpoint_dir=str(path))
        model.predict_probs(["uji muat"])
        return model

    def _ensure_router(self):
        if self._router is not None:
            return self._router
        from backend.src.tagging.router import TargetRouter

        # Path bawaan router, jangan dikarang: alias ada di
        # data/universe/aliases.csv, bukan data/target_aliases.yaml.
        self._router = TargetRouter()
        return self._router

    def analyze(
        self,
        text: str,
        kind: str | InputKind,
        source: Optional[str] = None,
        target: str = "XAU",
    ) -> SimResult:
        # 0. Target harus salah satu aset terkunci.
        #
        # Tanpa ini, target yang tidak dikenal (mis. "GOLD", nama yang wajar
        # bagi pengguna) lolos sampai ke routing, tidak cocok dengan apa pun,
        # lalu keluar sebagai direction="netral" TANPA peringatan. Pengguna
        # membaca "netral" sebagai hasil analisis, padahal artinya targetnya
        # tidak dikenali. Itu kegagalan yang menyamar sebagai jawaban.
        #
        # Normalisasi huruf besar/kecil dipertahankan: "xau" tetap diterima,
        # dan yang dikembalikan adalah ejaan resmi supaya klien tidak perlu
        # menormalkan sendiri.
        target_resmi = (target or "").strip().upper()
        if target_resmi not in LOCKED_UNIVERSE:
            raise InputRejected(
                f"Target {target!r} tidak dikenal. Pilih salah satu: "
                + ", ".join(sorted(LOCKED_UNIVERSE))
                + ".",
                code="target_tidak_dikenal",
                contoh=sorted(LOCKED_UNIVERSE),
            )

        # 1. Gerbang: hanya berita/rumor.
        v = validate(text, kind, source)

        # 2. Pilih model untuk teks INI, lalu skor.
        model, score_space, catatan = self._pilih_model(v.text)
        # Jalur lambat berhasil: model sudah termuat, jadi permintaan berikutnya
        # tidak perlu ditolak 503 lagi.
        self._siap = True
        self._alasan_belum_siap = None
        # P2-8: `_degraded`/`_score_space` dulu disimpan di instance lalu dibaca
        # di akhir fungsi yang sama. `SimulationService` adalah objek BERSAMA
        # antar request, dan rute `def` sinkron dijalankan FastAPI di threadpool
        # -> dua request bisa saling menimpa nilai ini di tengah jalan: arah
        # dihitung dengan score_space milik request lain, atau peringatan
        # degradasi milik request lain ikut terkirim. Variabel lokal menghapus
        # seluruh kelas bug itu.
        degraded = list(catatan or [])
        sentiment = model.score_article("input-pengguna", v.text)

        skor = float(sentiment.score)
        tone = sentiment.tone.value if hasattr(sentiment.tone, "value") else str(sentiment.tone)
        # Keyakinan = jarak dari netral, dipetakan ke 0..1.
        confidence_raw = min(1.0, abs(skor))

        # 3. Penalti rumor (angka tetap, bisa diuji).
        penalti = confidence_penalty(v)
        # confidence_raw dibiarkan penuh: membulatkannya lebih dulu membuat
        # confidence != confidence_raw * penalti dan audit jadi tidak telusur.
        confidence = round(confidence_raw * penalti, 4)

        # 4. Arah untuk target lewat router yang sudah dipakai pipeline.
        arah = "netral"
        conf_router: Optional[float] = None
        # P2-9: bedakan "netral karena analisis" dari "netral karena routing
        # gagal". Sebelumnya keduanya menghasilkan direction="netral" yang
        # identik, sehingga kegagalan teknis terbaca sebagai kesimpulan pasar.
        routing_gagal: Optional[str] = None
        try:
            from datetime import datetime, timezone

            from backend.src.schema import Article, Lang

            router = self._ensure_router()
            artikel = Article(
                article_id="input-pengguna",
                source=v.source or "input-pengguna",
                title=v.text,
                body="",
                language=Lang.EN,
                fetched_at=datetime.now(timezone.utc),
            )
            impacts = router.route_article(
                artikel, skor,
                model_version=model.model_version,
                score_space=score_space,
            )
            for imp in impacts:
                # Nama field-nya `asset_id` (TargetImpact), bukan `target`.
                if str(getattr(imp, "asset_id", "")).upper() == target_resmi:
                    arah = getattr(imp.direction, "value", str(imp.direction))
                    conf_router = float(imp.confidence)
                    break
            else:
                # Router tidak menghasilkan dampak karena teks tidak menyebut
                # aset mana pun ("The Fed may cut rates"). Untuk mode `stance`,
                # arah masih bisa ditentukan dari `stance_direction` di
                # sentiment_config.yaml -- sumber yang sama, bukan tebakan.
                if score_space == "stance":
                    arah = router.direction_for_target(
                        target_resmi, skor, score_space="stance"
                    )
        except Exception as exc:  # pragma: no cover - routing opsional
            logger.warning("Routing target gagal: %s", exc)
            routing_gagal = f"{type(exc).__name__}: {exc}"

        # 5. Stance persona.
        stances = self._stances(v.text, skor, confidence, target_resmi)

        peringatan: list[str] = []
        if v.is_rumor:
            peringatan.append(
                "Input ditandai sebagai RUMOR. Keyakinan diturunkan "
                f"x{penalti:.2f} dan hasilnya bukan konfirmasi."
            )
        if v.is_rumor and not v.source:
            peringatan.append(
                "Rumor tanpa sumber — tidak dapat diverifikasi."
            )
        if routing_gagal:
            peringatan.append(
                "Arah TIDAK dapat ditentukan karena routing gagal "
                f"({routing_gagal}). Nilai arah \"netral\" di sini berarti "
                "\"tidak diketahui\", bukan kesimpulan pasar."
            )
        if degraded:
            peringatan.append(
                "Model prioritas gagal dimuat: "
                + "; ".join(degraded)
                + f". Analisis memakai {model.model_name}."
            )
        if confidence < MIN_CONFIDENCE_WARNING:
            peringatan.append(
                f"Keyakinan {confidence:.2f} di bawah ambang {MIN_CONFIDENCE_WARNING}; "
                "anggap sinyal ini lemah."
            )

        return SimResult(
            input_kind=v.kind.value,
            is_rumor=v.is_rumor,
            source=v.source,
            text=v.text,
            target=target_resmi,
            tone=tone,
            score=round(skor, 4),
            confidence=confidence,
            confidence_raw=confidence_raw,
            penalty=penalti,
            horizon="pendek",
            direction=arah,
            model_version=model.model_version,
            stances=stances,
            summary=_susun_ringkasan(v, target_resmi, tone, arah, skor, confidence, penalti, stances),
            warnings=peringatan,
            degraded=degraded,
        )

    def _stances(self, text: str, score: float, confidence: float, target: str) -> list[SimStance]:
        """Evaluasi lima persona memakai engine yang sudah ada."""
        from backend.src.persona.engine import PersonaEngine

        nama = _nama_persona()
        try:
            engine = PersonaEngine()
            views = engine.evaluate_all(
                article_id="input-pengguna",
                target=target,
                score=score,
                confidence=confidence,
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("Persona engine gagal: %s", exc)
            return []

        hasil = []
        for view in views:
            stance = view.stance.value if hasattr(view.stance, "value") else str(view.stance)
            hasil.append(
                SimStance(
                    persona_id=view.persona_id,
                    persona_name=nama.get(view.persona_id, view.persona_id),
                    stance=stance,
                    strength=float(view.strength),
                    rationale=str(view.rationale),
                )
            )
        return hasil
