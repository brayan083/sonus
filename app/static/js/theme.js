(function() {
  const root = document.documentElement;
  const btn  = document.getElementById('themeToggle');
  const stored = localStorage.getItem('theme');
  const theme = stored || 'dark';

  root.setAttribute('data-theme', theme);
  btn.textContent = theme === 'dark' ? '🌙' : '☀️';

  btn.addEventListener('click', () => {
    const current = root.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    btn.textContent = next === 'dark' ? '🌙' : '☀️';
    localStorage.setItem('theme', next);
  });
})();
