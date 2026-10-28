/* Research Lab: pilih berita lalu lihat titiknya di grafik pasar, empat uji
   statistik, peluruhan hubungan menurut lag, selang kepercayaan, tabel
   lengkap, kualitas data, dan kualitas model.

   Halaman ini hanya fetch dan render. Semua angka dari API; tidak ada data
   contoh. Yang belum tersedia ditulis belum tersedia, bukan dikarang. */
(function (A) {
  "use strict";
  var esc = A.esc, fmt = A.fmt;

  var S = {
    prices: [],
    news: [],
    tests: [],
    selected: null,
    live: [],
    stored: [],
    maxLag: 5
  };

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
  function ensurePriceChart() {
    if (priceChart || typeof echarts === "undefined") return;
    priceChart = echarts.init($("priceChart"));
    window.addEventListener("resize", function () { if (priceChart) priceChart.resize(); });
  }

  function drawPriceChart() {
    ensurePriceChart();
    if (!priceChart) {
      A.showState("chartState", "Pustaka grafik lokal belum termuat.");
      return;
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

  /* ---------------- empat uji statistik ---------------- */
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

  /* ---------------- grafik peluruhan lag ----------------
     Tabel menyembunyikan pesan utama: hubungan melemah saat lag bertambah. */
  var lagChart = null;
  function drawLagChart(rows) {
    var el = $("lagChart");
    if (!el || typeof echarts === "undefined") return;
    if (!lagChart) {
      lagChart = echarts.init(el);
      window.addEventListener("resize", function () { if (lagChart) lagChart.resize(); });
    }
    /* Ringkasan harus ikut dikosongkan. Kalau tidak, angka target sebelumnya
       tertinggal dan terbaca sebagai milik target yang sedang dibuka. */
    if (!rows.length) {
      lagChart.clear();
      $("lagSummary").textContent = "Tidak ada hasil untuk target ini, jadi tidak ada peluruhan yang bisa dihitung.";
      return;
    }

    var sorted = rows.slice().sort(function (a, b) { return a.lag - b.lag; });
    var lags = sorted.map(function (r) { return "L" + r.lag; });
    var est = sorted.map(function (r) { return Number(r.estimate); });
    /* Pita CI hanya digambar bila kedua batas tersedia. Null tidak dikarang. */
    var hasCI = sorted.every(function (r) { return r.ci_low != null && r.ci_high != null; });

    var series = [{
      name: "Estimasi", type: "line", data: est, smooth: false,
      symbol: "circle", symbolSize: 6,
      lineStyle: { width: 2.5, color: "#FF7517" }, itemStyle: { color: "#FF7517" },
      markLine: {
        silent: true, symbol: "none",
        lineStyle: { color: "#BDB7B7", type: "dashed", width: 1 },
        label: { formatter: "nol", color: "#BDB7B7", fontSize: 10 },
        data: [{ yAxis: 0 }]
      }
    }];

    if (hasCI) {
      var lo = sorted.map(function (r) { return Number(r.ci_low); });
      var hi = sorted.map(function (r) { return Number(r.ci_high); });
      series.push({
        name: "Batas bawah", type: "line", data: lo, symbol: "none", stack: "ci",
        lineStyle: { opacity: 0 }, silent: true
      });
      series.push({
        name: "95% CI", type: "line", data: hi.map(function (v, i) { return v - lo[i]; }),
        symbol: "none", stack: "ci", silent: true, lineStyle: { opacity: 0 },
        areaStyle: { color: "rgba(255,117,23,.16)" }
      });
    }

    lagChart.setOption({
      backgroundColor: "transparent",
      grid: { left: 52, right: 24, top: 28, bottom: 40 },
      tooltip: {
        trigger: "axis", backgroundColor: "#2C2727", borderWidth: 0,
        textStyle: { color: "#F6F4F4", fontFamily: "JetBrains Mono, monospace", fontSize: 12 },
        formatter: function (ps) {
          var i = ps[0].dataIndex, r = sorted[i];
          return "<b>" + lags[i] + "</b><br/>estimasi " + fmt(r.estimate, 3) +
            "<br/>p_adj " + (r.p_adjusted != null ? Number(r.p_adjusted).toFixed(3) : "-") +
            "<br/>n " + r.n_obs;
        }
      },
      xAxis: {
        type: "category", data: lags,
        axisLine: { lineStyle: { color: "#5A5454" } },
        axisLabel: { color: "#BDB7B7", fontFamily: "JetBrains Mono, monospace", fontSize: 11 }
      },
      yAxis: {
        type: "value", scale: true,
        splitLine: { lineStyle: { color: "#5A5454", opacity: 0.35 } },
        axisLabel: { color: "#BDB7B7", fontFamily: "JetBrains Mono, monospace", fontSize: 10 }
      },
      series: series
    }, true);

    var first = est[0], last = est[est.length - 1];
    var drop = first !== 0 ? (1 - Math.abs(last) / Math.abs(first)) * 100 : null;
    $("lagSummary").textContent = drop == null
      ? "Estimasi L0 nol, jadi perubahan relatif tidak bisa dihitung."
      : "Kekuatan hubungan turun " + drop.toFixed(0) + "% dari " + lags[0] + " ke " +
        lags[lags.length - 1] + ". n berkurang dari " + sorted[0].n_obs + " ke " +
        sorted[sorted.length - 1].n_obs + " karena lag memakan observasi.";
  }

  /* ---------------- forest plot ---------------- */
  var forestChart = null;
  function drawForest(rows) {
    var el = $("forestChart");
    if (!el || typeof echarts === "undefined") return;
    if (!forestChart) {
      forestChart = echarts.init(el);
      window.addEventListener("resize", function () { if (forestChart) forestChart.resize(); });
    }
    var withCI = (rows || []).filter(function (r) {
      return r.ci_low != null && r.ci_high != null;
    });
    if (!withCI.length) {
      forestChart.clear();
      $("forestNote").textContent = "Tidak ada uji tersimpan dengan interval kepercayaan. " +
        "Interval tidak digambar karena tidak boleh dikarang.";
      return;
    }
    var labels = withCI.map(function (r) {
      return A.testLabel(r.test) + (r.lag != null ? " L" + r.lag : "");
    });
    var lo = withCI.map(function (r) { return Number(r.ci_low); });
    var hi = withCI.map(function (r) { return Number(r.ci_high); });
    var mid = withCI.map(function (r) { return Number(r.estimate); });
    var crosses = withCI.filter(function (r) {
      return Number(r.ci_low) <= 0 && Number(r.ci_high) >= 0;
    }).length;

    forestChart.setOption({
      backgroundColor: "transparent",
      grid: { left: 100, right: 28, top: 16, bottom: 30 },
      tooltip: {
        trigger: "item", backgroundColor: "#2C2727", borderWidth: 0,
        textStyle: { color: "#F6F4F4", fontFamily: "JetBrains Mono, monospace", fontSize: 12 },
        formatter: function (p) {
          var r = withCI[p.dataIndex];
          return "<b>" + labels[p.dataIndex] + "</b><br/>estimasi " + fmt(r.estimate, 3) +
            "<br/>95% CI [" + Number(r.ci_low).toFixed(2) + ", " + Number(r.ci_high).toFixed(2) + "]" +
            "<br/>p_adj " + (r.p_adjusted != null ? Number(r.p_adjusted).toFixed(3) : "-") +
            "<br/>n " + r.n_obs;
        }
      },
      xAxis: {
        type: "value", scale: true,
        splitLine: { lineStyle: { color: "#5A5454", opacity: 0.35 } },
        axisLabel: { color: "#BDB7B7", fontFamily: "JetBrains Mono, monospace", fontSize: 10 }
      },
      yAxis: {
        type: "category", data: labels, inverse: true,
        axisLine: { lineStyle: { color: "#5A5454" } },
        axisLabel: { color: "#BDB7B7", fontFamily: "Inter, sans-serif", fontSize: 11 }
      },
      series: [
        {
          type: "custom", silent: true,
          renderItem: function (params, api) {
            var i = api.value(0);
            var y = api.coord([0, api.value(1)])[1];
            var x1 = api.coord([lo[i], 0])[0];
            var x2 = api.coord([hi[i], 0])[0];
            return {
              type: "line", shape: { x1: x1, y1: y, x2: x2, y2: y },
              style: { stroke: "#8C8585", lineWidth: 2 }
            };
          },
          data: withCI.map(function (r, i) { return [i, i]; })
        },
        {
          type: "scatter", symbolSize: 9, itemStyle: { color: "#FF7517" },
          data: mid.map(function (v, i) { return [v, i]; })
        }
      ]
    }, true);

    $("forestNote").textContent = crosses
      ? crosses + " dari " + withCI.length +
        " uji punya interval kepercayaan yang melewati nol, jadi arahnya belum bisa dipastikan."
      : "Semua interval kepercayaan tidak melewati nol.";
  }

  /* ---------------- tabel lengkap ---------------- */
  function renderTable(rows) {
    var box = $("statTables");
    if (!box) return;
    if (!rows.length) {
      box.innerHTML = "";
      A.showState("statState", "Belum ada hasil uji tersimpan untuk target ini.");
      return;
    }
    A.showState("statState", "");
    var sorted = rows.slice().sort(function (a, b) {
      return (a.lag == null ? -1 : a.lag) - (b.lag == null ? -1 : b.lag);
    });
    var html = "<table class='rl-table'><thead><tr>" +
      "<th>Uji</th><th>Lag</th><th>Estimasi</th><th>95% CI</th><th>p_adj</th><th>n</th><th>Periode</th>" +
      "</tr></thead><tbody>";
    sorted.forEach(function (r) {
      var sig = r.p_adjusted != null && Number(r.p_adjusted) < 0.05;
      var ci = (r.ci_low != null && r.ci_high != null)
        ? "[" + Number(r.ci_low).toFixed(2) + ", " + Number(r.ci_high).toFixed(2) + "]"
        : "tidak tersedia";
      html += "<tr>" +
        "<td>" + esc(A.testLabel(r.test)) + "</td>" +
        "<td>" + (r.lag == null ? "-" : "L" + esc(r.lag)) + "</td>" +
        "<td class='rl-num'>" + fmt(r.estimate, 3) + "</td>" +
        "<td class='rl-num'>" + ci + "</td>" +
        "<td class='rl-num'>" + (r.p_adjusted != null ? Number(r.p_adjusted).toFixed(3) : "-") +
          (sig ? "<span class='rl-sig'>sig</span>" : "") + "</td>" +
        "<td class='rl-num'>" + esc(r.n_obs) + "</td>" +
        "<td class='rl-num'>" + esc(String(r.period_start || "").slice(0, 10)) + " – " +
          esc(String(r.period_end || "").slice(0, 10)) + "</td>" +
        "</tr>";
    });
    html += "</tbody></table>";
    box.innerHTML = html;
  }

  /* ---------------- ekspor CSV/JSON (P2) ----------------
     Ekspor apa adanya dari data yang sedang tampil, termasuk nilai kosong. */
  function toCSV(rows) {
    var cols = ["test", "market_metric", "lag", "estimate", "ci_low", "ci_high",
      "p_value", "p_adjusted", "n_obs", "period_start", "period_end"];
    var lines = [cols.join(",")];
    rows.forEach(function (r) {
      lines.push(cols.map(function (c) {
        var v = r[c];
        if (v == null) return "";
        var s = String(v);
        return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
      }).join(","));
    });
    return lines.join("\n");
  }
  function download(name, text, mime) {
    var blob = new Blob([text], { type: mime || "text/csv;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  /* ---------------- kualitas data (UI-06) ----------------
     Dulu diisi demoQuality() hard-coded. Sekarang hanya dari API. Bila backend
     belum menyediakan endpoint-nya, panel menyatakan belum tersedia. */
  function pct(part, total) { return A.pct(part, total); }
  function renderQuality(q) {
    var box = $("qualityTables");
    if (!box) return;
    if (!q) {
      box.innerHTML = "";
      A.showState("qualityState", "Belum ada artefak kualitas data (endpoint belum tersedia). Panel ini kosong dengan sengaja, bukan ilustrasi.");
      return;
    }
    A.showState("qualityState", "");
    var num = A.num;
    var t = q.totals || {}, c = q.completeness || {};
    var h = "<div class='q-row'>" +
      "<span class='chip hold'>artikel " + esc(num(t.articles)) + "</span>" +
      "<span class='chip hold'>duplikat " + esc(num(t.duplicates)) + "</span>" +
      "<span class='chip hold'>ditolak validator " + esc(num(t.rejected)) + "</span>" +
      "<span class='chip hold'>dampak tersimpan " + esc(num(t.impacts)) + "</span>" +
      "<span class='chip hold'>headline " + esc(num(c.headline)) + esc(pct(c.headline, t.articles)) + "</span>" +
      "<span class='chip hold'>isi lengkap " + esc(num(c.body)) + esc(pct(c.body, t.articles)) + "</span>" +
      "<span class='chip hold'>ada kutipan bukti " + esc(num(c.impacts_with_evidence)) + " dari " + esc(num(t.impacts)) + "</span>" +
      "</div>";
    var rows = q.per_target || [];
    if (rows.length) {
      h += "<table class='data'><thead><tr><th>Target</th><th>Artikel terpetakan</th><th>Hari berita</th><th>Hari tanpa berita</th></tr></thead><tbody>";
      rows.forEach(function (r) {
        h += "<tr><td>" + esc(r.asset_id) + "</td><td>" + esc(num(r.mapped_articles)) + "</td><td>" +
          esc(num(r.daily_days) - num(r.news_free_days)) + "</td><td>" + esc(num(r.news_free_days)) + " (gap)</td></tr>";
      });
      h += "</tbody></table>";
    }
    var srcs = q.by_source || [];
    if (srcs.length) {
      h += "<table class='data'><thead><tr><th>Sumber</th><th>Artikel</th></tr></thead><tbody>";
      srcs.forEach(function (s) {
        h += "<tr><td>" + esc(s.source) + "</td><td>" + esc(num(s.articles)) + "</td></tr>";
      });
      h += "</tbody></table>";
    }
    var warns = q.warnings || [];
    if (warns.length) {
      h += "<div class='q-row'>" + warns.map(function (w) {
        return "<span class='chip mix'>! " + esc(w) + "</span>";
      }).join("") + "</div>";
    }
    h += "<p class='hint' style='font-family:var(--font-mono);font-size:11px;color:var(--on-dark-muted)'>Versi universe " +
      esc(q.universe_version || "-") + " : panel memakai angka hasil hitung API. Bukan nasihat investasi.</p>";
    box.innerHTML = h;
  }

  /* ---------------- muat ---------------- */
  function isoDaysAgo(n) {
    var d = new Date(Date.now() - (n - 1) * 86400000);
    return d.toISOString().slice(0, 10);
  }

  function loadData() {
    var t = A.state.target;
    A.showState("chartState", "Memuat deret harga...");
    A.showState("newsState", "Memuat berita...");
    A.showState("testState", "Memuat hasil uji...");
    A.showState("statState", "Memuat hasil uji tersimpan...");
    A.showState("wbState", "Menghitung Spearman L0..L" + S.maxLag + " dari data harian...");

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
        .then(function (rows) {
          S.tests = rows || [];
          S.stored = rows || [];
        })
        .catch(function () { S.tests = []; S.stored = []; }),
      A.api("/api/stats/" + t + "?max_lag=" + S.maxLag)
        .then(function (rows) { S.live = rows || []; })
        .catch(function () { S.live = []; })
    ]).then(function () {
      if (S.selected == null && S.news.length) S.selected = 0;
      renderNews();
      renderSelected();
      renderTests();
      drawPriceChart();
      drawLagChart(S.live);
      drawForest(S.stored);
      renderTable(S.stored);
      A.showState("wbState", S.live.length ? "" : "Tidak ada hasil untuk target ini.");
      if (!S.live.length) {
        A.showState("wbState", "Perhitungan ulang tidak terjangkau : grafik dikosongkan, bukan diisi angka lama.");
      }
    });
  }

  function reloadLive() {
    var t = A.state.target;
    A.showState("wbState", "Menghitung ulang Spearman L0..L" + S.maxLag + " dari data harian...");
    return A.api("/api/stats/" + t + "?max_lag=" + S.maxLag).then(function (rows) {
      S.live = rows || [];
      A.showState("wbState", S.live.length ? "" : "Tidak ada hasil untuk target ini.");
      drawLagChart(S.live);
    }).catch(function () {
      S.live = [];
      drawLagChart([]);
      A.showState("wbState", "Perhitungan ulang tidak terjangkau : grafik dikosongkan, bukan diisi angka lama.");
    });
  }

  /* ---------------- kontrol ---------------- */
  function bind() {
    $("newsPicker").addEventListener("click", function (e) {
      var btn = e.target.closest(".rl-item");
      if (!btn) return;
      S.selected = Number(btn.getAttribute("data-i"));
      renderNews();
      renderSelected();
      drawPriceChart();
    });
    $("wbRun").addEventListener("click", reloadLive);
    $("maxLag").addEventListener("change", function () {
      S.maxLag = Number(this.value);
      reloadLive();
    });
    $("btnCSV").addEventListener("click", function () {
      var rows = S.live.length ? S.live : S.stored;
      if (!rows.length) { A.showState("exportState", "Tidak ada data untuk diekspor."); return; }
      A.showState("exportState", "Diekspor " + rows.length + " baris.");
      download("arcas-" + A.state.target + "-lag.csv", toCSV(rows));
    });
    $("btnJSON").addEventListener("click", function () {
      var rows = S.live.length ? S.live : S.stored;
      if (!rows.length) { A.showState("exportState", "Tidak ada data untuk diekspor."); return; }
      A.showState("exportState", "Diekspor " + rows.length + " baris.");
      download("arcas-" + A.state.target + "-lag.json", JSON.stringify(rows, null, 2), "application/json");
    });
  }

  bind();
  A.renderPage = loadData;
  A.boot();
  renderQuality(null); /* tidak ada angka karangan: panel kosong sampai backend menyediakan artefak */
})(window.ARCAS);
