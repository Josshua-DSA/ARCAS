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

  /* ---------------- kartu bawah: backtesting + keputusan ----------------
     Keduanya dirender di klien dari respons yang SUDAH ada:
     - backtest  : GET /api/stats/{target} (OLS / Granger / event study)
     - keputusan : agregasi 5 stance dari respons /api/simulate itu sendiri
     Tidak ada angka yang dikarang; bila sumber kosong, kartu mengatakannya. */

  var statCache = {};   /* target -> {prices, sentiments} | "gagal" */
  var idKartuTerakhir = "";
  var grafik = {};      /* idKartu -> instance ECharts */

  function kartuBawah(j) {
    nomorGiliran++;
    var id = "sim-" + nomorGiliran;
    idKartuTerakhir = id;
    return "<div class='s-cards'>" +
      kartuBacktest(id, j) + kartuKeputusan(id, j) +
    "</div>";
  }

  /* Kartu kiri: harga aset 180 hari terakhir. Tanpa legenda -- hanya satu
     deret, legenda tidak menambah informasi apa pun. Bukan lagi tabel
     OLS/Granger/CAR: angka itu sudah ada di Lab Riset, dan di sini yang
     dibutuhkan pembaca adalah bentuk pergerakan harganya. */
  function kartuBacktest(id, j) {
    return "<section class='s-card s-card-backtest' id='" + id + "-backtest'" +
        " data-target='" + esc(j.target) + "'>" +
      "<header class='s-card-head'>" +
        "<span class='s-card-kicker'>Backtesting &middot; 180 hari</span>" +
        "<h3>" + esc(A.metaFor(j.target).name) + " &middot; " + esc(j.target) + "</h3>" +
      "</header>" +
      "<div class='s-card-body' id='" + id + "-grafik'>" +
        "<p class='s-card-note'>memuat grafik&hellip;</p>" +
      "</div>" +
    "</section>";
  }

  function kartuKeputusan(id, j) {
    return "<section class='s-card s-card-decision' id='" + id + "-keputusan'" +
        " data-target='" + esc(j.target) + "'>" +
      "<header class='s-card-head'>" +
        "<span class='s-card-kicker'>Decision making</span>" +
        "<h3>Keputusan</h3>" +
      "</header>" +
      /* -isi, bukan -keputusan: id section sudah memakai akhiran itu dan
         getElementById hanya mengembalikan yang pertama. */
      "<div class='s-card-body' id='" + id + "-keputusan-isi'>" +
        "<p class='s-card-note'>memuat bukti historis&hellip;</p>" +
      "</div>" +
    "</section>";
  }

  /* Isi kartu keputusan setelah seri harga tersedia: keputusan butuh
     hit-rate, dan hit-rate butuh sentimen + harga. */
  function isiKeputusan(idKartu, j, seri) {
    var box = $(idKartu);
    if (!box) return;
    if (seri === "gagal") {
      box.innerHTML = "<p class='s-card-note'>Bukti historis tidak dapat " +
        "dimuat (API tidak menjawab). Halaman ini tidak menampilkan angka contoh.</p>";
      return;
    }

    var arah = j.direction === "bullish" ? "naik"
             : j.direction === "bearish" ? "turun" : "netral";
    var bukti = {
      T1: A.hitungBukti(seri.sentiments, seri.prices, arah, 1),
      T3: A.hitungBukti(seri.sentiments, seri.prices, arah, 3)
    };
    var d = A.keputusanBerita({
      stances: j.stances || [],
      confidence: j.confidence,
      warnings: j.warnings || [],
      arah: arah,
      bukti: bukti,
      persentil: persentil20(seri.prices)
    });
    box.innerHTML = isiKartuKeputusan(d);
  }

  function isiKartuKeputusan(d) {
    var kls = d.keputusan === "beli" ? "s-up"
            : d.keputusan === "jual" ? "s-down" : "s-hold";
    var label = d.keputusan === "beli" ? "BELI"
              : d.keputusan === "jual" ? "JUAL"
              : d.keputusan === "tahan" ? "TAHAN" : "TIDAK ADA SINYAL";

    return "<div class='s-decide'><span class='s-pill " + kls + "'>" + label + "</span>" +
        "<span class='s-decide-score'>skor persona <b>" +
        (d.skor_persona >= 0 ? "+" : "") + nilai01(d.skor_persona) + "</b>" +
        (d.label !== "persona" ? " &middot; " + esc(d.label) : "") +
        "</span></div>" +
      "<p class='s-card-note'>" + esc(d.alasan) + "</p>" +
      barisBukti(d) +
      (d.catatan ? "<p class='s-card-note'>" + esc(d.catatan) + "</p>" : "") +
      "<p class='s-card-note s-src'>Keputusan ini agregasi lima persona dan " +
        "hit-rate historis 180 hari, bukan rekomendasi investasi.</p>";
  }

  /* Bukti historis selalu ditampilkan, termasuk saat n kecil: angka yang
     tidak layak disimpulkan tetap berguna asal n-nya ikut terlihat. */
  function barisBukti(d) {
    if (d.hit_rate === null || d.hit_rate === undefined) return "";
    var pers = Math.round(d.hit_rate * 100) + "%";
    var tebal = d.layak ? " s-tegas" : "";
    return "<div class='s-bukti'>" +
      "<div class='s-bt-row'><span class='s-bt-k'>kejadian serupa</span>" +
        "<span class='s-bt-v" + tebal + "'>n " + d.n + "</span></div>" +
      "<div class='s-bt-row'><span class='s-bt-k'>searah berita (T+3)</span>" +
        "<span class='s-bt-v" + tebal + "'>" + pers + "</span></div>" +
      "<div class='s-bt-row'><span class='s-bt-k'>rata-rata T+3</span>" +
        "<span class='s-bt-v'>" + persenBertanda(d.rata2) + "</span></div>" +
      "<div class='s-bt-row'><span class='s-bt-k'>rata-rata T+1</span>" +
        "<span class='s-bt-v'>" + persenBertanda(d.rata2_t1) + "</span></div>" +
    "</div>";
  }

  function persenBertanda(v) {
    if (v === null || v === undefined) return "n/a";
    var n = Number(v) * 100;
    return (n >= 0 ? "+" : "") + n.toFixed(2) + "%";
  }

  /* Grafik harga: ECharts lokal, renderer SVG supaya teksnya tetap tajam dan
     kartu tidak butuh canvas bitmap. */
  function gambarGrafik(idKartu, target, prices) {
    var el = $(idKartu);
    if (!el) return;
    if (typeof echarts === "undefined") {
      el.innerHTML = "<p class='s-card-note'>Pustaka grafik lokal belum " +
        "termuat (src/js/echarts.min.js).</p>";
      return;
    }
    if (grafik[idKartu]) {
      grafik[idKartu].dispose();
      delete grafik[idKartu];
    }

    var info = A.metaFor(target);
    var tanggal = [], tutup = [];
    for (var i = 0; i < prices.length; i++) {
      if (prices[i].close === null || prices[i].close === undefined) continue;
      tanggal.push(prices[i].date);
      tutup.push(Number(prices[i].close));
    }
    if (!tanggal.length) {
      el.innerHTML = "<p class='s-card-note'>Belum ada harga untuk " +
        esc(target) + ".</p>";
      return;
    }

    el.innerHTML = "";
    var c = echarts.init(el, null, { renderer: "svg" });
    grafik[idKartu] = c;
    c.setOption({
      backgroundColor: "transparent",
      grid: { left: 4, right: 48, top: 8, bottom: 4, containLabel: true },
      tooltip: {
        trigger: "axis", backgroundColor: "#2C2727", borderWidth: 0,
        textStyle: { color: "#F6F4F4", fontFamily: "JetBrains Mono, monospace", fontSize: 11 },
        formatter: function (ps) {
          return ps[0].axisValue + " &middot; " + Number(ps[0].data).toLocaleString("id-ID");
        }
      },
      xAxis: {
        type: "category", data: tanggal, boundaryGap: false,
        axisLine: { lineStyle: { color: "#DDD8D8" } }, axisTick: { show: false },
        axisLabel: { color: "#8A8282", fontFamily: "JetBrains Mono, monospace",
          fontSize: 9, hideOverlap: true }
      },
      yAxis: {
        type: "value", scale: true, position: "right",
        splitLine: { lineStyle: { color: "#DDD8D8", opacity: 0.6 } },
        axisLabel: { color: "#8A8282", fontFamily: "JetBrains Mono, monospace", fontSize: 9 }
      },
      series: [{
        type: "line", data: tutup, showSymbol: false,
        lineStyle: { width: 2, color: info.color },
        itemStyle: { color: info.color },
        areaStyle: { opacity: 0.08, color: info.color }
      }]
    });
  }

  /* Satu permintaan /api/series per target dipakai bersama: grafik butuh
     prices, keputusan butuh sentiments + prices untuk hitungBukti. */
  function muatSeri(target, selesai) {
    if (statCache[target] === "gagal") { selesai("gagal"); return; }
    if (statCache[target]) { selesai(statCache[target]); return; }
    var mulai = new Date(Date.now() - 179 * 86400000);
    A.api("/api/series/" + encodeURIComponent(target) +
          "?start_date=" + A.localISO(mulai)).then(function (d) {
      statCache[target] = { prices: (d && d.prices) || [], sentiments: (d && d.sentiments) || [] };
      selesai(statCache[target]);
    }).catch(function () {
      statCache[target] = "gagal";
      selesai("gagal");
    });
  }

  function isiBacktest(idKartu, target, seri) {
    var box = $(idKartu);
    if (!box) return;
    if (seri === "gagal") {
      box.innerHTML = "<p class='s-card-note'>Harga tidak dapat dimuat " +
        "(API tidak menjawab). Kartu ini tidak menampilkan angka contoh.</p>";
      return;
    }
    gambarGrafik(idKartu, target, seri.prices || []);
  }

  /* Persentil close terakhir dalam 20 sesi terakhir (0..1). Dipakai sebagai
     keterangan "harga sudah di puncak/dasar", bukan sebagai keputusan. */
  function persentil20(prices) {
    var tutup = [];
    for (var i = 0; i < (prices || []).length; i++) {
      if (prices[i].close !== null && prices[i].close !== undefined) {
        tutup.push(Number(prices[i].close));
      }
    }
    if (tutup.length < 2) return null;
    var jendela = tutup.slice(-20);
    var akhir = jendela[jendela.length - 1];
    var bawah = Math.min.apply(null, jendela), atas = Math.max.apply(null, jendela);
    if (atas === bawah) return 0.5;
    return (akhir - bawah) / (atas - bawah);
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

    /* Satu permintaan seri untuk dua kartu. Kartu kanan menunggu angkanya;
       kartu kiri langsung menggambar begitu seri tiba. */
    var id = idKartuTerakhir;
    muatSeri(j.target, function (seri) {
      isiBacktest(id + "-grafik", j.target, seri);
      isiKeputusan(id + "-keputusan-isi", j, seri);
    });
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

    /* Satu listener resize untuk semua grafik, dipasang sekali per halaman.
       Sebelumnya tiap gambarGrafik menambah satu listener milik dirinya dan
       tidak pernah dilepas: empat giliran = empat listener yang menahan
       instance ECharts lama tetap hidup. */
    if (!pasang._resize) {
      pasang._resize = true;
      window.addEventListener("resize", function () {
        for (var k in grafik) if (grafik[k]) grafik[k].resize();
      });
    }

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
      /* Mulai percakapan baru: kosongkan riwayat, bukan menimpa satu kartu.
         Instance ECharts dilepas dulu -- mengosongkan innerHTML saja
         meninggalkan grafik yang masih memegang elemen DOM yang sudah hilang. */
      for (var k in grafik) if (grafik[k]) grafik[k].dispose();
      grafik = {};
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

  /* Ekspor untuk tes: dua kartu satu giliran, tanpa DOM. */
  A.__ujiKartu = function (id, target) {
    var j = { target: target };
    return { backtest: kartuBacktest(id, j), keputusan: kartuKeputusan(id, j) };
  };

  A.renderPage = function () {
    /* Badge mengikuti hasil deteksi API yang sudah dilakukan A.boot(). */
    setBadge(A.state.apiReachable !== false,
      A.state.apiReachable === false ? "API tidak terjangkau" : "siap · model termuat");
    pasang();
  };

  A.boot();
})(window.ARCAS);
