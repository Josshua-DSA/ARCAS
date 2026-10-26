/* Simulations (Upgrade.md 3): Allocation Tilt interactif, Persona POV, dan
   parameter/versi yang dipakai simulasi. Halaman ini hanya fetch dan render:
   widget alokasi dan modal persona hidup di shell.js. */
(function (A) {
  "use strict";
  var esc = A.esc;
  function chipArah(direction) { return A.dirChip(direction); }
  function fmtSkor(score) { return A.fmt(score); }

  var impacts = [];
  function renderPersonaCards(rows) {
    impacts = rows || [];
    var box = A.$("personaCards");
    if (!impacts.length) {
      box.innerHTML = "";
      A.showState("personaCardsState", "Belum ada dampak berita untuk memanggil persona.");
      return;
    }
    A.showState("personaCardsState", "");
    box.innerHTML = "<table class='data'><thead><tr><th>Berita</th><th>Arah</th><th>Skor</th><th>Stance? Buka di POV</th></tr></thead><tbody>" +
      impacts.slice(0, 5).map(function (it) {
        var title = (it.title || it.article_id).slice(0, 48);
        return "<tr><td>" + esc(title) + "</td><td>" + chipArah(it.direction) + "</td><td>" + fmtSkor(it.score) +
          "</td><td><button class='btn small' data-persona='" + esc(it.article_id) + "'>Lihat stance</button></td></tr>";
      }).join("") + "</tbody></table>" +
      "<p class='hint' style='font-family:var(--font-mono);font-size:11px;color:var(--text-muted)'>Stance lima persona dihitung dari skor dampak dan profil risiko. Sudut pandang simulasi, bukan saran jual-beli.</p>";
    box.querySelectorAll("[data-persona]").forEach(function (b) {
      b.onclick = function () {
        var id = b.getAttribute("data-persona");
        var fb = impacts.find(function (x) { return x.article_id === id; });
        A.openPersona(id, fb);
      };
    });
  }

  function renderVersions(meta) {
    var box = A.$("versionTables");
    if (!box) return;
    if (!meta) {
      box.innerHTML = "<p class='hint' style='font-family:var(--font-mono);font-size:12px;color:var(--text-muted)'>Metadata tidak terjangkau; simulasi memakai data ilustrasi berlabel. Tidak ada versi palsu di sini.</p>";
      return;
    }
    var rows = [
      ["versi universe", meta.universe_version],
      ["versi skema", meta.schema_version],
      ["versi model", meta.model_version + (meta.calibrated ? " (terkalibrasi)" : " (belum kalibrasi)")],
      ["versi params", meta.params_version || "-"],
      ["profil aktif", A.state.profile],
      ["mode data", meta.mode]
    ];
    box.innerHTML = "<table class='data'><tbody>" + rows.map(function (r) {
      return "<tr><td>" + esc(r[0]) + "</td><td>" + esc(r[1] == null ? "n/a" : String(r[1])) + "</td></tr>";
    }).join("") + "</tbody></table>";
  }

  function renderAll() {
    var t = A.state.target;
    A.showState("allocState", "Memuat simulasi alokasi profil " + A.state.profile + "...");
    A.api("/api/allocation?profile_id=" + A.state.profile + "&article_id=current_market&target=" + encodeURIComponent(t)).then(A.renderAllocation)
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
    A.api("/api/impacts/" + t + "?limit=5").then(renderPersonaCards)
      .catch(function () { renderPersonaCards(A.demoImpacts(t)); });
    renderVersions(A.state.meta);
  }

  A.renderPage = renderAll;
  A.boot("Simulasi dan persona : data berjalan");
})(window.ARCAS);
