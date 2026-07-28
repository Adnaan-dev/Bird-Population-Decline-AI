/* ============================================================
   Bird Population Decline AI — shared site behaviors
   Used by all pages (landing, dashboard, content pages).
   Vanilla JS, no dependencies. Safe to load on any page:
   every feature is guarded by presence checks.
   ============================================================ */
(function () {
  "use strict";

  var reduceMotion = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- Theme (light/dark) ---------- */
  function applyTheme(theme) {
    if (theme === "light") {
      document.documentElement.setAttribute("data-theme", "light");
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
  }
  // apply saved theme ASAP
  var saved = null;
  try { saved = localStorage.getItem("bpd_theme"); } catch (e) {}
  if (saved) applyTheme(saved);

  function initThemeToggle() {
    document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var isLight = document.documentElement.getAttribute("data-theme") === "light";
        var next = isLight ? "dark" : "light";
        applyTheme(next);
        try { localStorage.setItem("bpd_theme", next); } catch (e) {}
        btn.setAttribute("aria-pressed", String(next === "light"));
      });
    });
  }

  /* ---------- Condensing navbar ---------- */
  function initNavbarCondense() {
    var nav = document.querySelector(".navbar");
    if (!nav) return;
    var onScroll = function () {
      if (window.scrollY > 24) nav.classList.add("scrolled");
      else nav.classList.remove("scrolled");
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* ---------- Mobile nav toggle ---------- */
  function initMobileNav() {
    var toggle = document.querySelector(".nav-toggle");
    if (!toggle) return;
    toggle.addEventListener("click", function () {
      var open = document.body.classList.toggle("nav-open");
      toggle.setAttribute("aria-expanded", String(open));
    });
    // close after clicking a link
    document.querySelectorAll(".nav-links a").forEach(function (a) {
      a.addEventListener("click", function () {
        document.body.classList.remove("nav-open");
        toggle.setAttribute("aria-expanded", "false");
      });
    });
  }

  /* ---------- Scroll reveal ---------- */
  function initReveal() {
    var els = document.querySelectorAll(".reveal");
    if (!els.length) return;
    if (reduceMotion || !("IntersectionObserver" in window)) {
      els.forEach(function (el) { el.classList.add("in"); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("in");
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    els.forEach(function (el) { io.observe(el); });
  }

  /* ---------- Active section highlight (landing anchors) ---------- */
  function initSectionSpy() {
    var links = Array.prototype.slice.call(
      document.querySelectorAll('.nav-links a[href^="#"]'));
    if (!links.length || !("IntersectionObserver" in window)) return;
    var map = {};
    links.forEach(function (l) {
      var id = l.getAttribute("href").slice(1);
      var sec = document.getElementById(id);
      if (sec) map[id] = l;
    });
    var spy = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        var link = map[entry.target.id];
        if (!link) return;
        if (entry.isIntersecting) {
          links.forEach(function (l) { l.classList.remove("active-link"); });
          link.classList.add("active-link");
        }
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    Object.keys(map).forEach(function (id) {
      var sec = document.getElementById(id);
      if (sec) spy.observe(sec);
    });
  }

  /* ---------- Accordion ---------- */
  function initAccordion() {
    document.querySelectorAll(".acc-header").forEach(function (header) {
      header.addEventListener("click", function () {
        var item = header.closest(".acc-item");
        var body = item.querySelector(".acc-body");
        var isOpen = item.classList.toggle("open");
        header.setAttribute("aria-expanded", String(isOpen));
        body.style.maxHeight = isOpen ? body.scrollHeight + "px" : "0";
      });
    });
  }

  /* ---------- Count-up (shared, used by landing stat band) ---------- */
  function countUp(el, target, opts) {
    opts = opts || {};
    var decimals = opts.decimals || 0;
    var suffix = opts.suffix || "";
    var prefix = opts.prefix || "";
    var dur = reduceMotion ? 0 : (opts.duration || 1200);
    if (dur === 0) { el.textContent = prefix + target.toFixed(decimals) + suffix; return; }
    var start = performance.now();
    function frame(now) {
      var t = Math.min((now - start) / dur, 1);
      var eased = 1 - Math.pow(1 - t, 3);
      el.textContent = prefix + (target * eased).toFixed(decimals) + suffix;
      if (t < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }
  // expose for pages that want it
  window.BPD = window.BPD || {};
  window.BPD.countUp = countUp;

  function initStatBand() {
    var stats = document.querySelectorAll("[data-count]");
    if (!stats.length) return;
    var run = function (el) {
      countUp(el, parseFloat(el.getAttribute("data-count")), {
        decimals: parseInt(el.getAttribute("data-decimals") || "0", 10),
        suffix: el.getAttribute("data-suffix") || "",
        prefix: el.getAttribute("data-prefix") || "",
      });
    };
    if (!("IntersectionObserver" in window)) { stats.forEach(run); return; }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) { run(entry.target); io.unobserve(entry.target); }
      });
    }, { threshold: 0.5 });
    stats.forEach(function (el) { io.observe(el); });
  }

  /* ---------- Footer year ---------- */
  function initYear() {
    document.querySelectorAll("[data-year]").forEach(function (el) {
      el.textContent = new Date().getFullYear();
    });
  }

  /* ---------- PWA: manifest link, theme color, service worker ---------- */
  function initPWA() {
    if (!document.querySelector('link[rel="manifest"]')) {
      var m = document.createElement("link");
      m.rel = "manifest"; m.href = "/manifest.webmanifest";
      document.head.appendChild(m);
    }
    if (!document.querySelector('meta[name="theme-color"]')) {
      var t = document.createElement("meta");
      t.name = "theme-color"; t.content = "#10b981";
      document.head.appendChild(t);
    }
    if ("serviceWorker" in navigator && location.protocol !== "file:") {
      window.addEventListener("load", function () {
        navigator.serviceWorker.register("/sw.js").then(function (reg) {
          reg.update();
        }).catch(function () {});
        // When a new service worker activates, reload once so the fresh
        // assets (and cleared old caches) take effect immediately.
        var reloaded = false;
        navigator.serviceWorker.addEventListener("controllerchange", function () {
          if (reloaded) return;
          reloaded = true;
          window.location.reload();
        });
      });
    }
  }

  function init() {
    initThemeToggle();
    initNavbarCondense();
    initMobileNav();
    initReveal();
    initSectionSpy();
    initAccordion();
    initStatBand();
    initYear();
    initPWA();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
