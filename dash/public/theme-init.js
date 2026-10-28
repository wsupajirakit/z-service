// Runs before the app paints: the saved theme and language from src/theme.ts and src/i18n.
(function () {
  var root = document.documentElement;
  var saved = localStorage.getItem('zs.theme');
  var dark = saved === 'dark' || (saved !== 'light' && window.matchMedia('(prefers-color-scheme: dark)').matches);
  root.classList.add(dark ? 'dark' : 'light');
  root.setAttribute('data-theme', dark ? 'dark' : 'light');
  root.style.colorScheme = dark ? 'dark' : 'light';
  var lang = localStorage.getItem('zs.lang');
  root.lang = lang === 'th' || lang === 'en' ? lang : (navigator.language.toLowerCase().indexOf('th') === 0 ? 'th' : 'en');
})();
