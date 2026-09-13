<?php
/** @var array $utente @var array $saldi @var array $movimenti */
use Studio\Vista;

echo Vista::intestazione('Saldo', $utente, 'saldo');
?>
<h1>Il mio saldo</h1>

<div class="saldi">
  <div class="carta">
    <span class="numero"><?= (int) $saldi['individuale'] ?></span>
    <span class="voce">lezioni individuali</span>
  </div>
  <div class="carta">
    <span class="numero"><?= (int) $saldi['gruppo'] ?></span>
    <span class="voce">lezioni di gruppo</span>
  </div>
</div>

<h2 class="sezione">Movimenti</h2>

<?php if ($movimenti === []): ?>
  <p class="vuoto">Nessun movimento registrato.</p>
<?php else: ?>
  <!-- Il registro si mostra per intero: ogni riga dice data, causale e
       segno. E' la risposta alla domanda "perche' me ne risulta una in meno?" -->
  <ul class="movimenti">
  <?php foreach ($movimenti as $m):
    $delta = (int) $m['delta'];
  ?>
    <li>
      <span class="delta <?= $delta > 0 ? 'piu' : 'meno' ?>">
        <?= $delta > 0 ? '+' : '' ?><?= $delta ?>
      </span>
      <span class="descrizione">
        <?= Vista::e($m['etichetta']) ?>
        <span class="tipo"><?= $m['tipo'] === 'gruppo' ? 'gruppo' : 'individuale' ?></span>
        <?php if ($m['nota']): ?>
          <span class="nota"><?= Vista::e($m['nota']) ?></span>
        <?php endif; ?>
      </span>
      <span class="data">
        <?= Vista::e($m['locale']->format('d/m/Y')) ?>
      </span>
    </li>
  <?php endforeach; ?>
  </ul>
<?php endif; ?>

<form method="post" action="/esci" class="esci">
  <?= Vista::campoGettone() ?>
  <button type="submit" class="testuale">Esci</button>
</form>
<?php
echo Vista::chiusura();
