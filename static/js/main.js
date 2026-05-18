/* ═══════════════════════════════════════════════════════════
   INNER COMPASS PROJECT — main.js
   ═══════════════════════════════════════════════════════════ */

// ── Utility ───────────────────────────────────────────────────────────────────
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

// ── Nav scroll ────────────────────────────────────────────────────────────────
const nav = document.getElementById('nav');
if (nav) {
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 40);
  }, { passive: true });
  // Trigger once on load
  nav.classList.toggle('scrolled', window.scrollY > 40);
}

// ── Mobile menu ───────────────────────────────────────────────────────────────
const hamburger  = document.getElementById('hamburger');
const mobileMenu = document.getElementById('mobile-menu');
const mobileClose = document.getElementById('mobile-close');

if (hamburger && mobileMenu) {
  hamburger.addEventListener('click', () => mobileMenu.classList.toggle('open'));
}
if (mobileClose && mobileMenu) {
  mobileClose.addEventListener('click', () => mobileMenu.classList.remove('open'));
}

function closeMobileMenu() {
  if (mobileMenu) mobileMenu.classList.remove('open');
}

// ── Scroll reveal ─────────────────────────────────────────────────────────────
const revealObs = new IntersectionObserver((entries) => {
  entries.forEach((entry, i) => {
    if (entry.isIntersecting) {
      setTimeout(() => entry.target.classList.add('visible'), i * 80);
      revealObs.unobserve(entry.target);
    }
  });
}, { threshold: 0.1 });

document.querySelectorAll('.reveal').forEach(el => revealObs.observe(el));

// ── Counter animation ─────────────────────────────────────────────────────────
function animateCounter(el) {
  const target = parseInt(el.dataset.target) || 0;
  if (target === 0) { el.textContent = '0'; return; }
  const dur = 2000;
  const start = performance.now();
  const fmt = n => n >= 1000 ? (n / 1000).toFixed(1) + 'k' : String(n);
  const step = now => {
    const p = Math.min((now - start) / dur, 1);
    const e = 1 - Math.pow(1 - p, 3);
    el.textContent = fmt(Math.floor(e * target));
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

const counterObs = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      animateCounter(entry.target);
      counterObs.unobserve(entry.target);
    }
  });
}, { threshold: 0.5 });

document.querySelectorAll('[data-target]').forEach(el => counterObs.observe(el));

// ── Mood tracker (homepage) ───────────────────────────────────────────────────
document.querySelectorAll('.mood-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    document.querySelectorAll('.mood-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const mood   = btn.dataset.mood;
    const respEl = document.getElementById('mood-response');

    try {
      const data = await postJSON('/api/mood', { mood });
      if (respEl) respEl.textContent = data.success ? data.message : (data.error || '');
    } catch {
      if (respEl) respEl.textContent = 'Could not save — try again.';
    }
  });
});

// ── Contact form ──────────────────────────────────────────────────────────────
const contactForm = document.getElementById('contact-form');
if (contactForm) {
  contactForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = contactForm.querySelector('button[type=submit]');
    const msg = document.getElementById('c-msg');
    btn.disabled = true; btn.textContent = 'Sending…';

    try {
      const data = await postJSON('/api/contact', {
        name:    document.getElementById('c-name').value.trim(),
        email:   document.getElementById('c-email').value.trim(),
        subject: document.getElementById('c-subject').value.trim(),
        message: document.getElementById('c-message').value.trim(),
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

// ── Footer newsletter ─────────────────────────────────────────────────────────
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

// ── ESC closes modals ─────────────────────────────────────────────────────────
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.open')
            .forEach(m => m.classList.remove('open'));
  }
});

// ── Dashboard tab switching ───────────────────────────────────────────────────
function switchTab(tabName) {
  document.querySelectorAll('.dash-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.dash-nav__link').forEach(l => l.classList.remove('active'));
  const tab  = document.getElementById('tab-' + tabName);
  const link = document.querySelector(`[data-tab="${tabName}"]`);
  if (tab)  tab.classList.add('active');
  if (link) link.classList.add('active');
  if (tabName === 'overview') {
    document.querySelectorAll('#tab-overview [data-target]').forEach(animateCounter);
  }
}

document.querySelectorAll('[data-tab]').forEach(el => {
  el.addEventListener('click', (e) => {
    e.preventDefault();
    switchTab(el.dataset.tab);
  });
});

// ── Dashboard: mood picker ────────────────────────────────────────────────────
let selectedMood = '';
document.querySelectorAll('.mood-pick-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.mood-pick-btn').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
    selectedMood = btn.dataset.mood;
  });
});

const logMoodBtn = document.getElementById('log-mood-btn');
if (logMoodBtn) {
  logMoodBtn.addEventListener('click', async () => {
    const note = document.getElementById('mood-note');
    const msg  = document.getElementById('mood-msg');
    const btn  = logMoodBtn;
    if (!selectedMood) { showMsg(msg, 'Please select a mood first.', 'error'); return; }
    btn.disabled = true; btn.textContent = 'Saving…';
    try {
      const data = await postJSON('/api/mood', {
        mood: selectedMood,
        note: note ? note.value.trim() : ''
      });
      if (data.success) {
        showMsg(msg, data.message, 'success');
        if (note) note.value = '';
        document.querySelectorAll('.mood-pick-btn').forEach(b => b.classList.remove('selected'));
        selectedMood = '';
        setTimeout(() => location.reload(), 1800);
      } else {
        showMsg(msg, data.error, 'error');
      }
    } catch { showMsg(msg, 'Network error.', 'error'); }
    finally  { btn.disabled = false; btn.textContent = 'Save Mood Entry'; }
  });
}

// ── Dashboard: profile form ───────────────────────────────────────────────────
const profileForm = document.getElementById('profile-form');
if (profileForm) {
  profileForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = profileForm.querySelector('button[type=submit]');
    btn.disabled = true; btn.textContent = 'Saving…';
    try {
      const data = await postJSON('/api/profile', {
        full_name: document.getElementById('p-name').value.trim(),
        bio:       document.getElementById('p-bio').value.trim()
      });
      showMsg(document.getElementById('profile-msg'),
              data.message || data.error,
              data.success ? 'success' : 'error');
    } catch { showMsg(document.getElementById('profile-msg'), 'Network error.', 'error'); }
    finally  { btn.disabled = false; btn.textContent = 'Save Changes'; }
  });
}

// ── Admin: mark message read ──────────────────────────────────────────────────
function expandMsg(row) {
  const next = row.nextElementSibling;
  if (next && next.classList.contains('admin-table__expand')) {
    next.style.display = next.style.display === 'none' ? 'block' : 'none';
  }
}

async function markRead(e, id, btn) {
  e.stopPropagation();
  try {
    const data = await postJSON(`/api/admin/message/${id}/read`, {});
    if (data.success) {
      btn.closest('.admin-table__row').classList.remove('admin-table__row--unread');
      btn.outerHTML = '<span class="status-badge status-badge--read">Read</span>';
    }
  } catch {}
}

// ── Admin: change user role ───────────────────────────────────────────────────
async function makeAdmin(id, btn, role = 'admin') {
  try {
    const data = await postJSON(`/api/admin/user/${id}/role`, { role });
    if (data.success) location.reload();
  } catch {}
}

// ── Admin: add program form ───────────────────────────────────────────────────
const programForm = document.getElementById('program-form');
if (programForm) {
  programForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = programForm.querySelector('button[type=submit]');
    btn.disabled = true; btn.textContent = 'Adding…';
    try {
      const data = await postJSON('/api/admin/program', {
        title:            document.getElementById('prog-title').value.trim(),
        location:         document.getElementById('prog-location').value.trim(),
        students_reached: document.getElementById('prog-students').value || 0,
        description:      document.getElementById('prog-desc') ?
                          document.getElementById('prog-desc').value.trim() : ''
      });
      showMsg(document.getElementById('prog-msg'),
              data.message || data.error,
              data.success ? 'success' : 'error');
      if (data.success) { programForm.reset(); setTimeout(() => location.reload(), 1500); }
    } catch { showMsg(document.getElementById('prog-msg'), 'Network error.', 'error'); }
    finally  { btn.disabled = false; btn.textContent = 'Add Program'; }
  });
}

// ── Resources page: filter & search ──────────────────────────────────────────
document.querySelectorAll('.res-filter').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.res-filter').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const cat = btn.dataset.cat;
    document.querySelectorAll('.res-full-card').forEach(card => {
      card.style.display = (cat === 'all' || card.dataset.cat === cat) ? '' : 'none';
    });
  });
});

function filterResources(q) {
  q = q.toLowerCase();
  document.querySelectorAll('.res-full-card').forEach(card => {
    const title = (card.dataset.title || '').toLowerCase();
    card.style.display = title.includes(q) ? '' : 'none';
  });
}

// ── Resources page: newsletter subscribe ─────────────────────────────────────
async function resSubscribe() {
  const email = document.getElementById('res-nl-email');
  const msg   = document.getElementById('res-nl-msg');
  if (!email || !email.value.trim()) {
    showMsg(msg, 'Please enter your email.', 'error'); return;
  }
  try {
    const data = await postJSON('/api/subscribe', { email: email.value.trim() });
    showMsg(msg, data.message || data.error, data.success ? 'success' : 'error');
    if (data.success && email) email.value = '';
  } catch { showMsg(msg, 'Network error.', 'error'); }
}

// ── Breathing exercise ────────────────────────────────────────────────────────
let breathInterval = null;
const phases = [
  { label: 'Inhale...', dur: 4000, scale: 1.4 },
  { label: 'Hold...',   dur: 4000, scale: 1.4 },
  { label: 'Exhale...', dur: 4000, scale: 1.0 },
  { label: 'Hold...',   dur: 4000, scale: 1.0 },
];

function startBreathing() {
  const circle = document.getElementById('breath-circle');
  const text   = document.getElementById('breath-text');
  const btn    = document.getElementById('breath-btn');
  if (!circle) return;

  if (breathInterval) {
    clearInterval(breathInterval);
    breathInterval = null;
    circle.style.transform = 'scale(1)';
    circle.textContent     = 'Press Start';
    if (text) text.textContent = '';
    if (btn)  btn.textContent  = 'Start Exercise';
    return;
  }

  if (btn) btn.textContent = 'Stop';
  let i = 0, cycles = 0;

  function run() {
    if (cycles >= 4) {
      clearInterval(breathInterval); breathInterval = null;
      circle.style.transform = 'scale(1)';
      circle.textContent     = 'Done! 🌿';
      if (text) text.textContent = 'Great job. You should feel calmer now.';
      if (btn)  btn.textContent  = 'Start Again';
      return;
    }
    const p = phases[i % 4];
    circle.style.transition = `transform ${p.dur}ms ease`;
    circle.style.transform  = `scale(${p.scale})`;
    circle.textContent      = p.label;
    if (text) text.textContent = p.label;
    if (i % 4 === 3) cycles++;
    i++;
  }
  run();
  breathInterval = setInterval(run, 4000);
}

// ── Admin dashboard counters on tab switch ────────────────────────────────────
function animateAllCounters() {
  document.querySelectorAll('#tab-overview [data-target]').forEach(animateCounter);
}

// Auto-animate on page load for dashboard stats
window.addEventListener('load', () => {
  document.querySelectorAll('.dash-stat__num[data-target]').forEach(animateCounter);
});
