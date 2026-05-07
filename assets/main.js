// Mobile nav toggle + tiny extras. No framework, no dependencies.
(function () {
  'use strict';

  const toggle = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.nav');
  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      const open = nav.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    nav.addEventListener('click', (e) => {
      const a = e.target.closest('a');
      if (a) nav.classList.remove('is-open');
    });
  }

  // Auto-update copyright year in the footer.
  const year = document.querySelector('.js-year');
  if (year) year.textContent = new Date().getFullYear();
})();
