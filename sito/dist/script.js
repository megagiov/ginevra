/* Solo l'apertura del menu su mobile: nessuna libreria, nessun tracciamento. */
(function () {
  var b = document.querySelector('.nav-toggle');
  var n = document.getElementById('menu');
  if (!b || !n) return;
  b.addEventListener('click', function () {
    var aperto = n.classList.toggle('aperto');
    b.setAttribute('aria-expanded', aperto ? 'true' : 'false');
  });
})();
