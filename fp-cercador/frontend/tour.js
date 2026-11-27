/* Behaviour for com-funciona.html: scroll reveals, counters,
   scroll progress and the "route" diagram (stations + travelling progress). No dependencies.
   Every page works without this file: content is visible by default. */
(function () {
  var root = document.documentElement;
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  root.classList.add('js');

  /* ── Reveal on scroll ── */
  var revealed = document.querySelectorAll('.rv, .rv-rule, .rv-clip');
  if (reduce || !('IntersectionObserver' in window)) {
    revealed.forEach(function (el) { el.classList.add('in'); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        (entry.target._reveals || [entry.target]).forEach(function (el) { el.classList.add('in'); });
        io.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -12% 0px', threshold: 0.08 });
    revealed.forEach(function (el) {
      /* A fully clipped element never counts as intersecting, so a clip reveal is
         triggered by its parent coming into view, not by the clipped element itself. */
      if (el.classList.contains('rv-clip')) {
        var host = el.parentElement;
        if (!host._reveals) { host._reveals = []; io.observe(host); }
        host._reveals.push(el);
      } else {
        io.observe(el);
      }
    });
    /* Safety net: nothing stays hidden if the observer never fires. */
    window.addEventListener('load', function () {
      setTimeout(function () {
        revealed.forEach(function (el) {
          var r = el.getBoundingClientRect();
          if (r.top < window.innerHeight && r.bottom > 0) el.classList.add('in');
        });
      }, 1200);
    });
  }

  /* ── Counters: <span data-count="12989">12.989</span> counts up once when it enters ── */
  var fmt = new Intl.NumberFormat('ca-ES');
  function countUp(el) {
    var target = Number(el.getAttribute('data-count'));
    if (reduce || !isFinite(target)) return;
    var start = null;
    var duration = 1400;
    function frame(now) {
      if (start === null) start = now;
      var t = Math.min(1, (now - start) / duration);
      var eased = 1 - Math.pow(1 - t, 4);
      el.textContent = fmt.format(Math.round(target * eased));
      if (t < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }
  if ('IntersectionObserver' in window) {
    var cio = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        countUp(entry.target);
        cio.unobserve(entry.target);
      });
    }, { threshold: 0.6 });
    document.querySelectorAll('[data-count]').forEach(function (el) { cio.observe(el); });
  }

  /* ── Scroll progress: sets --prog (0..1) on [data-progress] as it crosses the viewport ── */
  var tracked = Array.prototype.slice.call(document.querySelectorAll('[data-progress]'));
  if (tracked.length) {
    var ticking = false;
    var update = function () {
      ticking = false;
      var vh = window.innerHeight;
      tracked.forEach(function (el) {
        var r = el.getBoundingClientRect();
        var p = (vh * 0.62 - r.top) / Math.max(r.height, 1);
        el.style.setProperty('--prog', reduce ? 1 : Math.max(0, Math.min(1, p)).toFixed(4));
      });
    };
    var onScroll = function () {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(update);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    update();
  }

  /* ── Route diagram ──
     Markup: .route[data-route] with .route-stations (buttons), .route-step, .route-text,
     optional [data-route-play] and a .seg[data-route-set] to switch between data sets.
     Data: window.TOUR_ROUTES[name] = { sets: { key: ["text per station", …] }, auto: ms } */
  function initRoute(el) {
    var data = (window.TOUR_ROUTES || {})[el.getAttribute('data-route')];
    if (!data) return;
    var stations = Array.prototype.slice.call(el.querySelectorAll('.route-stations li'));
    var stepEl = el.querySelector('.route-step');
    var textEl = el.querySelector('.route-text');
    var playBtn = el.querySelector('[data-route-play]');
    var setButtons = Array.prototype.slice.call(el.querySelectorAll('[data-route-set] button'));
    var setKey = Object.keys(data.sets)[0];
    var index = 0;
    var timer = null;

    el.style.setProperty('--n', stations.length);

    function render() {
      el.style.setProperty('--p', index);
      stations.forEach(function (li, i) {
        li.classList.toggle('is-done', i <= index);
        li.classList.toggle('is-now', i === index);
        li.querySelector('button').setAttribute('aria-current', i === index ? 'step' : 'false');
      });
      stepEl.textContent = stations[index].querySelector('button').textContent.trim();
      textEl.textContent = data.sets[setKey][index];
      textEl.classList.remove('swap');
      void textEl.offsetWidth;
      textEl.classList.add('swap');
    }

    function stop() {
      if (timer) { clearInterval(timer); timer = null; }
      if (playBtn) playBtn.textContent = playBtn.getAttribute('data-label-play');
    }

    function play() {
      stop();
      if (index >= stations.length - 1) index = 0;
      render();
      if (playBtn) playBtn.textContent = playBtn.getAttribute('data-label-stop');
      timer = setInterval(function () {
        if (index >= stations.length - 1) { stop(); return; }
        index += 1;
        render();
      }, data.auto || 2600);
    }

    stations.forEach(function (li, i) {
      li.querySelector('button').addEventListener('click', function () { stop(); index = i; render(); });
    });
    setButtons.forEach(function (btn) {
      btn.addEventListener('click', function () {
        setKey = btn.getAttribute('data-set');
        setButtons.forEach(function (b) { b.setAttribute('aria-pressed', String(b === btn)); });
        index = 0;
        if (reduce) { stop(); render(); } else { play(); }
      });
    });
    if (playBtn) playBtn.addEventListener('click', function () { if (timer) stop(); else play(); });

    render();
    /* Start the journey once, the first time the diagram is on screen. */
    if (!reduce && 'IntersectionObserver' in window) {
      var once = new IntersectionObserver(function (entries) {
        if (!entries[0].isIntersecting) return;
        once.disconnect();
        play();
      }, { threshold: 0.5 });
      once.observe(el);
    }
  }
  document.querySelectorAll('[data-route]').forEach(initRoute);

  window.TOUR = { reduce: reduce, fmt: fmt };
})();
