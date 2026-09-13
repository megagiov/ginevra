<?php
/** @var bool $inviata */
use Studio\Vista;

echo Vista::intestazione('Accedi');
?>
<div class="riquadro accesso">
<?php if ($inviata): ?>
  <h1>Controlla la posta</h1>
  <p>Se l'indirizzo e' registrato hai ricevuto un link per entrare.
     Vale 30 minuti e una volta sola.</p>
  <p class="sommesso">Non arriva? Controlla lo spam, oppure
     <a href="/accedi">richiedilo di nuovo</a>.</p>
<?php else: ?>
  <h1>Entra</h1>
  <p>Scrivi la tua email: ti mando un link per entrare.
     Nessuna password da ricordare.</p>

  <?= Vista::avviso('errore', $_GET['errore'] ?? null) ?>

  <form method="post" action="/accedi">
    <label for="email">Email</label>
    <input id="email" name="email" type="email" inputmode="email"
           autocomplete="email" required autofocus
           placeholder="nome@esempio.it">
    <button type="submit" class="principale">Mandami il link</button>
  </form>
<?php endif; ?>
</div>
<?php
echo Vista::chiusura();
