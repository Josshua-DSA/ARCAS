/* ARCAS state antarhalaman (Upgrade.md 3): target/range/profile hidup di
   URLSearchParams, bukan di memory tab. Alasan: state bertahan saat pindah
   halaman dan saat reload, tanpa storage yang bisa basi. */
window.ARCAS = window.ARCAS || {};
(function (A) {
  "use strict";

  A.state = { target: "XAU", days: 90, profile: "moderate", apiBase: "", apiReachable: null, apiOk: false, meta: null };

  function readFromUrl() {
    try {
      var q = new URLSearchParams(location.search);
      if (q.get("target")) A.state.target = q.get("target");
      var d = Number(q.get("days"));
      if (d === 30 || d === 90 || d === 180) A.state.days = d;
      var p = q.get("profile");
      if (p === "conservative" || p === "moderate" || p === "aggressive") A.state.profile = p;
    } catch (e) { /* URLSearchParams tidak didukung: pakai nilai awal, jangan gagal total. */ }
  }
  function writeUrl(replace) {
    try {
      var q = new URLSearchParams();
      q.set("target", A.state.target);
      q.set("days", String(A.state.days));
      q.set("profile", A.state.profile);
      history[replace === false ? "pushState" : "replaceState"]({}, "", location.pathname + "?" + q.toString());
    } catch (e) { /* tanpa history API: state tetap hidup di memori tab ini. */ }
  }
  A.readStateFromUrl = readFromUrl;
  A.syncUrl = writeUrl;

  /* Tautan antarhalaman membawa state saat ini, persis bentuk spec:
     research.html?target=XAU&days=90&profile=moderate */
  A.qhref = function (page) {
    try {
      var q = new URLSearchParams({ target: A.state.target, days: String(A.state.days), profile: A.state.profile });
      return page + "?" + q.toString();
    } catch (e) { return page; }
  };

  /* Registrasi renderer halaman aktif: shell memanggil ini setelah boot selesai
     dan setiap kali target/range/profile berubah dari kontrol bersama. */
  A.renderPage = null;
})(window.ARCAS);
