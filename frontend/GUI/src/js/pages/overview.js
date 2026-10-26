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

  /* Ilustrasi berlabel: dipakai hanya saat API mengirim kurang dari 5 berita,
     supaya daftar tidak tampil kosong. Tidak pernah dicampur dengan data API. */
  var NEWS_DEMO = [
    { article_id: "ilustrasi-01", direction: "bullish", source: "Contoh Redaksi", published_at: "2026-10-12",
      title: "The Fed memberi sinyal pemangkasan suku bunga pada kuartal berikutnya",
      rationale: "Nada dovish menekan imbal hasil obligasi dan menopang emas sebagai aset lindung nilai." },
    { article_id: "ilustrasi-02", direction: "bearish", source: "Contoh Redaksi", published_at: "2026-10-11",
      title: "Inflasi inti Amerika bertahan di atas target dua persen",
      rationale: "Data panas menunda ekspektasi pelonggaran, sehingga yield tenor panjang kembali naik." },
    { article_id: "ilustrasi-03", direction: "bullish", source: "Contoh Redaksi", published_at: "2026-10-10",
      title: "Laba emiten teknologi melampaui perkiraan analis",
      rationale: "Hasil kuartalan yang kuat mengangkat indeks acuan dan memperbaiki selera risiko." },
    { article_id: "ilustrasi-04", direction: "bearish", source: "Contoh Redaksi", published_at: "2026-10-09",
      title: "Ketegangan dagang kembali memunculkan kekhawatiran perlambatan",
      rationale: "Kekhawatiran pertumbuhan mendorong arus dana keluar dari aset berisiko menuju obligasi pemerintah." },
    { article_id: "ilustrasi-05", direction: "neutral", source: "Contoh Redaksi", published_at: "2026-10-08",
      title: "Pasar menanti rilis data tenaga kerja akhir pekan ini",
      rationale: "Belum ada kejutan berarti, pelaku pasar memilih menahan posisi sampai angka utama keluar." },
    { article_id: "ilustrasi-06", direction: "bullish", source: "Contoh Redaksi", published_at: "2026-10-07",
      title: "Bank sentral menambah cadangan emas untuk kuartal ketiga berturut-turut",
      rationale: "Permintaan bank sentral menjadi penopang struktural harga emas di tengah suku bunga tinggi." }
  ];

  function newsItem(t) {
    var d = String(t.direction || "neutral").toLowerCase();
    var cls = d === "bullish" ? "buy" : d === "bearish" ? "sell" : "hold";
    var arrow = d === "bullish" ? "▲" : d === "bearish" ? "▼" : "●";
    var label = d === "bullish" ? "Bullish" : d === "bearish" ? "Bearish" : "Netral";
    var title = t.title || t.article_id;
    var meta = [];
    if (t.source) meta.push("<span>" + esc(t.source) + "</span>");
    var when = A.fmtDate(t.published_at);
    if (when) meta.push("<span>" + esc(when) + "</span>");
    return "<article class='news-item'>" +
      "<h3>" + esc(title) + "</h3>" +
      (t.rationale ? "<p class='news-note'>" + esc(t.rationale) + "</p>" : "") +
      "<div class='news-top'><span class='chip " + cls + "'>" + arrow + " " + label + "</span>" +
      (t._demo ? "<span class='chip hold'>Ilustrasi</span>" : "") +
      (meta.length ? "<span class='news-src'>" + meta.join(" · ") + "</span>" : "") +
      "</div></article>";
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
    var real = rows || [];
    if (real.length < NEWS_PER_PAGE) {
      var pad = NEWS_DEMO.slice(0, NEWS_PER_PAGE - real.length).map(function (d) {
        d._demo = true;
        return d;
      });
      newsRows = real.concat(pad);
      newsPage = 1;
      renderNewsPage();
      A.showState("newsState", "API hanya mengirim " + real.length +
        " berita : sisanya ilustrasi berlabel.");
      return;
    }
    newsRows = real;
    newsPage = 1;
    A.showState("newsState", "");
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
