/* ARCAS API layer (Upgrade.md 3): deteksi base URL, fetch, dan penyedia data
   ilustrasi berlabel. Tanpa build, tanpa CDN: file script biasa. */
window.ARCAS = window.ARCAS || {};
(function (A) {
  "use strict";

  /* Basis API: coba path relatif dulu (deploy), lalu localhost (dev). Alasan:
     satu halaman jalan di dua konteks tanpa konfigurasi. */
  var basePromise = null;
  function detectBase() {
    /* apiReachable dipakai sebagai penanda hasil deteksi, bukan apiBase: ""
       berarti "path relatif jalan" sekaligus nilai fallback saat gagal. */
    if (A.state.apiReachable !== null) return Promise.resolve(A.state.apiBase);
    if (basePromise) return basePromise;
    var candidates = ["", "http://localhost:8000", "http://127.0.0.1:8000"];
    var chain = Promise.reject();
    candidates.forEach(function (base) {
      chain = chain.catch(function () {
        return fetch(base + "/health", { cache: "no-store" }).then(function (r) {
          if (!r.ok) throw new Error("bad");
          return r.json();
        }).then(function () { A.state.apiBase = base; A.state.apiReachable = true; return base; });
      });
    });
    basePromise = chain.catch(function () { A.state.apiBase = ""; A.state.apiReachable = false; return ""; });
    return basePromise;
  }
  /* Lupakan hasil deteksi supaya panggilan berikutnya memeriksa ulang.
     Tanpa ini, sekali API mati saat halaman dibuka (mis. backend belum siap),
     apiReachable=false terkunci selamanya: halaman terus menampilkan ilustrasi
     sampai di-reload manual, termasuk setelah backend hidup kembali. */
  function resetBase() {
    A.state.apiReachable = null;
    A.state.apiBase = "";
    basePromise = null;
  }
  A.resetBase = resetBase;

  /* Tanggal lokal YYYY-MM-DD. toISOString() memakai UTC, sehingga pengguna
     WIB (UTC+7) sebelum 07.00 melihat "hari ini" versi UTC = kemarin dan
     rentang bergeser satu hari. */
  function localISO(d) {
    var m = d.getMonth() + 1, day = d.getDate();
    return d.getFullYear() + "-" + (m < 10 ? "0" : "") + m + "-" + (day < 10 ? "0" : "") + day;
  }
  A.localISO = localISO;

  function api(path) {
    return detectBase().then(function (base) {
      return fetch(base + path, { cache: "no-store" }).then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status + " untuk " + path);
        return r.json();
      });
    });
  }
  A.detectBase = detectBase;
  A.api = api;

  /* Penyedia data ilustrasi jujur: hanya dipakai saat API mati, selalu berlabel.
     Alasan: R-38, tampilan tidak pernah mengarang angka lalu menyamarkannya. */
  A.demoSeries = function (target, days) {
    var out = { sentiments: [], prices: [] };
    var today = new Date();
    var base = target === "XAU" ? 2380 : target === "SPX" ? 5120 : 4.28;
    var seed = target === "XAU" ? 7 : target === "SPX" ? 13 : 29;
    for (var i = days - 1; i >= 0; i--) {
      var d = new Date(today.getTime() - i * 86400000);
      var iso = d.toISOString().slice(0, 10);
      seed = (seed * 1103515245 + 12345) % 2147483648;
      var wave = Math.sin(i / 9) * 0.35 + ((seed % 100) / 100 - 0.5) * 0.4;
      var gap = (i % 9 === 4); /* jeda NaN terjadwal agar perilakunya teruji */
      out.sentiments.push({ asset_id: target, date: iso, score_mean: gap ? null : Math.max(-1, Math.min(1, wave)), score_weighted: null, n_articles: gap ? 0 : 3 + (seed % 9), n_sources: 2, has_news: !gap, version: "demo" });
      var drift = 1 + wave * 0.004;
      base = base * drift;
      out.prices.push({ asset_id: target, date: iso, open: base * 0.999, high: base * 1.002, low: base * 0.998, close: base, adj_close: base, volume: 1000000 + (seed % 500000) });
    }
    return out;
  };
  /* Demo impacts: demo-001 sengaja terbit setelah cut-off 17:00 agar aturan
     "masuk sesi berikutnya" teruji langsung di tampilan. */
  A.demoImpacts = function (target) {
    return [
      { article_id: "demo-001", asset_id: target, direction: "bullish", score: 0.42, confidence: 0.81, basis: "explicit", themes: ["rates_down"], rationale: "Nada dovish menopang aset berisiko dan menekan yield.", evidence: [{ quote: "Bank sentral memberi sinyal pemangkasan suku bunga pada kuartal berikutnya.", start: 0, end: 20 }], flags: [], news_horizon: "medium", model_version: "demo", universe_version: "demo", schema_version: "0.5.0", created_at: new Date().toISOString(), title: "Sinyal dovish menopang sentimen " + target, source: "Contoh sumber", published_at: "2026-10-11T20:30:00", effective_trading_date: "2026-10-12", session_close: "17:00", timezone: "America/New_York", language: "id", headline_only: true, url: null, probs: [{ model: "demo-fusion", model_version: "demo-v1", p_pos: 0.62, p_neu: 0.28, p_neg: 0.10, translation_used: false }] },
      { article_id: "demo-002", asset_id: target, direction: "bearish", score: -0.31, confidence: 0.66, basis: "macro_factor", themes: ["risk_off"], rationale: "Gelombang risk-off menekan skor harian lewat graf makro.", evidence: [], flags: [], news_horizon: "short", model_version: "demo", universe_version: "demo", schema_version: "0.5.0", created_at: new Date().toISOString(), title: "Risk-off global menekan selera risiko", source: "Contoh sumber", published_at: "2026-10-11T09:00:00", effective_trading_date: "2026-10-11", session_close: "17:00", timezone: "America/New_York", language: "id", headline_only: false, url: null, probs: [{ model: "demo-fusion", model_version: "demo-v1", p_pos: 0.12, p_neu: 0.30, p_neg: 0.58, translation_used: false }] },
      { article_id: "demo-003", asset_id: target, direction: "neutral", score: 0.03, confidence: 0.38, basis: "macro_factor", themes: [], rationale: "Bukti lemah, tidak mengubah stance.", evidence: [], flags: ["weak_evidence"], news_horizon: "short", model_version: "demo", universe_version: "demo", schema_version: "0.5.0", created_at: new Date().toISOString(), title: "Pasar menunggu data inflasi berikutnya", source: "Contoh sumber", published_at: null, effective_trading_date: null, session_close: "17:00", timezone: "America/New_York", language: "id", headline_only: true, url: null, probs: [{ model: "demo-fusion", model_version: "demo-v1", p_pos: 0.38, p_neu: 0.44, p_neg: 0.18, translation_used: false }] }
    ];
  };
  /* Mockup kualitas (UI-06): bentuk datanya sama dengan kontrak /api/quality,
     selalu berlabel MOCKUP di urutan pertama panel. */
  A.demoQuality = function () {
    return {
      universe_version: "2026-10-12-core3",
      generated_at: new Date().toISOString(),
      totals: { articles: 312, duplicates: 7, rejected: 14, impacts: 312 },
      completeness: { headline: 308, body: 96, impacts_with_evidence: 291 },
      by_source: [
        { source: "Reuters", articles: 104 },
        { source: "Bloomberg", articles: 82 },
        { source: "Antara News", articles: 70 },
        { source: "CNBC", articles: 42 },
        { source: "Kontan", articles: 14 }
      ],
      per_target: [
        { asset_id: "SPX", mapped_articles: 128, daily_days: 62, news_free_days: 9 },
        { asset_id: "RATE_UST", mapped_articles: 97, daily_days: 62, news_free_days: 15 },
        { asset_id: "XAU", mapped_articles: 87, daily_days: 62, news_free_days: 20 }
      ],
      direction_counts: { bullish: 214, bearish: 62, neutral: 36 },
      warnings: [
        "MOCKUP : seluruh angka pada panel ini ilustrasi, bukan hasil hitung API.",
        "Kelas arah neutral langka: 36 dari 312 dampak (11,5%).",
        "XAU: 20 dari 62 hari tanpa berita (32,3%) : hari kosong tetap gap, bukan nol.",
        "Hanya 96 dari 312 artikel punya isi lengkap (body): mayoritas dianalisis headline saja."
      ]
    };
  };
})(window.ARCAS);