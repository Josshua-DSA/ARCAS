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

    /* Elemen legenda bisa tidak ada (mis. halaman lain memuat skrip ini).
       Tanpa penjaga, renderChart melempar TypeError dan grafik tidak pernah
       digambar sama sekali. */
    var lg = A.$("lgPrice");
    if (lg) lg.style.background = info.color;

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

  /* Tanggal lokal, bukan UTC: lihat catatan A.localISO di api.js. */
  function isoDaysAgo(n) { return A.localISO(new Date(Date.now() - (n - 1) * 86400000)); }

  /* Daftar berita + paginasi 5 per halaman. Halaman disimpan di memori;
     mengubah target/rentang mengembalikan ke halaman 1. */
  var newsPage = 1;
  var newsRows = [];
  var NEWS_PER_PAGE = 5;

  /* Tidak ada lagi berita ilustrasi. Dulu NEWS_DEMO mengisi kekurangan data
     API dengan berita karangan; itu bertabrakan dengan prinsip halaman lain
     yang selalu melabeli data palsu. Berita sekarang hanya dari API -- kalau
     kosong, tampilkan pesan apa adanya. */

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
    /* Judul menjadi tautan ke sumber asli bila URL tersedia. rel noopener
       wajib: tanpa itu halaman tujuan bisa mengakses window.opener. */
    var head = t.url
      ? "<a href='" + esc(t.url) + "' target='_blank' rel='noopener noreferrer' class='news-link'>" + esc(title) + "</a>"
      : esc(title);
    return "<article class='news-item'>" +
      "<h3>" + head + "</h3>" +
      (t.rationale ? "<p class='news-note'>" + esc(t.rationale) + "</p>" : "") +
      "<div class='news-top'><span class='chip " + cls + "'>" + arrow + " " + label + "</span>" +
      (Number(t.headline_only) === 1 ? "<span class='chip hold'>Headline saja</span>" : "") +
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

  /* Berita murni dari API. Tidak ada padding karangan: bila API mengirim
     sedikit, tampilkan sedikit; bila kosong, katakan kosong. `isError`
     membedakan "API mati" dari "API hidup tapi belum ada berita" -- dua
     hal berbeda yang dulu sama-sama diisi NEWS_DEMO. */
  function renderNews(rows, isError) {
    newsRows = rows || [];
    newsPage = 1;
    renderNewsPage();
    if (isError) {
      A.showState("newsState", "API berita tidak terjangkau : tidak ada berita untuk ditampilkan (bukan ilustrasi).");
    } else if (!newsRows.length) {
      A.showState("newsState", "Belum ada berita untuk target ini. Jalankan pipeline ingest/analyze dulu.");
    } else {
      A.showState("newsState", "");
    }
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

  /* Penjaga urutan + pembatalan (race condition). renderAll dipanggil ulang
     setiap target/rentang/profil berubah. Tanpa ini, ganti target cepat
     (XAU -> SPX -> RATE_UST) membuat tiga set request berjalan bersamaan dan
     respons yang tiba TERAKHIR menang -- bisa XAU menimpa grafik RATE_UST.
     Dua lapis: AbortController membatalkan request lama, dan `seq` memastikan
     respons yang sudah terlanjur masuk tidak menyentuh DOM. */
  var seq = 0;
  var inFlight = null;

  /* Cap waktu preload terakhir: menjawab "data ini setua apa?" tanpa
     mengarang. Sumbernya /api/preload/status (tabel ingest_runs). */
  function renderPreloadStamp(info) {
    var el = A.$("preloadStamp");
    if (!el) return;
    var last = info && info.last;
    if (!last) { el.textContent = ""; return; }
    var when = A.fmtDate(last.finished_at);
    var n = Number(last.raw_new) || 0;
    el.textContent = when
      ? "preload terakhir " + when + " · " + n + " berita baru"
      : "";
  }

  function loadPreloadStamp(signal, live) {
    A.api("/api/preload/status", signal).then(function (info) {
      if (!live()) return;
      renderPreloadStamp(info);
    }).catch(function (err) {
      if ((err && err.name === "AbortError") || !live()) return;
      var el = A.$("preloadStamp");
      if (el) el.textContent = "";
    });
  }

  function renderAll() {
    var t = A.state.target;
    var end = A.localISO(new Date());
    var start = isoDaysAgo(A.state.days);

    if (inFlight) inFlight.abort();
    var ctrl = typeof AbortController !== "undefined" ? new AbortController() : null;
    inFlight = ctrl;
    var mySeq = ++seq;
    var signal = ctrl ? { signal: ctrl.signal } : undefined;
    /* Masih render terbaru? Dipakai sebelum menyentuh DOM mana pun. */
    var live = function () { return mySeq === seq; };

    A.showState("chartState", "Memuat deret " + t + "...");
    A.showState("allocState", "Memuat strip alokasi...");
    A.showState("newsState", "Memuat berita...");

    A.api("/api/series/" + t + "?start_date=" + start + "&end_date=" + end, signal).then(function (payload) {
      if (!live()) return;
      A.state.apiOk = true; A.state.apiReachable = true; A.setStatus("ok", "terhubung ke API");
      renderChart(payload);
    }).catch(function (err) {
      if (!live() || (err && err.name === "AbortError")) return;
      A.state.apiOk = false; A.setStatus("err", "API tidak terjangkau : ilustrasi");
      renderChart(A.demoSeries(t, A.state.days));
    });

    A.api("/api/allocation?profile_id=" + A.state.profile + "&article_id=current_market", signal).then(function (payload) {
      if (!live()) return;
      A.renderAllocation(payload);
    }).catch(function (err) {
      if (!live() || (err && err.name === "AbortError")) return;
      /* Tidak ada alokasi karangan: strip kosong + pesan apa adanya. */
      A.renderAllocation({ lines: [] });
      A.showState("allocState", "API alokasi tidak terjangkau : tidak ada angka alokasi untuk ditampilkan (bukan ilustrasi).");
    });

    loadPreloadStamp(signal, live);
    A.api("/api/impacts/" + t + "?limit=60", signal).then(function (rows) {
      if (!live()) return;
      renderNews(rows, false);
    }).catch(function (err) {
      if (!live() || (err && err.name === "AbortError")) return;
      renderNews([], true);
    });
  }

  bindPager();
  A.renderPage = renderAll;
  A.boot();
})(window.ARCAS);
