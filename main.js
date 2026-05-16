/* ══════════════════════════════════════════════════════════
   INNER COMPASS PROJECT — main.js
   ══════════════════════════════════════════════════════════ */

// ── Utility ───────────────────────────────────────────────
function showMsg(el, text, type) {
  if (!el) return;
  el.textContent = text;
  el.className   = 'form-msg ' + type;
}

async function postJSON(url, data) {
  const res = await fetch(url, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(data),
  });
  return res.json();
}

// ── Nav scroll ────────────────────────────────────────────
const nav = document.getElementById('nav');
if (nav) {
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 40);
  }, { passive: true });
}

// ── Mobile menu ───────────────────────────────────────────
const hamburger  = document.getElementById('hamburger');
const mobileMenu = document.getElementById('mobile-menu');
const mobileClose= document.getElementById('mobile-close');

if (hamburger && mobileMenu) {
  hamburger.addEventListener('click', () => mobileMenu.classList.toggle('open'));
}
if (mobileClose && mobileMenu) {
  mobileClose.addEventListener('click', () => mobileMenu.classList.remove('open'));
}
function closeMobileMenu() {
  mobileMenu && mobileMenu.classList.remove('open');
}

// ── Scroll reveal ─────────────────────────────────────────
const revealObs = new IntersectionObserver((entries) => {
  entries.forEach((entry, i) => {
    if (entry.isIntersecting) {
      setTimeout(() => entry.target.classList.add('visible'), i * 70);
      revealObs.unobserve(entry.target);
    }
  });
}, { threshold: 0.1 });

document.querySelectorAll('.reveal').forEach(el => revealObs.observe(el));

// ── Counter animation ─────────────────────────────────────
function animateCounter(el) {
  const target = parseInt(el.dataset.target) || 0;
  if (target === 0) { el.textContent = '0'; return; }
  const dur = 2000, start = performance.now();
  const fmt = n => n >= 1000 ? (n/1000).toFixed(1) + 'k' : String(n);
  const step = now => {
    const p = Math.min((now - start) / dur, 1);
    const e = 1 - Math.pow(1 - p, 3);
    el.textContent = fmt(Math.floor(e * target));
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

// Animate counters when visible
const counterObs = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      animateCounter(entry.target);
      counterObs.unobserve(entry.target);
    }
  });
}, { threshold: 0.5 });

document.querySelectorAll('[data-target]').forEach(el => counterObs.observe(el));

// ── Mood tracker (homepage) ───────────────────────────────
document.querySelectorAll('.mood-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    document.querySelectorAll('.mood-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const mood    = btn.dataset.mood;
    const respEl  = document.getElementById('mood-response');

    try {
      const data = await postJSON('/api/mood', { mood });
      if (respEl) {
        respEl.textContent = data.success ? data.message : data.error;
      }
    } catch {
      if (respEl) respEl.textContent = 'Could not save — try again.';
    }
  });
});

// ── Contact form ──────────────────────────────────────────
const contactForm = document.getElementById('contact-form');
if (contactForm) {
  contactForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = contactForm.querySelector('button[type=submit]');
    const msg = document.getElementById('c-msg');
    btn.disabled = true; btn.textContent = 'Sending…';

    try {
      const data = await postJSON('/api/contact', {
        name:    document.getElementById('c-name').value,
        email:   document.getElementById('c-email').value,
        subject: document.getElementById('c-subject').value,
        message: document.getElementById('c-message').value,
      });
      showMsg(msg, data.success ? '✓ ' + data.message : data.error, data.success ? 'success' : 'error');
      if (data.success) contactForm.reset();
    } catch {
      showMsg(msg, 'Network error. Please try again.', 'error');
    } finally {
      btn.disabled = false; btn.textContent = 'Send Message';
    }
  });
}

// ── Footer newsletter ─────────────────────────────────────
const footerNlForm = document.getElementById('footer-nl-form');
if (footerNlForm) {
  footerNlForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('footer-nl-email').value.trim();
    const msg   = document.getElementById('footer-nl-msg');
    try {
      const data = await postJSON('/api/subscribe', { email });
      showMsg(msg, data.success ? '✓ ' + data.message : data.error, data.success ? 'success' : 'error');
      if (data.success) footerNlForm.reset();
    } catch {
      showMsg(msg, 'Network error.', 'error');
    }
  });
}

// ── ESC closes modals ─────────────────────────────────────
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
  }
});
