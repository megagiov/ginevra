/* Due cose soltanto: il menu su mobile e l'invio del modulo senza
   cambiare pagina. Nessuna libreria, nessuna richiesta esterna. */
(function () {
  var b = document.querySelector('.nav-toggle');
  var n = document.getElementById('menu');
  if (!b || !n) return;
  b.addEventListener('click', function () {
    var aperto = n.classList.toggle('aperto');
    b.setAttribute('aria-expanded', aperto ? 'true' : 'false');
  });
})();

/* Invio del modulo in AJAX: chi invia resta sul sito invece di finire sulla
   pagina di ringraziamento di Formspree. Se qualcosa non funziona (o se il
   JavaScript non parte) il modulo resta un normale POST e va a buon fine
   lo stesso: questo e' solo un miglioramento, non un requisito. */
(function () {
  var f = document.querySelector('form[action*="formspree"]');
  if (!f || !window.fetch) return;
  var esito = document.getElementById('esito-modulo');
  if (!esito) return;

  function mostra(classe, titolo, testo) {
    esito.className = classe;
    esito.innerHTML = '<strong>' + titolo + '</strong><br>' + testo;
    esito.hidden = false;
    esito.focus();
  }

  f.addEventListener('submit', function (ev) {
    if (!f.checkValidity()) return;
    ev.preventDefault();
    var invia = f.querySelector('button[type="submit"]');
    var etichetta = invia.textContent;
    invia.disabled = true;
    invia.textContent = 'Invio in corso...';

    fetch(f.action, {
      method: 'POST',
      body: new FormData(f),
      headers: { Accept: 'application/json' }
    }).then(function (r) {
      if (!r.ok) throw new Error(r.status);
      f.hidden = true;
      mostra('esito ok', 'Richiesta inviata.',
        'Vi ricontattiamo al numero che ci avete lasciato. Se avete fretta, ' +
        'chiamate pure il 347 263 6504.');
    }).catch(function () {
      invia.disabled = false;
      invia.textContent = etichetta;
      mostra('esito ko', 'Invio non riuscito.',
        'Riprovate fra poco, oppure scriveteci su WhatsApp o a ' +
        'sorgentetraslochi@gmail.com: ci arriva lo stesso.');
    });
  });
})();
