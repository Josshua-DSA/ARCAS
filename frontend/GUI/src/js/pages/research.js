/* Research Lab (Upgrade.md 3): statistik lengkap, meja kerja asosiasi,
   kualitas data, dan panel kualitas model. Halaman ini hanya fetch dan render:
   shell menyediakan tabel statistik serta fallback berlabel dari api.js. */
(function (A) {
  "use strict";

  /* Meja kerja asosiasi (Upgrade.md UI-05): kontrol minimum metrik + lag.
     Tujuan spec: pembaca melihat arah/ukuran hubungan berubah menurut lag
     tanpa membuka database. Rolling window tidak dipalsukan: engine belum
     punya fitur itu, jadi kontrolnya tidak ada di UI. */
  function metricLabel(m) {
    return { "return": "perubahan harga (return)", abnormal_return: "abnormal return (CAR)", volatility: "volatilitas", volume_change: "perubahan volume" }[m] || m;
  }
  function renderWorkbench(rows, note) {
    var box = A.$("wbTables");
    if (!rows || !rows.length) {
      box.innerHTML = "";
      A.showState("wbState", note || "Belum ada hasil untuk metrik ini. Engine saat ini menghitung return dan abnormal return.");
      return;
    }
    A.showState("wbState", note || "");
    var esc = A.esc, fmt = A.fmt;
    var sorted = rows.slice().sort(function (a, b) {
      return (a.lag == null ? -1 : a.lag) - (b.lag == null ? -1 : b.lag);
    });
    var maxAbs = 0.001;
    rows.forEach(function (r) { maxAbs = Math.max(maxAbs, Math.abs(Number(r.estimate)) || 0); });
    var html = "<table class='data'><thead><tr><th>Uji</th><th>Lag</th><th>Est</th><th>95% CI</th><th>p_adj</th><th>n</th></tr></thead><tbody>";
    sorted.forEach(function (r) {
      var est = Number(r.estimate);
      var cls = est > 0 ? "pos" : est < 0 ? "neg" : "flat";
      var w = Math.round(Math.abs(est) / maxAbs * 80);
      var ci = (r.ci_low != null && r.ci_high != null) ? "[" + Number(r.ci_low).toFixed(2) + ", " + Number(r.ci_high).toFixed(2) + "]" : "-";
      var sig = r.p_adjusted != null && Number(r.p_adjusted) < 0.05;
      var win = "";
      try {
        var p = JSON.parse(r.params_json || "{}");
        if (p.window_pre != null && p.window_post != null) win = "jendela " + p.window_pre + " sebelum .. " + p.window_post + " sesudah";
      } catch (e) { /* params_json bukan JSON: biarkan kosong, jangan mengarang. */ }
      html += "<tr><td>" + esc(A.testLabel(r.test) + (win ? " : " + win : "")) + "</td>" +
        "<td>" + (r.lag == null ? "-" : "L" + esc(r.lag)) + "</td>" +
        "<td class='" + cls + "'><span class='wb-bar " + cls + "' style='width:" + w + "px'></span>" + fmt(est, 3) + (sig ? "<span class='sig'>sig</span>" : "") + "</td>" +
        "<td>" + ci + "</td>" +
        "<td>" + (r.p_adjusted != null ? Number(r.p_adjusted).toFixed(3) : "-") + "</td>" +
        "<td>" + esc(r.n_obs) + "</td></tr>";
    });
    html += "</tbody></table>";
    var starts = [], ends = [];
    sorted.forEach(function (r) {
      if (r.period_start) starts.push(String(r.period_start));
      if (r.period_end) ends.push(String(r.period_end));
    });
    if (starts.length && ends.length) {
      starts.sort(); ends.sort();
      html += "<p class='hint' style='font-family:var(--font-mono);font-size:11px;color:var(--on-dark-muted)'>Periode: " +
        esc(starts[0]) + " .. " + esc(ends[ends.length - 1]) +
        (A.state.meta && A.state.meta.coverage ? " : hari berita (universe) " + esc(A.state.meta.coverage.days_with_news) : "") +
        ". Lag lebih panjang makan observasi lebih sedikit; bandingkan est per lag, bukan pilih yang paling menarik.</p>";
    }
    box.innerHTML = html;
  }
  function updateWorkbenchControls(rows) {
    var sel = A.$("wbMetric");
    var metrics = [];
    rows.forEach(function (r) {
      if (r.market_metric != null && metrics.indexOf(r.market_metric) === -1) metrics.push(r.market_metric);
    });
    metrics.sort();
    var current = sel.value;
    var previous = (metrics.indexOf(current) !== -1) ? current : "return";
    sel.innerHTML = "";
    metrics.forEach(function (m) {
      var o = document.createElement("option");
      o.value = m;
      o.textContent = metricLabel(m);
      sel.appendChild(o);
    });
    sel.value = (metrics.indexOf(previous) !== -1) ? previous : (metrics[0] || "");
    renderWorkbench(rows.filter(function (r) { return r.market_metric === sel.value; }), "");
  }
  function runWorkbench() {
    var t = A.state.target;
    A.showState("wbState", "Menghitung ulang Spearman L0..L5 dari data harian : " + t + " ...");
    A.api("/api/stats/" + t + "?max_lag=5").then(function (rows) {
      renderWorkbench(rows, "");
    }).catch(function () {
      var byMetric = storedRows.filter(function (r) { return r.market_metric === A.$("wbMetric").value; });
      renderWorkbench(byMetric, "Perhitungan ulang tidak terjangkau : tabel berisi data tersimpan/ilustrasi berlabel, bukan hasil hitung baru.");
    });
  }

  /* Kualitas data (UI-06): MODE MOCKUP SEMENTARA dari api.js demoQuality().
     Angka hard-coded dan selalu berlabel; renderer tidak berubah saat backend
     menyediakan endpoint, hanya penyedianya yang ditukar. */
  function pct(part, total) { return A.pct(part, total); }
  function renderQuality(q) {
    var box = A.$("qualityTables");
    if (!q) { box.innerHTML = ""; A.showState("qualityState", ""); return; }
    A.showState("qualityState", "");
    var num = A.num, esc = A.esc;
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
      esc(q.universe_version || "-") + " : panel memakai angka hasil hitung API begitu endpoint kualitas tersedia. Bukan nasihat investasi.</p>";
    box.innerHTML = h;
  }

  var storedRows = [];
  function renderAll() {
    var t = A.state.target;
    A.showState("statState", "Memuat uji statistik...");
    A.showState("wbState", "Memuat meja kerja...");
    A.api("/api/stats/" + t).then(function (rows) {
      storedRows = A.renderStats(rows, "Belum ada hasil uji untuk target ini. Jalankan pipeline analyze dulu.");
      updateWorkbenchControls(storedRows);
    }).catch(function () {
      var fallback = [{ test: "spearman", market_metric: "return", lag: 1, estimate: 0.18, p_value: 0.04, p_adjusted: 0.09, n_obs: 62, period_start: "2026-07-15", period_end: "2026-10-12" }, { test: "ols", market_metric: "return", lag: 1, estimate: 0.11, p_value: 0.07, p_adjusted: 0.12, n_obs: 62, period_start: "2026-07-15", period_end: "2026-10-12" }, { test: "granger", market_metric: "return", lag: 2, estimate: 3.4, p_value: 0.06, p_adjusted: 0.11, n_obs: 60, period_start: "2026-07-15", period_end: "2026-10-12" }, { test: "event_study", market_metric: "abnormal_return", lag: 0, estimate: 0.006, p_value: 0.03, p_adjusted: 0.08, n_obs: 18, period_start: "2026-08-01", period_end: "2026-10-12" }];
      storedRows = A.renderStats(fallback);
      /* Setelah renderStats dan updateWorkbench, bukan sebelum: keduanya mengosongkan state. */
      updateWorkbenchControls(storedRows);
      A.showState("statState", "API statistik tidak terjangkau : tabel ini ilustrasi berlabel, bukan hasil uji nyata.");
      A.showState("wbState", "API statistik tidak terjangkau : meja kerja menampilkan data tersimpan berlabel.");
    });
  }

  A.$("wbMetric").addEventListener("change", function () { updateWorkbenchControls(storedRows); });
  A.$("wbRun").addEventListener("click", runWorkbench);
  A.renderPage = renderAll;
  A.boot("Meja riset : data berjalan");
  renderQuality(A.demoQuality()); /* stats boot akan dipanggil: kualitas mock tetap satu kali */
})(window.ARCAS);
