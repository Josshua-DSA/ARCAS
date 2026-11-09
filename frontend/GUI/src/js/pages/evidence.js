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
      "<div class='card-actions'>" +
      "<button class='btn small' data-persona='" + esc(it.article_id) + "'>Lihat Persona POV</button></div></article>";
  }

  var impacts = [];
  var PER_HALAMAN = 10;
  var halaman = 1;

  /* Saringan atas SELURUH baris, bukan atas satu halaman. Memotong populasi
     dulu akan membuat saringan arah kehilangan hasil di halaman lain. */
  function saringBaris(rows, kata, arah) {
    var q = String(kata || "").toLowerCase();
    return (rows || []).filter(function (it) {
      if (arah && String(it.direction).toLowerCase() !== arah) return false;
      if (!q) return true;
      return ((it.title || "") + " " + (it.source || "")).toLowerCase().indexOf(q) !== -1;
    });
  }

  /* Satu halaman potong. Nomor halaman di luar rentang dipangkas ke halaman
     terakhir yang ada, supaya memperkecil saringan tidak menyisakan halaman
     kosong. Tanpa baris -> satu halaman kosong, bukan nol halaman. */
  function potongHalaman(rows, no, per) {
    var semua = rows || [];
    var perHal = per || PER_HALAMAN;
    var jumlah = Math.max(1, Math.ceil(semua.length / perHal));
    var n = Math.min(Math.max(1, no || 1), jumlah);
    var dari = (n - 1) * perHal;
    return {
      baris: semua.slice(dari, dari + perHal),
      jumlahHalaman: jumlah,
      halaman: n,
      total: semua.length
    };
  }
  A.__ujiSaring = saringBaris;
  A.__ujiPotong = potongHalaman;

  function renderPager(jumlahHalaman) {
    var pager = A.$("newsPager");
    if (!pager) return;
    if (jumlahHalaman <= 1) {
      pager.hidden = true;
      pager.innerHTML = "";
      return;
    }
    var tombol = [];
    for (var i = 1; i <= jumlahHalaman; i++) {
      tombol.push("<button type='button' class='pager-btn' data-page-no='" + i + "'" +
        (i === halaman ? " aria-current='page'" : "") + ">" + i + "</button>");
    }
    pager.innerHTML =
      "<button type='button' class='pager-btn' data-step='-1'" +
      (halaman === 1 ? " disabled" : "") + " aria-label='Halaman sebelumnya'>Sebelumnya</button>" +
      tombol.join("") +
      "<button type='button' class='pager-btn' data-step='1'" +
      (halaman === jumlahHalaman ? " disabled" : "") +
      " aria-label='Halaman berikutnya'>Berikutnya</button>";
    pager.hidden = false;
  }

  function renderHalaman() {
    var baris = saringBaris(impacts, A.$("newsFilter").value, A.$("dirFilter").value);
    var potong = potongHalaman(baris, halaman, PER_HALAMAN);
    halaman = potong.halaman;

    var list = A.$("newsList");
    list.innerHTML = potong.baris.map(impactCard).join("");
    bindPersonaButtons();

    var kick = A.$("evCount");
    if (kick) {
      kick.textContent = potong.total === 0
        ? "0 artikel dampak"
        : potong.total + " artikel dampak · halaman " + potong.halaman +
          "/" + potong.jumlahHalaman;
    }
    A.showState("newsState", potong.total ? ""
      : impacts.length ? "Tidak ada berita cocok dengan saringan. Kosongkan kata kunci atau ubah arah."
      : "Belum ada dampak untuk target ini pada rentang ini.");
    renderPager(potong.jumlahHalaman);
  }

  /* Saringan berubah -> selalu kembali ke halaman 1, karena halaman aktif
     bisa saja tidak ada lagi setelah populasi menyusut. */
  function applyNewsFilter() {
    halaman = 1;
    renderHalaman();
  }

  function bindPager() {
    var pager = A.$("newsPager");
    if (!pager) return;
    pager.addEventListener("click", function (e) {
      var b = e.target.closest(".pager-btn");
      if (!b || b.disabled) return;
      var step = b.getAttribute("data-step");
      var no = b.getAttribute("data-page-no");
      halaman = step ? halaman + Number(step) : Number(no);
      renderHalaman();
    });
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
    applyNewsFilter();
  }

  function renderAll() {
    var t = A.state.target;
    A.showState("newsState", "Memuat dampak berita " + t + "...");
    A.api("/api/impacts/" + t + "?limit=50").then(renderImpacts)
      .catch(function () {
        /* Tanpa berita karangan. Bedakan "API mati" dari "belum ada dampak". */
        renderImpacts([]);
        A.showState("newsState", "API dampak berita tidak terjangkau : tidak ada data untuk ditampilkan (bukan ilustrasi).");
      });
  }

  A.$("newsFilter").addEventListener("input", applyNewsFilter);
  A.$("dirFilter").addEventListener("change", applyNewsFilter);
  bindPager();
  A.renderPage = renderAll;
  A.boot();
})(window.ARCAS);
