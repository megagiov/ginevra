<?php
/** @var array $utente @var array|null $piano */
use Studio\Vista;

echo Vista::intestazione('Piano', $utente, 'piano');
?>
<h1>Il tuo piano</h1>

<?php if ($piano === null): ?>
  <p class="vuoto">
    Il tuo personal trainer non ha ancora scritto un piano per te.
    Chiediglielo pure di persona: comparirà qui.
  </p>
<?php else: ?>
  <p class="sommesso piccolo">
    Ultimo aggiornamento: <?= Vista::e(Vista::giorno($piano['aggiornato_il'])) ?>.
  </p>

  <?php if ($piano['alimentare']): ?>
    <h2 class="sezione">Alimentazione</h2>
    <p class="testo-piano"><?= nl2br(Vista::e($piano['alimentare'])) ?></p>
  <?php endif; ?>

  <?php if ($piano['allenamento']): ?>
    <h2 class="sezione">Allenamento a casa</h2>
    <p class="testo-piano"><?= nl2br(Vista::e($piano['allenamento'])) ?></p>
  <?php endif; ?>
<?php endif; ?>
<?php
echo Vista::chiusura();
