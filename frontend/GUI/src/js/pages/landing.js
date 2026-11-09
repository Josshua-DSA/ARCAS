/* Halaman muka: sengaja terpisah dari shell.js.
   Landing tidak butuh splash, ticker, tab target, atau boot data penuh — ia
   hanya menarik /api/meta sekali untuk menampilkan cakupan nyata. Memakai
   shell.js di sini berarti menyeret seluruh mesin dasbor untuk satu angka. */

(function () {
  "use strict";

  var kotak = document.getElementById("lpFacts");
  if (!kotak) return;

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function kartu(label, nilai, catatan, tanggalKah) {
    return "<div class='lp-fact'>" +
      "<span class='lp-fact-label'>" + esc(label) + "</span>" +
      "<span class='lp-fact-value" + (tanggalKah ? " is-date" : "") + "'>" +
        esc(nilai) + "</span>" +
      (catatan ? "<span class='lp-fact-sub'>" + esc(catatan) + "</span>" : "") +
    "</div>";
  }

  /* Satu format tanggal untuk seluruh halaman: sumbu grafik dan kartu cakupan
     memakai bentuk yang sama. ISO hanya di API, bukan di layar. */
  function tanggal(d) {
    var t = new Date(String(d) + "T00:00:00Z");
    if (isNaN(t.getTime())) return String(d);
    return t.toLocaleDateString("id-ID", {
      day: "2-digit", month: "short", year: "numeric", timeZone: "UTC"
    });
  }

  /* Angka diambil dari /api/meta. Kalau API mati, halaman TIDAK mengarang
     angka: ia menyembunyikan deret fakta dan hanya menyisakan kalimat. */
  fetch("api/meta", { headers: { Accept: "application/json" } })
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(function (m) {
      var c = (m && m.coverage) || {};
      var html = "";
      if (c.articles) html += kartu("Artikel tersimpan", c.articles.toLocaleString("id-ID"));
      if (c.days_with_news) html += kartu("Hari berita", c.days_with_news.toLocaleString("id-ID"));
      if (c.sources) html += kartu("Sumber", c.sources.toLocaleString("id-ID"));
      if (c.last_price_date) html += kartu("Harga terakhir", tanggal(c.last_price_date), "", true);
      if (!html) {
        kotak.innerHTML = "<p class='lp-fact-note'>Cakupan data belum tersedia.</p>";
        return;
      }
      kotak.innerHTML = html;
    })
    .catch(function () {
      /* Sengaja tanpa angka pengganti. Dasbor tetap bisa dibuka; yang hilang
         hanya ringkasan cakupan. */
      kotak.innerHTML =
        "<p class='lp-fact-note'>Ringkasan cakupan tidak dapat dimuat. " +
        "Dasbor tetap bisa dibuka.</p>";
    });

  /* ---------------- bukti visual ---------------- */

  var W = 720, H = 150, PAD = 8;
  var PL = 46, PR = 6; /* kiri lega untuk label harga, kanan tipis */
  var svg = document.getElementById("lpProofSvg");
  var bungkus = document.getElementById("lpProof");
  var warn = document.getElementById("lpProofWarn");
  var sub = document.getElementById("lpProofSub");
  if (!svg || !bungkus) return;

  function gambar(prices, sentiments) {
    var tutup = [], i;
    /* Label sumbu harga: 2 desimal kalau rentangnya sempit (mis. yield), 0 kalau
       lebar (mis. indeks). Tanpa ini angka sumbu jadi "4215.3000000000002". */
    var fmt = function (v) {
      var n = Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(2);
      return n.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    };
    for (i = 0; i < prices.length; i++) {
      var v = prices[i].close;
      if (v === null || v === undefined) continue;
      tutup.push({ d: prices[i].date, v: Number(v) });
    }
    if (tutup.length < 2) return false;

    var min = Infinity, max = -Infinity;
    for (i = 0; i < tutup.length; i++) {
      if (tutup[i].v < min) min = tutup[i].v;
      if (tutup[i].v > max) max = tutup[i].v;
    }
    if (max === min) { max = min + 1; }  /* deret datar: hindari bagi nol */

    var n = tutup.length;
    var xDari = function (k) { return PL + (k / (n - 1)) * (W - PL - PR); };
    var yDari = function (v) {
      return H - PAD - 14 - ((v - min) / (max - min)) * (H - PAD * 2 - 28);
    };

    var garis = "";
    for (i = 0; i < n; i++) {
      garis += (i ? "L" : "M") + xDari(i).toFixed(1) + " " + yDari(tutup[i].v).toFixed(1);
    }

    /* Batang sentimen menempel ke hari bursa terdekat yang ada di deret harga.
       Hari tanpa berita tidak digambar sama sekali — bukan batang nol, karena
       nol berarti "netral" dan itu arti yang berbeda. */
    var tengah = H - PAD - 14 - (H - PAD * 2 - 28) / 2;
    var skala = (H - PAD * 2 - 28) / 2;
    /* Lebar batang tetap: kalau dihitung dari n, bar jadi kurus saat deret
       panjang dan tebal saat pendek — dua kartu berbeda skala terlihat rusak. */
    var lebar = 3.5;
    var batang = "", dipakai = 0;
    for (i = 0; i < sentiments.length; i++) {
      var s = sentiments[i];
      if (s.score_mean === null || s.score_mean === undefined) continue;
      var k = -1, j;
      for (j = 0; j < n; j++) {
        if (tutup[j].d >= s.date) { k = j; break; }
      }
      if (k < 0) continue;
      var skor = Math.max(-1, Math.min(1, Number(s.score_mean)));
      var tinggi = Math.abs(skor) * skala;
      var y = skor >= 0 ? tengah - tinggi : tengah;
      batang += "<rect x='" + (xDari(k) - lebar / 2).toFixed(1) +
        "' y='" + y.toFixed(1) + "' width='" + lebar.toFixed(1) +
        "' height='" + Math.max(0.5, tinggi).toFixed(1) +
        "' fill='" + (skor >= 0 ? "var(--up-dark)" : "var(--down-dark)") +
        "' opacity='0.55'/>";
      dipakai++;
    }

    svg.innerHTML =
      /* Garis nol sentimen: tanpa ini batang hanya bisa dibedakan warna, bukan
         posisi — pembaca buta warna kehilangan arah sama sekali. */
      "<line x1='" + (PL - 4) + "' y1='" + tengah.toFixed(1) + "' x2='" + (W - PR) +
        "' y2='" + tengah.toFixed(1) + "' stroke='var(--border-dark-strong)' " +
        "stroke-width='1' stroke-dasharray='3 3'/>" +
      "<text x='0' y='" + (PAD + 8) + "' class='lp-ax'>" + fmt(max) + "</text>" +
      "<text x='0' y='" + (H - PAD - 12).toFixed(1) + "' class='lp-ax'>" + fmt(min) + "</text>" +
      "<text x='" + (W - PR) + "' y='" + (tengah - 4).toFixed(1) +
        "' class='lp-ax lp-ax-zero' text-anchor='end'>skor 0</text>" +
      batang +
      "<path d='" + garis + "' fill='none' stroke='var(--chart-xau-dark)' " +
        "stroke-width='2' stroke-linejoin='round' vector-effect='non-scaling-stroke'/>" +
      "<text x='0' y='" + (H + 14) + "' class='lp-ax'>" + tanggal(tutup[0].d) + "</text>" +
      "<text x='" + ((PL + W - PR) / 2) + "' y='" + (H + 14) +
        "' class='lp-ax' text-anchor='middle'>" + tanggal(tutup[(n - 1) >> 1].d) + "</text>" +
      "<text x='" + (W - PR) + "' y='" + (H + 14) + "' class='lp-ax' text-anchor='end'>" +
        tanggal(tutup[n - 1].d) + "</text>";

    if (sub) {
      sub.textContent = tanggal(tutup[0].d) + " – " + tanggal(tutup[n - 1].d) +
        " \u00b7 " + n + " sesi XAU \u00b7 " + dipakai + " hari ada berita XAU";
    }
    /* Bukti tipis disebut, bukan disembunyikan. */
    if (warn) {
      warn.textContent = dipakai < n / 2
        ? "hanya " + Math.round((dipakai / n) * 100) + "% sesi punya berita"
        : "";
    }
    bungkus.hidden = false;
    return true;
  }

  fetch("api/series/XAU", { headers: { Accept: "application/json" } })
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(function (s) {
      gambar(s.prices || [], s.sentiments || []);
    })
    .catch(function () {
      /* Tanpa grafik lebih baik daripada grafik karangan. */
      if (bungkus) bungkus.hidden = true;
    });
})();
