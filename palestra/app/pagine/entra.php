<?php
/** @var string $token */
use Studio\Vista;

echo Vista::intestazione('Entra');
?>
<div class="riquadro accesso">
  <h1>Bentornato</h1>
  <p>Tocca il pulsante per completare l'accesso.</p>

  <!-- Il consumo del codice avviene solo qui, con l'invio di questo modulo.
       Niente invio automatico: alcuni controlli antiphishing eseguono anche
       il JavaScript delle pagine che aprono, quindi un invio automatico
       verrebbe eseguito anche da loro. Un tocco vero non lo replicano. -->
  <form method="post" action="<?= Vista::u('/entra') ?>">
    <input type="hidden" name="token" value="<?= Vista::e($token) ?>">
    <button type="submit" class="principale">Entra</button>
  </form>
</div>
<?php
echo Vista::chiusura();
