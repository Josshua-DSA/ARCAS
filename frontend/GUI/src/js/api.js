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

  function api(path, opts) {
    var signal = opts && opts.signal;
    return detectBase().then(function (base) {
      return fetch(base + path, { cache: "no-store", signal: signal }).then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status + " untuk " + path);
        return r.json();
      });
    }).catch(function (err) {
      /* Pembatalan bukan kegagalan API: jangan tandai mati, jangan reset base. */
      if (err && err.name === "AbortError") throw err;
      resetBase();
      throw err;
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
      var iso = localISO(d);
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
})(window.ARCAS);
