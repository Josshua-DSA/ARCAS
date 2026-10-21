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

    A.$("targetMeta").textContent = "Target: " + A.state.target + " : " + info.name + " (" + info.ticker + ")";
    A.$("rangeMeta").textContent = "Rentang: " + A.state.days + " hari terakhir";
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
    var last = scores.filter(function (v) { return v !== null; }).slice(-1)[0];
    A.$("heroKicker").textContent = "Ringkasan " + A.state.target + " : skor terakhir " + (last == null ? "n/a (hari tanpa berita)" : A.fmt(last) + (last > 0.1 ? " condong bullish" : last < -0.1 ? " condong bearish" : " netral"));
  }

  function isoDaysAgo(n) { return new Date(Date.now() - (n - 1) * 86400000).toISOString().slice(0, 10); }

  /* Berita teratas: tabel tiga baris dari dampak terbaru. Card lengkap + bukti
     ada di halaman Evidence; pembawa query mengetahui target/rentang aktif. */
  function renderTop(rows) {
    var top = (rows || []).slice(0, 3);
    var box = A.$("topList");
    box.innerHTML = top.length ? "<table class='data'><thead><tr><th>Judul</th><th>Arah</th><th>Conf</th></tr></thead><tbody>" +
      top.map(function (t) {
        var cls = String(t.direction) === "bullish" ? "pos" : String(t.direction) === "bearish" ? "neg" : "flat";
        var arrow = String(t.direction) === "bullish" ? "▲" : String(t.direction) === "bearish" ? "▼" : "●";
        return "<tr><td>" + esc((t.title || t.article_id).slice(0, 64)) + "</td><td class='" + cls + "'>" + arrow + " " + esc(t.direction) + "</td><td>" + esc(Number(t.confidence || 0).toFixed(2)) + "</td></tr>";
      }).join("") + "</tbody></table>"
      : "";
    A.showState("topState", top.length ? "" : "Belum ada berita berdampak.");
    var kicker = A.$("topKick");
    if (kicker) kicker.textContent = "menampilkan 3 teratas" + ((rows || []).length > top.length ? " dari " + rows.length + " dampak" : "");
  }

  function renderAll() {
    var t = A.state.target;
    var end = new Date().toISOString().slice(0, 10);
    var start = isoDaysAgo(A.state.days);
    A.showState("chartState", "Memuat deret " + t + "...");
    A.showState("statState", "Memuat uji statistik...");
    A.showState("allocState", "Memuat strip alokasi...");
    A.showState("topState", "Memuat berita teratas...");

    A.api("/api/series/" + t + "?start_date=" + start + "&end_date=" + end).then(function (payload) {
      A.state.apiOk = true; A.setStatus("ok", "terhubung ke API");
      renderChart(payload);
    }).catch(function () {
      A.state.apiOk = false; A.setStatus("warn", "API tidak terjangkau : ilustrasi");
      renderChart(A.demoSeries(t, A.state.days));
    });

    A.api("/api/stats/" + t).then(function (rows) { A.renderStats(rows, "Belum ada hasil uji untuk target ini. Jalankan pipeline analyze dulu."); })
      .catch(function () {
        A.renderStats([{ test: "spearman", market_metric: "return", lag: 1, estimate: 0.18, p_value: 0.04, p_adjusted: 0.09, n_obs: 62, period_start: "2026-07-15", period_end: "2026-10-12" }, { test: "ols", market_metric: "return", lag: 1, estimate: 0.11, p_value: 0.07, p_adjusted: 0.12, n_obs: 62, period_start: "2026-07-15", period_end: "2026-10-12" }, { test: "granger", market_metric: "return", lag: 2, estimate: 3.4, p_value: 0.06, p_adjusted: 0.11, n_obs: 60, period_start: "2026-07-15", period_end: "2026-10-12" }, { test: "event_study", market_metric: "abnormal_return", lag: 0, estimate: 0.006, p_value: 0.03, p_adjusted: 0.08, n_obs: 18, period_start: "2026-08-01", period_end: "2026-10-12" }]);
        /* Setelah renderStats, bukan sebelum: renderStats mengosongkan state di awal. */
        A.showState("statState", "API statistik tidak terjangkau : tabel ini ilustrasi berlabel, bukan hasil uji nyata.");
      });

    A.api("/api/allocation?profile_id=" + A.state.profile + "&article_id=current_market").then(A.renderAllocation)
      .catch(function () {
        A.renderAllocation({ lines: [
          { alloc_class: "bond", baseline_pct: 40, new_pct: 42, delta_pp: 2, confidence: 0.7 },
          { alloc_class: "mutual_fund", baseline_pct: 15, new_pct: 15, delta_pp: 0, confidence: 0.5 },
          { alloc_class: "stock", baseline_pct: 15, new_pct: 14, delta_pp: -1, confidence: 0.65 },
          { alloc_class: "etf", baseline_pct: 20, new_pct: 19, delta_pp: -1, confidence: 0.8 },
          { alloc_class: "btc", baseline_pct: 5, new_pct: 5, delta_pp: 0, confidence: 0.4 },
          { alloc_class: "gold", baseline_pct: 5, new_pct: 5, delta_pp: 0, confidence: 0.7 }
        ]});
        A.showState("allocState", "API alokasi tidak terjangkau, ilustrasi berlabel (total tetap 100%).");
      });

    A.api("/api/impacts/" + t + "?limit=6").then(renderTop)
      .catch(function () { renderTop(A.demoImpacts(t)); });
  }

  A.renderPage = renderAll;
  A.boot("Ringkasan hari ini : data berjalan");
})(window.ARCAS);
