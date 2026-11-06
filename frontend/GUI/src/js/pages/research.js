/* Research Lab: pilih berita, lihat titiknya di grafik pasar, baca uji
   statistik yang tersimpan untuk target itu.

   Halaman ini hanya fetch dan render. Semua angka dari API; tidak ada data
   contoh. Yang belum tersedia ditulis belum tersedia, bukan dikarang. */
(function (A) {
  "use strict";
  var esc = A.esc, fmt = A.fmt;

  var S = { prices: [], sents: [], news: [], tests: [], selected: null };

  function $(id) { return document.getElementById(id); }

  /* ---------------- perapian daftar uji ----------------

     `stat_results` menyimpan baris kembar persis: menjalankan ulang `cli
     stats` menambah baris baru tanpa membuang yang lama. Untuk XAU itu berarti
     28 baris padahal hanya 24 kombinasi (uji, lag, estimate, p_adj, n) yang
     berbeda -- tabel menampilkan uji yang sama dua kali dan pembaca mengira
     rangkaiannya lebih panjang dari kenyataan.

     Kunci dedup memakai nilai yang benar-benar tampil di baris, bukan run_id:
     dua baris identik dari run berbeda adalah satu bukti yang sama.
     `JSON.stringify` memisahkan null dari 0, jadi p_adj null tidak tertukar
     dengan p_adj 0. */
  function dedupUji(rows) {
    var terlihat = {}, hasil = [];
    (rows || []).forEach(function (r) {
      var kunci = JSON.stringify([r.test, r.market_metric, r.lag,
        r.estimate, r.p_adjusted, r.n_obs, r.ci_low, r.ci_high]);
      if (terlihat[kunci]) return;
      terlihat[kunci] = true;
      hasil.push(r);
    });
    return hasil;
  }

  /* Urut berdasarkan kekuatan bukti: p_adj terkecil dulu, yang tidak punya
     p_adj paling bawah. Di 24 baris mono 10px, dua baris signifikan tenggelam
     kalau urutannya mengikuti jenis uji. Pengurutan stabil supaya dua baris
     setara tidak bertukar posisi tiap kali target diganti. */
  function urutUji(rows) {
    return (rows || []).map(function (r, i) { return { r: r, i: i }; })
      .sort(function (a, b) {
        var pa = a.r.p_adjusted == null ? Infinity : Number(a.r.p_adjusted);
        var pb = b.r.p_adjusted == null ? Infinity : Number(b.r.p_adjusted);
        if (pa !== pb) return pa - pb;
        return a.i - b.i;
      })
      .map(function (x) { return x.r; });
  }

  /* Rentang n_obs per jenis uji. Baris tanpa n_obs dilewati, bukan dihitung
     nol: nol akan menakut-nakuti tanpa alasan. Mengembalikan "tidak tersedia"
     bila jenis uji itu memang tidak dihitung untuk target ini. */
  function rentangN(rows, test) {
    var v = rows.filter(function (r) { return r.test === test; })
      .map(function (r) { return r.n_obs; })
      .filter(function (n) { return n != null && isFinite(Number(n)); })
      .map(Number);
    if (!v.length) return "tidak tersedia";
    var lo = Math.min.apply(null, v), hi = Math.max.apply(null, v);
    return lo === hi ? String(lo) : lo + "–" + hi;
  }

  /* Tanggal berita bisa jatuh di hari bursa tutup. Marker digeser ke tanggal
     bursa terdekat yang tersedia, dan UI menyebut pergeserannya supaya tidak
     terbaca sebagai presisi palsu. */
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
     tidak ada angka karangan: kalau indeks T+n melewati ujung deret, sel itu
     ditulis "belum tersedia". T+n memakai indeks baris deret harga, yang hanya
     berisi hari bursa -- bukan hari kalender. */
  var JENDELA = [1, 3, 5];
  var KUNCI_JENDELA = { 1: "T+1", 3: "T+3", 5: "T+5" };

  function jejakHarga(idx, dates, closes) {
    var hasil = [];
    for (var j = 0; j < JENDELA.length; j++) {
      var n = JENDELA[j];
      var target = idx + n;
      var tersedia = idx >= 0 && target < closes.length &&
        isFinite(closes[target]) && isFinite(closes[idx]);
      hasil.push({
        label: KUNCI_JENDELA[n],
        persen: tersedia ? (closes[target] / closes[idx] - 1) * 100 : null,
        tanggal: tersedia ? dates[target] : null
      });
    }
    return hasil;
  }

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
        return "<div class='rl-after-cell'>" +
          "<p class='rl-after-k'>" + esc(c.label) + "</p>" +
          "<p class='rl-after-v' style='color:" + warna + "'>" + esc(teks) + "</p>" +
          "<p class='rl-after-sub'>" + esc(c.tanggal || "di luar deret") + "</p></div>";
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

     Kartu uji statistik memeriksa asosiasi harian sentimen dan harga; kartu
     ini menjawab pertanyaan tindak lanjutnya: "kalau berita seperti ini
     keluar, arah apa yang terbukti menguntungkan?" Persis alur keputusan di
     Simulations, hanya tanpa lima persona: basisnya riset kuantitatif penuh,
     dan bukti yang tipis diakui sebagai bukti tipis. */
  function renderKeputusan() {
    var box = $("keputusanBox");
    if (!box) return;
    var n = (S.selected != null) ? S.news[S.selected] : null;
    if (!n) { box.innerHTML = ""; return; }

    var arah = n.direction === "bullish" ? "naik"
             : n.direction === "bearish" ? "turun" : "netral";

    if (!S.prices.length || !S.sents.length) {
      box.innerHTML =
        "<div class='rl-decide'><header class='rl-decide-head'><h3>Decision making</h3>" +
        "<span class='hint'>dari backtesting</span></header>" +
        "<p class='rl-k-note'>Keputusan belum bisa dihitung: deret harga atau " +
        "sentimen harian target ini tidak tersedia. Tidak ada angka pengganti.</p></div>";
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
    var judul = n.title && n.title.length > 46
      ? n.title.slice(0, 46) + "…"
      : (n.title || n.article_id);

    box.innerHTML =
      "<div class='rl-decide'><header class='rl-decide-head'><h3>Decision making</h3>" +
        "<span class='hint'>dari backtesting &middot; 90 hari</span></header>" +
      "<p class='rl-k-note' style='margin:0 0 10px'>" + esc(judul) + "</p>" +
      "<div class='rl-decide-body'><span class='rl-decide-pill " + kls + "'>" + label + "</span>" +
        "<span class='hint'>" + esc(d.label) + "</span></div>" +
      "<p class='rl-k-note'>" + esc(d.alasan) + "</p>" +
      barisBuktiKeputusan(d) +
      (d.catatan ? "<p class='rl-k-note'>" + esc(d.catatan) + "</p>" : "") +
      "<p class='rl-k-note rl-decide-src'>Keputusan ini dihitung dari hit-rate " +
        "historis sentimen-harga pada data bursa 90 hari, tanpa lima persona " +
        "(alur persona ada di halaman Simulasi). Bukan nasihat investasi.</p>" +
      "</div>";
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

  /* ---------------- uji statistik ---------------- */
  var TESTS = ["spearman", "ols", "granger", "event_study"];
  /* Ambang signifikansi. p_adj 0.049 dan 0.051 tampil sama sebagai 0.05 di
     UI, jadi statusnya dihitung dari nilai mentah, bukan dari angka bulat. */
  var SIG_AMBANG = 0.05;

  /* Nilai `est` tidak sama artinya antar uji, dan kolom CI tidak selalu ada:
     - `granger` menyimpan statistik F (selalu >= 0, tanpa tanda), dan uji ini
       memang tidak menghasilkan interval kepercayaan -> ci_low/ci_high NULL
       untuk SEMUA baris Granger, bukan sebagian.
     - `event_study` menyimpan CAR (jumlah return jendela event), punya CI.
     - `ols` menyimpan koefisien sentimen, punya CI.
     Tanpa label ini, kolom `est` terbaca seolah satu besaran yang sama di
     semua baris, dan "—" di kolom CI terbaca sebagai data yang gagal dimuat. */
  var KETERANGAN_UJI = {
    ols: { estimasi: "koefisien sentimen", ada_ci: true },
    granger: { estimasi: "statistik F", ada_ci: false },
    event_study: { estimasi: "CAR jendela event", ada_ci: true },
    spearman: { estimasi: "koefisien Spearman", ada_ci: false },
    pearson: { estimasi: "koefisien Pearson", ada_ci: false }
  };

  function renderTests() {
    var box = $("testList");
    if (!box) return;
    /* Urutan: dedup dulu (baris kembar dari run berulang), baru urut menurut
       kekuatan bukti. Membalik urutannya membuat dedup memilih wakil yang
       salah saat nilai yang sama muncul dari run berbeda. */
    var rows = urutUji(dedupUji(S.tests.filter(function (r) {
      return TESTS.indexOf(r.test) !== -1;
    })));
    if (!rows.length) {
      box.innerHTML = "";
      A.showState("testState", "Belum ada hasil uji tersimpan. Jalankan `cli stats` dulu agar panel terisi.");
      return;
    }
    A.showState("testState", "");
    /* Uji yang belum dihitung disebut namanya. Tanpa ini, panel terbaca
       seolah dua uji itulah seluruh rangkaian yang dirancang. */
    var missing = TESTS.filter(function (t) {
      return !rows.some(function (r) { return r.test === t; });
    });
    /* Baris no. 1 adalah bukti terkuat; urutan mengikuti p_adj, bukan jenis
       uji (lihat urutUji). */
    box.innerHTML =
      "<div class='rl-test rl-test--head' aria-hidden='true'>" +
        "<span>uji</span><span>lag</span><span class='rl-test-num'>est</span>" +
        "<span>95% CI</span><span class='rl-test-num'>p_adj</span>" +
        "<span class='rl-test-num'>n</span><span></span></div>" +
      rows.map(function (r) {
        var sig = r.p_adjusted != null && Number(r.p_adjusted) < SIG_AMBANG;
        var ket = KETERANGAN_UJI[r.test] || { estimasi: "estimasi", ada_ci: true };
        /* Granger tidak punya CI: tulis "—" dengan judul yang menyebut alasannya,
           supaya tidak terbaca sebagai data yang gagal dimuat. */
        var ci = (r.ci_low != null && r.ci_high != null)
          ? "[" + Number(r.ci_low).toFixed(2) + ", " + Number(r.ci_high).toFixed(2) + "]"
          : "—";
        var judulCi = ket.ada_ci ? "interval kepercayaan 95%"
          : "uji ini tidak menghasilkan interval kepercayaan";
        var crosses = r.ci_low != null && r.ci_high != null &&
          Number(r.ci_low) <= 0 && Number(r.ci_high) >= 0;
        return "<div class='rl-test'>" +
          "<span class='rl-test-name'>" + esc(A.testLabel(r.test)) + "</span>" +
          "<span class='rl-test-lag'>" + (r.lag != null ? "L" + esc(r.lag) : "—") + "</span>" +
          "<span class='rl-test-num' title='" + esc(ket.estimasi) + "'>" +
            fmt(r.estimate, 3) + "</span>" +
          "<span class='rl-test-ci" + (crosses ? " rl-cross" : "") + "' title='" +
            esc(judulCi) + "'>" + ci + "</span>" +
          "<span class='rl-test-num'>" + (r.p_adjusted != null ? Number(r.p_adjusted).toFixed(3) : "—") + "</span>" +
          "<span class='rl-test-num'>" + esc(r.n_obs) + "</span>" +
          (sig ? "<span class='rl-sig'>sig</span>" : "<span></span>") +
          "</div>";
      }).join("") +
      (missing.length
        ? "<p class='rl-sel-note' style='color:var(--on-dark-muted)'>Belum dihitung untuk target ini: " +
          esc(missing.map(function (t) { return A.testLabel(t); }).join(", ")) +
          ". Tidak ada angkanya di sini karena memang belum ada.</p>"
        : "") +
      /* `n_obs` tidak sama artinya per uji: event_study menghitung jumlah
         spike sentimen (bisa 2), sedangkan OLS/Granger menghitung hari
         berpasangan (32-49). Menyebut satu rentang "2-46 hari berpasangan"
         mencampur dua satuan dan membuat sampelnya terbaca lebih buruk dari
         kenyataan untuk OLS. */
      "<p class='rl-sel-note rl-n-mini'>Jumlah sampel berbeda satuan: OLS " +
        esc(rentangN(rows, "ols")) + " hari berpasangan, Granger " +
        esc(rentangN(rows, "granger")) + " hari berpasangan, CAR " +
        esc(rentangN(rows, "event_study")) + " kejadian spike. p_adj kecil pada " +
        "sampel sekecil ini berarti asosiasi lemah yang belum stabil, bukan " +
        "kepastian.</p>" +
      /* Tanpa kalimat ini, pembaca membandingkan est OLS (-0,007) dengan est
         Granger (0,96) seolah keduanya besaran yang sama. */
      "<p class='rl-sel-note rl-n-mini'>Arti kolom <code>est</code> berbeda per uji: " +
        "OLS = koefisien sentimen, Granger = statistik F, CAR = jumlah return " +
        "jendela event. Tanda “—” di kolom CI bukan data hilang: Granger memang " +
        "tidak menghasilkan interval kepercayaan.</p>";
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
    A.showState("testState", "Memuat hasil uji...");

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
        .catch(function (err) { fail(err); S.news = []; }),
      A.api("/api/stats/" + t, signal)
        .then(function (rows) { S.tests = rows || []; })
        .catch(function (err) { fail(err); S.tests = []; })
    ]).then(function () {
      if (!live()) return;
      /* Indeks terpilih hanya bermakna di dalam satu target. Tanpa reset,
         pindah target bisa menunjuk kartu yang tidak ada. */
      S.selected = S.news.length ? 0 : null;
      renderNews();
      renderSelected();
      renderKeputusan();
      renderTests();
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
    A.dedupUji = dedupUji;
    A.urutUji = urutUji;
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

  A.dedupUji = dedupUji;
  A.urutUji = urutUji;
  A.renderPage = loadData;
  A.boot();
})(window.ARCAS);
