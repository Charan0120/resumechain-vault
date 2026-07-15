/* ── Password visibility toggle ─────────────────────────── */
document.querySelectorAll('.eye-toggle').forEach(btn => {
  btn.addEventListener('click', () => {
    const input = btn.closest('.input-wrap').querySelector('input');
    const isText = input.type === 'text';
    input.type = isText ? 'password' : 'text';
    btn.textContent = isText ? '👁' : '🙈';
  });
});

/* ── Password strength checker ──────────────────────────── */
const pwInput = document.getElementById('password');
if (pwInput) {
  const rules = [
    { id: 'rule-len',   test: v => v.length >= 8 },
    { id: 'rule-upper', test: v => /[A-Z]/.test(v) },
    { id: 'rule-num',   test: v => /\d/.test(v) },
  ];

  pwInput.addEventListener('input', () => {
    const val = pwInput.value;
    rules.forEach(r => {
      const el = document.getElementById(r.id);
      if (el) el.classList.toggle('ok', r.test(val));
    });
  });
}

/* ── Auto-dismiss flash messages after 5s ───────────────── */
setTimeout(() => {
  document.querySelectorAll('.alert').forEach(el => {
    el.style.transition = 'opacity 0.5s ease';
    el.style.opacity = '0';
    setTimeout(() => el.remove(), 500);
  });
}, 5000);
