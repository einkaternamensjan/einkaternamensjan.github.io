/* einkaternamensjan site files — set 6 (blog_template.html, generate_blogs.py, styles.css, post.js gehören zusammen) */
/* einkaternamensjan — shared behaviour for blog and bibliography pages.
   Everything here degrades gracefully: with JavaScript off the page still
   shows both languages, linked footnotes and a full footnote apparatus. */

(function () {
  'use strict';

  var VIEW_KEY = 'ekj-view-mode';
  var VIEWS = ['parallel', 'de', 'en'];
  var NARROW = 860;
  var EXPECTED_STYLESHEET_VERSION = '6';

  /* --- stylesheet check -------------------------------------------------- */
  /* The switch only changes a class on <body>; hiding the other column is the
     stylesheet's job. If an old styles.css is being served, clicking appears
     to do nothing at all — so say so plainly instead of failing silently. */

  function checkStylesheet() {
    var found = getComputedStyle(document.documentElement)
      .getPropertyValue('--stylesheet-version').trim();

    if (found === EXPECTED_STYLESHEET_VERSION) return;

    console.warn(
      'einkaternamensjan: styles.css ist Version "' + (found || 'unbekannt') +
      '", post.js erwartet "' + EXPECTED_STYLESHEET_VERSION + '".\n' +
      'Der Sprachumschalter setzt die Klasse, aber das Stylesheet reagiert nicht darauf.\n' +
      'Entweder liegt noch die alte styles.css im Repo, oder der Browser liefert eine ' +
      'zwischengespeicherte Fassung aus (Strg+F5 bzw. Cmd+Shift+R).'
    );
  }

  /* --- theme ------------------------------------------------------------ */
  /* The initial class is set by an inline script in the template so there is no
     flash on load; this only handles the toggle afterwards. */

  function initTheme() {
    var button = document.getElementById('theme-toggle');
    if (!button) return;

    var root = document.documentElement;

    var label = function () {
      var dark = root.classList.contains('theme-dark');
      button.setAttribute('aria-pressed', String(dark));
      button.title = dark ? 'Heller Modus' : 'Dunkler Modus';
    };

    label();

    button.addEventListener('click', function () {
      var next = root.classList.contains('theme-dark') ? 'light' : 'dark';
      root.className = 'theme-' + next;
      try { localStorage.setItem('ekj-theme', next); } catch (e) { /* private mode */ }
      label();
    });
  }

  /* --- view mode ------------------------------------------------------- */

  function availableViews() {
    var has = { de: !!document.querySelector('.lang-de'), en: !!document.querySelector('.lang-en') };
    if (has.de && has.en) return VIEWS;
    return has.de ? ['de'] : ['en'];
  }

  function currentView() {
    for (var i = 0; i < VIEWS.length; i++) {
      if (document.body.classList.contains('view-' + VIEWS[i])) return VIEWS[i];
    }
    return 'parallel';
  }

  function applyView(view) {
    VIEWS.forEach(function (v) {
      document.body.classList.toggle('view-' + v, v === view);
    });
    var buttons = document.querySelectorAll('.view-switch button');
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].setAttribute('aria-pressed', String(buttons[i].dataset.view === view));
    }
  }

  function setView(view, remember) {
    applyView(view);
    if (remember) {
      try { localStorage.setItem(VIEW_KEY, view); } catch (e) { /* private mode */ }
    }
  }

  function initView() {
    var views = availableViews();
    var stored = null;
    try { stored = localStorage.getItem(VIEW_KEY); } catch (e) { /* ignore */ }

    var view = views.indexOf(stored) !== -1 ? stored : views[0];

    // Parallel columns are unreadable on a phone. Pick the reader's language.
    if (view === 'parallel' && window.innerWidth < NARROW) {
      var preferred = (navigator.language || 'en').toLowerCase().indexOf('de') === 0 ? 'de' : 'en';
      if (views.indexOf(preferred) !== -1) view = preferred;
    }

    setView(view, false);

    var switcher = document.querySelector('.view-switch');
    if (!switcher) return;
    if (views.length < 2) { switcher.hidden = true; return; }

    switcher.addEventListener('click', function (event) {
      var button = event.target.closest('button[data-view]');
      if (button) setView(button.dataset.view, true);
    });
  }

  /* --- paragraph pairing ------------------------------------------------ */

  function initPairHighlight() {
    var layout = document.querySelector('.bilingual-layout.is-aligned');
    if (!layout) return;

    var hovered = null;
    var pinned = null;

    function paint(index, on) {
      if (index === null) return;
      var nodes = layout.querySelectorAll('.para[data-p="' + index + '"]');
      for (var i = 0; i < nodes.length; i++) nodes[i].classList.toggle('pair-active', on);
    }

    function repaint(next) {
      if (hovered === next) return;
      if (hovered !== null && hovered !== pinned) paint(hovered, false);
      hovered = next;
      paint(hovered, true);
    }

    layout.addEventListener('mouseover', function (event) {
      if (currentView() !== 'parallel') return;
      var para = event.target.closest('.para[data-p]');
      repaint(para ? para.dataset.p : null);
    });

    layout.addEventListener('mouseleave', function () {
      if (hovered !== null && hovered !== pinned) paint(hovered, false);
      hovered = null;
    });

    // Click pins a pair so it stays lit while reading, and works on touch.
    layout.addEventListener('click', function (event) {
      if (currentView() !== 'parallel') return;
      if (event.target.closest('a')) return;
      var para = event.target.closest('.para[data-p]');
      if (!para) return;

      var index = para.dataset.p;
      if (pinned === index) {
        paint(pinned, false);
        pinned = null;
        return;
      }
      if (pinned !== null) paint(pinned, false);
      pinned = index;
      paint(pinned, true);
    });
  }

  /* --- footnote bubbles ------------------------------------------------- */

  var bubble = null;

  function hideBubble() {
    if (bubble) { bubble.remove(); bubble = null; }
  }

  function showBubble(ref) {
    hideBubble();
    var target = document.getElementById(ref.getAttribute('href').slice(1));
    if (!target) return;

    var clone = target.cloneNode(true);
    var backref = clone.querySelector('.footnote-backref');
    if (backref) backref.remove();

    bubble = document.createElement('div');
    bubble.className = 'footnote-bubble';
    bubble.setAttribute('role', 'note');
    bubble.innerHTML = clone.innerHTML;
    document.body.appendChild(bubble);

    var rect = ref.getBoundingClientRect();
    var width = bubble.offsetWidth;
    var left = rect.left + window.scrollX;
    var top = rect.bottom + window.scrollY + 8;

    if (left + width > window.innerWidth - 12) left = window.innerWidth - width - 12;
    if (left < 12) left = 12;

    bubble.style.left = left + 'px';
    bubble.style.top = top + 'px';
  }

  function initFootnotes() {
    var refs = document.querySelectorAll('.footnote-ref');
    for (var i = 0; i < refs.length; i++) {
      refs[i].addEventListener('mouseenter', function (e) { showBubble(e.currentTarget); });
      refs[i].addEventListener('mouseleave', hideBubble);
      refs[i].addEventListener('focus', function (e) { showBubble(e.currentTarget); });
      refs[i].addEventListener('blur', hideBubble);
    }
    document.addEventListener('scroll', hideBubble, { passive: true });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') hideBubble();
    });
  }

  /* --- progress bar and back to top ------------------------------------- */

  function initScrollUi() {
    var bar = document.querySelector('.reading-progress span');
    var button = document.getElementById('back-to-top');
    var ticking = false;

    function update() {
      var doc = document.documentElement;
      var max = doc.scrollHeight - window.innerHeight;
      if (bar) bar.style.width = (max > 0 ? (window.scrollY / max) * 100 : 0) + '%';
      if (button) button.classList.toggle('is-visible', window.scrollY > window.innerHeight * 0.5);
      ticking = false;
    }

    window.addEventListener('scroll', function () {
      if (!ticking) { ticking = true; window.requestAnimationFrame(update); }
    }, { passive: true });

    window.addEventListener('resize', update, { passive: true });

    if (button) {
      button.addEventListener('click', function () {
        var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        window.scrollTo({ top: 0, behavior: reduce ? 'auto' : 'smooth' });
      });
    }

    update();
  }

  /* --- boot -------------------------------------------------------------- */

  function init() {
    checkStylesheet();
    initTheme();
    initView();
    initPairHighlight();
    initFootnotes();
    initScrollUi();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();