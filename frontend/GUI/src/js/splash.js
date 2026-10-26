/* splash.js : adaptasi frontend/splash-screen/splash.js ke token lokal theme.css.
   Perilaku GUI: splash penuh pada setiap refresh (alwaysFull), log boot masuk
   beranimasi, dan bar progres bergerak. Tidak ada timer palsu: status hanya
   muncul dari tahap yang benar-benar terjadi (shell memanggil Splash.status),
   dan Splash.done() dipanggil setelah /health + /api/meta + /api/universe
   selesai atau fallback ilustrasi dipilih. */
(function () {
  "use strict";

  var cfg = Object.assign({
    key: "arcas_splash_seen", alwaysFull: true, reloadMode: "skeleton",
    fullMs: 950, skeletonMs: 450, maxMs: 8000, waitForApp: true
  }, window.SPLASH_CONFIG || {});

  var root = document.documentElement, el = document.getElementById("splash");
  var seen = false;
  try { seen = sessionStorage.getItem(cfg.key) === "1"; } catch (e) {}
  var mode = cfg.alwaysFull ? "full" : (seen ? cfg.reloadMode : "full");
  try { sessionStorage.setItem(cfg.key, "1"); } catch (e) {}

  var reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  var t0 = performance.now(), minDone = !cfg.waitForApp, ready = false, finished = false;
  var raf = 0, timers = [];
  var later = function (f, ms) { timers.push(setTimeout(f, ms)); };

  if (mode === "none" || (!el && mode !== "skeleton")) { if (el) el.remove(); return expose(); }

  var minMs = mode === "full" ? cfg.fullMs : cfg.skeletonMs;
  var bar, pct, log, topbar;

  if (mode === "skeleton") {
    if (el) el.remove();
    root.classList.add("is-loading");
    topbar = document.createElement("div");
    topbar.className = "splash-topbar";
    document.body.appendChild(topbar);
    requestAnimationFrame(function () {
      topbar.style.transition = "width " + minMs + "ms ease-out";
      topbar.style.width = "100%";
    });
  } else {
    el.hidden = false;
    bar = el.querySelector(".splash__bar i");
    pct = el.querySelector(".splash__pct");
    log = el.querySelector(".splash__log");
    animateBar(minMs);
    status("MENGHUBUNGI API", 0);
  }

  /* Bar bergerak dari 0 ke 92% selama minimum visual; sisa 8% ditutup saat
     data benar-benar siap. Gerak, bukan tebakan progres model. */
  function animateBar(ms) {
    var s = performance.now();
    (function f(n) {
      var p = Math.min(1, (n - s) / ms), e = 0.92 * (1 - Math.pow(1 - p, 1.8));
      if (!finished) {
        bar.style.width = e * 100 + "%";
        pct.textContent = Math.round(e * 100) + "%";
      }
      if (p < 1 && !finished) raf = requestAnimationFrame(f);
    })(s);
  }

  function stamp() {
    var dt = Math.max(0, (performance.now() - t0) / 1000);
    return "+" + dt.toFixed(2) + "s";
  }

  /* Log hanya berisi tahapan yang benar-benar terjadi; tiap baris masuk
     beranimasi dan baris sebelumnya ditandai OK tepat saat tahap berikutnya
     dimulai. Tanpa baris dramatis buatan. */
  function status(text) {
    if (!log) return;
    var prev = log.querySelector(".log-line.is-active");
    if (prev) {
      prev.classList.remove("is-active");
      prev.classList.add("is-ok");
      var mark = prev.querySelector(".log-mark");
      if (mark) mark.textContent = "OK";
    }
    var row = document.createElement("div");
    row.className = "log-line is-active";
    var m = document.createElement("span");
    m.className = "log-mark";
    m.textContent = ">";
    var t = document.createElement("span");
    t.className = "log-text";
    t.textContent = text;
    var ts = document.createElement("span");
    ts.className = "log-time";
    ts.textContent = stamp();
    row.appendChild(m);
    row.appendChild(t);
    row.appendChild(ts);
    log.appendChild(row);
    log.scrollTop = log.scrollHeight;
  }

  function markAllDone() {
    if (!log) return;
    log.querySelectorAll(".log-line").forEach(function (line) {
      line.classList.remove("is-active");
      line.classList.add("is-ok");
      var mark = line.querySelector(".log-mark");
      if (mark) mark.textContent = "OK";
    });
  }

  function tryFinish() {
    if (finished || !minDone || !ready) return;
    finished = true;
    cancelAnimationFrame(raf);
    if (bar) {
      bar.style.transition = "width .28s ease-out";
      bar.style.width = "100%";
      pct.textContent = "100%";
    }
    markAllDone();
    if (el && mode !== "skeleton") {
      el.classList.add("is-hiding");
      later(function () { el.remove(); }, reduce ? 0 : 380);
    }
    if (topbar) later(function () { topbar.remove(); }, 250);
    root.classList.remove("is-loading");
    document.dispatchEvent(new CustomEvent("splash:done", { detail: { mode: mode, ms: Math.round(performance.now() - t0) } }));
  }

  later(function () { minDone = true; tryFinish(); }, minMs);
  later(function () { ready = true; minDone = true; tryFinish(); }, cfg.maxMs);

  function expose() {
    window.Splash = { done: function () {}, status: function () {}, mode: mode };
  }
  window.Splash = {
    mode: mode,
    done: function () { ready = true; tryFinish(); },
    status: status
  };
})();
