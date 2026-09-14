<?php
/** @var string $token */
use Studio\Vista;

echo Vista::intestazione('Entra');
?>
<div class="riquadro accesso">
  <h1>Bentornato</h1>
  <p>Stiamo completando l'accesso...</p>

  <!-- Un client di posta o un antivirus che apre questo link da solo non
       esegue il JavaScript qui sotto: vede solo questa pagina e non invia
       mai il modulo, quindi non consuma il codice al posto tuo. -->
  <form id="modulo-entra" method="post" action="<?= Vista::u('/entra') ?>">
    <input type="hidden" name="token" value="<?= Vista::e($token) ?>">
    <noscript>
      <button type="submit" class="principale">Entra</button>
    </noscript>
  </form>
</div>
<script>document.getElementById('modulo-entra').submit();</script>
<?php
echo Vista::chiusura();
