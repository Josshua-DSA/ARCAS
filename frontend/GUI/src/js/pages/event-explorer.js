/* Event Explorer : pilih berita, lihat titiknya di grafik pasar, lalu 4 uji
   statistik di sebelahnya. File eksperimen terpisah; tidak menyentuh halaman
   milik Josshua. Semua angka dari API, tidak ada data contoh. */
(function (A) {
  "use strict";
  var esc = A.esc, fmt = A.fmt;

  var S = {
    target: "XAU",
    prices: [],
    news: [],
    tests: [],
    selected: null,   /* index berita terpilih */
    chart: null
  };

  function $(id) { return document.getElementById(id); }
  function show(id, msg) {
    var el = $(id);
    if (!el) return;
    if (!msg) { el.hidden = true; el.textContent = ""; return; }
    el.hidden = false; el.textContent = msg;
  }

  /* Tanggal berita bisa jatuh di hari bursa tutup (Sabtu/Minggu/libur).
     Marker digeser ke tanggal bursa terdekat yang tersedia, dan UI menyebut
     pergeserannya supaya tidak terbaca sebagai presisi palsu. */
  function nearestTradingDate(iso, dates) {
    if (!iso || !dates.length) return null;
    var d = String(iso).slice(0, 10);
    if (dates.indexOf(d) !== -1) return { date: d, shifted: false };
    var best = null, bestGap = Infinity;
    for (var i = 0; i < dates.length; i++) {
      var gap = Math.abs(new Date(dates[i]) - new Date(d));
      if (gap < bestGap) { bestGap = gap; best = dates[i]; }
    }
    return best ? { date: best, shifted: true } : null;
  }

  /* ---------------- grafik ---------------- */
  function ensureChart() {
    if (S.chart || typeof echarts === "undefined") return;
    S.chart = echarts.init($("priceChart"));
    window.addEventListener("resize", function () { if (S.chart) S.chart.resize(); });
  }

  function drawChart() {
    ensureChart();
    if (!S.chart) {
      show("chartState", "Pustaka grafik lokal belum termuat.");
      return;
    }
    if (!S.prices.length) {
      S.chart.clear();
      show("chartState", "Belum ada deret harga untuk target ini.");
      return;
    }
    show("chartState", "");

    var dates = S.prices.map(function (p) { return p.date; });
    var closes = S.prices.map(function (p) { return Number(p.close); });
    var byDate = {};
    S.prices.forEach(function (p) { byDate[p.date] = Number(p.close); });

    /* Semua berita jadi titik kecil; yang terpilih jadi penanda besar + garis. */
    var dots = [];
    S.news.forEach(function (n) {
      var near = nearestTradingDate(n.published_at, dates);
      if (!near) return;
      dots.push({
        value: [near.date, byDate[near.date]],
        name: n.title || n.article_id,
        itemStyle: { color: n.direction === "bearish" ? "#FF7B72" : n.direction === "bullish" ? "#56D364" : "#BDB7B7" }
      });
    });

    var series = [{
      name: "Harga tutup", type: "line", data: closes, showSymbol: false, smooth: false,
      lineStyle: { width: 2.2, color: "#FFD33D" }, itemStyle: { color: "#FFD33D" }
    }, {
      name: "Berita", type: "scatter", data: dots, symbolSize: 9,
      itemStyle: { borderColor: "#3E3939", borderWidth: 1 }
    }];

    var sel = S.selected != null ? S.news[S.selected] : null;
    var selNear = sel ? nearestTradingDate(sel.published_at, dates) : null;
    if (selNear) {
      series.push({
        name: "Berita terpilih", type: "scatter", symbolSize: 16, symbol: "pin",
        data: [{ value: [selNear.date, byDate[selNear.date]], name: sel.title || sel.article_id }],
        itemStyle: { color: "#FF7517" },
        markLine: {
          silent: true, symbol: "none",
          lineStyle: { color: "#FF7517", type: "dashed", width: 1.2 },
          label: { formatter: selNear.date, color: "#FF7517", fontSize: 10, position: "insideEndTop" },
          data: [{ xAxis: selNear.date }]
        }
      });
    }

    S.chart.setOption({
      backgroundColor: "transparent",
      grid: { left: 58, right: 22, top: 26, bottom: 44 },
      tooltip: {
        trigger: "axis", backgroundColor: "#2C2727", borderWidth: 0,
        textStyle: { color: "#F6F4F4", fontFamily: "JetBrains Mono, monospace", fontSize: 12 }
      },
      legend: {
        data: ["Harga tutup", "Berita"], bottom: 0,
        textStyle: { color: "#BDB7B7", fontFamily: "Inter, sans-serif", fontSize: 11 },
        itemWidth: 10, itemHeight: 10
      },
      xAxis: {
        type: "category", data: dates, boundaryGap: false,
        axisLine: { lineStyle: { color: "#5A5454" } },
        axisLabel: { color: "#BDB7B7", fontFamily: "JetBrains Mono, monospace", fontSize: 10, hideOverlap: true }
      },
      yAxis: {
        type: "value", scale: true,
        splitLine: { lineStyle: { color: "#5A5454", opacity: 0.35 } },
        axisLabel: { color: "#BDB7B7", fontFamily: "JetBrains Mono, monospace", fontSize: 10 }
      },
      series: series
    }, true);
  }

  /* ---------------- daftar berita ---------------- */
  function renderNews() {
    var box = $("newsPicker");
    if (!box) return;
    if (!S.news.length) {
      box.innerHTML = "";
      show("newsState", "Belum ada berita untuk target ini. Tarik berita dulu lewat news_cli fetch.");
      return;
    }
    show("newsState", "");
    var dates = S.prices.map(function (p) { return p.date; });
    box.innerHTML = S.news.map(function (n, i) {
      var near = nearestTradingDate(n.published_at, dates);
      var d = String(n.direction || "neutral").toLowerCase();
      var arrow = d === "bullish" ? "▲" : d === "bearish" ? "▼" : "●";
      var cls = d === "bullish" ? "buy" : d === "bearish" ? "sell" : "hold";
      var when = near
        ? (near.shifted ? near.date + " (hari bursa terdekat)" : near.date)
        : "tanggal tidak tersedia";
      return "<button type='button' class='ev-item' data-i='" + i + "' aria-pressed='" +
        (S.selected === i ? "true" : "false") + "'>" +
        "<span class='ev-when'>" + esc(when) + "</span>" +
        "<span class='ev-title'>" + esc(n.title || n.article_id) + "</span>" +
        "<span class='ev-meta'><span class='chip " + cls + "'>" + arrow + " " +
          esc(d === "bullish" ? "Bullish" : d === "bearish" ? "Bearish" : "Netral") +
        "</span><span class='ev-src'>" + esc(n.source || "sumber tidak terekam") + "</span></span>" +
        "</button>";
    }).join("");
  }

  /* ---------------- 4 uji statistik ---------------- */
  var TESTS = ["spearman", "ols", "granger", "event_study"];
  function renderTests() {
    var box = $("testList");
    if (!box) return;
    var rows = S.tests.filter(function (r) { return TESTS.indexOf(r.test) !== -1; });
    if (!rows.length) {
      box.innerHTML = "";
      show("testState", "Belum ada hasil uji tersimpan. Jalankan pipeline stats dulu.");
      return;
    }
    show("testState", "");
    box.innerHTML = rows.map(function (r) {
      var sig = r.p_adjusted != null && Number(r.p_adjusted) < 0.05;
      var ci = (r.ci_low != null && r.ci_high != null)
        ? "[" + Number(r.ci_low).toFixed(2) + ", " + Number(r.ci_high).toFixed(2) + "]"
        : "tidak tersedia";
      var crosses = r.ci_low != null && r.ci_high != null &&
        Number(r.ci_low) <= 0 && Number(r.ci_high) >= 0;
      return "<div class='ev-test'>" +
        "<div class='ev-test-head'><span class='ev-test-name'>" + esc(A.testLabel(r.test)) + "</span>" +
        (r.lag != null ? "<span class='ev-test-lag'>L" + esc(r.lag) + "</span>" : "") +
        (sig ? "<span class='ev-sig'>sig</span>" : "") + "</div>" +
        "<dl class='ev-kv'>" +
        "<dt>estimasi</dt><dd>" + fmt(r.estimate, 3) + "</dd>" +
        "<dt>95% CI</dt><dd>" + ci + (crosses ? " <span class='ev-cross'>melewati nol</span>" : "") + "</dd>" +
        "<dt>p_adj</dt><dd>" + (r.p_adjusted != null ? Number(r.p_adjusted).toFixed(3) : "-") + "</dd>" +
        "<dt>n</dt><dd>" + esc(r.n_obs) + "</dd>" +
        "</dl></div>";
    }).join("");
  }

  /* ---------------- detail berita terpilih ---------------- */
  function renderSelected() {
    var box = $("selDetail");
    if (!box) return;
    if (S.selected == null) {
      box.innerHTML = "<p class='ev-empty'>Pilih satu berita di atas untuk melihat titiknya di grafik.</p>";
      return;
    }
    var n = S.news[S.selected];
    var dates = S.prices.map(function (p) { return p.date; });
    var near = nearestTradingDate(n.published_at, dates);
    var byDate = {};
    S.prices.forEach(function (p) { byDate[p.date] = Number(p.close); });
    var d = String(n.direction || "neutral").toLowerCase();
    var arrow = d === "bullish" ? "▲" : d === "bearish" ? "▼" : "●";

    box.innerHTML =
      "<h3 class='ev-sel-title'>" + esc(n.title || n.article_id) + "</h3>" +
      "<p class='ev-sel-meta'>" + esc(n.source || "sumber tidak terekam") +
        " · terbit " + esc(String(n.published_at || "tidak terekam").slice(0, 16).replace("T", " ")) + "</p>" +
      "<dl class='ev-kv'>" +
      "<dt>titik di grafik</dt><dd>" + esc(near ? near.date : "tidak tersedia") +
        (near && near.shifted ? " <span class='ev-cross'>digeser ke hari bursa terdekat</span>" : "") + "</dd>" +
      "<dt>harga saat itu</dt><dd>" + (near && byDate[near.date] != null
        ? byDate[near.date].toLocaleString("id-ID", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
        : "tidak tersedia") + "</dd>" +
      "<dt>arah dampak</dt><dd>" + arrow + " " + esc(n.direction || "netral") + "</dd>" +
      "<dt>skor</dt><dd>" + fmt(n.score) + "</dd>" +
      "<dt>keyakinan</dt><dd>" + (n.confidence != null ? Number(n.confidence).toFixed(2) : "-") + "</dd>" +
      "</dl>" +
      (n.rationale ? "<p class='ev-sel-note'>" + esc(n.rationale) + "</p>" : "");
  }

  /* ---------------- muat ---------------- */
  function isoDaysAgo(n) {
    var d = new Date(Date.now() - (n - 1) * 86400000);
    return d.toISOString().slice(0, 10);
  }

  function load() {
    var t = A.state.target;
    S.target = t;
    $("evTarget").textContent = t;
    show("chartState", "Memuat deret harga...");
    show("newsState", "Memuat berita...");
    show("testState", "Memuat hasil uji...");

    var start = isoDaysAgo(90);
    var end = new Date().toISOString().slice(0, 10);

    return Promise.all([
      A.api("/api/series/" + t + "?start_date=" + start + "&end_date=" + end)
        .then(function (p) { S.prices = (p && p.prices) || []; })
        .catch(function () { S.prices = []; }),
      A.api("/api/impacts/" + t + "?limit=40")
        .then(function (rows) {
          /* Urut terbaru dulu supaya berita yang baru masuk langsung terlihat. */
          S.news = (rows || []).slice().sort(function (a, b) {
            return String(b.published_at || "").localeCompare(String(a.published_at || ""));
          });
        })
        .catch(function () { S.news = []; }),
      A.api("/api/stats/" + t)
        .then(function (rows) { S.tests = rows || []; })
        .catch(function () { S.tests = []; })
    ]).then(function () {
      if (S.selected == null && S.news.length) S.selected = 0;
      renderNews();
      renderTests();
      renderSelected();
      drawChart();
    });
  }

  function bind() {
    $("btnReload").addEventListener("click", load);
    $("newsPicker").addEventListener("click", function (e) {
      var btn = e.target.closest(".ev-item");
      if (!btn) return;
      S.selected = Number(btn.getAttribute("data-i"));
      renderNews();
      renderSelected();
      drawChart();
    });
  }

  bind();
  A.renderPage = load;
  A.boot();
})(window.ARCAS);
