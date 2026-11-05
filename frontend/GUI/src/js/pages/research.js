/* Research Lab: pilih berita, lihat titiknya di grafik pasar, baca uji
   statistik yang tersimpan untuk target itu.

   Halaman ini hanya fetch dan render. Semua angka dari API; tidak ada data
   contoh. Yang belum tersedia ditulis belum tersedia, bukan dikarang. */
(function (A) {
  "use strict";
  var esc = A.esc, fmt = A.fmt;

  var S = { prices: [], news: [], tests: [], selected: null };

  function $(id) { return document.getElementById(id); }

  /* ---------------- perapian daftar uji ----------------

     `stat_results` menyimpan baris kembar persis: menjalankan ulang `cli
     stats` menambah baris baru tanpa membuang yang lama. Untuk XAU itu berarti
     28 baris padahal hanya 24 kombinasi (uji, lag, estimate, p_adj, n) yang
     berbeda -- tabel menampilkan uji yang sama dua kali dan pembaca mengira
     rangkaiannya lebih panjang dari kenyataan.

     Kunci dedup memakai nilai yang benar-benar tampil di baris, bukan run_id:
     dua baris identik dari run berbeda adalah satu bukti yang sama.
     `JSON.stringify` memisahkan null dari 0, jadi p_adj null tidak tertukar
     dengan p_adj 0. */
  function dedupUji(rows) {
    var terlihat = {}, hasil = [];
    (rows || []).forEach(function (r) {
      var kunci = JSON.stringify([r.test, r.market_metric, r.lag,
        r.estimate, r.p_adjusted, r.n_obs, r.ci_low, r.ci_high]);
      if (terlihat[kunci]) return;
      terlihat[kunci] = true;
      hasil.push(r);
    });
    return hasil;
  }

  /* Urut berdasarkan kekuatan bukti: p_adj terkecil dulu, yang tidak punya
     p_adj paling bawah. Di 24 baris mono 10px, dua baris signifikan tenggelam
     kalau urutannya mengikuti jenis uji. Pengurutan stabil supaya dua baris
     setara tidak bertukar posisi tiap kali target diganti. */
  function urutUji(rows) {
    return (rows || []).map(function (r, i) { return { r: r, i: i }; })
      .sort(function (a, b) {
        var pa = a.r.p_adjusted == null ? Infinity : Number(a.r.p_adjusted);
        var pb = b.r.p_adjusted == null ? Infinity : Number(b.r.p_adjusted);
        if (pa !== pb) return pa - pb;
        return a.i - b.i;
      })
      .map(function (x) { return x.r; });
  }

  /* Rentang n_obs untuk kalimat pengingat sampel kecil. Baris tanpa n_obs
     dilewati, bukan dihitung nol: nol akan menakut-nakuti tanpa alasan. */
  function minN(rows) {
    var v = rows.map(function (r) { return r.n_obs; })
      .filter(function (n) { return n != null && isFinite(Number(n)); })
      .map(Number);
    return v.length ? Math.min.apply(null, v) : "?";
  }
  function maxN(rows) {
    var v = rows.map(function (r) { return r.n_obs; })
      .filter(function (n) { return n != null && isFinite(Number(n)); })
      .map(Number);
    return v.length ? Math.max.apply(null, v) : "?";
  }

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
  /* Ambang signifikansi. p_adj 0.049 dan 0.051 tampil sama sebagai 0.05 di
     UI, jadi statusnya dihitung dari nilai mentah, bukan dari angka bulat. */
  var SIG_AMBANG = 0.05;

  function renderTests() {
    var box = $("testList");
    if (!box) return;
    /* Urutan: dedup dulu (baris kembar dari run berulang), baru urut menurut
       kekuatan bukti. Membalik urutannya membuat dedup memilih wakil yang
       salah saat nilai yang sama muncul dari run berbeda. */
    var rows = urutUji(dedupUji(S.tests.filter(function (r) {
      return TESTS.indexOf(r.test) !== -1;
    })));
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
    /* Baris no. 1 adalah bukti terkuat; urutan mengikuti p_adj, bukan jenis
       uji (lihat urutUji). */
    box.innerHTML =
      "<div class='rl-test rl-test--head' aria-hidden='true'>" +
        "<span>uji</span><span>lag</span><span class='rl-test-num'>est</span>" +
        "<span>95% CI</span><span class='rl-test-num'>p_adj</span>" +
        "<span class='rl-test-num'>n</span><span></span></div>" +
      rows.map(function (r) {
        var sig = r.p_adjusted != null && Number(r.p_adjusted) < SIG_AMBANG;
        /* Granger tidak punya CI: tulis "—", bukan "tidak tersedia" per baris,
           supaya daftar 11 uji tetap terbaca. */
        var ci = (r.ci_low != null && r.ci_high != null)
          ? "[" + Number(r.ci_low).toFixed(2) + ", " + Number(r.ci_high).toFixed(2) + "]"
          : "—";
        var crosses = r.ci_low != null && r.ci_high != null &&
          Number(r.ci_low) <= 0 && Number(r.ci_high) >= 0;
        return "<div class='rl-test'>" +
          "<span class='rl-test-name'>" + esc(A.testLabel(r.test)) + "</span>" +
          "<span class='rl-test-lag'>" + (r.lag != null ? "L" + esc(r.lag) : "—") + "</span>" +
          "<span class='rl-test-num'>" + fmt(r.estimate, 3) + "</span>" +
          "<span class='rl-test-ci" + (crosses ? " rl-cross" : "") + "'>" + ci + "</span>" +
          "<span class='rl-test-num'>" + (r.p_adjusted != null ? Number(r.p_adjusted).toFixed(3) : "—") + "</span>" +
          "<span class='rl-test-num'>" + esc(r.n_obs) + "</span>" +
          (sig ? "<span class='rl-sig'>sig</span>" : "<span></span>") +
          "</div>";
      }).join("") +
      (missing.length
        ? "<p class='rl-sel-note' style='color:var(--on-dark-muted)'>Belum dihitung untuk target ini: " +
          esc(missing.map(function (t) { return A.testLabel(t); }).join(", ")) +
          ". Tidak ada angkanya di sini karena memang belum ada.</p>"
        : "") +
      /* n_obs di sini 24–49 hari berpasangan. Tanpa kalimat ini, p_adj kecil
         terbaca sebagai kepastian padahal sampelnya sebulan-dua bulan. */
      "<p class='rl-sel-note rl-n-mini'>Sampel tiap uji " + esc(minN(rows)) + "–" +
        esc(maxN(rows)) + " hari berpasangan. p_adj kecil pada sampel sekecil ini " +
        "berarti asosiasi lemah yang belum stabil, bukan kepastian.</p>";
  }

  /* ---------------- muat ----------------
     Pola sama dengan overview.js: request lama dibatalkan dan hasilnya
     diabaikan lewat nomor urut. Tanpa ini, ganti target cepat membuat berita
     target sebelumnya menimpa target yang sedang dibuka. */
  var inFlight = null, seq = 0;

  function loadData() {
    var t = A.state.target;
    if (inFlight) inFlight.abort();
    var ctrl = typeof AbortController !== "undefined" ? new AbortController() : null;
    inFlight = ctrl;
    var mySeq = ++seq;
    var signal = ctrl ? { signal: ctrl.signal } : undefined;
    var live = function () { return mySeq === seq; };

    A.showState("chartState", "Memuat deret harga...");
    A.showState("newsState", "Memuat berita...");
    A.showState("testState", "Memuat hasil uji...");

    var start = new Date(Date.now() - 89 * 86400000).toISOString().slice(0, 10);
    var end = new Date().toISOString().slice(0, 10);

    function fail(err) {
      if (err && err.name === "AbortError") throw err;
    }

    return Promise.all([
      A.api("/api/series/" + t + "?start_date=" + start + "&end_date=" + end, signal)
        .then(function (p) { S.prices = (p && p.prices) || []; })
        .catch(function (err) { fail(err); S.prices = []; }),
      A.api("/api/impacts/" + t + "?limit=50", signal)
        .then(function (rows) {
          /* Urut terbaru dulu supaya berita yang baru masuk langsung terlihat. */
          S.news = (rows || []).slice().sort(function (a, b) {
            return String(b.published_at || "").localeCompare(String(a.published_at || ""));
          });
        })
        .catch(function (err) { fail(err); S.news = []; }),
      A.api("/api/stats/" + t, signal)
        .then(function (rows) { S.tests = rows || []; })
        .catch(function (err) { fail(err); S.tests = []; })
    ]).then(function () {
      if (!live()) return;
      /* Indeks terpilih hanya bermakna di dalam satu target. Tanpa reset,
         pindah target bisa menunjuk kartu yang tidak ada. */
      S.selected = S.news.length ? 0 : null;
      renderNews();
      renderSelected();
      renderTests();
      drawPriceChart();
    }).catch(function () { /* dibatalkan: target lain sudah mengambil alih */ });
  }

  /* ---------------- kontrol ----------------
     Scrollbar disembunyikan karena bar abu di bawah kartu terlihat seperti
     salah layout. Konsekuensinya penggeseran harus disediakan sendiri:
     roda mouse (vertikal dipetakan ke horizontal) dan seret dengan pointer.
     Tanpa ini, kartu di luar layar tidak bisa dijangkau di desktop. */
  var picker = $("newsPicker");
  if (!picker) {
    /* Tanpa DOM (diuji lewat node) tidak ada kontrol untuk didaftari. */
    A.dedupUji = dedupUji;
    A.urutUji = urutUji;
    A.renderPage = loadData;
    return;
  }
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

  A.dedupUji = dedupUji;
  A.urutUji = urutUji;
  A.renderPage = loadData;
  A.boot();
})(window.ARCAS);
