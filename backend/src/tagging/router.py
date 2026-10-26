"""Router for mapping news text to targets via keywords and macro themes."""

import csv
import re
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import yaml

from backend.src.schema import (
    Article,
    Basis,
    Direction,
    EvidenceSpan,
    NewsHorizon,
    TargetImpact,
)
from model.common.sentiment_config import stance_direction as sentiment_stance_direction

if TYPE_CHECKING:  # pragma: no cover - hanya untuk anotasi tipe
    from backend.src.tagging.model_router import ModelRouter


@lru_cache(maxsize=512)
def _alias_pattern(alias: str) -> re.Pattern[str]:
    """Kompilasi alias menjadi regex word-boundary, case-insensitive.

    Spasi/tanda hubung di dalam frasa dilonggarkan agar "safe haven" juga
    cocok dengan "safe-haven". `(?<!\\w)`/`(?!\\w)` mencegah alias cocok
    sebagai potongan kata lain ("gold" di "Goldman", "spx" di "spxfoo").

    Versi `keywords.py` sengaja tidak diimpor langsung: modul itu milik
    kolektor berita (membawa dependensi konfigurasi feed), sedangkan router
    dipakai juga oleh pipeline tanpa kolektor. Regex-nya identik.
    """
    parts = [re.escape(p) for p in re.split(r"[\s\-]+", alias.strip()) if p]
    body = r"[\s\-]*".join(parts)
    return re.compile(rf"(?<!\w){body}(?!\w)", re.IGNORECASE)


LOCKED_UNIVERSE = {"XAU", "RATE_UST", "SPX"}


class TargetRouter:
    """Tags targets and projects macro impact from text."""

    def __init__(
        self,
        aliases_path: Path | str = Path("data/universe/aliases.csv"),
        impact_graph_path: Path | str = Path("data/impact_graph.yaml"),
    ):
        self.aliases_path = Path(aliases_path)
        self.impact_graph_path = Path(impact_graph_path)
        self.aliases: dict[str, list[str]] = {}  # asset_id -> list of alias strings
        self.impact_graph: dict[str, list[dict]] = {}  # theme -> list of targets
        self._load_configs()

    def _load_configs(self) -> None:
        # P0-2: arah stance -> aset dari `data/sentiment_config.yaml`.
        # Dibaca sekali di sini agar jalur hot (`route_article`) tidak
        # menyentuh disk per artikel.
        self.stance_direction: dict[str, int] = sentiment_stance_direction()

        if self.aliases_path.exists():
            with open(self.aliases_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    asset = row["asset_id"]
                    if asset in LOCKED_UNIVERSE:
                        self.aliases.setdefault(asset, []).append(row["alias"].strip().lower())

        if self.impact_graph_path.exists():
            with open(self.impact_graph_path, mode="r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                self.impact_graph = data.get("themes", {})

        # T-5: ambang & kalibrasi dari YAML, bukan angka ajaib di kode.
        self.config_path = Path("data/router_config.yaml")
        self.routing: dict[str, float] = {
            "direction_threshold": 0.1,
            "explicit_confidence": 0.88,
            "macro_confidence_base": 0.50,
            "macro_confidence_weight_factor": 0.35,
            "macro_confidence_cap": 0.85,
        }
        # S-5: horizon per jenis jalur. Bawaan di sini mencerminkan isi YAML
        # supaya perilaku tidak berubah bila file tidak ada.
        self.horizon_policy: dict[str, Any] = {
            "explicit": "short",
            "macro": "medium",
            "intraday_keywords": [],
        }
        if self.config_path.exists():
            with open(self.config_path, mode="r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            section = data.get("routing") if isinstance(data, dict) else None
            if isinstance(section, dict):
                horizon = section.pop("horizon", None)
                self.routing.update(section)
                if isinstance(horizon, dict):
                    self.horizon_policy.update(horizon)

    def _stance_sign(self, asset_id: str) -> int:
        """Arah aset terhadap stance hawkish (+1/-1).

        Aset yang tidak terdaftar di `stance_direction` dianggap `+1` agar
        perilaku sama seperti sebelumnya (skor dipakai apa adanya) dan aset
        baru tidak diam-diam berbalik arah.
        """
        return self.stance_direction.get(asset_id, 1)

    def _directional_score(self, asset_id: str, sentiment_score: float, is_stance: bool) -> float:
        """Skor dalam ruang arah harga untuk satu aset.

        Mode `price`: skor sudah berupa arah harga, kembalikan apa adanya.
        Mode `stance`: skor adalah stance The Fed; kalikan dengan arah aset
        supaya dovish (stance negatif) menjadi bullish untuk XAU.
        """
        if not is_stance:
            return sentiment_score
        return sentiment_score * self._stance_sign(asset_id)

    def resolve_horizon(self, text: str, basis: Basis) -> NewsHorizon:
        """Horizon berita untuk satu dampak (S-5 / FR-23).

        Sebelumnya `news_horizon` selalu jatuh ke nilai bawaan SHORT karena
        router tidak pernah mengisinya — FR-23 hanya "terisi" secara teknis.

        Aturan, semuanya dari `router_config.yaml`:
        - kata kunci intraday muncul  -> INTRADAY (reda di hari yang sama)
        - jalur eksplisit             -> `horizon.explicit` (bawaan short)
        - jalur makro                 -> `horizon.macro` (bawaan medium)
        """
        lower = text.lower()
        for kw in self.horizon_policy.get("intraday_keywords", []) or []:
            if str(kw).lower() in lower:
                return NewsHorizon.INTRADAY

        key = "explicit" if basis is Basis.EXPLICIT else "macro"
        raw = str(self.horizon_policy.get(key, "short")).lower()
        try:
            return NewsHorizon(raw)
        except ValueError:
            # Konfigurasi salah tidak boleh menjatuhkan pipeline; pakai short
            # dan biarkan nilai mentahnya terlihat di log pemanggil.
            return NewsHorizon.SHORT

    def find_explicit_mentions(self, text: str) -> list[tuple[str, str, int, int]]:
        """
        Finds direct alias matches in text.
        Returns list of (asset_id, matched_alias, start_pos, end_pos).

        Pencocokan memakai word-boundary, bukan `str.find`. Dengan substring
        polos, "gold" ikut cocok di dalam "**Goldman** Sachs" dan "emas" di
        dalam "s**emas**", sehingga berita yang tidak menyebut emas sama sekali
        tetap ditandai XAU sebagai sebutan eksplisit — keyakinan tertinggi.
        Itu mencemari sentimen aset dan tidak bisa dibedakan lagi di hilir.

        Pencocokan bersifat case-insensitive; posisi yang dikembalikan tetap
        merujuk teks asli agar `matched_text` dapat diaudit apa adanya.
        """
        matches: list[tuple[str, str, int, int]] = []

        for asset_id, alias_list in self.aliases.items():
            for alias in alias_list:
                pattern = _alias_pattern(alias)
                found = pattern.search(text)
                if found is not None:
                    matches.append((asset_id, alias, found.start(), found.end()))
                    break  # Found match for this asset
        return matches

    #: Kamus tema makro. Setiap tema sengaja memuat frasa ID **dan** EN:
    #: berita yang masuk campur (RSS Inggris + media Indonesia), dan kamus
    #: yang hanya berisi satu bahasa membuat separuh korpus tak terpetakan.
    #: Versi sebelumnya hanya punya "geopolitik"/"dovish" dsb sehingga
    #: "geopolitical tensions" dan "Fed cuts rates" lolos tanpa tema.
    THEME_KEYWORDS: dict[str, tuple[str, ...]] = {
        "rates_down": (
            # Bentuk dasar + berimbuhan (me-, di-) didaftarkan eksplisit:
            # word-boundary memblokir "memangkas" bila kamus hanya memuat
            # "pangkas". Lebih mudah diaudit daripada menambal regex dengan
            # aturan morfologi.
            "pangkas suku bunga",
            "memangkas suku bunga",
            "dipangkas",
            "pemotongan bunga",
            "penurunan suku bunga",
            "suku bunga turun",
            "turunkan suku bunga",
            "menurunkan suku bunga",
            "dovish",
            "rate cut",
            "rate cuts",
            "cut rates",
            "cuts rates",
            "lower rates",
            "rate reduction",
            "downward pressure on rates",
        ),
        "rates_up": (
            "naikkan suku bunga",
            "menaikkan suku bunga",
            "kenaikan bunga",
            "suku bunga naik",
            "hawkish",
            "rate hike",
            "rate hikes",
            "hike rates",
            "hikes rates",
            "hiked rates",
            "raise rates",
            "raises rates",
            "raised rates",
            "hike interest rates",
            "hiked interest rates",
            "raise interest rates",
            "raised interest rates",
            "higher rates",
            "interest rate hike",
        ),
        "usd_up": (
            "dolar perkasa",
            "dolar menguat",
            "dolar naik",
            "usd menguat",
            "rupiah melemah",
            "strong dollar",
            "dollar surges",
            "dollar strengthens",
            "dollar rallies",
            "dollar rallied",
            "dollar rises",
            "dollar gains",
        ),
        "risk_off": (
            "gejolak pasar",
            "ketidakpastian global",
            "panic selling",
            "flight to safety",
            "pasar panik",
            "aksi jual",
            "selloff",
            "sell-off",
            "risk aversion",
            "risk-off",
            "safe haven buying",
            "flee to safety",
            "investors flee",
        ),
        "geopolitical_tension": (
            "eskalasi perang",
            "geopolitik",
            "konflik timur tengah",
            "sanksi dagang",
            "ketegangan geopolitik",
            "geopolitical tension",
            "geopolitical tensions",
            "geopolitics",
            "middle east conflict",
            "middle east tensions",
            "war escalates",
            "military conflict",
            "sanctions",
        ),
    }

    def detect_themes(self, text: str) -> list[str]:
        """Deteksi tema makro dari kata kunci ID + EN (word-boundary)."""
        return [
            theme
            for theme, keywords in self.THEME_KEYWORDS.items()
            if any(_alias_pattern(kw).search(text) for kw in keywords)
        ]

    def route_article(
        self,
        article: Article,
        sentiment_score: float,
        model_version: str = "fusion-v1",
        model_router: Optional["ModelRouter"] = None,
        score_space: str = "price",
    ) -> list[TargetImpact]:
        """
        Routes an article to target impacts via explicit mentions and macro themes.
        Strict rule: caps confidence by basis and builds evidence for explicit tags.

        Bila `model_router` diberikan, pilihan model spesialis dicatat di
        `routed_from`/`route_score` supaya keputusan routing dapat diaudit.

        `score_space` menyatakan **arti** `sentiment_score`:

        - `"price"` (bawaan): skor sudah menyatakan arah harga aset, sehingga
          arah ditentukan langsung oleh tanda skor. Berlaku untuk FinBERT-EMAS
          yang dilatih pada sentimen harga emas.
        - `"stance"`: skor menyatakan stance The Fed (hawkish positif, dovish
          negatif) dan **bukan** arah harga. Untuk mode ini arah tiap aset
          dihitung lewat `stance_direction` (`data/sentiment_config.yaml`),
          dan `sign` pada `impact_graph.yaml` **tidak** dikalikan lagi —
          mengalikan keduanya membalik arah dua kali (mis. dovish: stance
          negatif x XAU -1 x rates_down +1 = bearish, padahal dovish justru
          bullish emas).
        """
        impacts: list[TargetImpact] = []
        full_text = f"{article.title} {article.body or ''}".strip()
        is_stance = score_space == "stance"

        routed_from: Optional[str] = None
        route_score: Optional[float] = None
        if model_router is not None:
            models, reason, score = model_router.route(full_text, article.source or "")
            routed_from = f"{reason}:{'+'.join(models)}"
            route_score = score

        # 1. Explicit matches
        explicit_matches = self.find_explicit_mentions(full_text)
        tagged_assets = set()

        for asset_id, matched_alias, start, end in explicit_matches:
            tagged_assets.add(asset_id)
            # P0-2: arah mengikuti arti skor. Untuk mode `stance`, skor adalah
            # stance The Fed sehingga harus dipetakan per aset lewat
            # `stance_direction`; memakai skor mentah akan menghasilkan dovish
            # -> bearish XAU, kebalikan dari hubungan ekonomi yang benar.
            effective_score = self._directional_score(asset_id, sentiment_score, is_stance)
            threshold = self.routing["direction_threshold"]
            if effective_score > threshold:
                direction = Direction.BULLISH
            elif effective_score < -threshold:
                direction = Direction.BEARISH
            else:
                direction = Direction.NEUTRAL

            evidence = [
                EvidenceSpan(
                    quote=full_text[max(0, start - 20) : min(len(full_text), end + 40)],
                    start=start,
                    end=end,
                )
            ]

            impacts.append(
                TargetImpact(
                    article_id=article.article_id,
                    asset_id=asset_id,
                    direction=direction,
                    # P0-2: simpan skor yang sudah berarah harga, bukan skor
                    # stance mentah. Kalau tidak, `direction=BULLISH` bisa
                    # berpasangan dengan `score=-0.38` dan konsumen hilir
                    # (persona/alloc) membaca sinyal yang saling bertentangan.
                    score=max(-1.0, min(1.0, effective_score)),
                    confidence=self.routing["explicit_confidence"],
                    basis=Basis.EXPLICIT,
                    themes=[],
                    evidence=evidence,
                    flags=[],
                    news_horizon=self.resolve_horizon(full_text, Basis.EXPLICIT),
                    model_version=model_version,
                    routed_from=routed_from,
                    route_score=route_score,
                )
            )

        # 2. Macro themes mapping via impact_graph
        themes = self.detect_themes(full_text)
        for theme in themes:
            theme_targets = self.impact_graph.get(theme, [])
            for entry in theme_targets:
                macro_asset = entry.get("target")
                if not macro_asset or macro_asset not in LOCKED_UNIVERSE:
                    continue
                if macro_asset in tagged_assets:
                    continue  # Explicit priority

                sign = entry.get("sign", 1)
                weight = entry.get("weight", 0.5)
                if is_stance:
                    # P0-2: mode stance — arah dari pemetaan stance->aset,
                    # BUKAN dari `sign` tema. `sign` tema mengasumsikan
                    # `sentiment_score` sudah berisi arah harga; mengalikannya
                    # dengan stance_direction membalik arah dua kali.
                    # `weight` tetap dipakai untuk besaran/keyakinan.
                    projected_score = sentiment_score * self._stance_sign(macro_asset) * weight
                else:
                    projected_score = sentiment_score * sign * weight

                threshold = self.routing["direction_threshold"]
                if projected_score > threshold:
                    direction = Direction.BULLISH
                elif projected_score < -threshold:
                    direction = Direction.BEARISH
                else:
                    direction = Direction.NEUTRAL

                impacts.append(
                    TargetImpact(
                        article_id=article.article_id,
                        asset_id=macro_asset,
                        direction=direction,
                        score=max(-1.0, min(1.0, projected_score)),
                        confidence=min(
                            self.routing["macro_confidence_cap"],
                            self.routing["macro_confidence_base"]
                            + weight * self.routing["macro_confidence_weight_factor"],
                        ),
                        basis=Basis.MACRO_FACTOR,
                        themes=[theme],
                        causal_path=[theme, f"{macro_asset}_{direction.value}"],
                        evidence=[],
                        flags=[],
                        news_horizon=self.resolve_horizon(full_text, Basis.MACRO_FACTOR),
                        model_version=model_version,
                        routed_from=routed_from,
                        route_score=route_score,
                    )
                )

        return impacts
