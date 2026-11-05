/* Simulations: alur dua fase mengikuti mockup-simulations.html.

   Fase 1 = composer di tengah. Fase 2 = percakapan + kartu jawaban.
   Semua angka berasal dari POST /api/simulate. Tidak ada angka contoh:
   kalau API tidak menjawab, halaman mengatakannya. */
(function (A) {
  "use strict";

  var esc = A.esc;
  var sedangKirim = false;
  /* Penghitung giliran untuk id kartu backtesting. `run_id` dari server bisa
     null (penyimpanan jejak gagal) sehingga dua giliran bisa bertabrakan di
     id yang sama; penghitung ini selalu unik per tab. */
  var nomorGiliran = 0;

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

  /* Angka bertanda untuk koefisien/p-value. A.fmt() menambahkan "+" di depan
     semua nilai positif, yang salah untuk p-value (p +0.98 tidak berarti apa-apa;
     p-value adalah besaran 0..1 tanpa arah). */
  function angka(v, d) {
    if (v === null || v === undefined || Number.isNaN(Number(v))) return "n/a";
    return Number(v).toFixed(d);
  }

  /* ---------------- kartu bawah: backtesting + keputusan ----------------
     Keduanya dirender di klien dari respons yang SUDAH ada:
     - backtest  : GET /api/stats/{target} (OLS / Granger / event study)
     - keputusan : agregasi 5 stance dari respons /api/simulate itu sendiri
     Tidak ada angka yang dikarang; bila sumber kosong, kartu mengatakannya. */

  var statCache = {};   /* target -> array baris | "gagal" */
  var idKartuTerakhir = "";

  function kartuBawah(j) {
    return "<div class='s-cards'>" + kartuBacktest(j) + kartuKeputusan(j) + "</div>";
  }

  /* Backtesting: ringkas tiga jenis uji, satu baris wakil per jenis.
     Rincian per lag tetap di Lab Riset; menampilkan semuanya di sini hanya
     jadi kebisingan. */
  function kartuBacktest(j) {
    nomorGiliran++;
    var id = "bt-" + nomorGiliran;
    idKartuTerakhir = id;
    return "<section class='s-card s-card-backtest' data-target='" + esc(j.target) + "'>" +
      "<header class='s-card-head'>" +
        "<span class='s-card-kicker'>Backtesting</span>" +
        "<h3>Evaluasi dari sentimen &middot; " + esc(j.target) + "</h3>" +
      "</header>" +
      "<div class='s-card-body' id='" + id + "'>" +
        "<p class='s-card-note'>memuat statistik&hellip;</p>" +
      "</div>" +
    "</section>";
  }

  function kartuKeputusan(j) {
    var d = A.agregasiStance(j.stances || [], j.confidence, j.warnings || []);
    var kls = d.keputusan === "beli" ? "s-up"
            : d.keputusan === "jual" ? "s-down" : "s-hold";
    var label = d.keputusan === "beli" ? "BELI"
              : d.keputusan === "jual" ? "JUAL"
              : d.keputusan === "tahan" ? "TAHAN" : "TIDAK ADA SINYAL";

    var alasan;
    if (d.keputusan === "tidak_ada_sinyal") {
      alasan = Number(j.confidence) < d.ambang_keyakinan
        ? "Keyakinan model (" + nilai01(j.confidence) + ") di bawah ambang " +
          nilai01(d.ambang_keyakinan) + ", jadi tidak ada dasar untuk mengambil posisi."
        : "Kelima persona tidak cukup searah untuk disebut sinyal.";
    } else {
      alasan = d.searah.buy + " beli, " + d.searah.hold + " tahan, " +
               d.searah.sell + " jual dari " + d.jumlah_persona + " persona; " +
               "skor agregat " + (d.skor >= 0 ? "+" : "") + nilai01(d.skor) + ".";
    }

    return "<section class='s-card s-card-decision'>" +
      "<header class='s-card-head'>" +
        "<span class='s-card-kicker'>Decision making</span>" +
        "<h3>Keputusan</h3>" +
      "</header>" +
      "<div class='s-card-body'>" +
        "<div class='s-decide'><span class='s-pill " + kls + "'>" + label + "</span>" +
          "<span class='s-decide-score'>skor agregat <b>" +
          (d.skor >= 0 ? "+" : "") + nilai01(d.skor) + "</b></span></div>" +
        "<p class='s-card-note'>" + esc(alasan) + "</p>" +
        "<p class='s-card-note s-src'>Keputusan ini agregasi aturan lima persona, " +
          "bukan rekomendasi investasi.</p>" +
      "</div>" +
    "</section>";
  }

  function isiBacktest(idKartu, target, rows) {
    var box = $(idKartu);
    if (!box) return;

    if (rows === "gagal") {
      box.innerHTML = "<p class='s-card-note'>Statistik tidak dapat dimuat " +
        "(API tidak menjawab). Kartu ini tidak menampilkan angka contoh.</p>";
      return;
    }
    if (!rows || !rows.length) {
      box.innerHTML = "<p class='s-card-note'>Belum ada hasil statistik untuk " +
        esc(target) + ". Jalankan <code>pipeline stats</code> lebih dulu.</p>";
      return;
    }

    var jenis = { ols: null, granger: null, event_study: null };
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i];
      if (!(r.test in jenis)) continue;
      if (jenis[r.test] === null || (r.n_obs || 0) > (jenis[r.test].n_obs || 0)) {
        jenis[r.test] = r;
      }
    }

    function baris(nama, r) {
      if (!r) {
        return "<div class='s-bt-row'><span class='s-bt-k'>" + nama + "</span>" +
               "<span class='s-bt-v muted'>belum dihitung</span></div>";
      }
      var p = (r.p_adjusted === null || r.p_adjusted === undefined) ? r.p_value : r.p_adjusted;
      var sig = (p !== null && p !== undefined && Number(p) < 0.05);
      return "<div class='s-bt-row'>" +
        "<span class='s-bt-k'>" + nama + "</span>" +
        "<span class='s-bt-v'>" + A.fmt(r.estimate, 4) + "</span>" +
        "<span class='s-bt-p" + (sig ? " sig" : "") + "'>p " + angka(p, 3) + "</span>" +
        "<span class='s-bt-n'>n " + (r.n_obs === null ? "n/a" : r.n_obs) + "</span>" +
      "</div>";
    }

    box.innerHTML =
      baris("OLS (lag 0)", jenis.ols) +
      baris("Granger (lag terbaik)", jenis.granger) +
      baris("Event study (CAR)", jenis.event_study) +
      "<p class='s-card-note'>p &lt; 0,05 ditandai tebal. Asosiasi historis, " +
      "bukan bukti sebab-akibat.</p>";
  }

  function muatBacktest(idKartu, target) {
    if (statCache[target] === "gagal") { isiBacktest(idKartu, target, "gagal"); return; }
    if (statCache[target]) { isiBacktest(idKartu, target, statCache[target]); return; }
    A.api("/api/stats/" + encodeURIComponent(target)).then(function (rows) {
      statCache[target] = rows || [];
      isiBacktest(idKartu, target, statCache[target]);
    }).catch(function () {
      statCache[target] = "gagal";
      isiBacktest(idKartu, target, "gagal");
    });
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
  function giliran(teks, label, judul, tags, metrik, isi, kartu, peringatan) {
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
        "<div class='s-body'>" + isi + peringatan + "</div>" +
        kartu +
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
      judul, tags, metrik, par, kartuBawah(j), per
    ));
    muatBacktest(idKartuTerakhir, j.target);
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
      /* 422 punya dua arti yang sangat berbeda dan tidak boleh disamakan:
         - kode "model_tidak_ada" : server tidak punya bobot, teksnya tidak salah
         - kode lain              : teksnya memang bukan berita/rumor
         Menyebut keduanya "DITOLAK" membuat pengguna mengira beritanya yang
         salah padahal mesinnya yang belum siap. */
      var d = err && err.payload && err.payload.detail;
      if (err && err.status === 422 && d && d.pesan) {
        if (d.kode === "model_tidak_ada") {
          setBadge(false, "model tidak termuat");
          tambahTurn(giliran(teks, "tidak dapat dianalisis", "Model belum termuat",
            "<span class='s-tag s-hold'>MODEL TIDAK ADA</span>", "",
            "<p>Server tidak menemukan bobot model, jadi teks ini belum bisa " +
            "dinilai. Ini masalah pemasangan di server, bukan kesalahan teks yang " +
            "kamu kirim.</p>" +
            "<p class='s-src'>" + esc(d.pesan) + "</p>" +
            "<p>Perbaikan di sisi server: jalankan <code>python scripts/fetch_weights.py</code> " +
            "lalu mulai ulang API. Bobot tidak ikut repo karena dikecualikan " +
            "<code>.gitignore</code>.</p>", "", ""));
          return;
        }
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
