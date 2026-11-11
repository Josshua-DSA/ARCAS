/* Market Overview (Upgrade.md 3): grafik harga vs sentimen, statistik ringkas,
   dan berita teratas. Detail penuh ada di halaman
   lain (research, evidence, simulations). Halaman ini hanya fetch dan render. */
(function (A) {
  "use strict";
  var esc = A.esc;

  /* Grafik dual-axis. Alasan ECharts lokal: nol dependensi jaringan saat sidang. */
  var chart = null;
  function ensureChart() {
    if (chart || typeof echarts === "undefined") return;
    chart = echarts.init(A.$("chart"));
    window.addEventListener("resize", function () { if (chart) chart.resize(); });
  }
  function renderChart(payload) {
    ensureChart();
    var info = A.metaFor(A.state.target);

    /* Sumbu-x HANYA dari hari bursa, lalu sentimen ditempelkan ke hari bursa
       berikutnya oleh A.rapikanKeHariBursa. Sebelumnya sumbu-x digabung dari
       tanggal sentimen DAN tanggal harga, sehingga hari yang hanya punya salah
       satunya tampil sebagai celah: pada jendela 180 hari, garis harga kosong
       selama 56 hari pertama karena harga baru mulai 2026-07-06 sementara
       sentimen sudah ada sejak Desember. */
    var rapi = A.rapikanKeHariBursa(payload.sentiments || [], payload.prices || []);
    var dates = rapi.tanggal;
    var closes = rapi.tutup.map(function (v) { return v == null ? null : Math.round(v * 100) / 100; });
    var scores = rapi.skor.map(function (v) { return v == null ? null : Math.round(v * 1000) / 1000; });
    var gapCount = scores.filter(function (v) { return v === null; }).length;

    /* Elemen legenda bisa tidak ada (mis. halaman lain memuat skrip ini).
       Tanpa penjaga, renderChart melempar TypeError dan grafik tidak pernah
       digambar sama sekali. */
    var lg = A.$("lgPrice");
    if (lg) lg.style.background = info.color;

    if (!chart) { A.showState("chartState", "Pustaka grafik lokal belum termuat (src/js/echarts.min.js). Periksa path file."); return; }
    if (!dates.length) { A.showState("chartState", "Belum ada deret untuk target ini pada rentang terpilih."); chart.clear(); return; }
    A.showState("chartState", gapCount ? gapCount + " hari tanpa berita tampil sebagai jeda (bukan nol)." : "");

    chart.setOption({
      backgroundColor: "transparent",
      grid: { left: 64, right: 64, top: 36, bottom: 34 },
      tooltip: { trigger: "axis", backgroundColor: "#2C2727", borderWidth: 0,
        textStyle: { color: "#F6F4F4", fontFamily: "JetBrains Mono, monospace", fontSize: 12 } },
      xAxis: { type: "category", data: dates, axisLine: { lineStyle: { color: "#5A5454" } },
        axisLabel: { color: "#D4CFCF", fontFamily: "JetBrains Mono, monospace", fontSize: 12, hideOverlap: true } },
      yAxis: [
        { type: "value", scale: true, splitLine: { lineStyle: { color: "#5A5454", opacity: 0.5 } },
          axisLabel: { color: "#D4CFCF", fontFamily: "JetBrains Mono, monospace", fontSize: 12,
            formatter: function (v) { return String(Math.round(v)).replace(/\B(?=(\d{3})+(?!\d))/g, "."); } } },
        { type: "value", min: -1, max: 1, splitNumber: 4, splitLine: { show: false },
          axisLabel: { color: "#D4CFCF", fontFamily: "JetBrains Mono, monospace", fontSize: 12,
            formatter: function (v) {
              var s = String(v).replace(".", ",");
              return v > 0 ? "+" + s : s;
            } } }
      ],
      series: [
        { name: "Tutup", type: "line", data: closes, yAxisIndex: 0, showSymbol: false, connectNulls: false,
          lineStyle: { width: 2, color: info.color }, itemStyle: { color: info.color }, z: 3 },
        /* Bar sentimen diwarnai menurut TANDA skornya, bukan satu warna
           untuk semua. Sebelumnya seluruh bar putih, sehingga hari sentimen
           positif dan negatif tidak bisa dibedakan sekilas — padahal itu
           inti dari grafik ini. Hijau/merah dipilih yang tetap terbaca di
           latar gelap; opasitas penuh supaya tidak tenggelam di bawah garis
           harga. Lebar 72% dari satu hari bursa (maks 12px) membuat batang
           terbaca tanpa menutupi garis. */
        { name: "Skor", type: "bar", data: scores, yAxisIndex: 1, connectNulls: false,
          barWidth: "72%", barMaxWidth: 12, z: 2,
          itemStyle: { color: function (p) {
            var v = p.value;
            if (v == null) return "transparent";
            return v > 0 ? "#3FB950" : v < 0 ? "#F85149" : "#BDB7B7";
          }, opacity: 1, borderRadius: 2 },
          markLine: { silent: true, symbol: "none", label: { show: false },
            lineStyle: { color: "#8C8585", width: 1, opacity: 0.7 }, data: [{ yAxis: 0 }] } }
      ]
    }, true);
  }

  /* Tanggal lokal, bukan UTC: lihat catatan A.localISO di api.js. */
  function isoDaysAgo(n) { return A.localISO(new Date(Date.now() - (n - 1) * 86400000)); }

  /* Daftar berita + paginasi 5 per halaman. Halaman disimpan di memori;
     mengubah target/rentang mengembalikan ke halaman 1. */
  var newsPage = 1;
  var newsRows = [];
  var NEWS_PER_PAGE = 5;

  /* Tidak ada lagi berita ilustrasi. Dulu NEWS_DEMO mengisi kekurangan data
     API dengan berita karangan; itu bertabrakan dengan prinsip halaman lain
     yang selalu melabeli data palsu. Berita sekarang hanya dari API -- kalau
     kosong, tampilkan pesan apa adanya. */

  /* Label sumber untuk PEMBACA, bukan key internal.
     `source` di DB berbentuk "eulerpool:CNBC" — gabungan nama agregator dan
     penerbit asli, berguna untuk penelusuran tapi tidak untuk dibaca.
     Yang ditampilkan hanya penerbitnya ("CNBC"). Bila tidak ada pemisah,
     key itu sendiri dipakai. Underscore diganti spasi dan nama kanal yang
     sudah dikenal diterjemahkan, supaya "rss:fed_press" tidak muncul
     sebagai "fed_press" di layar. */
  var SUMBER_TERKENAL = {
    fed_press: "Federal Reserve",
    investing_commodities_news: "Investing.com",
    investing_commodities_analysis: "Investing.com (analisis)"
  };
  function sourceLabel(s) {
    if (!s) return "";
    var t = String(s).trim();
    var i = t.indexOf(":");
    var kunci = i >= 0 ? t.slice(i + 1).trim() : t;
    if (SUMBER_TERKENAL[kunci]) return SUMBER_TERKENAL[kunci];
    return (kunci || t).replace(/_/g, " ");
  }

  function newsItem(t) {
    var d = String(t.direction || "neutral").toLowerCase();
    var cls = d === "bullish" ? "buy" : d === "bearish" ? "sell" : "hold";
    var arrow = d === "bullish" ? "▲" : d === "bearish" ? "▼" : "●";
    /* Arah HARUS menyebut asetnya. "Bullish" tanpa objek ambigu: bullish
       untuk emas, untuk dolar, atau untuk surat utang? Saat tab Emas aktif
       dan harga turun, tag hijau tanpa konteks terbaca seperti kontradiksi.
       `asset_id` dari API adalah aset yang dipengaruhi artikel ini, jadi
       itulah yang ditulis. */
    var aset = t.asset_id ? (A.TARGET_INFO[t.asset_id] || {}).name || t.asset_id : null;
    var label = d === "bullish" ? "Bullish" : d === "bearish" ? "Bearish" : "Netral";
    if (aset) label += " " + aset;
    var title = t.title || t.article_id;
    var meta = [];
    if (t.source) meta.push("<span>" + esc(sourceLabel(t.source)) + "</span>");
    var when = A.fmtDate(t.published_at);
    if (when) meta.push("<span>" + esc(when) + "</span>");
    /* Judul menjadi tautan ke sumber asli bila URL tersedia. rel noopener
       wajib: tanpa itu halaman tujuan bisa mengakses window.opener. */
    var head = t.url
      ? "<a href='" + esc(t.url) + "' target='_blank' rel='noopener noreferrer' class='news-link'>" + esc(title) + "</a>"
      : esc(title);
    return "<article class='news-item'>" +
      "<h3>" + head + "</h3>" +
      (t.rationale ? "<p class='news-note'>" + esc(t.rationale) + "</p>" : "") +
      "<div class='news-top'><span class='chip " + cls + "'>" + arrow + " " + label + "</span>" +
      (Number(t.headline_only) === 1 ? "<span class='chip hold'>Headline saja</span>" : "") +
      (meta.length ? "<span class='news-src'>" + meta.join(" · ") + "</span>" : "") +
      "</div></article>";
  }

  function renderPager() {
    var pager = A.$("newsPager");
    if (!pager) return;
    var pages = Math.ceil(newsRows.length / NEWS_PER_PAGE);
    if (pages <= 1) { pager.hidden = true; pager.innerHTML = ""; return; }
    var buttons = [];
    for (var i = 1; i <= pages; i++) {
      buttons.push("<button type='button' class='pager-btn' data-page-no='" + i + "'" +
        (i === newsPage ? " aria-current='page'" : "") + ">" + i + "</button>");
    }
    pager.innerHTML = "<button type='button' class='pager-btn' data-step='-1'" +
      (newsPage === 1 ? " disabled" : "") + " aria-label='Halaman sebelumnya'>Sebelumnya</button>" +
      buttons.join("") +
      "<button type='button' class='pager-btn' data-step='1'" +
      (newsPage === pages ? " disabled" : "") + " aria-label='Halaman berikutnya'>Berikutnya</button>";
    pager.hidden = false;
  }

  function renderNewsPage() {
    var box = A.$("newsList");
    if (!box) return;
    var from = (newsPage - 1) * NEWS_PER_PAGE;
    var slice = newsRows.slice(from, from + NEWS_PER_PAGE);
    box.innerHTML = slice.length ? slice.map(newsItem).join("")
      : "<p class='hint'>Tidak ada berita pada halaman ini.</p>";
    var kick = A.$("newsKick");
    if (kick) {
      kick.textContent = newsRows.length
        ? "menampilkan " + (from + 1) + "-" + (from + slice.length) + " dari " + newsRows.length
        : "belum ada berita";
    }
    renderPager();
  }

  /* Berita murni dari API. Tidak ada padding karangan: bila API mengirim
     sedikit, tampilkan sedikit; bila kosong, katakan kosong. `isError`
     membedakan "API mati" dari "API hidup tapi belum ada berita" -- dua
     hal berbeda yang dulu sama-sama diisi NEWS_DEMO. */
  function renderNews(rows, isError) {
    newsRows = rows || [];
    newsPage = 1;
    renderNewsPage();
    if (isError) {
      A.showState("newsState", "API berita tidak terjangkau : tidak ada berita untuk ditampilkan (bukan ilustrasi).");
    } else if (!newsRows.length) {
      A.showState("newsState", "Belum ada berita untuk target ini. Jalankan pipeline ingest/analyze dulu.");
    } else {
      A.showState("newsState", "");
    }
  }

  function bindPager() {
    var pager = A.$("newsPager");
    if (!pager) return;
    pager.addEventListener("click", function (e) {
      var btn = e.target.closest("button[data-page-no],button[data-step]");
      if (!btn || btn.disabled) return;
      var pages = Math.ceil(newsRows.length / NEWS_PER_PAGE);
      if (btn.dataset.pageNo) newsPage = Number(btn.dataset.pageNo);
      else newsPage = Math.min(pages, Math.max(1, newsPage + Number(btn.dataset.step)));
      renderNewsPage();
    });
  }

  /* Penjaga urutan + pembatalan (race condition). renderAll dipanggil ulang
     setiap target/rentang/profil berubah. Tanpa ini, ganti target cepat
     (XAU -> SPX -> RATE_UST) membuat tiga set request berjalan bersamaan dan
     respons yang tiba TERAKHIR menang -- bisa XAU menimpa grafik RATE_UST.
     Dua lapis: AbortController membatalkan request lama, dan `seq` memastikan
     respons yang sudah terlanjur masuk tidak menyentuh DOM. */
  var seq = 0;
  var inFlight = null;

  /* Cap waktu preload terakhir: menjawab "data ini setua apa?" tanpa
     mengarang. Sumbernya /api/preload/status (tabel ingest_runs).

     Dulu labelnya "preload terakhir <tanggal>" dan muncul berdampingan
     dengan "data per <tanggal>" di ticker. Dua tanggal berbeda tanpa
     keterangan membuat pembaca tidak tahu mana yang jadi acuan. Sekarang
     keduanya dibedakan tegas: "data pasar" = tanggal harga terakhir,
     "berita terakhir masuk" = kapan ingest terakhir selesai. */
  function renderPreloadStamp(info) {
    var el = A.$("preloadStamp");
    if (!el) return;
    var last = info && info.last;
    if (!last) { el.textContent = ""; return; }
    var when = A.fmtDate(last.finished_at);
    var n = Number(last.raw_new) || 0;
    el.textContent = when
      ? "berita terakhir masuk " + when + " · " + n + " berita baru"
      : "";
  }

  /* Ringkasan hero berupa dua kartu angka, bukan satu kalimat panjang.
     Kalimat lama ("... negatif 0 dari 8 hari terakhir") mudah terlewat dan
     frasa "0 dari 8" ambigu. Kartu memisahkan dua fakta yang berbeda:
     perubahan harga pada rentang aktif, dan berapa hari berita terakhir
     yang skornya negatif. Bila datanya tidak cukup, tulis n/a -- bukan 0. */
  /* Cakupan berita: berapa hari bursa yang benar-benar punya berita.
     Kartu ketiga sengaja mengukur KETEBALAN DATA, bukan mengulang arah.
     Hari tanpa berita bukan nol sentimen, jadi tidak dihitung netral. */
  function hitungCakupan(sentiments, hariBursa) {
    var berisi = (sentiments || []).filter(function (s) {
      return s && s.score_mean != null;
    });
    var totalArtikel = berisi.reduce(function (a, s) {
      return a + Number(s.n_articles || 0);
    }, 0);
    var persen = null;
    if (hariBursa && hariBursa > 0) {
      persen = Math.round(berisi.length / hariBursa * 1000) / 10;
    }
    return {
      hariBerita: berisi.length,
      totalArtikel: totalArtikel,
      hariBursa: hariBursa || null,
      persen: persen
    };
  }
  /* Diekspor untuk tes node; dijalankan sebelum A.boot() di akhir berkas. */
  A.__ujiCakupan = hitungCakupan;

  function renderHeroLead(target, payload) {
    var el = A.$("heroLead");
    if (!el) return;
    var info = A.metaFor(target);
    var rows = (payload && payload.prices) || [];
    var sent = (payload && payload.sentiments) || [];

    /* Kartu harga. n/a dipakai saat deret kosong atau tidak valid; 0%
       hanya muncul bila harga benar-benar datar. */
    var isiHarga = "<span class='sr-only'>tidak tersedia</span><span aria-hidden='true'>n/a</span>";
    var kelasHarga = "na";
    var catatanHarga = "data harga belum tersedia";
    if (rows.length) {
      var firstRaw = rows[0] && rows[0].close;
      var lastRaw = rows[rows.length - 1] && rows[rows.length - 1].close;
      var first = Number(firstRaw);
      var last = Number(lastRaw);
      if (firstRaw != null && lastRaw != null && isFinite(first) && isFinite(last) && first !== 0) {
        var pct = (last - first) / first * 100;
        var datar = Math.abs(pct) < 0.005;
        var arah = datar ? "datar" : pct < 0 ? "turun" : "naik";
        var ikon = datar ? "●" : pct < 0 ? "▼" : "▲";
        var desimal = Math.abs(pct) < 1 ? 2 : 1;
        var angka = Math.abs(pct).toFixed(desimal).replace(".", ",");
        var tanda = datar ? "" : pct < 0 ? "−" : "+";
        kelasHarga = datar ? "flat" : pct < 0 ? "down" : "up";
        isiHarga = "<span class='sr-only'>" + esc(arah + " " + angka + " persen") + "</span>" +
          "<span class='fact-dir' aria-hidden='true'>" + ikon + "</span>" +
          "<span aria-hidden='true'>" + tanda + angka + "%</span>";
        catatanHarga = esc(info.name) + " · " + esc(String(A.state.days)) + " hari";
      }
    }

    /* Kartu sentimen. Hanya dihitung dari hari yang PUNYA berita; hari
       kosong tidak dianggap netral. Jumlah hari mengikuti data, bukan
       dipaksa 8, supaya "dari x hari" selalu jujur. */
    var isiSent = "<span class='sr-only'>tidak tersedia</span><span aria-hidden='true'>n/a</span>";
    var kelasSent = "na";
    var catatanSent = "belum ada berita pada rentang ini";
    var berisi = sent.filter(function (s) { return s && s.score_mean != null; });
    var akhir = berisi.slice(-8);
    if (akhir.length) {
      var neg = akhir.filter(function (s) { return Number(s.score_mean) < 0; }).length;
      kelasSent = "";
      isiSent = "<span class='sr-only'>" + neg + " hari negatif</span>" +
        "<span aria-hidden='true'>" + neg + "</span>" +
        "<span class='fact-unit' aria-hidden='true'>hari negatif</span>";
      catatanSent = "dari " + akhir.length + " hari terakhir yang punya berita";
    }

    /* Kartu cakupan: tebal dasar dua kartu di atasnya. */
    var cakupan = hitungCakupan(sent, rows.length);
    var isiCakup, kelasCakup = "", catatanCakup;
    if (cakupan.hariBerita) {
      isiCakup = "<span class='sr-only'>" + cakupan.hariBerita + " hari berita</span>" +
        "<span aria-hidden='true'>" + cakupan.hariBerita + "</span>" +
        "<span class='fact-unit' aria-hidden='true'>hari berita</span>";
      catatanCakup = cakupan.persen == null
        ? cakupan.totalArtikel + " artikel"
        : String(cakupan.persen).replace(".", ",") + "% dari " + cakupan.hariBursa +
          " hari bursa · " + cakupan.totalArtikel + " artikel";
    } else {
      kelasCakup = "na";
      isiCakup = "<span class='sr-only'>tidak tersedia</span><span aria-hidden='true'>n/a</span>";
      catatanCakup = "belum ada berita pada rentang ini";
    }

    el.innerHTML =
      "<div class='fact'>" +
        "<span class='fact-label'>Perubahan harga</span>" +
        "<span class='fact-value " + kelasHarga + "'>" + isiHarga + "</span>" +
        "<p class='fact-note'>" + catatanHarga + "</p>" +
      "</div>" +
      "<div class='fact'>" +
        "<span class='fact-label'>Sentimen berita</span>" +
        "<span class='fact-value " + kelasSent + "'>" + isiSent + "</span>" +
        "<p class='fact-note'>" + catatanSent + "</p>" +
      "</div>" +
      "<div class='fact'>" +
        "<span class='fact-label'>Cakupan berita</span>" +
        "<span class='fact-value " + kelasCakup + "'>" + isiCakup + "</span>" +
        "<p class='fact-note'>" + esc(catatanCakup) + "</p>" +
      "</div>";
  }

  function loadPreloadStamp(signal, live) {
    A.api("/api/preload/status", signal).then(function (info) {
      if (!live()) return;
      renderPreloadStamp(info);
    }).catch(function (err) {
      if ((err && err.name === "AbortError") || !live()) return;
      var el = A.$("preloadStamp");
      if (el) el.textContent = "";
    });
  }

  function renderAll() {
    var t = A.state.target;
    var end = A.localISO(new Date());
    var start = isoDaysAgo(A.state.days);

    if (inFlight) inFlight.abort();
    var ctrl = typeof AbortController !== "undefined" ? new AbortController() : null;
    inFlight = ctrl;
    var mySeq = ++seq;
    var signal = ctrl ? { signal: ctrl.signal } : undefined;
    /* Masih render terbaru? Dipakai sebelum menyentuh DOM mana pun. */
    var live = function () { return mySeq === seq; };

    A.showState("chartState", "Memuat deret " + t + "...");
    A.showState("newsState", "Memuat berita...");

    A.api("/api/series/" + t + "?start_date=" + start + "&end_date=" + end, signal).then(function (payload) {
      if (!live()) return;
      A.state.apiOk = true; A.state.apiReachable = true; A.setStatus("ok", "terhubung ke API");
      renderChart(payload);
      renderHeroLead(t, payload);
    }).catch(function (err) {
      if (!live() || (err && err.name === "AbortError")) return;
      A.state.apiOk = false; A.setStatus("err", "API tidak terjangkau : ilustrasi");
      renderChart(A.demoSeries(t, A.state.days));
    });

    loadPreloadStamp(signal, live);
    /* 20, bukan 60: pager menampilkan 5 per halaman, jadi 60 berarti 55 baris
       terbuang tiap muat. 20 memberi 4 halaman riwayat tanpa membawa sisa yang
       tidak pernah bisa dijangkau pembaca. */
    /* Promise dikembalikan supaya skeleton tahu kapan data benar-benar tiba;
       tanpa ini skeleton ditutup sebelum grafik digambar. */
    return A.api("/api/impacts/" + t + "?limit=20", signal).then(function (rows) {
      if (!live()) return;
      renderNews(rows, false);
    }).catch(function (err) {
      if (!live() || (err && err.name === "AbortError")) return;
      renderNews([], true);
    });
  }

  bindPager();
  A.renderPage = renderAll;
  A.boot();
})(window.ARCAS);
