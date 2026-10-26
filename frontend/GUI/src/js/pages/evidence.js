/* News & Evidence (Upgrade.md 3): filter berita, kartu dampak dengan Evidence
   Drawer dan audit waktu, Personal POV. Halaman ini hanya fetch dan render:
   shell dan api menyediakan helper serta fallback berlabel. */
(function (A) {
  "use strict";
  var esc = A.esc;

  /* Audit waktu (UI-02): terbit vs sesi efektif, tanpa klaim sebab.
     Jika salah satu waktu tidak terekam di DB, barisnya jujur bilang belum terekam. */
  function timeAuditLine(it) {
    var parts = [];
    if (it.published_at) {
      parts.push("<span>terbit " + esc(A.fmtDate(it.published_at)) + " " + esc(String(it.published_at).slice(11, 16)) + "</span>");
    } else {
      parts.push("<span>waktu terbit belum terekam</span>");
    }
    if (it.effective_trading_date && it.published_at) {
      var nextSession = String(it.effective_trading_date) > String(it.published_at).slice(0, 10);
      parts.push("<span>sesi efektif " + esc(it.effective_trading_date) + (nextSession ? " : masuk sesi berikutnya" : "") + "</span>");
    } else if (it.effective_trading_date) {
      parts.push("<span>sesi efektif " + esc(it.effective_trading_date) + "</span>");
    }
    if (it.session_close) {
      parts.push("<span>cut-off " + esc(it.session_close) + " " + esc(it.timezone || "") + "</span>");
    }
    return parts.length ? "<div class='news-meta audit-line'>" + parts.join("") + "</div>" : "";
  }

  /* Evidence drawer (UI-03): <details> native, keyboard bisa buka-tutup.
     Probabilitas per model + badge headline-only + URL asli. Bagian kosong jujur
     menyebut belum terekam, tidak pernah dipalsukan. */
  function evidenceDrawer(it) {
    var inner = [];
    if (it.probs && it.probs.length) {
      inner.push("<table class='data'><thead><tr><th>Model</th><th>p_pos</th><th>p_neu</th><th>p_neg</th></tr></thead><tbody>" +
        it.probs.map(function (p) {
          return "<tr><td>" + esc(p.model) + (p.translation_used ? " : hasil terjemahan" : "") + "</td><td>" +
            esc(Number(p.p_pos).toFixed(2)) + "</td><td>" + esc(Number(p.p_neu).toFixed(2)) + "</td><td>" +
            esc(Number(p.p_neg).toFixed(2)) + "</td></tr>";
        }).join("") + "</tbody></table>");
    } else {
      inner.push("<p class='drawer-note'>Probabilitas kelas per model belum terekam di basis data.</p>");
    }
    if (it.headline_only === 1 || it.headline_only === true) {
      inner.push("<span class='chip hold'>Hanya judul yang dianalisis</span>");
    }
    if (it.url) {
      inner.push("<a class='drawer-link' href='" + esc(it.url) + "' target='_blank' rel='noopener noreferrer'>Sumber asli</a>");
    } else {
      inner.push("<p class='drawer-note'>URL sumber belum terekam.</p>");
    }
    return "<details class='evidence-drawer'><summary>Bukti dan model</summary><div class='drawer-body'>" +
      inner.join("") + "</div></details>";
  }

  function impactCard(it) {
    var quote = (it.evidence && it.evidence[0] && it.evidence[0].quote) ? it.evidence[0].quote : "";
    var themes = (it.themes || []).map(esc).join(", ") || "tanpa tema";
    return "<article class='news-card' data-id='" + esc(it.article_id) + "' data-title='" + esc(it.title || it.article_id) + "'>" +
      "<div class='news-meta'>" + A.dirChip(it.direction) +
      "<span>skor " + A.fmt(it.score) + "</span><span>conf " + esc(Number(it.confidence || 0).toFixed(2)) + "</span>" +
      "<span>" + esc(it.basis || "") + "</span><span>" + esc(A.fmtDate(it.created_at)) + "</span></div>" +
      "<h3>" + esc(it.title || it.article_id) + "</h3>" +
      "<div class='news-meta'><span>" + esc(it.source || "sumber API") + "</span><span>tema: " + themes + "</span><span>horizon: " + esc(it.news_horizon || "short") + "</span></div>" +
      (it.rationale ? "<p style='font-size:14px;color:var(--text-secondary);margin:6px 0'>" + esc(it.rationale) + "</p>" : "") +
      (quote ? "<blockquote class='quote'>" + esc(quote) + "</blockquote>" : "") +
      timeAuditLine(it) + evidenceDrawer(it) +
      "<div style='display:flex;gap:8px;flex-wrap:wrap;margin-top:10px'>" +
      "<button class='btn small primary' data-persona='" + esc(it.article_id) + "'>Lihat Persona POV</button></div></article>";
  }

  var impacts = [];
  function applyNewsFilter() {
    var q = A.$("newsFilter").value.toLowerCase();
    var dir = A.$("dirFilter").value;
    var cards = document.querySelectorAll("#newsList .news-card");
    var visible = 0;
    cards.forEach(function (c) {
      var hitQ = !q || c.textContent.toLowerCase().indexOf(q) !== -1;
      var art = impacts.find(function (x) { return x.article_id === c.getAttribute("data-id"); });
      var hitD = !dir || (art && String(art.direction).toLowerCase() === dir);
      var show = hitQ && hitD;
      c.style.display = show ? "" : "none";
      if (show) visible++;
    });
    A.showState("newsState", visible ? "" : "Tidak ada berita cocok dengan saringan. Kosongkan kata kunci atau ubah arah.");
  }

  function bindPersonaButtons() {
    document.querySelectorAll("[data-persona]").forEach(function (b) {
      b.onclick = function () {
        var id = b.getAttribute("data-persona");
        var fb = impacts.find(function (x) { return x.article_id === id; });
        A.openPersona(id, fb);
      };
    });
  }

  function renderImpacts(rows) {
    impacts = rows || [];
    var kick = A.$("evCount");
    if (kick) kick.textContent = impacts.length + " artikel dampak";
    var list = A.$("newsList");
    list.innerHTML = impacts.map(impactCard).join("");
    A.showState("newsState", impacts.length ? "" : "Belum ada dampak untuk target ini pada rentang ini.");
    bindPersonaButtons();
    applyNewsFilter();
  }

  function renderAll() {
    var t = A.state.target;
    A.showState("newsState", "Memuat dampak berita " + t + "...");
    A.api("/api/impacts/" + t + "?limit=50").then(renderImpacts)
      .catch(function () { renderImpacts(A.demoImpacts(t)); });
  }

  A.$("newsFilter").addEventListener("input", applyNewsFilter);
  A.$("dirFilter").addEventListener("change", applyNewsFilter);
  A.renderPage = renderAll;
  A.boot();
})(window.ARCAS);
