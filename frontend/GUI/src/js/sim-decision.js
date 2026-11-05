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

  A.agregasiStance = agregasiStance;
  A.AMBANG_AGREGAT = AMBANG_AGREGAT;
})(window.ARCAS);
