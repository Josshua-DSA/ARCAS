/* Simulations: alur dua fase mengikuti mockup-simulations.html.

   Fase 1 = composer di tengah. Fase 2 = percakapan + kartu jawaban.
   Semua angka berasal dari POST /api/simulate. Tidak ada angka contoh:
   kalau API tidak menjawab, halaman mengatakannya. */
(function (A) {
  "use strict";

  var esc = A.esc;
  var sedangKirim = false;

  function $(id) { return document.getElementById(id); }

  /* Nilai 0..1 (keyakinan, penalti) diformat tanpa tanda plus. */
  function nilai01(v) {
    if (v === null || v === undefined || Number.isNaN(Number(v))) return "n/a";
    return Number(v).toFixed(2);
  }
  function kelasArah(d) {
    if (d === "bullish") return "s-up";
    if (d === "bearish") return "s-down";
    return "s-hold";
  }
  function labelArah(d) {
    if (d === "bullish") return "BULLISH";
    if (d === "bearish") return "BEARISH";
    return "NETRAL";
  }
  function labelStance(s) {
    if (s === "buy") return "BUY";
    if (s === "sell") return "SELL";
    return "HOLD";
  }
  function kelasStance(s) {
    if (s === "buy") return "s-up";
    if (s === "sell") return "s-down";
    return "s-hold";
  }

  /* ---------------- fase ---------------- */
  function setFase(n) {
    $("simStage").classList.toggle("s-off", n !== 1);
    $("simConv").classList.toggle("s-on", n === 2);
    $("simDock").classList.toggle("s-on", n === 2);
    if (n === 1) {
      var ta = $("simNews");
      if (ta) ta.focus();
      /* Gulir ke atas hanya saat kembali ke composer. Di fase 2, yang perlu
         dilihat adalah giliran terbaru di bawah. */
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  /* ---------------- status badge ---------------- */
  function setBadge(ok, teks) {
    var b = $("simBadge");
    if (!b) return;
    b.classList.toggle("s-off", !ok);
    $("simBadgeText").textContent = teks;
  }

  /* ---------------- render jawaban ----------------
     Setiap panggilan MENAMBAH satu giliran ke percakapan, tidak menimpa.
     Riwayat hanya hidup selama tab terbuka: backend tidak menyimpan simulasi,
     dan halaman ini tidak menulis apa pun ke browser. */
  function giliran(teks, label, judul, tags, metrik, isi, stances, peringatan) {
    return "<div class='s-turn'>" +
      "<div class='s-msg-user'><div class='s-bubble'>" +
        "<span class='s-lbl'>" + esc(label) + "</span>" +
        "<span>" + esc(teks) + "</span>" +
      "</div></div>" +
      "<article class='s-answer'>" +
        "<div class='s-head'>" +
          "<h2>" + esc(judul) + "</h2>" +
          "<div class='s-tags'>" + tags + "</div>" +
          "<div class='s-metric'>" + metrik + "</div>" +
        "</div>" +
        "<div class='s-body'>" + isi +
          (stances
            ? "<div class='s-stance-title'>Sudut pandang lima persona</div>" +
              "<div class='s-stance-list'>" + stances + "</div>"
            : "") +
          peringatan +
        "</div>" +
      "</article>" +
    "</div>";
  }

  function tambahTurn(html) {
    var box = $("simThread");
    if (!box) return;
    box.insertAdjacentHTML("beforeend", html);
    setFase(2);
    var last = box.lastElementChild;
    if (last) last.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function renderJawaban(teksAsli, j) {
    /* Judul: kalimat ringkas dari server, bukan disusun ulang di klien. */
    var judul = j.summary.split(". ")[0] + ".";

    var tags =
      "<span class='s-tag " + kelasArah(j.direction) + "'>" + labelArah(j.direction) + "</span>" +
      "<span class='s-tag'>" + esc(j.target) + "</span>" +
      "<span class='s-tag'>" + esc(j.input_kind) + "</span>" +
      "<span class='s-tag'>horizon " + esc(j.horizon) + "</span>" +
      (j.is_rumor ? "<span class='s-tag s-down'>keyakinan &times;0,60</span>" : "");

    var metrik =
      "<span>skor <b>" + esc(A.fmt(j.score)) + "</b></span>" +
      "<span>keyakinan <b>" + esc(nilai01(j.confidence)) + "</b></span>" +
      "<span>penalti <b>&times;" + esc(nilai01(j.penalty)) + "</b></span>" +
      "<span>model <b>" + esc(j.model_version) + "</b></span>";

    /* Paragraf: ringkasan utuh, lalu catatan model bila ada.
       `degraded` adalah LIST (kosong saat sehat), jadi list kosong berarti
       tidak ada catatan -- jangan cek truthiness saja. */
    var par = "<p>" + esc(j.summary) + "</p>";
    if (Array.isArray(j.degraded) && j.degraded.length) {
      par += "<p><strong>Catatan model:</strong> " + esc(j.degraded.join("; ")) + "</p>";
    } else if (typeof j.degraded === "string" && j.degraded) {
      par += "<p><strong>Catatan model:</strong> " + esc(j.degraded) + "</p>";
    }
    if (j.disclaimer) par += "<p class='s-src'>" + esc(j.disclaimer) + "</p>";

    /* Stance: baris + alasan apa adanya dari server. */
    var rows = "";
    for (var i = 0; i < j.stances.length; i++) {
      var s = j.stances[i];
      rows +=
        "<div class='s-stance'>" +
        "<span class='s-who'>" + esc(s.persona_name || s.persona_id) + "</span>" +
        "<span class='s-pill " + kelasStance(s.stance) + "'>" + labelStance(s.stance) + "</span>" +
        "<span class='s-str'>" + esc(A.fmt(s.strength)) + "</span>" +
        (s.rationale ? "<span class='s-why'>" + esc(s.rationale) + "</span>" : "") +
        "</div>";
    }

    /* Peringatan: semua ditampilkan, tidak ada yang disembunyikan. */
    var per = "";
    if (j.warnings && j.warnings.length) {
      var li = "";
      for (var k = 0; k < j.warnings.length; k++) li += "<li>" + esc(j.warnings[k]) + "</li>";
      per = "<div class='s-disc'><strong>Perlu dibaca.</strong><ul>" + li + "</ul></div>";
    }

    tambahTurn(giliran(
      teksAsli,
      (j.input_kind === "rumor" ? "rumor yang diuji" : "berita yang diuji"),
      judul, tags, metrik, par, rows, per
    ));
  }

  /* ---------------- kirim ---------------- */
  function kirim(teks, sumber) {
    if (sedangKirim) return;
    teks = (teks || "").trim();
    if (!teks) {
      setBadge(false, "teks masih kosong");
      return;
    }

    var target = $("simTarget").value;
    var kind = $("simKind").value;
    sedangKirim = true;
    $("simSend").disabled = true;
    $("simSendDock").disabled = true;
    setBadge(true, "menganalisis...");

    A.api("/api/simulate", {
      method: "POST",
      body: JSON.stringify({ text: teks, kind: kind, target: target })
    }).then(function (j) {
      setBadge(true, "siap · " + j.model_version);
      renderJawaban(teks, j);
    }).catch(function (err) {
      /* Penolakan gerbang (422): tampilkan alasan server apa adanya. */
      var d = err && err.payload && err.payload.detail;
      if (err && err.status === 422 && d && d.pesan) {
        setBadge(false, "ditolak");
        var isi = "<p>" + esc(d.pesan) + "</p>";
        if (d.contoh && d.contoh.length) {
          isi += "<p><strong>Contoh yang diterima:</strong> " + esc(d.contoh.slice(0, 2).join(" | ")) + "</p>";
        }
        tambahTurn(giliran(teks, "ditolak", "Tidak dianalisis",
          "<span class='s-tag s-hold'>DITOLAK</span>", "", isi, "", ""));
      } else {
        setBadge(false, "API tidak menjawab");
        tambahTurn(giliran(teks, "gagal", "Tidak ada hasil",
          "<span class='s-tag s-hold'>GAGAL</span>", "",
          "<p>Analisis tidak dapat dijalankan karena API tidak menjawab. " +
          "Halaman ini tidak menampilkan angka contoh.</p>", "", ""));
      }
    }).then(function () {
      sedangKirim = false;
      $("simSend").disabled = false;
      $("simSendDock").disabled = false;
      /* Kosongkan input agar uji berikutnya tinggal tempel. */
      $("simNewsDock").value = "";
    });
  }

  /* ---------------- pemasangan ---------------- */
  function pasang() {
    var ta = $("simNews");
    if (!ta) return; /* bukan halaman Simulations */

    $("simSend").addEventListener("click", function () {
      kirim(ta.value, null);
    });
    ta.addEventListener("keydown", function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") kirim(ta.value, null);
    });

    $("simSendDock").addEventListener("click", function () {
      kirim($("simNewsDock").value, null);
    });
    $("simNewsDock").addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        kirim($("simNewsDock").value, null);
      }
    });

    $("simUlang").addEventListener("click", function () {
      /* Mulai percakapan baru: kosongkan riwayat, bukan menimpa satu kartu. */
      $("simThread").innerHTML = "";
      setFase(1);
    });

    /* Chip contoh: isi textarea, jangan langsung kirim. */
    var chips = document.querySelectorAll("#simRoot .s-chip");
    for (var i = 0; i < chips.length; i++) {
      chips[i].addEventListener("click", function () {
        ta.value = this.getAttribute("data-fill");
        ta.focus();
      });
    }

    /* Target di dock mengikuti pilihan di fase 1. */
    $("simTarget").addEventListener("change", function () {
      $("simTargetDock").textContent = this.value;
    });

    setFase(1);
  }

  A.renderPage = function () {
    /* Badge mengikuti hasil deteksi API yang sudah dilakukan A.boot(). */
    setBadge(A.state.apiReachable !== false,
      A.state.apiReachable === false ? "API tidak terjangkau" : "siap · model termuat");
    pasang();
  };

  A.boot();
})(window.ARCAS);
