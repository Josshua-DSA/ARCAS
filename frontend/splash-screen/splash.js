/* splash.js — vanilla JS, tanpa dependensi.
   Kunjungan pertama dalam sesi  -> splash penuh (log boot)
   Load berikutnya / reload      -> SPLASH_CONFIG.reloadMode: 'quick' | 'full' | 'skeleton' | 'none'
   Panggil window.Splash.done() bila ingin menunggu data aplikasi siap (set waitForApp: true). */
(function () {
  var cfg = Object.assign({
    key: 'sd_splash_seen', reloadMode: 'quick',
    fullMs: 2600, quickMs: 700, skeletonMs: 900, maxMs: 8000, waitForApp: false,
    log: ['INITIALIZING FEEDS', 'LOADING SOURCE REGISTRY', 'LOADING SENTIMENT MODEL', 'SYNCING PRICES', 'READY']
  }, window.SPLASH_CONFIG || {});

  var root = document.documentElement, el = document.getElementById('splash');
  var seen = false;
  try { seen = sessionStorage.getItem(cfg.key) === '1'; } catch (e) {}
  var mode = seen ? cfg.reloadMode : 'full';
  try { sessionStorage.setItem(cfg.key, '1'); } catch (e) {}

  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var t0 = performance.now(), minDone = false, ready = !cfg.waitForApp && document.readyState === 'complete';
  var finished = false, raf = 0, timers = [];
  var later = function (f, ms) { timers.push(setTimeout(f, ms)); };

  if (mode === 'none' || !el && mode !== 'skeleton') { if (el) el.remove(); return expose(); }

  var minMs = mode === 'full' ? cfg.fullMs : mode === 'quick' ? cfg.quickMs : cfg.skeletonMs;
  var bar, pct, log, topbar;

  if (mode === 'skeleton') {
    if (el) el.remove();
    root.classList.add('is-loading');
    topbar = document.createElement('div'); topbar.className = 'splash-topbar';
    document.body.appendChild(topbar);
    requestAnimationFrame(function () {
      topbar.style.transition = 'width ' + minMs + 'ms ease-out'; topbar.style.width = '100%';
    });
  } else {
    el.hidden = false; el.classList.add('splash--' + mode);
    bar = el.querySelector('.splash__bar i'); pct = el.querySelector('.splash__pct'); log = el.querySelector('.splash__log');
    animateBar(minMs);
    if (mode === 'full' && log) cfg.log.forEach(function (_, i) {
      later(function () {
        log.innerHTML = cfg.log.slice(0, i + 1).map(function (x, j) {
          return (j < i ? '✓ ' : '› ') + x + (j === i && i < cfg.log.length - 1 ? '…' : '');
        }).join('<br>');
      }, i * (minMs / (cfg.log.length + 0.5)));
    });
  }

  function animateBar(ms) {
    var s = performance.now();
    (function f(n) {
      var p = Math.min(1, (n - s) / ms), e = 0.9 * (1 - Math.pow(1 - p, 1.6));
      if (!finished) { bar.style.width = e * 100 + '%'; pct.textContent = Math.round(e * 100) + '%'; }
      if (p < 1 && !finished) raf = requestAnimationFrame(f);
    })(s);
  }

  function tryFinish() {
    if (finished || !minDone || !ready) return;
    finished = true; cancelAnimationFrame(raf);
    if (bar) { bar.style.width = '100%'; pct.textContent = '100%'; }
    if (el && mode !== 'skeleton') {
      el.classList.add('is-hiding');
      later(function () { el.remove(); }, reduce ? 0 : 380);
    }
    if (topbar) later(function () { topbar.remove(); }, 250);
    root.classList.remove('is-loading');
    document.dispatchEvent(new CustomEvent('splash:done', { detail: { mode: mode, ms: Math.round(performance.now() - t0) } }));
  }

  later(function () { minDone = true; tryFinish(); }, minMs);
  later(function () { ready = true; minDone = true; tryFinish(); }, cfg.maxMs);   // pengaman
  if (!ready && !cfg.waitForApp) window.addEventListener('load', function () { ready = true; tryFinish(); });

  function expose() {
    window.Splash = { done: function () {}, mode: mode };
  }
  window.Splash = { mode: mode, done: function () { ready = true; tryFinish(); } };
})();
