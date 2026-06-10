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

  // Tour the app — sticky scroll slideshow.
  // Triggers are invisible 90vh divs. Whichever one is closest to the
  // viewport centre sets the active step. Dots are clickable and scroll
  // the matching trigger into view.
  const tourWrap = document.querySelector('.tour-sticky__wrap');
  if (tourWrap && 'IntersectionObserver' in window) {
    const triggers = tourWrap.querySelectorAll('.tour-trigger');
    const screens = tourWrap.querySelectorAll('.tour-screen');
    const steps = tourWrap.querySelectorAll('.tour-step');
    const dots = tourWrap.querySelectorAll('.tour-dot');

    const setActive = (idx) => {
      screens.forEach((el, i) => el.classList.toggle('is-active', i === idx));
      steps.forEach((el, i) => el.classList.toggle('is-active', i === idx));
      dots.forEach((el, i) => {
        el.classList.toggle('is-active', i === idx);
        if (i === idx) el.setAttribute('aria-current', 'true');
        else el.removeAttribute('aria-current');
      });
    };

    // Use a narrow centred root margin so only the trigger crossing the
    // viewport midpoint is "active" at any moment.
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const idx = Number(entry.target.dataset.step);
          if (!Number.isNaN(idx)) setActive(idx);
        }
      });
    }, { rootMargin: '-45% 0px -45% 0px', threshold: 0 });

    triggers.forEach((t) => io.observe(t));

    // Dot click → scroll the matching trigger to viewport centre.
    dots.forEach((dot) => {
      dot.addEventListener('click', () => {
        const idx = Number(dot.dataset.step);
        const trigger = triggers[idx];
        if (!trigger) return;
        const rect = trigger.getBoundingClientRect();
        const target = window.scrollY + rect.top - (window.innerHeight / 2) + (rect.height / 2);
        window.scrollTo({ top: target, behavior: 'smooth' });
      });
    });
  }
})();
