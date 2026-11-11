/* Research Lab: pilih berita, lihat titiknya di grafik pasar, lalu baca
   keputusan yang lahir dari backtesting harga dan sentimennya.

   Halaman ini hanya fetch dan render. Semua angka dari API; tidak ada data
   contoh. Yang belum tersedia ditulis belum tersedia, bukan dikarang. */
(function (A) {
  "use strict";
  var esc = A.esc, fmt = A.fmt;

  var S = { prices: [], sents: [], news: [], selected: null };

  function $(id) { return document.getElementById(id); }

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
  function drawPriceChart() {
    var el = $("priceChart");
    if (!el || typeof echarts === "undefined") {
      A.showState("chartState", "Pustaka grafik lokal belum termuat.");
      return;
    }
    if (!priceChart) {
      priceChart = echarts.init(el);
      window.addEventListener("resize", function () { if (priceChart) priceChart.resize(); });
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

    var sel = S.news[S.selected];
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
      /* containLabel: tanpa ini label sumbu "4,700" kepotong digit pertama
         karena left 58px tidak cukup memuat angka emapatan. */
      grid: { left: 58, right: 22, top: 26, bottom: 44, containLabel: true },
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

  /* ---------------- jejak harga setelah berita ----------------
     Dihitung dari deret harga yang sudah dimuat. Tidak ada request baru dan
     tidak ada angka karangan. T+n memakai indeks baris deret harga, yang hanya
     berisi hari bursa -- bukan hari kalender.

     Dua sebab kosong dibedakan karena artinya berbeda jauh:
       "sesi belum terjadi"    -> T+n melewati ujung deret, harganya memang
                                  belum ada. Bukan cacat data.
       "tanggal tidak di deret" -> idx = -1, tanggal berita tidak ada di
                                  rentang harga yang dimuat. Data bolong.
     Dulu keduanya tampil "di luar deret", jadi cacat data tak bisa dibedakan
     dari sesi yang belum berjalan. */
  var JENDELA = [1, 3, 5];
  var KUNCI_JENDELA = { 1: "T+1", 3: "T+3", 5: "T+5" };

  function jejakHarga(idx, dates, closes) {
    var hasil = [];
    for (var j = 0; j < JENDELA.length; j++) {
      var n = JENDELA[j];
      var target = idx + n;
      var sebab = null;
      if (idx < 0) {
        sebab = "tanggal tidak di deret";
      } else if (target >= closes.length) {
        sebab = "sesi belum terjadi";
      } else if (!isFinite(closes[target]) || !isFinite(closes[idx])) {
        sebab = "harga tidak tersedia";
      }
      var tersedia = sebab === null;
      hasil.push({
        label: KUNCI_JENDELA[n],
        persen: tersedia ? (closes[target] / closes[idx] - 1) * 100 : null,
        tanggal: tersedia ? dates[target] : null,
        sebab: sebab
      });
    }
    return hasil;
  }

  /* Hanya untuk tes node: logika jejak menentukan angka yang dilihat pembaca.
     Didaftarkan di sini, bukan di akhir berkas, karena guard `if (!picker)`
     di bawah membuat eksekusi berhenti lebih awal saat tanpa DOM. */
  A.__ujiJejak = jejakHarga;

  function renderJejak(n, near, dates, closes) {
    var box = $("jejakHarga");
    if (!box) return;
    var idx = near ? dates.indexOf(near.date) : -1;
    if (!near) {
      box.innerHTML = "<p class='rl-empty'>Tanggal berita tidak jatuh di rentang harga mana pun, " +
        "jadi jejak setelahnya tidak bisa dihitung.</p>";
      return;
    }
    var arah = String(n.direction || "neutral").toLowerCase();
    var komentar = arah === "netral" || arah === "neutral"
      ? "Berita ini tanpa arah, jadi tidak ada yang bisa dicocokkan."
      : "Arah berita " + arah + "; bandingkan dengan tanda persen di atas.";
    box.innerHTML = "<div class='rl-after'>" +
      jejakHarga(idx, dates, closes).map(function (c) {
        var teks = c.persen == null ? "belum tersedia"
          : (c.persen > 0 ? "+" : "") + c.persen.toFixed(2) + "%";
        var warna = c.persen == null ? "var(--on-dark-muted)"
          : c.persen > 0 ? "var(--up-dark)" : c.persen < 0 ? "var(--down-dark)" : "var(--on-dark-primary)";
        /* Sebab kosong ditulis apa adanya: "sesi belum terjadi" wajar,
           "tanggal tidak di deret" menandakan data bolong. */
        return "<div class='rl-after-cell'>" +
          "<p class='rl-after-k'>" + esc(c.label) + "</p>" +
          "<p class='rl-after-v' style='color:" + warna + "'>" + esc(teks) + "</p>" +
          "<p class='rl-after-sub'>" + esc(c.tanggal || c.sebab || "") + "</p></div>";
      }).join("") + "</div>" +
      "<p class='rl-after-sub' style='margin-top:8px'>" + esc(komentar) +
      " Perubahan dihitung dari harga tutup hari berita, bukan dari harga saat berita terbit.</p>";
  }

  /* ---------------- pemilih berita ----------------
     Hanya 5 kartu terbaru yang dirender. Sebelumnya 50 kartu dirender ke satu
     baris horizontal 13.394px: 45 di antaranya di luar layar tanpa petunjuk,
     dan "50 berita" di layar terbaca sebagai 5 berita. Angka total tetap
     disebut supaya pembaca tahu ini pilihan, bukan seluruh arsip. */
  var MAKS_KARTU = 5;

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
    var tampil = S.news.slice(0, MAKS_KARTU);
    box.innerHTML = tampil.map(function (n, i) {
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
      (n.rationale ? "<p class='rl-sel-note'>" + esc(n.rationale) + "</p>" : "") +
      "<div id='jejakHarga'></div>";

    var dates = S.prices.map(function (p) { return p.date; });
    var closes = S.prices.map(function (p) { return Number(p.close); });
    renderJejak(n, near, dates, closes);
  }

  /* ---------------- keputusan dari backtesting ----------------

     Panel penuh di bawah grafik dan uji statistik. Kartu uji memeriksa
     asosiasi harian sentimen dan harga; panel ini menjawab pertanyaan tindak
     lanjutnya: "kalau berita seperti ini keluar, arah apa yang terbukti
     menguntungkan?" Persis alur keputusan di Simulations, hanya tanpa lima
     persona: basisnya riset kuantitatif penuh, dan bukti yang tipis diakui
     sebagai bukti tipis. */
  function renderKeputusan() {
    var box = $("keputusanBox");
    if (!box) return;
    var n = (S.selected != null) ? S.news[S.selected] : null;
    if (!n) {
      box.innerHTML = "<p class='rl-k-note' style='margin:0'>Pilih satu berita " +
        "di atas untuk melihat keputusannya.</p>";
      return;
    }

    var arah = n.direction === "bullish" ? "naik"
             : n.direction === "bearish" ? "turun" : "netral";

    if (!S.prices.length || !S.sents.length) {
      box.innerHTML =
        "<h3 class='rl-sel-title'>" + esc(judulBerita(n)) + "</h3>" +
        "<p class='rl-k-note'>Keputusan belum bisa dihitung: deret harga atau " +
        "sentimen harian target ini tidak tersedia. Tidak ada angka pengganti.</p>";
      return;
    }

    var bukti = {
      T1: A.hitungBukti(S.sents, S.prices, arah, 1),
      T3: A.hitungBukti(S.sents, S.prices, arah, 3)
    };
    var d = A.keputusanDariBukti(arah, bukti);
    var kls = d.keputusan === "beli" ? "rl-up"
            : d.keputusan === "jual" ? "rl-down" : "rl-hold";
    var label = d.keputusan === "beli" ? "BELI"
              : d.keputusan === "jual" ? "JUAL"
              : d.keputusan === "tahan" ? "TAHAN" : "TIDAK ADA SINYAL";

    box.innerHTML =
      "<h3 class='rl-sel-title'>" + esc(judulBerita(n)) + "</h3>" +
      "<div class='rl-decide-body'><span class='rl-decide-pill " + kls + "'>" + label + "</span>" +
        "<span class='rl-k-note' style='margin:0'>" + esc(d.label) + "</span></div>" +
      "<p class='rl-k-note'>" + esc(d.alasan) + "</p>" +
      barisBuktiKeputusan(d) +
      (d.catatan ? "<p class='rl-k-note'>" + esc(d.catatan) + "</p>" : "") +
      "<p class='rl-k-note rl-decide-src'>Keputusan ini dihitung dari hit-rate " +
        "historis sentimen-harga pada data bursa 90 hari, tanpa lima persona " +
        "(alur persona ada di halaman Simulation). Bukan nasihat investasi.</p>";
  }

  function judulBerita(n) {
    if (!n.title || n.title.length <= 46) return n.title || n.article_id;
    return n.title.slice(0, 46) + "…";
  }

  /* n kecil tetap ditampilkan: angka yang tidak layak disimpulkan berbohong
     kalau n-nya disembunyikan. Salinan baris bukti Simulations. */
  function barisBuktiKeputusan(d) {
    if (d.hit_rate === null || d.hit_rate === undefined) return "";
    var pers = Math.round(Number(d.hit_rate) * 100) + "%";
    return "<div class='rl-row'><span>kejadian serupa</span><b>n " + d.n + "</b></div>" +
      "<div class='rl-row'><span>searah berita (T+3)</span><b>" + pers + "</b></div>" +
      "<div class='rl-row'><span>rata-rata T+3</span><b>" + persenBertanda(d.rata2) + "</b></div>" +
      "<div class='rl-row'><span>rata-rata T+1</span><b>" + persenBertanda(d.rata2_t1) + "</b></div>";
  }

  function persenBertanda(v) {
    if (v === null || v === undefined || !isFinite(Number(v))) return "n/a";
    var p = Number(v) * 100;
    return (p >= 0 ? "+" : "") + p.toFixed(2).replace(".", ",") + "%";
  }

  /* ---------------- muat ----------------
     Pola sama dengan overview.js: request lama dibatalkan dan hasilnya
     diabaikan lewat nomor urut. Tanpa ini, ganti target cepat membuat berita
     target sebelumnya menimpa target yang sedang dibuka. */
  var inFlight = null, seq = 0;

  function loadData() {
    var t = A.state.target;
    if (inFlight) inFlight.abort();
    var ctrl = typeof AbortController !== "undefined" ? new AbortController() : null;
    inFlight = ctrl;
    var mySeq = ++seq;
    var signal = ctrl ? { signal: ctrl.signal } : undefined;
    var live = function () { return mySeq === seq; };

    A.showState("chartState", "Memuat deret harga...");
    A.showState("newsState", "Memuat berita...");

    var start = new Date(Date.now() - 89 * 86400000).toISOString().slice(0, 10);
    var end = new Date().toISOString().slice(0, 10);

    function fail(err) {
      if (err && err.name === "AbortError") throw err;
    }

    return Promise.all([
      A.api("/api/series/" + t + "?start_date=" + start + "&end_date=" + end, signal)
        .then(function (p) {
          /* Sentimen harian ikut disimpan: keputusan dari backtesting
             menghitung hit-rate dari pasangan (skor harian, harga tutup). */
          S.prices = (p && p.prices) || [];
          S.sents = (p && p.sentiments) || [];
        })
        .catch(function (err) { fail(err); S.prices = []; S.sents = []; }),
      A.api("/api/impacts/" + t + "?limit=50", signal)
        .then(function (rows) {
          /* Urut terbaru dulu supaya berita yang baru masuk langsung terlihat. */
          S.news = (rows || []).slice().sort(function (a, b) {
            return String(b.published_at || "").localeCompare(String(a.published_at || ""));
          });
        })
        .catch(function (err) { fail(err); S.news = []; })
    ]).then(function () {
      if (!live()) return;
      /* Indeks terpilih hanya bermakna di dalam satu target. Tanpa reset,
         pindah target bisa menunjuk kartu yang tidak ada. */
      S.selected = S.news.length ? 0 : null;
      renderNews();
      renderSelected();
      renderKeputusan();
      drawPriceChart();
      perbaruiPetunjuk();
    }).catch(function () { /* dibatalkan: target lain sudah mengambil alih */ });
  }

  /* ---------------- kontrol ----------------
     Scrollbar disembunyikan karena bar abu di bawah kartu terlihat seperti
     salah layout. Konsekuensinya penggeseran harus disediakan sendiri:
     roda mouse (vertikal dipetakan ke horizontal) dan seret dengan pointer.
     Tanpa ini, kartu di luar layar tidak bisa dijangkau di desktop. */
  /* Penghitung dan gradien tepi. Dengan lima kartu yang semuanya muat, tidak
     ada lagi isi tersembunyi: hitungannya menyebut bahwa ini lima terbaru dari
     arsip, bukan lima kartu yang bisa digeser. Gradien hanya muncul kalau
     layar sempit sampai kartu benar-benar terpotong. */
  function perbaruiPetunjuk() {
    var wrap = $("pickerWrap"), hitung = $("newsCount");
    if (!wrap || !hitung) return;
    var total = S.news.length;
    if (!total) { hitung.hidden = true; return; }
    var tampil = Math.min(total, MAKS_KARTU);
    var meluber = picker.scrollWidth > picker.clientWidth + 4;
    hitung.hidden = false;
    hitung.textContent = tampil < total
      ? tampil + " berita terbaru dari " + total + " yang tersimpan"
      : total + " berita tersimpan";
    wrap.classList.toggle("at-end", !meluber ||
      picker.scrollLeft + picker.clientWidth >= picker.scrollWidth - 4);
  }

  var picker = $("newsPicker");
  if (!picker) {
    /* Tanpa DOM (diuji lewat node) tidak ada kontrol untuk didaftari. */
    A.renderPage = loadData;
    return;
  }
  var drag = { on: false, x: 0, left: 0, moved: false, endedAt: 0 };

  picker.addEventListener("wheel", function (e) {
    if (picker.scrollWidth <= picker.clientWidth) return;
    if (Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return;
    picker.scrollLeft += e.deltaY;
    e.preventDefault();
  }, { passive: false });

  picker.addEventListener("pointerdown", function (e) {
    /* Sentuhan sudah digeser sendiri oleh browser; menyeret manual di sini
       akan merebut gestur gulir bawaan. */
    if (e.button !== 0 || e.pointerType !== "mouse") return;
    drag.on = true; drag.moved = false;
    drag.x = e.clientX; drag.left = picker.scrollLeft;
  });
  picker.addEventListener("pointermove", function (e) {
    if (!drag.on) return;
    var dx = e.clientX - drag.x;
    if (!drag.moved && Math.abs(dx) > 3) {
      drag.moved = true;
      /* Kelas baru dipasang setelah gerakan nyata. Kalau dipasang sejak
         pointerdown, anak-anak kartu kehilangan pointer-events dan klik
         biasa mendarat di wadah, bukan di kartunya. */
      picker.classList.add("is-dragging");
    }
    if (drag.moved) picker.scrollLeft = drag.left - dx;
  });
  function endDrag() {
    if (!drag.on) return;
    drag.on = false;
    if (drag.moved) drag.endedAt = Date.now();
    picker.classList.remove("is-dragging");
  }
  picker.addEventListener("pointerup", endDrag);
  picker.addEventListener("pointercancel", endDrag);
  picker.addEventListener("pointerleave", endDrag);
  /* scrollLeft berubah juga saat roda mouse dan seret, bukan hanya saat
     scrollbar dipakai; satu listener menutup ketiganya. */
  picker.addEventListener("scroll", perbaruiPetunjuk, { passive: true });
  window.addEventListener("resize", perbaruiPetunjuk);
  perbaruiPetunjuk();

  picker.addEventListener("click", function (e) {
    /* Klik yang lahir dari seret diabaikan berdasarkan waktu, bukan flag yang
       bisa tertinggal menyala kalau event click tidak pernah datang. */
    if (Date.now() - drag.endedAt < 200) return;
    var btn = e.target.closest(".rl-item");
    if (!btn) return;
    S.selected = Number(btn.getAttribute("data-i"));
    renderNews();
    renderSelected();
    renderKeputusan();
    drawPriceChart();
  });

  A.renderPage = loadData;
  A.boot();
})(window.ARCAS);
