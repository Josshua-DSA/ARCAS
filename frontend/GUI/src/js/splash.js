/* splash.js : adaptasi frontend/splash-screen/splash.js ke token lokal theme.css.
   Bedanya: log boot bukan timer palsu (Upgrade.md 3.1-5), tapi status nyata yang
   di-set aplikasi lewat Splash.status(). Splash.done() dipanggil aplikasi setelah
   /health + /api/universe selesai atau fallback ilustrasi dipilih. */
(function () {
  "use strict";

  var cfg = Object.assign({
    key: "arcas_splash_seen", reloadMode: "skeleton",
    fullMs: 900, skeletonMs: 450, maxMs: 8000, waitForApp: true
  }, window.SPLASH_CONFIG || {});

  var root = document.documentElement, el = document.getElementById("splash");
  var seen = false;
  try { seen = sessionStorage.getItem(cfg.key) === "1"; } catch (e) {}
  var mode = seen ? cfg.reloadMode : "full";
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

  function animateBar(ms) {
    var s = performance.now();
    (function f(n) {
      var p = Math.min(1, (n - s) / ms), e = 0.9 * (1 - Math.pow(1 - p, 1.6));
      if (!finished) { bar.style.width = e * 100 + "%"; pct.textContent = Math.round(e * 100) + "%"; }
      if (p < 1 && !finished) raf = requestAnimationFrame(f);
    })(s);
  }

  /* Log hanya berisi tahapan yang benar-benar terjadi; langsung tampil, tanpa delay dramatis. */
  function status(text) {
    if (!log) return;
    var lines = log.querySelectorAll("div");
    for (var i = 0; i < lines.length - 1; i++) lines[i].textContent = "OK " + lines[i].textContent;
    var row = document.createElement("div");
    row.textContent = "... " + text;
    log.appendChild(row);
  }

  function tryFinish() {
    if (finished || !minDone || !ready) return;
    finished = true;
    cancelAnimationFrame(raf);
    if (bar) { bar.style.width = "100%"; pct.textContent = "100%"; }
    if (log) {
      var lines = log.querySelectorAll("div");
      for (var i = 0; i < lines.length; i++) lines[i].textContent = "OK " + lines[i].textContent;
    }
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
