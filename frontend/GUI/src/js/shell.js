/* ARCAS shell bersama (Upgrade.md 3): helper format/escape, status API,
   provenance bar, tab target, tabel statistik bersama, widget alokasi,
   widget modal persona, navigasi antarhalaman, dan orkestrasi boot.
   Halaman (pages/*.js) hanya fetch dan render isi khusus. */
window.ARCAS = window.ARCAS || {};
(function (A) {
  "use strict";

  /* Komponen target: peta tampilan dengan fallback generik. Tab tetap dibangun
     dari respons /api/universe, bukan dari konstanta lokal ini. */
  var TARGET_INFO = {
    XAU: { name: "Emas", ticker: "GC=F", venue: "CME", color: "#FFD33D", icon: "src/assets/gold.svg" },
    RATE_UST: { name: "Suku Bunga", ticker: "^TNX", venue: "CBOE", color: "#58A6FF", icon: "src/assets/rate_ust.svg" },
    SPX: { name: "S&P 500", ticker: "^GSPC", venue: "SNP", color: "#FF7517", icon: "src/assets/spx.svg" }
  };
  A.TARGET_INFO = TARGET_INFO;
  A.metaFor = function (assetId, row) {
    if (TARGET_INFO[assetId]) return TARGET_INFO[assetId];
    return {
      name: (row && row.name) || assetId,
      ticker: (row && row.price_ticker) || assetId,
      venue: (row && row.exchange) || "-",
      color: "#BDB7B7"
    };
  };
  function visualTarget(info) {
    if (info && info.icon) return "<img class='ticon' src='" + esc(info.icon) + "' alt=''>";
    return "<span class='swatch' style='background:" + esc(info.color) + "' aria-hidden='true'></span>";
  }
  A.visualTarget = visualTarget;
  var CLASS_LABEL = { bond: "Obligasi", mutual_fund: "Reksadana", stock: "Saham", etf: "ETF", btc: "BTC", gold: "Emas", cash: "Kas" };
  var PERSONA_LABEL = { retail: "Retail Investor", day_trader: "Day Trader", fund_manager: "Fund Manager", pension: "Long-term / Pension", risk_manager: "Risk Manager" };

  /* Helper dasar */
  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function fmt(n, d) {
    if (n === null || n === undefined || Number.isNaN(n)) return "n/a";
    var sign = n > 0 ? "+" : "";
    return sign + Number(n).toFixed(d == null ? 2 : d);
  }
  function fmtDate(iso) { return String(iso || "").slice(0, 10); }
  function num(v) { return v == null ? 0 : Number(v); }
  function pct(part, total) {
    if (!num(total)) return "";
    return " : " + String(Math.round(num(part) / num(total) * 1000) / 10).replace(".", ",") + "%";
  }
  function showState(id, msg) {
    var el = $(id);
    if (!el) return;
    if (!msg) { el.hidden = true; el.textContent = ""; return; }
    el.hidden = false; el.textContent = msg;
  }
  A.$ = $; A.esc = esc; A.fmt = fmt; A.fmtDate = fmtDate; A.num = num; A.pct = pct; A.showState = showState;
  A.CLASS_LABEL = CLASS_LABEL; A.PERSONA_LABEL = PERSONA_LABEL;

  /* Chip arah: selalu ikon + teks, oranye tak pernah untuk arah. Alasan: aturan
     aksesibilitas THEME.md, warna arah khusus hijau/merah/abu. */
  A.dirChip = function (direction) {
    var d = String(direction || "neutral").toLowerCase();
    if (d === "bullish" || d === "buy") return "<span class='chip buy'>▲ Bullish</span>";
    if (d === "bearish" || d === "sell") return "<span class='chip sell'>▼ Bearish</span>";
    if (d === "mixed") return "<span class='chip mix'>◆ Mixed</span>";
    return "<span class='chip hold'>● Netral</span>";
  };
  A.stanceChip = function (stance, strength) {
    var s = String(stance || "hold").toLowerCase();
    var dots = "";
    var n = Math.max(1, Math.min(5, Math.round(Number(strength || 0) * 5) || 1));
    for (var i = 0; i < n; i++) dots += "●";
    if (s === "buy") return "<span class='chip buy'>▲ BUY " + dots + "</span>";
    if (s === "sell") return "<span class='chip sell'>▼ SELL " + dots + "</span>";
    return "<span class='chip hold'>● HOLD " + dots + "</span>";
  };

  /* Status data: teks tampil di strip disclaimer (badge terpisah dihapus).
     Teks hanya muncul untuk tahap yang benar-benar terjadi; aria-live tetap. */
  function setStatus(mode, text) {
    var badge = $("dataBadge");
    if (badge) badge.textContent = text;
    var src = $("srcMeta");
    if (src) src.textContent = "Sumber: " + (A.state.apiOk ? (A.state.apiBase === "" ? "API relatif" : A.state.apiBase) : "ilustrasi lokal (API tidak terjangkau)");
  }
  function splashStatus(text) {
    if (window.Splash && typeof window.Splash.status === "function") window.Splash.status(text);
  }
  function splashDone() {
    if (window.Splash && typeof window.Splash.done === "function") window.Splash.done();
  }
  A.setStatus = setStatus;

  /* Data Provenance Bar (UI-01): mode live/empty/demo selalu terbaca teks. */
  A.renderProvenance = function (meta) {
    var box = $("provenance");
    if (!box) return;
    if (!meta) {
      $("provMode").textContent = "demo : ilustrasi lokal (API tidak terjangkau)";
      box.querySelector(".prov-item").classList.add("warn");
      ["provUniverse", "provSchema", "provModel", "provArticles", "provNews", "provFresh"]
        .forEach(function (id) { $(id).textContent = "ilustrasi"; });
      return;
    }
    box.querySelector(".prov-item").classList.remove("warn");
    $("provMode").textContent = "mode : " + meta.mode;
    $("provUniverse").textContent = meta.universe_version || "n/a";
    $("provSchema").textContent = meta.schema_version || "n/a";
    $("provModel").textContent = (meta.model_version || "n/a") + (meta.calibrated ? " (terkalibrasi)" : " (belum kalibrasi)");
    $("provArticles").textContent = String(meta.coverage.articles);
    $("provNews").textContent = String(meta.coverage.days_with_news);
    var fresh = meta.coverage.last_price_date || meta.coverage.last_news_date;
    $("provFresh").textContent = fresh ? "harga " + fresh : "belum ada deret";
  };
  A.loadMeta = function () {
    splashStatus("MEMUAT METADATA");
    return A.api("/api/meta").then(function (meta) {
      A.state.meta = meta;
      A.renderProvenance(meta);
      return meta;
    }).catch(function () {
      A.state.meta = null;
      A.renderProvenance(null);
      return null;
    });
  };

  /* Widget alokasi bersama: bar baseline vs baru + validasi total persis 100.
     Alasan validasi tampil: konstrain domain paling mudah dilanggar diam-diam. */
  A.renderAllocation = function (data) {
    var bars = $("allocBars");
    if (!bars) return;
    if (!data || !data.lines || !data.lines.length) {
      bars.innerHTML = "";
      showState("allocState", "Belum ada simulasi alokasi untuk profil ini.");
      var t = $("allocTotalNum"); if (t) t.textContent = "n/a";
      return;
    }
    showState("allocState", "");
    var total = data.lines.reduce(function (a, l) { return a + Number(l.new_pct || 0); }, 0);
    var ok = Math.abs(total - 100) < 0.01;
    var totalBox = $("allocTotal");
    totalBox.classList.toggle("valid", ok);
    totalBox.classList.toggle("invalid", !ok);
    $("allocTotalNum").textContent = total.toFixed(2) + "% " + (ok ? ": valid" : ": TIDAK valid");
    bars.innerHTML = data.lines.map(function (l) {
      var d = Number(l.delta_pp || 0);
      var cls = d > 0.005 ? "pos" : d < -0.005 ? "neg" : "flat";
      var arrow = d > 0.005 ? "▲" : d < -0.005 ? "▼" : "●";
      var wBase = Math.max(0, Math.min(100, Number(l.baseline_pct || 0)));
      var wNew = Math.max(0, Math.min(100, Number(l.new_pct || 0)));
      return "<div class='alloc-row'><div class='lbl'><span>" + esc(CLASS_LABEL[l.alloc_class] || l.alloc_class) +
        "</span><span class='" + cls + "'>" + esc(wBase.toFixed(1)) + "% " + arrow + " " + fmt(d, 2) + " pp : " + esc(wNew.toFixed(1)) + "%</span></div>" +
        "<div class='bar' role='img' aria-label='" + esc(l.alloc_class) + " baseline " + esc(wBase.toFixed(1)) + " persen, baru " + esc(wNew.toFixed(1)) + " persen'>" +
        "<div class='base' style='width:" + wBase + "%'></div><div class='tilt' style='width:" + wNew + "%;opacity:.85'></div></div></div>";
    }).join("");
  };

  /* Tabel statistik bersama (dipakai overview ringkas dan research lengkap). */
  var TEST_LABEL = { spearman: "Spearman", pearson: "Pearson", ols: "OLS-HAC", granger: "Granger", event_study: "CAR" };
  A.testLabel = function (t) { return TEST_LABEL[t] || t; };
  function statRow(r) {
    var sig = r.p_adjusted != null && r.p_adjusted < 0.05;
    var cls = r.estimate > 0.02 ? "pos" : r.estimate < -0.02 ? "neg" : "flat";
    var arrow = r.estimate > 0.02 ? "▲" : r.estimate < -0.02 ? "▼" : "●";
    return "<tr><td>" + esc(A.testLabel(r.test)) + (r.lag != null ? " L" + esc(r.lag) : "") + "</td>" +
      "<td class='" + cls + "'>" + arrow + " " + fmt(r.estimate, 3) + (sig ? "<span class='sig'>sig</span>" : "") + "</td>" +
      "<td>" + (r.p_adjusted != null ? Number(r.p_adjusted).toFixed(3) : Number(r.p_value).toFixed(3)) + "</td>" +
      "<td>" + esc(r.n_obs) + "</td></tr>";
  }
  A.renderStats = function (rows, emptyMsg) {
    var box = $("statTables");
    if (!box) return rows || [];
    if (!rows || !rows.length) {
      box.innerHTML = "";
      showState("statState", emptyMsg || "Belum ada hasil uji untuk target ini.");
      return [];
    }
    showState("statState", "");
    var order = ["spearman", "ols", "granger", "event_study", "pearson"];
    var html = "<table class='data'><thead><tr><th>Uji</th><th>Est</th><th>p_adj</th><th>n</th></tr></thead><tbody>";
    order.forEach(function (t) {
      rows.filter(function (r) { return r.test === t; }).slice(0, 6).forEach(function (r) { html += statRow(r); });
    });
    html += "</tbody></table>";
    /* Periode dan lag yang diuji (UI-02): angka statis punya denominasi yang terlihat. */
    var starts = [], ends = [], lagSeen = {}, lags = [];
    rows.forEach(function (r) {
      if (r.period_start) starts.push(String(r.period_start));
      if (r.period_end) ends.push(String(r.period_end));
      if (r.lag != null && !lagSeen[r.lag]) { lagSeen[r.lag] = true; lags.push(r.lag); }
    });
    if (starts.length && ends.length) {
      lags.sort(function (a, b) { return a - b; });
      starts.sort(); ends.sort();
      html += "<p class='hint' style='font-family:var(--font-mono);font-size:11px;color:var(--on-dark-muted)'>Periode uji: " +
        esc(starts[0]) + " .. " + esc(ends[ends.length - 1]) + " : lag diuji L" + lags.join(", L") +
        ". Asosiasi historis, bukan sebab.</p>";
    }
    box.innerHTML = html;
    return rows.slice();
  };

  /* Modal persona (evidence.html dan simulations.html hidup di latar terang,
     tabelnya pakai varian terang lewat CSS. barang modal dipakai bersama). */
  A.openPersona = function (articleId, fallback, onDone) {
    var modal = $("personaModal");
    if (!modal) return;
    $("personaList").innerHTML = "";
    showState("personaState", "Memuat stance lima persona...");
    if (typeof modal.showModal === "function" && !modal.open) modal.showModal();
    var params = "?target=" + encodeURIComponent(A.state.target) +
      "&score=" + encodeURIComponent(fallback && fallback.score != null ? fallback.score : 0.35) +
      "&confidence=" + encodeURIComponent(fallback && fallback.confidence != null ? fallback.confidence : 0.75);
    A.api("/api/persona/" + encodeURIComponent(articleId) + params).then(function (views) {
      renderPersona(articleId, views);
      if (onDone) onDone();
    }).catch(function () {
      var demo = ["retail", "day_trader", "fund_manager", "pension", "risk_manager"].map(function (p, i) {
        return { article_id: articleId, persona_id: p, target: A.state.target, stance: i === 0 ? "buy" : i === 4 ? "sell" : "hold", strength: 0.4 + i * 0.1, news_horizon: "medium", raw_value: 0.2, confidence: 0.6, rationale: "Ilustrasi lokal: API persona tidak terjangkau.", params_version: "demo", disclaimer: "Simulasi sudut pandang. Bukan nasihat investasi." };
      });
      renderPersona(articleId, demo);
      showState("personaState", "API persona tidak terjangkau, menampilkan ilustrasi berlabel.");
      if (onDone) onDone();
    });
  };
  function renderPersona(articleId, views) {
    if (!views || !views.length) { showState("personaState", "Tidak ada stance untuk artikel ini."); return; }
    showState("personaState", "");
    $("personaTitle").textContent = "Stance untuk " + articleId.slice(0, 24);
    $("personaList").innerHTML = "<table class='data'><thead><tr><th>Persona</th><th>Stance</th><th>Alasan</th></tr></thead><tbody>" +
      views.map(function (v) {
        return "<tr><td>" + esc(PERSONA_LABEL[v.persona_id] || v.persona_id) + "</td><td>" + A.stanceChip(v.stance, v.strength) + "</td><td style='font-family:var(--font-sans);font-size:13px'>" + esc(v.rationale || "") + "</td></tr>";
      }).join("") + "</tbody></table>";
  }
  function bindPersonaModal() {
    var modal = $("personaModal");
    if (!modal) return;
    $("personaClose").addEventListener("click", function () { modal.close(); });
    modal.addEventListener("click", function (e) {
      var r = modal.getBoundingClientRect();
      var outside = e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
      if (outside) modal.close();
    });
  }

  /* Tab target dari /api/universe + keyboard pemilihan pakai tombol arah saat
     tab fokus. Nomor 1-4 lepas ke navigasi halaman sesuai spec Upgrade.md. */
  var TAB_ORDER = { XAU: 0, RATE_UST: 1, SPX: 2 };
  function renderTabs(rows) {
    rows = rows.slice().sort(function (a, b) {
      var ao = TAB_ORDER[a.asset_id], bo = TAB_ORDER[b.asset_id];
      if (ao == null && bo == null) return a.asset_id < b.asset_id ? -1 : 1;
      if (ao == null) return 1;
      if (bo == null) return -1;
      return ao - bo;
    });
    var box = $("targetTabs");
    if (!box) return;
    box.innerHTML = rows.map(function (row) {
      var id = row.asset_id;
      var info = A.metaFor(id, row);
      var sel = id === A.state.target ? "true" : "false";
      return "<button class='target-tab' role='tab' data-target='" + esc(id) + "' aria-selected='" + sel + "'>" +
        visualTarget(info) +
        "<span class='tick'>" + esc(info.name) + "</span></button>";
    }).join("");
    var active = rows.filter(function (r) { return r.asset_id === A.state.target; });
    if (!active.length && rows.length) { A.state.target = rows[0].asset_id; } /* target URL tidak dikenal: pilih pertama */
    return rows;
  }
  function selectTarget(btn) {
    document.querySelectorAll(".target-tab").forEach(function (b) { b.setAttribute("aria-selected", "false"); });
    btn.setAttribute("aria-selected", "true");
    A.state.target = btn.getAttribute("data-target");
    A.syncUrl();
    if (typeof A.renderPage === "function") A.renderPage();
  }
  function bindTabs() {
    var box = $("targetTabs");
    if (!box) return;
    box.addEventListener("click", function (e) {
      var btn = e.target.closest(".target-tab");
      if (btn) selectTarget(btn);
    });
    box.addEventListener("keydown", function (e) {
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight" && e.key !== "ArrowUp" && e.key !== "ArrowDown") return;
      var tabs = Array.prototype.slice.call(document.querySelectorAll(".target-tab"));
      var cur = document.querySelector(".target-tab[aria-selected='true']") || tabs[0];
      if (!cur) return;
      var i = tabs.indexOf(cur) + (e.key === "ArrowLeft" || e.key === "ArrowUp" ? -1 : 1);
      var next = tabs[(i + tabs.length) % tabs.length];
      next.focus();
      selectTarget(next);
      e.preventDefault();
    });
    document.addEventListener("keydown", function (e) {
      if (e.target.matches("input, select, textarea")) return;
      /* Hotkey halaman 1-4 (Upgrade.md 3): pindah halaman membawa state URL. */
      var PAGES = ["index.html", "evidence.html", "research.html", "simulations.html"];
      var idx = Number(e.key) - 1;
      if (idx >= 0 && idx < PAGES.length && location.pathname.split("/").pop() !== PAGES[idx]) {
        location.href = A.qhref(PAGES[idx]);
      }
    });
  }
  A.loadUniverse = function () {
    splashStatus("MEMUAT UNIVERSE");
    return A.api("/api/universe").then(function (rows) {
      var active = (rows || []).filter(function (r) { return r.active === 1 || r.active === true; });
      if (!active.length) throw new Error("universe kosong");
      renderTabs(active);
    }).catch(function () {
      renderTabs([{ asset_id: "XAU" }, { asset_id: "RATE_UST" }, { asset_id: "SPX" }]);
    });
  };
  /* Kontrol rentang dan profil dipakai beberapa halaman; markup opsional. */
  A.bindSharedControls = function () {
    document.querySelectorAll(".range-btn").forEach(function (b) {
      b.addEventListener("click", function () {
        document.querySelectorAll(".range-btn").forEach(function (x) { x.setAttribute("aria-pressed", "false"); });
        b.setAttribute("aria-pressed", "true");
        A.state.days = Number(b.getAttribute("data-days"));
        A.syncUrl();
        if (typeof A.renderPage === "function") A.renderPage();
      });
    });
    document.querySelectorAll(".profile-btn").forEach(function (b) {
      b.addEventListener("click", function () {
        document.querySelectorAll(".profile-btn").forEach(function (x) { x.setAttribute("aria-pressed", "false"); });
        b.setAttribute("aria-pressed", "true");
        A.state.profile = b.getAttribute("data-profile");
        A.syncUrl();
        if (typeof A.renderPage === "function") A.renderPage();
      });
    });
    /* href statis diset agar menu benar saat middle-click; saat klik biasa,
       query dihitung ulang di satu waktu klik. Alasan: href yang dibangun saat
       boot akan membawa state basi saat user pindah tab dulu. */
    document.querySelectorAll("a[data-page]").forEach(function (a) {
      a.setAttribute("href", A.qhref(a.getAttribute("data-page")));
      a.addEventListener("click", function (e) {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return; /* tab baru: href statis dipakai */
        e.preventDefault();
        location.href = A.qhref(a.getAttribute("data-page"));
        document.querySelectorAll("a[data-page]").forEach(function (x) { x.removeAttribute("aria-current"); });
        a.setAttribute("aria-current", "page");
      });
    });
    bindPersonaModal();
    var pressed = document.querySelector(".range-btn[data-days='" + A.state.days + "']");
    if (pressed) { document.querySelectorAll(".range-btn").forEach(function (x) { x.setAttribute("aria-pressed", "false"); }); pressed.setAttribute("aria-pressed", "true"); }
    var profile = document.querySelector(".profile-btn[data-profile='" + A.state.profile + "']");
    if (profile) { document.querySelectorAll(".profile-btn").forEach(function (x) { x.setAttribute("aria-pressed", "false"); }); profile.setAttribute("aria-pressed", "true"); }
  };

  /* Boot bersama: base dulu, meta + universe paralel, lalu render halaman dan
     tutup splash. Tidak ada log palsu: status hanya untuk tahap nyata. */
  A.boot = function () {
    A.readStateFromUrl();
    A.bindSharedControls();
    bindTabs();
    setStatus("loading", "menghubungi API...");
    return A.detectBase().then(function () {
      setStatus(A.state.apiReachable ? "ok" : "err", A.state.apiReachable ? "terhubung ke API" : "API tidak terjangkau : ilustrasi");
      return Promise.allSettled([A.loadMeta(), A.loadUniverse()]);
    }).then(function () {
      splashStatus(A.state.meta ? "MODE " + A.state.meta.mode.toUpperCase() : "MODE DEMO");
      if (typeof A.renderPage === "function") return A.renderPage();
    }).then(splashDone);
  };
})(window.ARCAS);
