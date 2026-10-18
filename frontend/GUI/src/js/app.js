/* ARCAS Sentiment Desk : Vanilla JS, tanpa build, tanpa CDN.
   Alasan arsitektur satu baris: satu state global dibaca semua renderer agar tab target selalu konsisten. */
(function () {
  "use strict";

  /* Tab target dirender dari /api/universe, bukan dari konstanta lokal.
     TARGET_INFO hanya peta tampilan (warna, nama) dengan fallback generik. */
  var TARGET_INFO = {
    XAU: { name: "Emas", ticker: "GC=F", venue: "CME", color: "#FFD33D" },
    RATE_UST: { name: "Yield UST 10Y", ticker: "^TNX", venue: "CBOE", color: "#58A6FF" },
    SPX: { name: "S&P 500", ticker: "^GSPC", venue: "SNP", color: "#FF7517" }
  };
  function metaFor(assetId, row) {
    if (TARGET_INFO[assetId]) return TARGET_INFO[assetId];
    return {
      name: (row && row.name) || assetId,
      ticker: (row && row.price_ticker) || assetId,
      venue: (row && row.exchange) || "-",
      color: "#BDB7B7"
    };
  }
  var CLASS_LABEL = { bond: "Obligasi", mutual_fund: "Reksadana", stock: "Saham", etf: "ETF", btc: "BTC", gold: "Emas", cash: "Kas" };
  var PERSONA_LABEL = { retail: "Retail Investor", day_trader: "Day Trader", fund_manager: "Fund Manager", pension: "Long-term / Pension", risk_manager: "Risk Manager" };

  var state = { target: "XAU", days: 90, profile: "moderate", impacts: [], apiOk: false, apiBase: "", meta: null };

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function fmt(n, d) {
    if (n === null || n === undefined || Number.isNaN(n)) return "n/a";
    var sign = n > 0 ? "+" : "";
    return sign + Number(n).toFixed(d == null ? 2 : d);
  }
  function fmtDate(iso) { return String(iso || "").slice(0, 10); }
  function showState(id, msg) {
    var el = $(id);
    if (!msg) { el.hidden = true; el.textContent = ""; return; }
    el.hidden = false; el.textContent = msg;
  }

  /* Basis API: coba path relatif dulu (deploy), lalu localhost (dev). Alasan: satu file jalan di dua konteks. */
  var basePromise = null;
  function detectBase() {
    if (state.apiBase) return Promise.resolve(state.apiBase);
    if (basePromise) return basePromise;
    var candidates = ["", "http://localhost:8000", "http://127.0.0.1:8000"];
    var chain = Promise.reject();
    candidates.forEach(function (base) {
      chain = chain.catch(function () {
        return fetch(base + "/health", { cache: "no-store" }).then(function (r) {
          if (!r.ok) throw new Error("bad");
          return r.json();
        }).then(function () { state.apiBase = base; return base; });
      });
    });
    basePromise = chain.catch(function () { state.apiBase = ""; return ""; });
    return basePromise;
  }
  function api(path) {
    return detectBase().then(function (base) {
      return fetch(base + path, { cache: "no-store" }).then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status + " untuk " + path);
        return r.json();
      });
    });
  }
  function setStatus(mode, text) {
    var dot = $("statusDot");
    dot.className = "dot" + (mode === "ok" ? " ok" : mode === "err" ? " err" : mode === "warn" ? " warn" : "");
    $("statusText").textContent = text;
    $("dataBadge").textContent = text;
    $("srcMeta").textContent = "Sumber: " + (state.apiOk ? (state.apiBase === "" ? "API relatif" : state.apiBase) : "ilustrasi lokal (API tidak terjangkau)");
  }

  /* Splash status nyata: teks hanya muncul untuk tahap yang benar-benar sedang dilakukan. */
  function splashStatus(text) {
    if (window.Splash && typeof window.Splash.status === "function") window.Splash.status(text);
  }
  function splashDone() {
    if (window.Splash && typeof window.Splash.done === "function") window.Splash.done();
  }

  /* Data Provenance Bar: satu sumber kebenaran mode data, ditegaskan berlabel teks.
     live = DB punya harga/berita; empty = API hidup tapi kosong; demo = fallback ilustrasi. */
  function renderProvenance(meta) {
    var box = $("provenance");
    if (!meta) {
      $("provMode").textContent = "demo : ilustrasi lokal (API tidak terjangkau)";
      box.querySelector(".prov-item").classList.add("warn");
      ["provUniverse", "provSchema", "provModel", "provArticles", "provNews", "provFresh"]
        .forEach(function (id) { $(id).textContent = "ilustrasi"; });
      return;
    }
    box.querySelector(".prov-item").classList.remove("warn");
    $("provMode").textContent = "mode : " + meta.mode;
    $("provUniverse").textContent = meta.universe_version || "n/a";
    $("provSchema").textContent = meta.schema_version || "n/a";
    $("provModel").textContent = (meta.model_version || "n/a") + (meta.calibrated ? " (terkalibrasi)" : " (belum kalibrasi)");
    $("provArticles").textContent = String(meta.coverage.articles);
    $("provNews").textContent = String(meta.coverage.days_with_news);
    var fresh = meta.coverage.last_price_date || meta.coverage.last_news_date;
    $("provFresh").textContent = fresh ? "harga " + fresh : "belum ada deret";
  }
  function loadMeta() {
    splashStatus("MEMUAT METADATA");
    return api("/api/meta").then(function (meta) {
      state.meta = meta;
      renderProvenance(meta);
      return meta;
    }).catch(function () {
      state.meta = null;
      renderProvenance(null);
      return null;
    });
  }

  /* Data ilustrasi jujur: hanya dipakai saat API mati, selalu berlabel. Alasan: R-38 tanpa angka fabrikasi. */
  function demoSeries(target) {
    var out = { sentiments: [], prices: [] };
    var today = new Date();
    var base = target === "XAU" ? 2380 : target === "SPX" ? 5120 : 4.28;
    var seed = target === "XAU" ? 7 : target === "SPX" ? 13 : 29;
    for (var i = state.days - 1; i >= 0; i--) {
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
  }
  /* Data ilustrasi jujur: hanya dipakai saat API mati, selalu berlabel. Alasan: R-38 tanpa angka fabrikasi.
     Demo-001 sengaja terbit setelah cut-off 17:00 agar aturan "masuk sesi berikutnya" teruji di tampilan. */
  function demoImpacts(target) {
    return [
      { article_id: "demo-001", asset_id: target, direction: "bullish", score: 0.42, confidence: 0.81, basis: "explicit", themes: ["rates_down"], rationale: "Nada dovish menopang aset berisiko dan menekan yield.", evidence: [{ quote: "Bank sentral memberi sinyal pemangkasan suku bunga pada kuartal berikutnya.", start: 0, end: 20 }], flags: [], news_horizon: "medium", model_version: "demo", universe_version: "demo", schema_version: "0.5.0", created_at: new Date().toISOString(), title: "Sinyal dovish menopang sentimen " + target, source: "Contoh sumber", published_at: "2026-10-11T20:30:00", effective_trading_date: "2026-10-12", session_close: "17:00", timezone: "America/New_York", language: "id" },
      { article_id: "demo-002", asset_id: target, direction: "bearish", score: -0.31, confidence: 0.66, basis: "macro_factor", themes: ["risk_off"], rationale: "Gelombang risk-off menekan skor harian lewat graf makro.", evidence: [], flags: [], news_horizon: "short", model_version: "demo", universe_version: "demo", schema_version: "0.5.0", created_at: new Date().toISOString(), title: "Risk-off global menekan selera risiko", source: "Contoh sumber", published_at: "2026-10-11T09:00:00", effective_trading_date: "2026-10-11", session_close: "17:00", timezone: "America/New_York", language: "id" },
      { article_id: "demo-003", asset_id: target, direction: "neutral", score: 0.03, confidence: 0.38, basis: "macro_factor", themes: [], rationale: "Bukti lemah, tidak mengubah stance.", evidence: [], flags: ["weak_evidence"], news_horizon: "short", model_version: "demo", universe_version: "demo", schema_version: "0.5.0", created_at: new Date().toISOString(), title: "Pasar menunggu data inflasi berikutnya", source: "Contoh sumber", published_at: null, effective_trading_date: null, session_close: "17:00", timezone: "America/New_York", language: "id" }
    ];
  }

  /* Grafik dual-axis. Alasan ECharts lokal: nol dependensi jaringan saat sidang. */
  var chart = null;
  function ensureChart() {
    if (chart || typeof echarts === "undefined") return;
    chart = echarts.init($("chart"));
    window.addEventListener("resize", function () { if (chart) chart.resize(); });
  }
  function renderChart(payload) {
    ensureChart();
    var info = metaFor(state.target);
    var byDate = {};
    (payload.sentiments || []).forEach(function (s) { byDate[s.date] = byDate[s.date] || {}; byDate[s.date].score = s.score_mean; byDate[s.date].n = s.n_articles; });
    (payload.prices || []).forEach(function (p) { byDate[p.date] = byDate[p.date] || {}; byDate[p.date].close = p.close; });
    var dates = Object.keys(byDate).sort();
    var closes = dates.map(function (d) { var v = byDate[d].close; return v == null ? null : Math.round(v * 100) / 100; });
    var scores = dates.map(function (d) { var v = byDate[d].score; return v == null ? null : Math.round(v * 1000) / 1000; });
    var gapCount = scores.filter(function (v) { return v === null; }).length;

    $("targetMeta").textContent = "Target: " + state.target + " : " + info.name + " (" + info.ticker + ")";
    $("rangeMeta").textContent = "Rentang: " + state.days + " hari terakhir";
    $("lgPrice").style.background = info.color;

    if (!chart) { showState("chartState", "Pustaka grafik lokal belum termuat (src/js/echarts.min.js). Periksa path file."); return; }
    if (!dates.length) { showState("chartState", "Belum ada deret untuk target ini pada rentang terpilih."); chart.clear(); return; }
    showState("chartState", gapCount ? gapCount + " hari tanpa berita tampil sebagai jeda (bukan nol)." : "");

    chart.setOption({
      backgroundColor: "transparent",
      grid: { left: 56, right: 56, top: 34, bottom: 30 },
      tooltip: { trigger: "axis", backgroundColor: "#2C2727", borderWidth: 0,
        textStyle: { color: "#F6F4F4", fontFamily: "JetBrains Mono, monospace", fontSize: 12 } },
      xAxis: { type: "category", data: dates, axisLine: { lineStyle: { color: "#5A5454" } },
        axisLabel: { color: "#BDB7B7", fontFamily: "JetBrains Mono, monospace", fontSize: 10, hideOverlap: true } },
      yAxis: [
        { type: "value", scale: true, splitLine: { lineStyle: { color: "#5A5454", opacity: 0.5 } },
          axisLabel: { color: "#BDB7B7", fontFamily: "JetBrains Mono, monospace", fontSize: 10 } },
        { type: "value", min: -1, max: 1, splitNumber: 4, splitLine: { show: false },
          axisLabel: { color: "#BDB7B7", fontFamily: "JetBrains Mono, monospace", fontSize: 10 } }
      ],
      series: [
        { name: "Tutup", type: "line", data: closes, yAxisIndex: 0, showSymbol: false, connectNulls: false,
          lineStyle: { width: 2.5, color: info.color }, itemStyle: { color: info.color } },
        { name: "Skor", type: "bar", data: scores, yAxisIndex: 1, connectNulls: false,
          itemStyle: { color: "#F6F4F4", opacity: 0.85 }, barMaxWidth: 5 }
      ]
    }, true);
    var last = scores.filter(function (v) { return v !== null; }).slice(-1)[0];
    $("heroKicker").textContent = "Ringkasan " + state.target + " : skor terakhir " + (last == null ? "n/a (hari tanpa berita)" : fmt(last) + (last > 0.1 ? " condong bullish" : last < -0.1 ? " condong bearish" : " netral"));
  }

  /* Statistik: kelompokkan per uji, tampilkan estimate + CI + p_adj + n. Alasan tabel ringkas: analis butuh efek dan n, bukan cuma p. */
  function statGroup(rows, test) { return rows.filter(function (r) { return r.test === test; }).slice(0, 6); }
  function statRow(r) {
    var sig = r.p_adjusted != null && r.p_adjusted < 0.05;
    var cls = r.estimate > 0.02 ? "pos" : r.estimate < -0.02 ? "neg" : "flat";
    var arrow = r.estimate > 0.02 ? "▲" : r.estimate < -0.02 ? "▼" : "●";
    return "<tr><td>" + esc(testLabel(r.test)) + (r.lag != null ? " L" + esc(r.lag) : "") + "</td>" +
      "<td class='" + cls + "'>" + arrow + " " + fmt(r.estimate, 3) + (sig ? "<span class='sig'>sig</span>" : "") + "</td>" +
      "<td>" + (r.p_adjusted != null ? Number(r.p_adjusted).toFixed(3) : Number(r.p_value).toFixed(3)) + "</td>" +
      "<td>" + esc(r.n_obs) + "</td></tr>";
  }
  function testLabel(t) {
    return { spearman: "Spearman", pearson: "Pearson", ols: "OLS-HAC", granger: "Granger", event_study: "CAR" }[t] || t;
  }
  function renderStats(rows) {
    var box = $("statTables");
    if (!rows || !rows.length) {
      box.innerHTML = "";
      showState("statState", "Belum ada hasil uji untuk target ini. Jalankan pipeline analyze dulu, atau ini tampilan ilustrasi.");
      return;
    }
    showState("statState", "");
    var order = ["spearman", "ols", "granger", "event_study", "pearson"];
    var html = "<table class='data'><thead><tr><th>Uji</th><th>Est</th><th>p_adj</th><th>n</th></tr></thead><tbody>";
    order.forEach(function (t) { statGroup(rows, t).forEach(function (r) { html += statRow(r); }); });
    html += "</tbody></table>";
    /* Periode dan lag yang diuji (Upgrade.md UI-02): angka statis punya denominasi yang terlihat. */
    var starts = [], ends = [];
    rows.forEach(function (r) {
      if (r.period_start) starts.push(String(r.period_start));
      if (r.period_end) ends.push(String(r.period_end));
    });
    if (starts.length && ends.length) {
      var lagSeen = {}, lags = [];
      rows.forEach(function (r) {
        if (r.lag != null && !lagSeen[r.lag]) { lagSeen[r.lag] = true; lags.push(r.lag); }
      });
      lags.sort(function (a, b) { return a - b; });
      starts.sort(); ends.sort();
      html += "<p class='hint' style='font-family:var(--font-mono);font-size:11px;color:var(--on-dark-muted)'>Periode uji: " +
        esc(starts[0]) + " .. " + esc(ends[ends.length - 1]) + " : lag diuji L" + lags.join(", L") +
        ". Asosiasi historis, bukan sebab.</p>";
    }
    box.innerHTML = html;
  }

  /* Alokasi: bar baseline vs baru + validasi total persis 100. Alasan: konstrain domain paling mudah dilanggar diam-diam. */
  function renderAllocation(data) {
    var bars = $("allocBars");
    if (!data || !data.lines || !data.lines.length) {
      bars.innerHTML = "";
      showState("allocState", "Belum ada simulasi alokasi untuk profil ini.");
      $("allocTotalNum").textContent = "n/a";
      return;
    }
    showState("allocState", "");
    var total = data.lines.reduce(function (a, l) { return a + Number(l.new_pct || 0); }, 0);
    var ok = Math.abs(total - 100) < 0.01;
    var totalBox = $("allocTotal");
    totalBox.classList.toggle("valid", ok);
    totalBox.classList.toggle("invalid", !ok);
    $("allocTotalNum").textContent = total.toFixed(2) + "% " + (ok ? ": valid" : ": TIDAK valid");
    bars.innerHTML = data.lines.map(function (l) {
      var d = Number(l.delta_pp || 0);
      var cls = d > 0.005 ? "pos" : d < -0.005 ? "neg" : "flat";
      var arrow = d > 0.005 ? "▲" : d < -0.005 ? "▼" : "●";
      var wBase = Math.max(0, Math.min(100, Number(l.baseline_pct || 0)));
      var wNew = Math.max(0, Math.min(100, Number(l.new_pct || 0)));
      return "<div class='alloc-row'><div class='lbl'><span>" + esc(CLASS_LABEL[l.alloc_class] || l.alloc_class) +
        "</span><span class='" + cls + "'>" + esc(wBase.toFixed(1)) + "% " + arrow + " " + fmt(d, 2) + " pp : " + esc(wNew.toFixed(1)) + "%</span></div>" +
        "<div class='bar' role='img' aria-label='" + esc(l.alloc_class) + " baseline " + esc(wBase.toFixed(1)) + " persen, baru " + esc(wNew.toFixed(1)) + " persen'>" +
        "<div class='base' style='width:" + wBase + "%'></div><div class='tilt' style='width:" + wNew + "%;opacity:.85'></div></div></div>";
    }).join("");
  }

  /* Dampak berita: chip arah selalu ikon + teks, oranye tak pernah untuk arah. Alasan: aturan aksesibilitas THEME. */
  function dirChip(direction) {
    var d = String(direction || "neutral").toLowerCase();
    if (d === "bullish" || d === "buy") return "<span class='chip buy'>▲ Bullish</span>";
    if (d === "bearish" || d === "sell") return "<span class='chip sell'>▼ Bearish</span>";
    if (d === "mixed") return "<span class='chip mix'>◆ Mixed</span>";
    return "<span class='chip hold'>● Netral</span>";
  }
  /* Audit waktu (Upgrade.md UI-02): terbit vs sesi efektif, tanpa klaim sebab.
     Jika salah satu waktu tidak terekam di DB, barisnya jujur bilang belum terekam. */
  function timeAuditLine(it) {
    var parts = [];
    if (it.published_at) {
      parts.push("<span>terbit " + esc(fmtDate(it.published_at)) + " " + esc(String(it.published_at).slice(11, 16)) + "</span>");
    } else {
      parts.push("<span>waktu terbit belum terekam</span>");
    }
    if (it.effective_trading_date && it.published_at) {
      var nextSession = String(it.effective_trading_date) > String(it.published_at).slice(0, 10);
      parts.push("<span>sesi efektif " + esc(it.effective_trading_date) + (nextSession ? " : masuk sesi berikutnya" : "") + "</span>");
    } else if (it.effective_trading_date) {
      parts.push("<span>sesi efektif " + esc(it.effective_trading_date) + "</span>");
    }
    if (it.session_close) {
      parts.push("<span>cut-off " + esc(it.session_close) + " " + esc(it.timezone || "") + "</span>");
    }
    return parts.length ? "<div class='news-meta audit-line'>" + parts.join("") + "</div>" : "";
  }
  function impactCard(it) {
    var quote = (it.evidence && it.evidence[0] && it.evidence[0].quote) ? it.evidence[0].quote : "";
    var themes = (it.themes || []).map(esc).join(", ") || "tanpa tema";
    return "<article class='news-card' data-id='" + esc(it.article_id) + "' data-title='" + esc(it.title || it.article_id) + "'>" +
      "<div class='news-meta'>" + dirChip(it.direction) +
      "<span>skor " + fmt(it.score) + "</span><span>conf " + esc(Number(it.confidence || 0).toFixed(2)) + "</span>" +
      "<span>" + esc(it.basis || "") + "</span><span>" + esc(fmtDate(it.created_at)) + "</span></div>" +
      "<h3>" + esc(it.title || it.article_id) + "</h3>" +
      "<div class='news-meta'><span>" + esc(it.source || "sumber API") + "</span><span>tema: " + themes + "</span><span>horizon: " + esc(it.news_horizon || "short") + "</span></div>" +
      (it.rationale ? "<p style='font-size:14px;color:var(--text-secondary);margin:6px 0'>" + esc(it.rationale) + "</p>" : "") +
      (quote ? "<blockquote class='quote'>" + esc(quote) + "</blockquote>" : "") +
      timeAuditLine(it) +
      "<div style='display:flex;gap:8px;flex-wrap:wrap;margin-top:10px'>" +
      "<button class='btn small primary' data-persona='" + esc(it.article_id) + "'>Lihat Persona POV</button></div></article>";
  }
  function applyNewsFilter() {
    var q = $("newsFilter").value.toLowerCase();
    var dir = $("dirFilter").value;
    var cards = document.querySelectorAll("#newsList .news-card");
    var visible = 0;
    cards.forEach(function (c) {
      var hitQ = !q || c.textContent.toLowerCase().indexOf(q) !== -1;
      var art = state.impacts.find(function (x) { return x.article_id === c.getAttribute("data-id"); });
      var hitD = !dir || (art && String(art.direction).toLowerCase() === dir);
      var show = hitQ && hitD;
      c.style.display = show ? "" : "none";
      if (show) visible++;
    });
    showState("newsState", visible ? "" : "Tidak ada berita cocok dengan saringan. Kosongkan kata kunci atau ubah arah.");
  }
  function renderImpacts(rows) {
    state.impacts = rows || [];
    $("impactCount").textContent = state.impacts.length + " artikel";
    var top = state.impacts.slice(0, 3);
    $("topList").innerHTML = top.length ? "<table class='data'><thead><tr><th>Judul</th><th>Arah</th><th>Conf</th></tr></thead><tbody>" +
      top.map(function (t) {
        var cls = String(t.direction) === "bullish" ? "pos" : String(t.direction) === "bearish" ? "neg" : "flat";
        var arrow = String(t.direction) === "bullish" ? "▲" : String(t.direction) === "bearish" ? "▼" : "●";
        return "<tr><td>" + esc((t.title || t.article_id).slice(0, 64)) + "</td><td class='" + cls + "'>" + arrow + " " + esc(t.direction) + "</td><td>" + esc(Number(t.confidence || 0).toFixed(2)) + "</td></tr>";
      }).join("") + "</tbody></table>"
      : "";
    showState("topState", top.length ? "" : "Belum ada berita berdampak.");
    $("newsList").innerHTML = state.impacts.map(impactCard).join("");
    showState("newsState", state.impacts.length ? "" : "Belum ada dampak untuk target ini pada rentang ini.");
    bindPersonaButtons();
    applyNewsFilter();
  }

  /* Persona modal: dialog asli, tutup via Esc dan tombol. Alasan: keyboard harus bisa keluar. */
  function stanceChip(stance, strength) {
    var s = String(stance || "hold").toLowerCase();
    var dots = "";
    var n = Math.max(1, Math.min(5, Math.round(Number(strength || 0) * 5) || 1));
    for (var i = 0; i < n; i++) dots += "●";
    if (s === "buy") return "<span class='chip buy'>▲ BUY " + dots + "</span>";
    if (s === "sell") return "<span class='chip sell'>▼ SELL " + dots + "</span>";
    return "<span class='chip hold'>● HOLD " + dots + "</span>";
  }
  function openPersona(articleId, fallback) {
    var modal = $("personaModal");
    $("personaList").innerHTML = "";
    showState("personaState", "Memuat stance lima persona...");
    if (typeof modal.showModal === "function" && !modal.open) modal.showModal();
    var params = "?target=" + encodeURIComponent(state.target) +
      "&score=" + encodeURIComponent(fallback && fallback.score != null ? fallback.score : 0.35) +
      "&confidence=" + encodeURIComponent(fallback && fallback.confidence != null ? fallback.confidence : 0.75);
    api("/api/persona/" + encodeURIComponent(articleId) + params).then(function (views) {
      renderPersona(articleId, views);
    }).catch(function () {
      var demo = ["retail", "day_trader", "fund_manager", "pension", "risk_manager"].map(function (p, i) {
        return { article_id: articleId, persona_id: p, target: state.target, stance: i === 0 ? "buy" : i === 4 ? "sell" : "hold", strength: 0.4 + i * 0.1, news_horizon: "medium", raw_value: 0.2, confidence: 0.6, rationale: "Ilustrasi lokal: API persona tidak terjangkau.", params_version: "demo", disclaimer: "Simulasi sudut pandang. Bukan nasihat investasi." };
      });
      renderPersona(articleId, demo);
      showState("personaState", "API persona tidak terjangkau, menampilkan ilustrasi berlabel.");
    });
  }
  function renderPersona(articleId, views) {
    if (!views || !views.length) { showState("personaState", "Tidak ada stance untuk artikel ini."); return; }
    showState("personaState", "");
    $("personaTitle").textContent = "Stance untuk " + articleId.slice(0, 24);
    $("personaList").innerHTML = "<table class='data'><thead><tr><th>Persona</th><th>Stance</th><th>Alasan</th></tr></thead><tbody>" +
      views.map(function (v) {
        return "<tr><td>" + esc(PERSONA_LABEL[v.persona_id] || v.persona_id) + "</td><td>" + stanceChip(v.stance, v.strength) + "</td><td style='font-family:var(--font-sans);font-size:13px'>" + esc(v.rationale || "") + "</td></tr>";
      }).join("") + "</tbody></table>";
  }
  function bindPersonaButtons() {
    document.querySelectorAll("[data-persona]").forEach(function (b) {
      b.onclick = function () {
        var id = b.getAttribute("data-persona");
        var fb = state.impacts.find(function (x) { return x.article_id === id; });
        openPersona(id, fb);
      };
    });
  }

  /* Muat ulang semua panel untuk target aktif. Alasan satu fungsi: cegah panel basi beda target. */
  function isoDaysAgo(n) { return new Date(Date.now() - (n - 1) * 86400000).toISOString().slice(0, 10); }
  function reload() {
    var t = state.target;
    var end = new Date().toISOString().slice(0, 10);
    var start = isoDaysAgo(state.days);
    showState("chartState", "Memuat deret " + t + "...");
    showState("statState", "Memuat uji statistik...");
    showState("allocState", "Memuat simulasi alokasi...");
    showState("newsState", "Memuat dampak berita...");

    api("/api/series/" + t + "?start_date=" + start + "&end_date=" + end).then(function (payload) {
      state.apiOk = true; setStatus("ok", "terhubung ke API");
      renderChart(payload);
    }).catch(function () {
      state.apiOk = false; setStatus("warn", "API tidak terjangkau : ilustrasi");
      renderChart(demoSeries(t));
    });

    api("/api/stats/" + t).then(function (rows) { renderStats(rows); })
      .catch(function () {
        renderStats([{ test: "spearman", lag: 1, estimate: 0.18, p_value: 0.04, p_adjusted: 0.09, n_obs: 62, period_start: "2026-07-15", period_end: "2026-10-12" }, { test: "ols", lag: 1, estimate: 0.11, p_value: 0.07, p_adjusted: 0.12, n_obs: 62, period_start: "2026-07-15", period_end: "2026-10-12" }, { test: "granger", lag: 2, estimate: 3.4, p_value: 0.06, p_adjusted: 0.11, n_obs: 60, period_start: "2026-07-15", period_end: "2026-10-12" }, { test: "event_study", lag: 0, estimate: 0.006, p_value: 0.03, p_adjusted: 0.08, n_obs: 18, period_start: "2026-08-01", period_end: "2026-10-12" }]);
        /* Setelah renderStats, bukan sebelum: renderStats mengosongkan state di awal. */
        showState("statState", "API statistik tidak terjangkau : tabel ini ilustrasi berlabel, bukan hasil uji nyata.");
      });

    api("/api/allocation?profile_id=" + state.profile + "&article_id=current_market").then(function (d) { renderAllocation(d); })
      .catch(function () {
        renderAllocation({ lines: [
          { alloc_class: "bond", baseline_pct: 40, new_pct: 42, delta_pp: 2, confidence: 0.7 },
          { alloc_class: "mutual_fund", baseline_pct: 15, new_pct: 15, delta_pp: 0, confidence: 0.5 },
          { alloc_class: "stock", baseline_pct: 15, new_pct: 14, delta_pp: -1, confidence: 0.65 },
          { alloc_class: "etf", baseline_pct: 20, new_pct: 19, delta_pp: -1, confidence: 0.8 },
          { alloc_class: "btc", baseline_pct: 5, new_pct: 5, delta_pp: 0, confidence: 0.4 },
          { alloc_class: "gold", baseline_pct: 5, new_pct: 5, delta_pp: 0, confidence: 0.7 }
        ]});
        showState("allocState", "API alokasi tidak terjangkau, ilustrasi berlabel (total tetap 100%).");
      });

    api("/api/impacts/" + t + "?limit=50").then(function (rows) {
      state.apiOk = true;
      renderImpacts(rows);
    }).catch(function () { renderImpacts(demoImpacts(t)); });
  }

  /* Tab dibangun dari respons /api/universe. Alasan delegasi event:
     jumlah tab mengikuti server, tidak lagi diasumsikan tiga. */
  var TAB_ORDER = { XAU: 0, RATE_UST: 1, SPX: 2 };
  function renderTabs(rows) {
    rows = rows.slice().sort(function (a, b) {
      var ao = TAB_ORDER[a.asset_id], bo = TAB_ORDER[b.asset_id];
      if (ao == null && bo == null) return a.asset_id < b.asset_id ? -1 : 1;
      if (ao == null) return 1;
      if (bo == null) return -1;
      return ao - bo;
    });
    var box = $("targetTabs");
    box.innerHTML = rows.map(function (row, i) {
      var id = row.asset_id;
      var info = metaFor(id, row);
      var sel = i === 0 ? "true" : "false";
      return "<button class='target-tab' role='tab' data-target='" + esc(id) + "' aria-selected='" + sel + "'>" +
        "<span class='swatch' style='background:" + esc(info.color) + "' aria-hidden='true'></span>" +
        "<span><span class='tick'>" + esc(id) + "</span>" +
        "<span class='meta'>" + esc(info.name) + " : " + esc(info.ticker) + " : " + esc(info.venue) + "</span></span></button>";
    }).join("");
    if (rows.length) state.target = rows[0].asset_id;
  }
  function bindTabs() {
    $("targetTabs").addEventListener("click", function (e) {
      var btn = e.target.closest(".target-tab");
      if (!btn) return;
      document.querySelectorAll(".target-tab").forEach(function (b) { b.setAttribute("aria-selected", "false"); });
      btn.setAttribute("aria-selected", "true");
      state.target = btn.getAttribute("data-target");
      reload();
    });
    document.addEventListener("keydown", function (e) {
      if (e.target.matches("input, select, textarea")) return;
      var tabs = document.querySelectorAll(".target-tab");
      var idx = Number(e.key) - 1;
      if (idx >= 0 && idx < tabs.length) tabs[idx].click();
    });
  }
  function loadUniverse() {
    splashStatus("MEMUAT UNIVERSE");
    return api("/api/universe").then(function (rows) {
      var active = (rows || []).filter(function (r) { return r.active === 1 || r.active === true; });
      if (!active.length) throw new Error("universe kosong");
      renderTabs(active);
      $("heroKicker").textContent = "Ringkasan hari ini : " + active.length + " target inti dari API";
    }).catch(function () {
      renderTabs([{ asset_id: "XAU" }, { asset_id: "RATE_UST" }, { asset_id: "SPX" }]);
      $("heroKicker").textContent = "Ringkasan hari ini : ilustrasi lokal (API tidak terjangkau)";
    });
  }

  function bindControls() {
    document.querySelectorAll(".range-btn").forEach(function (b) {
      b.addEventListener("click", function () {
        document.querySelectorAll(".range-btn").forEach(function (x) { x.setAttribute("aria-pressed", "false"); });
        b.setAttribute("aria-pressed", "true");
        state.days = Number(b.getAttribute("data-days"));
        reload();
      });
    });
    document.querySelectorAll(".profile-btn").forEach(function (b) {
      b.addEventListener("click", function () {
        document.querySelectorAll(".profile-btn").forEach(function (x) { x.setAttribute("aria-pressed", "false"); });
        b.setAttribute("aria-pressed", "true");
        state.profile = b.getAttribute("data-profile");
        reload();
      });
    });
    $("newsFilter").addEventListener("input", applyNewsFilter);
    $("dirFilter").addEventListener("change", applyNewsFilter);
    $("personaClose").addEventListener("click", function () { $("personaModal").close(); });
    $("personaModal").addEventListener("click", function (e) {
      var r = $("personaModal").getBoundingClientRect();
      var outside = e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
      if (outside) $("personaModal").close();
    });
    document.querySelectorAll("nav.sections a").forEach(function (a) {
      a.addEventListener("click", function () {
        document.querySelectorAll("nav.sections a").forEach(function (x) { x.removeAttribute("aria-current"); });
        a.setAttribute("aria-current", "page");
      });
    });
  }

  /* Boot: base dulu, lalu meta + universe paralel. Splash selesai hanya setelah
     keduanya beres ATAU fallback dipilih : tidak ada log palsu (Upgrade.md 3.1-5). */
  detectBase().then(function () {
    setStatus(state.apiBase ? "ok" : "warn", state.apiBase ? "terhubung ke API" : "API tidak terjangkau : ilustrasi");
    Promise.allSettled([loadMeta(), loadUniverse()])
      .then(function () { splashStatus(state.meta ? "MODE " + state.meta.mode.toUpperCase() : "MODE DEMO"); })
      .then(reload)
      .then(splashDone);
  });
  bindTabs();
  bindControls();
})();
