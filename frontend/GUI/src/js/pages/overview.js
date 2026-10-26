/* Market Overview (Upgrade.md 3): grafik harga vs sentimen, statistik ringkas,
   strip alokasi profil aktif, dan berita teratas. Detail penuh ada di halaman
   lain (research, evidence, simulations). Halaman ini hanya fetch dan render. */
(function (A) {
  "use strict";
  var esc = A.esc;

  /* Grafik dual-axis. Alasan ECharts lokal: nol dependensi jaringan saat sidang. */
  var chart = null;
  function ensureChart() {
    if (chart || typeof echarts === "undefined") return;
    chart = echarts.init(A.$("chart"));
    window.addEventListener("resize", function () { if (chart) chart.resize(); });
  }
  function renderChart(payload) {
    ensureChart();
    var info = A.metaFor(A.state.target);
    var byDate = {};
    (payload.sentiments || []).forEach(function (s) { byDate[s.date] = byDate[s.date] || {}; byDate[s.date].score = s.score_mean; byDate[s.date].n = s.n_articles; });
    (payload.prices || []).forEach(function (p) { byDate[p.date] = byDate[p.date] || {}; byDate[p.date].close = p.close; });
    var dates = Object.keys(byDate).sort();
    var closes = dates.map(function (d) { var v = byDate[d].close; return v == null ? null : Math.round(v * 100) / 100; });
    var scores = dates.map(function (d) { var v = byDate[d].score; return v == null ? null : Math.round(v * 1000) / 1000; });
    var gapCount = scores.filter(function (v) { return v === null; }).length;

    A.$("lgPrice").style.background = info.color;

    if (!chart) { A.showState("chartState", "Pustaka grafik lokal belum termuat (src/js/echarts.min.js). Periksa path file."); return; }
    if (!dates.length) { A.showState("chartState", "Belum ada deret untuk target ini pada rentang terpilih."); chart.clear(); return; }
    A.showState("chartState", gapCount ? gapCount + " hari tanpa berita tampil sebagai jeda (bukan nol)." : "");

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
  }

  function isoDaysAgo(n) { return new Date(Date.now() - (n - 1) * 86400000).toISOString().slice(0, 10); }

  /* Daftar berita + paginasi 5 per halaman. Halaman disimpan di memori;
     mengubah target/rentang mengembalikan ke halaman 1. */
  var newsPage = 1;
  var newsRows = [];
  var NEWS_PER_PAGE = 5;

  function newsItem(t) {
    var d = String(t.direction || "neutral").toLowerCase();
    var cls = d === "bullish" ? "buy" : d === "bearish" ? "sell" : "hold";
    var arrow = d === "bullish" ? "▲" : d === "bearish" ? "▼" : "●";
    var label = d === "bullish" ? "Bullish" : d === "bearish" ? "Bearish" : "Netral";
    var title = t.title || t.article_id;
    return "<article class='news-card'>" +
      "<div class='news-meta'><span>" + esc(t.source || "sumber belum terekam") + "</span>" +
      "<span>" + esc(A.fmtDate(t.published_at) || "tanggal belum terekam") + "</span>" +
      "<span class='chip " + cls + "'>" + arrow + " " + label + "</span></div>" +
      "<h3>" + esc(title) + "</h3>" +
      (t.rationale ? "<p class='news-note'>" + esc(t.rationale) + "</p>" : "") +
      "</article>";
  }

  function renderPager() {
    var pager = A.$("newsPager");
    if (!pager) return;
    var pages = Math.ceil(newsRows.length / NEWS_PER_PAGE);
    if (pages <= 1) { pager.hidden = true; pager.innerHTML = ""; return; }
    var buttons = [];
    for (var i = 1; i <= pages; i++) {
      buttons.push("<button type='button' class='pager-btn' data-page-no='" + i + "'" +
        (i === newsPage ? " aria-current='page'" : "") + ">" + i + "</button>");
    }
    pager.innerHTML = "<button type='button' class='pager-btn' data-step='-1'" +
      (newsPage === 1 ? " disabled" : "") + " aria-label='Halaman sebelumnya'>Sebelumnya</button>" +
      buttons.join("") +
      "<button type='button' class='pager-btn' data-step='1'" +
      (newsPage === pages ? " disabled" : "") + " aria-label='Halaman berikutnya'>Berikutnya</button>";
    pager.hidden = false;
  }

  function renderNewsPage() {
    var box = A.$("newsList");
    if (!box) return;
    var from = (newsPage - 1) * NEWS_PER_PAGE;
    var slice = newsRows.slice(from, from + NEWS_PER_PAGE);
    box.innerHTML = slice.length ? slice.map(newsItem).join("")
      : "<p class='hint'>Tidak ada berita pada halaman ini.</p>";
    var kick = A.$("newsKick");
    if (kick) {
      kick.textContent = newsRows.length
        ? "menampilkan " + (from + 1) + "-" + (from + slice.length) + " dari " + newsRows.length
        : "belum ada berita";
    }
    renderPager();
  }

  function renderNews(rows) {
    newsRows = rows || [];
    newsPage = 1;
    A.showState("newsState", newsRows.length ? "" : "Belum ada berita terkumpul untuk target ini.");
    renderNewsPage();
  }

  function bindPager() {
    var pager = A.$("newsPager");
    if (!pager) return;
    pager.addEventListener("click", function (e) {
      var btn = e.target.closest("button[data-page-no],button[data-step]");
      if (!btn || btn.disabled) return;
      var pages = Math.ceil(newsRows.length / NEWS_PER_PAGE);
      if (btn.dataset.pageNo) newsPage = Number(btn.dataset.pageNo);
      else newsPage = Math.min(pages, Math.max(1, newsPage + Number(btn.dataset.step)));
      renderNewsPage();
    });
  }

  function renderAll() {
    var t = A.state.target;
    var end = new Date().toISOString().slice(0, 10);
    var start = isoDaysAgo(A.state.days);
    A.showState("chartState", "Memuat deret " + t + "...");
    A.showState("allocState", "Memuat strip alokasi...");
    A.showState("newsState", "Memuat berita...");

    A.api("/api/series/" + t + "?start_date=" + start + "&end_date=" + end).then(function (payload) {
      A.state.apiOk = true; A.state.apiReachable = true; A.setStatus("ok", "terhubung ke API");
      renderChart(payload);
    }).catch(function () {
      A.state.apiOk = false; A.setStatus("err", "API tidak terjangkau : ilustrasi");
      renderChart(A.demoSeries(t, A.state.days));
    });

    A.api("/api/allocation?profile_id=" + A.state.profile + "&article_id=current_market").then(A.renderAllocation)
      .catch(function () {
        A.renderAllocation({ lines: [
          { alloc_class: "bond", baseline_pct: 40, new_pct: 42, delta_pp: 2, confidence: 0.7 },
          { alloc_class: "mutual_fund", baseline_pct: 15, new_pct: 15, delta_pp: 0, confidence: 0.5 },
          { alloc_class: "stock", baseline_pct: 15, new_pct: 14, delta_pp: -1, confidence: 0.65 },
          { alloc_class: "etf", baseline_pct: 20, new_pct: 19, delta_pp: -1, confidence: 0.8 },
          { alloc_class: "gold", baseline_pct: 5, new_pct: 5, delta_pp: 0, confidence: 0.7 }
        ]});
        A.showState("allocState", "API alokasi tidak terjangkau, ilustrasi berlabel (total tetap 100%).");
      });

    A.api("/api/impacts/" + t + "?limit=60").then(renderNews)
      .catch(function () {
        renderNews(A.demoImpacts(t));
        A.showState("newsState", "API berita tidak terjangkau : daftar ini ilustrasi berlabel.");
      });
  }

  bindPager();
  A.renderPage = renderAll;
  A.boot();
})(window.ARCAS);
