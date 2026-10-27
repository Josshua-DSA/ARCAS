/* Simulations: fase 1 saja -- composer di tengah, mengikuti
   mockup-simulations.html.

   Kartu jawaban (fase 2) belum ada karena endpoint /api/simulate belum
   tersedia. Tombol "Uji berita" sengaja tidak berpura-pura mengirim:
   ia menyatakan bahwa analisis belum terpasang. */
(function (A) {
  "use strict";

  function $(id) { return document.getElementById(id); }

  function setBadge(ok, teks) {
    var b = $("simBadge");
    if (!b) return;
    b.classList.toggle("s-off", !ok);
    $("simBadgeText").textContent = teks;
  }

  function pasang() {
    var ta = $("simNews");
    if (!ta) return; /* bukan halaman Simulations */

    /* Chip contoh: isi textarea, jangan langsung kirim. */
    var chips = document.querySelectorAll("#simRoot .s-chip");
    for (var i = 0; i < chips.length; i++) {
      chips[i].addEventListener("click", function () {
        ta.value = this.getAttribute("data-fill");
        ta.focus();
      });
    }

    $("simSend").addEventListener("click", function () {
      setBadge(false, "analisis belum terpasang");
    });
  }

  A.renderPage = function () {
    setBadge(A.state.apiReachable !== false,
      A.state.apiReachable === false ? "API tidak terjangkau" : "siap · model termuat");
    pasang();
  };

  A.boot();
})(window.ARCAS);
