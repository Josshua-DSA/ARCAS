/* Agregasi stance lima persona menjadi satu keputusan.

   Dipisah dari simulations.js supaya bisa diuji tanpa DOM.

   Kenapa tidak dirata-ratakan begitu saja: berita lemah membuat kelima persona
   "hold" dengan strength ~0.005, dan merata-ratakan itu menghasilkan "TAHAN" --
   pernyataan bahwa pasar netral, padahal modelnya hanya tidak yakin. Itu dua hal
   berbeda dan pengguna berhak tahu bedanya. */
window.ARCAS = window.ARCAS || {};
(function (A) {
  "use strict";

  /* Ambang keyakinan bawaan. Angka ini BUKAN karangan klien: server sudah
     memakai 0.35 di `warnings` ("Keyakinan 0.07 di bawah ambang 0.35").
     Nilai di sini hanya jaring bila server tidak mengirim peringatan. */
  var AMBANG_KEYAKINAN_BAWAAN = 0.35;

  /* Agregat di bawah ini dianggap belum cukup searah untuk disebut sinyal.
     Lima persona dengan strength median ~0.2 menghasilkan agregat ~0.2 saat
     semuanya searah, jadi 0.15 memisahkan "searah tapi tipis" dari "searah". */
  var AMBANG_AGREGAT = 0.15;

  /* Ambang minimal kejadian sebelum bukti historis boleh mengubah keputusan.
     15 dipilih karena di bawah itu satu kejadian menggeser hit-rate >6 poin;
     SPX pada data ini punya n=13 dan memang tidak layak disimpulkan. */
  var AMBANG_LAYAK = 15;

  /* |skor| minimal agar sebuah hari dianggap punya arah yang jelas. */
  var AMBANG_SINYAL_SKOR = 0.3;

  /* Zona tanpa keunggulan: hit-rate 0.45..0.55 setara lempar koin. */
  var HIT_TINGGI = 0.55;
  var HIT_RENDAH = 0.45;

  function ambangDariWarnings(warnings) {
    if (!warnings || !warnings.length) return AMBANG_KEYAKINAN_BAWAAN;
    for (var i = 0; i < warnings.length; i++) {
      var m = /ambang\s+([0-9]*\.?[0-9]+)/i.exec(String(warnings[i]));
      if (m) {
        var v = parseFloat(m[1]);
        if (!isNaN(v)) return v;
      }
    }
    return AMBANG_KEYAKINAN_BAWAAN;
  }

  function agregasiStance(stances, confidence, warnings) {
    var ambang = ambangDariWarnings(warnings);
    var n = (stances && stances.length) || 0;

    if (!n) {
      return { keputusan: "tidak_ada_sinyal", skor: 0, ambang_keyakinan: ambang,
               jumlah_persona: 0, searah: { buy: 0, hold: 0, sell: 0 } };
    }

    var jumlah = 0, searah = { buy: 0, hold: 0, sell: 0 };
    for (var i = 0; i < n; i++) {
      var s = stances[i];
      var str = Number(s.strength);
      if (isNaN(str)) str = 0;
      if (s.stance === "buy") { jumlah += str; searah.buy++; }
      else if (s.stance === "sell") { jumlah -= str; searah.sell++; }
      else { searah.hold++; }
    }
    var skor = jumlah / n;

    var keputusan;
    if (Number(confidence) < ambang) keputusan = "tidak_ada_sinyal";
    else if (skor >= AMBANG_AGREGAT) keputusan = "beli";
    else if (skor <= -AMBANG_AGREGAT) keputusan = "jual";
    else keputusan = "tahan";

    return { keputusan: keputusan, skor: skor, ambang_keyakinan: ambang,
             jumlah_persona: n, searah: searah };
  }

  /* ---------------- bukti historis: sentimen x harga ----------------

     Menjawab "buy on news atau sell on news?" dari data, bukan dari selera.
     Untuk tiap hari yang punya skor sentimen DAN harga, hitung return
     close-to-close h hari bursa kemudian, lalu kelompokkan menurut arah berita.

     Kenapa `n` selalu ikut dikembalikan: hit-rate 33% dari 12 kejadian dan dari
     400 kejadian adalah dua benda berbeda. Menyembunyikan n membuat angka itu
     berbohong tanpa berbohong. */

  function hitungBukti(sentiments, prices, arah, horizon) {
    var skor = {}, tutup = {}, tanggal = [], i;

    for (i = 0; i < (sentiments || []).length; i++) {
      var s = sentiments[i];
      if (s.score_mean !== null && s.score_mean !== undefined) {
        skor[s.date] = Number(s.score_mean);
      }
    }
    for (i = 0; i < (prices || []).length; i++) {
      var p = prices[i];
      if (p.close !== null && p.close !== undefined) {
        tutup[p.date] = Number(p.close);
      }
    }
    /* Tanggal diambil dari harga, bukan dari sentimen: hari tanpa harga tidak
       punya return, dan urutan harga adalah urutan bursa yang sebenarnya. */
    for (i = 0; i < (prices || []).length; i++) {
      if (tutup[prices[i].date] !== undefined) tanggal.push(prices[i].date);
    }
    tanggal.sort();

    var maju = [];
    for (i = 0; i < tanggal.length; i++) {
      var j = i + horizon;
      if (j >= tanggal.length) break;   /* ekor tanpa pasangan: lewati, bukan 0 */
      var d0 = tanggal[i];
      var s0 = skor[d0];
      if (s0 === undefined) continue;
      if (arah === "naik" && s0 < AMBANG_SINYAL_SKOR) continue;
      if (arah === "turun" && s0 > -AMBANG_SINYAL_SKOR) continue;
      if (!tutup[d0]) continue;
      maju.push((tutup[tanggal[j]] - tutup[d0]) / tutup[d0]);
    }

    var n = maju.length;
    if (!n) return { n: 0, hit_rate: null, rata2: null, horizon: horizon };

    var benar = 0, jumlah = 0;
    for (i = 0; i < n; i++) {
      jumlah += maju[i];
      if (arah === "naik" ? maju[i] > 0 : maju[i] < 0) benar++;
    }
    return { n: n, hit_rate: benar / n, rata2: jumlah / n, horizon: horizon };
  }

  /* ---------------- keputusan: persona x bukti ----------------

     Urutan wewenang: keyakinan model dulu (kalau modelnya sendiri tidak yakin,
     tidak ada yang boleh menyimpulkan), lalu bukti historis bila jumlah
     kejadiannya layak, lalu persona sebagai bawaan.

     Bukti yang membalik persona BUKAN bug: XAU pada data ini memang bergerak
     turun setelah berita positif (sell on news). */
  function keputusanBerita(input) {
    input = input || {};
    var stances = input.stances || [];
    var warnings = input.warnings || [];
    var arah = input.arah;                       /* "naik" | "turun" | lainnya */
    var bukti = input.bukti || {};
    var t3 = bukti.T3 || null;
    var t1 = bukti.T1 || null;

    var persona = agregasiStance(stances, input.confidence, warnings);

    var hasil = {
      keputusan: persona.keputusan,
      label: "persona",
      alasan: "",
      n: t3 ? t3.n : 0,
      hit_rate: t3 ? t3.hit_rate : null,
      horizon: 3,
      rata2: t3 ? t3.rata2 : null,
      rata2_t1: t1 ? t1.rata2 : null,
      skor_persona: persona.skor,
      catatan: null,
      layak: false
    };

    if (persona.keputusan === "tidak_ada_sinyal") {
      hasil.alasan = "Keyakinan model di bawah ambang, jadi tidak ada dasar " +
        "untuk mengambil posisi.";
      return hasil;
    }

    var nLayak = !!(t3 && t3.n >= AMBANG_LAYAK && t3.hit_rate !== null);
    hasil.layak = nLayak;

    if (!nLayak) {
      hasil.alasan = "Bukti historis belum cukup (" + hasil.n + " kejadian, " +
        "ambang " + AMBANG_LAYAK + "), jadi keputusan mengikuti lima persona.";
      hasil.label = "bukti tipis";
    } else if (t3.hit_rate >= HIT_TINGGI) {
      /* Historis searah berita lebih sering benar. */
      hasil.keputusan = arah === "turun" ? "jual" : "beli";
      hasil.alasan = "Arah ini benar " + persen(t3.hit_rate) + " dari " +
        t3.n + " kejadian serupa, jadi mengikuti arah berita.";
    } else if (t3.hit_rate <= HIT_RENDAH) {
      /* Historis berbalik arah: ini inti sell on news. */
      hasil.keputusan = arah === "turun" ? "beli" : "jual";
      hasil.alasan = "Arah ini hanya benar " + persen(t3.hit_rate) + " dari " +
        t3.n + " kejadian serupa, jadi dibalik dari arah berita.";
    } else {
      hasil.keputusan = "tahan";
      hasil.label = "tanpa keunggulan";
      hasil.alasan = "Hit-rate " + persen(t3.hit_rate) + " masih di sekitar " +
        "lempar koin, jadi tidak ada keunggulan arah yang bisa dipakai.";
    }

    /* Label mengikuti KEPUTUSAN, bukan cabang yang menghasilkannya: "buy on
       news" berarti tindakannya membeli karena berita ini. Cabang hit-rate
       rendah pada berita buruk juga menghasilkan BELI, dan menyebutnya
       "sell on news" akan menamai tindakan dengan kebalikannya.
       Kasus bukti tipis dibiarkan berlabel "bukti tipis": di situ keputusan
       datang dari persona, bukan dari berita, jadi menamainya "on news" bohong. */
    if (nLayak) {
      if (hasil.keputusan === "beli") hasil.label = "buy on news";
      else if (hasil.keputusan === "jual") hasil.label = "sell on news";
    }

    /* Keterangan, bukan keputusan: "priced in" belum diuji di data ini. */
    var pers = input.persentil;
    if (pers !== null && pers !== undefined) {
      if (arah === "naik" && Number(pers) >= 0.90) {
        hasil.catatan = "harga sudah di puncak 20 hari";
      } else if (arah === "turun" && Number(pers) <= 0.10) {
        hasil.catatan = "harga sudah di dasar 20 hari";
      }
    }

    return hasil;
  }

  function persen(v) {
    if (v === null || v === undefined) return "n/a";
    return Math.round(Number(v) * 100) + "%";
  }

  A.agregasiStance = agregasiStance;
  A.hitungBukti = hitungBukti;
  A.keputusanBerita = keputusanBerita;
  A.AMBANG_AGREGAT = AMBANG_AGREGAT;
  A.AMBANG_LAYAK = AMBANG_LAYAK;
})(window.ARCAS);
