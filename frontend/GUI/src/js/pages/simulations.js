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
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  /* ---------------- status badge ---------------- */
  function setBadge(ok, teks) {
    var b = $("simBadge");
    if (!b) return;
    b.classList.toggle("s-off", !ok);
    $("simBadgeText").textContent = teks;
  }

  /* ---------------- render jawaban ---------------- */
  function renderJawaban(teksAsli, j) {
    $("simTeksUser").textContent = teksAsli;
    $("simUkuran").textContent = (j.input_kind === "rumor" ? "rumor yang diuji" : "berita yang diuji");

    /* Judul: kalimat ringkas dari server, bukan disusun ulang di klien. */
    $("simJudul").textContent = j.summary.split(". ")[0] + ".";

    var tags =
      "<span class='s-tag " + kelasArah(j.direction) + "'>" + labelArah(j.direction) + "</span>" +
      "<span class='s-tag'>" + esc(j.target) + "</span>" +
      "<span class='s-tag'>" + esc(j.input_kind) + "</span>" +
      "<span class='s-tag'>horizon " + esc(j.horizon) + "</span>" +
      (j.is_rumor ? "<span class='s-tag s-down'>keyakinan &times;0,60</span>" : "");
    $("simTags").innerHTML = tags;

    var metrik =
      "<span>skor <b>" + esc(A.fmt(j.score)) + "</b></span>" +
      "<span>keyakinan <b>" + esc(nilai01(j.confidence)) + "</b></span>" +
      "<span>penalti <b>&times;" + esc(nilai01(j.penalty)) + "</b></span>" +
      "<span>model <b>" + esc(j.model_version) + "</b></span>";
    $("simMetrik").innerHTML = metrik;

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
    $("simParagraf").innerHTML = par;

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
    $("simStances").innerHTML = rows;

    /* Peringatan: semua ditampilkan, tidak ada yang disembunyikan. */
    var per = $("simPeringatan");
    if (j.warnings && j.warnings.length) {
      var li = "";
      for (var k = 0; k < j.warnings.length; k++) li += "<li>" + esc(j.warnings[k]) + "</li>";
      per.innerHTML = "<strong>Perlu dibaca.</strong><ul>" + li + "</ul>";
      per.hidden = false;
    } else {
      per.hidden = true;
      per.innerHTML = "";
    }

    setFase(2);
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
        $("simTeksUser").textContent = teks;
        $("simUkuran").textContent = "ditolak";
        $("simJudul").textContent = "Tidak dianalisis";
        $("simTags").innerHTML = "<span class='s-tag s-hold'>DITOLAK</span>";
        $("simMetrik").innerHTML = "";
        $("simParagraf").innerHTML = isi;
        $("simStances").innerHTML = "";
        $("simPeringatan").hidden = true;
        setFase(2);
      } else {
        setBadge(false, "API tidak menjawab");
        $("simTeksUser").textContent = teks;
        $("simUkuran").textContent = "gagal";
        $("simJudul").textContent = "Tidak ada hasil";
        $("simTags").innerHTML = "<span class='s-tag s-hold'>GAGAL</span>";
        $("simMetrik").innerHTML = "";
        $("simParagraf").innerHTML =
          "<p>Analisis tidak dapat dijalankan karena API tidak menjawab. " +
          "Halaman ini tidak menampilkan angka contoh.</p>";
        $("simStances").innerHTML = "";
        $("simPeringatan").hidden = true;
        setFase(2);
      }
    }).then(function () {
      sedangKirim = false;
      $("simSend").disabled = false;
      $("simSendDock").disabled = false;
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
    /* Badge mengikuti hasil deteksi API yang sudah dilakukan A.boot().
       Sengaja tidak menulis "model termuat": status bobot model baru terbukti
       setelah satu permintaan berhasil, dan di situ badge diganti versi model. */
    setBadge(A.state.apiReachable !== false,
      A.state.apiReachable === false ? "API tidak terjangkau" : "siap · API terjangkau");
    pasang();
  };

  A.boot();
})(window.ARCAS);
