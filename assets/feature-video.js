/* Feature animations: show the poster only for reduced motion; pause when off screen. */
(function () {
  var vids = document.querySelectorAll('video.fa-video');
  if (!vids.length) return;
  var rm = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  function still(v) {
    v.removeAttribute('autoplay'); v.autoplay = false; v.pause();
    if (v.currentTime > 0) v.load(); // back to the poster
    v.setAttribute('controls', '');
  }
  function play(v) { var p = v.play(); if (p && p.catch) p.catch(function () {}); }
  Array.prototype.forEach.call(vids, function (v) {
    if (rm && rm.matches) { still(v); return; }
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (rm && rm.matches) return;
          if (e.isIntersecting) play(v); else v.pause();
        });
      }, { threshold: 0.15 }).observe(v);
    }
  });
  if (rm) {
    var onChange = function () { if (rm.matches) Array.prototype.forEach.call(vids, still); };
    if (rm.addEventListener) rm.addEventListener('change', onChange); else if (rm.addListener) rm.addListener(onChange);
  }
})();
