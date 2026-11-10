/* Site-wide motion layer (yinonz-bina.com). Progressive enhancement only. */
(function () {
  'use strict';
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var noanim = document.body.classList.contains('a11y-noanim');
  if (reduce || noanim) return;
  var html = document.documentElement;
  html.classList.add('mo');

  /* 1. drifting background blobs */
  var bg = document.createElement('div');
  bg.className = 'mo-bg'; bg.setAttribute('aria-hidden', 'true');
  bg.innerHTML = '<span class="b1"></span><span class="b2"></span><span class="b3"></span>';
  document.body.insertBefore(bg, document.body.firstChild);

  /* 2. auto-tag elements for scroll reveal (skips things the page already animates) */
  var SEL = [
    '.sec-title', '.sec-head', '.card', '.need', '.step', '.tile', '.pcard', '.post', '.voice', '.vcard', '.ex',
    '.trust-list li', '.chooser', '.case-visual', '.case-copy', '.case-steps li', '.success-band', '.vmore', '.cform', '.contact-copy',
    '.faq details', '.about-copy', '.about .photo', '.who .card', '.checks li', '.flow li', '.more a', '.cta', '.showcase', '.examples .ex',
    '.band .proj-text', '.band .proj-visual', '.trio > div', '.tiles-groups .tile', '.post-card', '.bhero-panel', '.posts-grid > *',
    '.post-content > :not(h1):not(script):not(style)', 'main > article > :not(h1):not(header):not(script):not(style)',
    '.task-card', '.step-card', '.ks-card', '.ks-step'
  ].join(',');
  var items = [];
  try { items = Array.prototype.slice.call(document.querySelectorAll(SEL)); } catch (e) { items = []; }
  var vh = innerHeight;
  var groups = {};
  items.forEach(function (el) {
    if (el.closest('.hero') || el.closest('[data-reveal]') || el.hasAttribute('data-reveal') || el.classList.contains('reveal') || el.classList.contains('mo-in')) return;
    if (el.closest('.reveal') || el.closest('.mo-in')) return;
    var r = el.getBoundingClientRect();
    if (r.top < vh * 0.9) return; /* already on the first screen: never hide it */
    el.classList.add('mo-in');
    var parent = el.parentElement;
    var key = parent ? (parent.tagName + (parent.className || '')) : 'x';
    groups[key] = (groups[key] || 0) + 1;
    var idx = groups[key] - 1;
    el.style.setProperty('--mo-i', Math.min(idx, 6));
    if (el.matches('.case-visual, .proj-visual, .about .photo, .showcase img')) el.classList.add('mo-left');
    else if (el.matches('.case-copy, .proj-text, .about-copy')) el.classList.add('mo-right');
    else if (el.matches('.tile, .trust-list li, .vcard, .pcard')) el.classList.add('mo-zoom');
  });
  var revealed = 0, total = document.querySelectorAll('.mo-in').length;
  if ('IntersectionObserver' in window && total) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (x) {
        if (x.isIntersecting) { x.target.classList.add('mo-on'); io.unobserve(x.target); revealed++; }
      });
    }, { threshold: 0.08, rootMargin: '0px 0px -8% 0px' });
    document.querySelectorAll('.mo-in').forEach(function (el) { io.observe(el); });
    /* fail-safe: nothing stays hidden */
    setTimeout(function () { html.classList.add('mo-done'); }, 2500);
  } else {
    html.classList.add('mo-done');
  }

  /* 3. parallax: hero photo + large images, header shadow, reading progress */
  var heroPhoto = document.querySelector('.hero-photo');
  var parImgs = Array.prototype.slice.call(document.querySelectorAll('.about .photo img, .case-shot img'));
  var isPost = !!document.querySelector('.post-content, main article');
  var prog = null;
  if (isPost) { prog = document.createElement('div'); prog.className = 'mo-progress'; prog.setAttribute('aria-hidden', 'true'); document.body.appendChild(prog); }
  var ticking = false;
  function onScroll() {
    if (ticking) return; ticking = true;
    requestAnimationFrame(function () {
      var y = scrollY;
      html.classList.toggle('mo-scrolled', y > 24);
      if (!html.classList.contains('mo-done')) {
        document.querySelectorAll('.mo-in:not(.mo-on)').forEach(function (el) { var r = el.getBoundingClientRect(); if (r.top < vh * 0.92 && r.bottom > 0) el.classList.add('mo-on'); });
      }
      if (heroPhoto && y < vh * 1.2) heroPhoto.style.setProperty('--mo-par', (y * 0.22).toFixed(1) + 'px');
      parImgs.forEach(function (img) {
        var r = img.getBoundingClientRect();
        if (r.bottom < 0 || r.top > vh) return;
        var p = (r.top + r.height / 2 - vh / 2) / vh; /* -1..1 */
        img.style.setProperty('--mo-par2', (p * -18).toFixed(1) + 'px');
      });
      if (prog) {
        var max = document.documentElement.scrollHeight - vh;
        html.style.setProperty('--mo-prog', max > 0 ? Math.min(1, y / max).toFixed(3) : 0);
      }
      ticking = false;
    });
  }
  addEventListener('scroll', onScroll, { passive: true });
  addEventListener('resize', function () { vh = innerHeight; onScroll(); });
  onScroll();

  /* 4. hover tilt on cards (mouse only) */
  if (matchMedia('(hover: hover) and (pointer: fine)').matches) {
    var tilts = document.querySelectorAll('.card, .pcard, .vcard, .post, .ex, .tile, .step, .voice, .who .card, .post-card');
    tilts.forEach(function (c) {
      c.classList.add('mo-tilt');
      c.addEventListener('pointermove', function (e) {
        var r = c.getBoundingClientRect();
        var px = (e.clientX - r.left) / r.width - 0.5, py = (e.clientY - r.top) / r.height - 0.5;
        c.style.setProperty('--ry', (px * 6).toFixed(2) + 'deg');
        c.style.setProperty('--rx', (-py * 6).toFixed(2) + 'deg');
        c.classList.add('is-tilting');
      });
      c.addEventListener('pointerleave', function () { c.classList.remove('is-tilting'); c.style.removeProperty('--rx'); c.style.removeProperty('--ry'); });
    });
  }
})();
