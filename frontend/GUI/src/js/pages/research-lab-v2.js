/* Research Lab v2 : file eksperimen terpisah.
   Tidak menyentuh research.html / research.js milik Josshua.
   Semua angka dibaca langsung dari API; tidak ada data contoh.
   Buka lewat http://localhost:8080/research-lab-v2.html saat GUI jalan. */
(function (A) {
  "use strict";
  var esc = A.esc, fmt = A.fmt;

  /* ---------------- state halaman ---------------- */
  var S = { live: [], stored: [], metric: "return", maxLag: 5 };

  function $(id) { return document.getElementById(id); }
  function show(id, msg) {
    var el = $(id);
    if (!el) return;
    if (!msg) { el.hidden = true; el.textContent = ""; return; }
    el.hidden = false; el.textContent = msg;
  }

  /* ---------------- grafik peluruhan lag ----------------
     Alasan: tabel menyembunyikan pesan utama UI-05, yaitu hubungan melemah
     saat lag bertambah. Garis + pita CI membuatnya terlihat sekaligus. */
  var lagChart = null;
  function drawLagChart(rows) {
    var el = $("lagChart");
    if (!el || typeof echarts === "undefined") return;
    if (!lagChart) {
      lagChart = echarts.init(el);
      window.addEventListener("resize", function () { if (lagChart) lagChart.resize(); });
    }
    if (!rows.length) { lagChart.clear(); return; }

    var sorted = rows.slice().sort(function (a, b) { return a.lag - b.lag; });
    var lags = sorted.map(function (r) { return "L" + r.lag; });
    var est = sorted.map(function (r) { return Number(r.estimate); });
    /* Pita CI hanya digambar bila kedua batas tersedia. Null = tidak dikarang. */
    var hasCI = sorted.every(function (r) { return r.ci_low != null && r.ci_high != null; });
    var series = [{
      name: "Estimasi", type: "line", data: est, smooth: false, symbol: "circle", symbolSize: 6,
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
        name: "Batas bawah", type: "line", data: lo, symbol: "none",
        lineStyle: { opacity: 0 }, stack: "ci", silent: true
      });
      series.push({
        name: "95% CI", type: "line", data: hi.map(function (v, i) { return v - lo[i]; }),
        symbol: "none", stack: "ci", silent: true,
        lineStyle: { opacity: 0 },
        areaStyle: { color: "rgba(255,117,23,.16)" }
      });
    }

    lagChart.setOption({
      backgroundColor: "transparent",
      grid: { left: 52, right: 24, top: 30, bottom: 42 },
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

    /* Ringkasan perubahan: berapa persen kekuatan hubungan turun dari L0 ke lag terakhir. */
    var first = est[0], last = est[est.length - 1];
    var drop = first !== 0 ? (1 - Math.abs(last) / Math.abs(first)) * 100 : null;
    $("lagSummary").textContent = drop == null
      ? "Estimasi L0 tidak bisa dipakai menghitung perubahan relatif."
      : "Kekuatan hubungan turun " + drop.toFixed(0) + "% dari " + lags[0] + " ke " +
        lags[lags.length - 1] + ". n berkurang dari " + sorted[0].n_obs + " ke " +
        sorted[sorted.length - 1].n_obs + " karena lag memakan observasi.";
  }

  /* ---------------- forest plot uji tersimpan ---------------- */
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
      $("forestNote").textContent =
        "Tidak ada uji tersimpan dengan interval kepercayaan. Interval tidak digambar karena tidak boleh dikarang.";
      return;
    }
    var labels = withCI.map(function (r) {
      return A.testLabel(r.test) + (r.lag != null ? " L" + r.lag : "");
    });
    var lo = withCI.map(function (r) { return Number(r.ci_low); });
    var hi = withCI.map(function (r) { return Number(r.ci_high); });
    var mid = withCI.map(function (r) { return Number(r.estimate); });
    var crossesZero = withCI.filter(function (r) {
      return Number(r.ci_low) <= 0 && Number(r.ci_high) >= 0;
    }).length;

    forestChart.setOption({
      backgroundColor: "transparent",
      grid: { left: 96, right: 28, top: 16, bottom: 32 },
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
        /* garis CI: digambar sebagai custom bar dari lo ke hi */
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
          type: "scatter", symbolSize: 9,
          itemStyle: { color: "#FF7517" },
          data: mid.map(function (v, i) { return [v, i]; })
        }
      ]
    }, true);

    $("forestNote").textContent = crossesZero
      ? crossesZero + " dari " + withCI.length +
        " uji punya interval kepercayaan yang melewati nol, jadi arahnya belum bisa dipastikan."
      : "Semua interval kepercayaan tidak melewati nol.";
  }

  /* ---------------- tabel lengkap ---------------- */
  function renderTable(rows) {
    var box = $("fullTable");
    if (!box) return;
    if (!rows.length) {
      box.innerHTML = "";
      show("tableState", "Belum ada hasil uji untuk target ini.");
      return;
    }
    show("tableState", "");
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

  /* ---------------- ekspor CSV (P2) ----------------
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

  /* ---------------- muat data ---------------- */
  function loadStored() {
    var t = A.state.target;
    show("tableState", "Memuat hasil uji tersimpan...");
    return A.api("/api/stats/" + t).then(function (rows) {
      S.stored = rows || [];
      renderTable(S.stored);
      drawForest(S.stored);
      return S.stored;
    }).catch(function () {
      S.stored = [];
      renderTable([]);
      drawForest([]);
      show("tableState", "API statistik tidak terjangkau : tidak ada angka untuk ditampilkan.");
      return [];
    });
  }

  function loadLive() {
    var t = A.state.target;
    show("lagState", "Menghitung Spearman L0..L" + S.maxLag + " dari data harian...");
    return A.api("/api/stats/" + t + "?max_lag=" + S.maxLag).then(function (rows) {
      S.live = rows || [];
      show("lagState", S.live.length ? "" : "Tidak ada hasil untuk metrik ini.");
      drawLagChart(S.live);
      return S.live;
    }).catch(function () {
      S.live = [];
      drawLagChart([]);
      show("lagState", "Perhitungan ulang tidak terjangkau : grafik dikosongkan, bukan diisi angka lama.");
      return [];
    });
  }

  function renderAll() {
    $("labTarget").textContent = A.state.target;
    return Promise.all([loadStored(), loadLive()]);
  }

  /* ---------------- kontrol ---------------- */
  function bind() {
    $("btnReload").addEventListener("click", renderAll);
    $("btnCSV").addEventListener("click", function () {
      var rows = S.live.length ? S.live : S.stored;
      if (!rows.length) { show("exportState", "Tidak ada data untuk diekspor."); return; }
      show("exportState", "Diekspor " + rows.length + " baris.");
      download("arcas-" + A.state.target + "-lag.csv", toCSV(rows));
    });
    $("btnJSON").addEventListener("click", function () {
      var rows = S.live.length ? S.live : S.stored;
      if (!rows.length) { show("exportState", "Tidak ada data untuk diekspor."); return; }
      show("exportState", "Diekspor " + rows.length + " baris.");
      download("arcas-" + A.state.target + "-lag.json",
        JSON.stringify(rows, null, 2), "application/json");
    });
    var lagSel = $("maxLag");
    lagSel.addEventListener("change", function () {
      S.maxLag = Number(lagSel.value);
      loadLive();
    });
  }

  bind();
  A.renderPage = renderAll;
  A.boot();
})(window.ARCAS);
