/* Research Lab: pilih berita, lihat titiknya di grafik pasar, baca uji
   statistik yang tersimpan untuk target itu.

   Halaman ini hanya fetch dan render. Semua angka dari API; tidak ada data
   contoh. Yang belum tersedia ditulis belum tersedia, bukan dikarang. */
(function (A) {
  "use strict";
  var esc = A.esc, fmt = A.fmt;

  var S = { prices: [], news: [], tests: [], selected: null };

  function $(id) { return document.getElementById(id); }

  /* Tanggal berita bisa jatuh di hari bursa tutup. Marker digeser ke tanggal
     bursa terdekat yang tersedia, dan UI menyebut pergeserannya supaya tidak
     terbaca sebagai presisi palsu. */
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

  /* ---------------- grafik harga + penanda berita ---------------- */
  var priceChart = null;
  function drawPriceChart() {
    var el = $("priceChart");
    if (!el || typeof echarts === "undefined") {
      A.showState("chartState", "Pustaka grafik lokal belum termuat.");
      return;
    }
    if (!priceChart) {
      priceChart = echarts.init(el);
      window.addEventListener("resize", function () { if (priceChart) priceChart.resize(); });
    }
    if (!S.prices.length) {
      priceChart.clear();
      A.showState("chartState", "Belum ada deret harga untuk target ini.");
      return;
    }
    A.showState("chartState", "");

    var dates = S.prices.map(function (p) { return p.date; });
    var closes = S.prices.map(function (p) { return Number(p.close); });
    var byDate = {};
    S.prices.forEach(function (p) { byDate[p.date] = Number(p.close); });

    /* Semua berita jadi titik kecil; yang terpilih jadi pin besar + garis. */
    var dots = [];
    S.news.forEach(function (n) {
      var near = nearestTradingDate(n.published_at, dates);
      if (!near) return;
      dots.push({
        value: [near.date, byDate[near.date]],
        name: n.title || n.article_id,
        itemStyle: {
          color: n.direction === "bearish" ? "#FF7B72"
            : n.direction === "bullish" ? "#56D364" : "#BDB7B7"
        }
      });
    });

    var series = [{
      name: "Harga tutup", type: "line", data: closes, showSymbol: false,
      lineStyle: { width: 2.2, color: "#FFD33D" }, itemStyle: { color: "#FFD33D" }
    }, {
      name: "Berita", type: "scatter", data: dots, symbolSize: 9,
      itemStyle: { borderColor: "#3E3939", borderWidth: 1 }
    }];

    var sel = S.news[S.selected];
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

    priceChart.setOption({
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

  /* ---------------- pemilih berita ---------------- */
  function renderNews() {
    var box = $("newsPicker");
    if (!box) return;
    if (!S.news.length) {
      box.innerHTML = "";
      A.showState("newsState", "Belum ada berita untuk target ini. Tarik berita dulu lewat news_cli fetch.");
      return;
    }
    A.showState("newsState", "");
    var dates = S.prices.map(function (p) { return p.date; });
    box.innerHTML = S.news.map(function (n, i) {
      var near = nearestTradingDate(n.published_at, dates);
      var d = String(n.direction || "neutral").toLowerCase();
      var arrow = d === "bullish" ? "▲" : d === "bearish" ? "▼" : "●";
      var cls = d === "bullish" ? "buy" : d === "bearish" ? "sell" : "hold";
      var when = near
        ? (near.shifted ? near.date + " (hari bursa terdekat)" : near.date)
        : "tanggal tidak tersedia";
      return "<button type='button' class='rl-item' data-i='" + i + "' aria-pressed='" +
        (S.selected === i ? "true" : "false") + "'>" +
        "<span class='rl-when'>" + esc(when) + "</span>" +
        "<span class='rl-title'>" + esc(n.title || n.article_id) + "</span>" +
        "<span class='rl-meta'><span class='chip " + cls + "'>" + arrow + " " +
          esc(d === "bullish" ? "Bullish" : d === "bearish" ? "Bearish" : "Netral") +
        "</span><span class='rl-src'>" + esc(n.source || "sumber tidak terekam") + "</span></span>" +
        "</button>";
    }).join("");
  }

  /* ---------------- detail berita terpilih ---------------- */
  function renderSelected() {
    var box = $("selDetail");
    if (!box) return;
    /* S.selected bisa menunjuk indeks yang tidak ada lagi setelah ganti target. */
    if (S.selected == null || !S.news[S.selected]) {
      box.innerHTML = "<p class='rl-empty'>Pilih satu berita di atas untuk melihat titiknya di grafik.</p>";
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
      "<h3 class='rl-sel-title'>" + esc(n.title || n.article_id) + "</h3>" +
      "<p class='rl-sel-meta'>" + esc(n.source || "sumber tidak terekam") +
        " · terbit " + esc(String(n.published_at || "tidak terekam").slice(0, 16).replace("T", " ")) + "</p>" +
      "<dl class='rl-kv'>" +
      "<dt>titik di grafik</dt><dd>" + esc(near ? near.date : "tidak tersedia") +
        (near && near.shifted ? " <span class='rl-cross'>digeser ke hari bursa terdekat</span>" : "") + "</dd>" +
      "<dt>harga saat itu</dt><dd>" + (near && byDate[near.date] != null
        ? byDate[near.date].toLocaleString("id-ID", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
        : "tidak tersedia") + "</dd>" +
      "<dt>arah dampak</dt><dd>" + arrow + " " + esc(n.direction || "netral") + "</dd>" +
      "<dt>skor</dt><dd>" + fmt(n.score) + "</dd>" +
      "<dt>keyakinan</dt><dd>" + (n.confidence != null ? Number(n.confidence).toFixed(2) : "-") + "</dd>" +
      "</dl>" +
      (n.rationale ? "<p class='rl-sel-note'>" + esc(n.rationale) + "</p>" : "");
  }

  /* ---------------- uji statistik ---------------- */
  var TESTS = ["spearman", "ols", "granger", "event_study"];
  function renderTests() {
    var box = $("testList");
    if (!box) return;
    var rows = S.tests.filter(function (r) { return TESTS.indexOf(r.test) !== -1; });
    if (!rows.length) {
      box.innerHTML = "";
      A.showState("testState", "Belum ada hasil uji tersimpan. Jalankan `cli stats` dulu agar panel terisi.");
      return;
    }
    A.showState("testState", "");
    /* Uji yang belum dihitung disebut namanya. Tanpa ini, panel terbaca
       seolah dua uji itulah seluruh rangkaian yang dirancang. */
    var missing = TESTS.filter(function (t) {
      return !rows.some(function (r) { return r.test === t; });
    });
    box.innerHTML = rows.map(function (r) {
      var sig = r.p_adjusted != null && Number(r.p_adjusted) < 0.05;
      var ci = (r.ci_low != null && r.ci_high != null)
        ? "[" + Number(r.ci_low).toFixed(2) + ", " + Number(r.ci_high).toFixed(2) + "]"
        : "tidak tersedia";
      var crosses = r.ci_low != null && r.ci_high != null &&
        Number(r.ci_low) <= 0 && Number(r.ci_high) >= 0;
      return "<div class='rl-test'>" +
        "<div class='rl-test-head'><span class='rl-test-name'>" + esc(A.testLabel(r.test)) + "</span>" +
        (r.lag != null ? "<span class='rl-test-lag'>L" + esc(r.lag) + "</span>" : "") +
        (sig ? "<span class='rl-sig'>sig</span>" : "") + "</div>" +
        "<dl class='rl-kv'>" +
        "<dt>estimasi</dt><dd>" + fmt(r.estimate, 3) + "</dd>" +
        "<dt>95% CI</dt><dd>" + ci + (crosses ? " <span class='rl-cross'>melewati nol</span>" : "") + "</dd>" +
        "<dt>p_adj</dt><dd>" + (r.p_adjusted != null ? Number(r.p_adjusted).toFixed(3) : "-") + "</dd>" +
        "<dt>n</dt><dd>" + esc(r.n_obs) + "</dd>" +
        "</dl></div>";
    }).join("") +
    (missing.length
      ? "<p class='rl-sel-note' style='color:var(--on-dark-muted)'>Belum dihitung untuk target ini: " +
        esc(missing.map(function (t) { return A.testLabel(t); }).join(", ")) +
        ". Tidak ada angkanya di sini karena memang belum ada.</p>"
      : "");
  }

  /* ---------------- muat ---------------- */
  function loadData() {
    var t = A.state.target;
    A.showState("chartState", "Memuat deret harga...");
    A.showState("newsState", "Memuat berita...");
    A.showState("testState", "Memuat hasil uji...");

    var start = new Date(Date.now() - 89 * 86400000).toISOString().slice(0, 10);
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
      /* Indeks terpilih hanya bermakna di dalam satu target. Tanpa reset,
         pindah target bisa menunjuk kartu yang tidak ada. */
      S.selected = S.news.length ? 0 : null;
      renderNews();
      renderSelected();
      renderTests();
      drawPriceChart();
    });
  }

  /* ---------------- kontrol ----------------
     Scrollbar disembunyikan karena bar abu di bawah kartu terlihat seperti
     salah layout. Konsekuensinya penggeseran harus disediakan sendiri:
     roda mouse (vertikal dipetakan ke horizontal) dan seret dengan pointer.
     Tanpa ini, kartu di luar layar tidak bisa dijangkau di desktop. */
  var picker = $("newsPicker");
  var drag = { on: false, x: 0, left: 0, moved: false, endedAt: 0 };

  picker.addEventListener("wheel", function (e) {
    if (picker.scrollWidth <= picker.clientWidth) return;
    if (Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return;
    picker.scrollLeft += e.deltaY;
    e.preventDefault();
  }, { passive: false });

  picker.addEventListener("pointerdown", function (e) {
    /* Sentuhan sudah digeser sendiri oleh browser; menyeret manual di sini
       akan merebut gestur gulir bawaan. */
    if (e.button !== 0 || e.pointerType !== "mouse") return;
    drag.on = true; drag.moved = false;
    drag.x = e.clientX; drag.left = picker.scrollLeft;
  });
  picker.addEventListener("pointermove", function (e) {
    if (!drag.on) return;
    var dx = e.clientX - drag.x;
    if (!drag.moved && Math.abs(dx) > 3) {
      drag.moved = true;
      /* Kelas baru dipasang setelah gerakan nyata. Kalau dipasang sejak
         pointerdown, anak-anak kartu kehilangan pointer-events dan klik
         biasa mendarat di wadah, bukan di kartunya. */
      picker.classList.add("is-dragging");
    }
    if (drag.moved) picker.scrollLeft = drag.left - dx;
  });
  function endDrag() {
    if (!drag.on) return;
    drag.on = false;
    if (drag.moved) drag.endedAt = Date.now();
    picker.classList.remove("is-dragging");
  }
  picker.addEventListener("pointerup", endDrag);
  picker.addEventListener("pointercancel", endDrag);
  picker.addEventListener("pointerleave", endDrag);

  picker.addEventListener("click", function (e) {
    /* Klik yang lahir dari seret diabaikan berdasarkan waktu, bukan flag yang
       bisa tertinggal menyala kalau event click tidak pernah datang. */
    if (Date.now() - drag.endedAt < 200) return;
    var btn = e.target.closest(".rl-item");
    if (!btn) return;
    S.selected = Number(btn.getAttribute("data-i"));
    renderNews();
    renderSelected();
    drawPriceChart();
  });

  A.renderPage = loadData;
  A.boot();
})(window.ARCAS);
