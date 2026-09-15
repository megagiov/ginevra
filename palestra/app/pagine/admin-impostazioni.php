<?php
/** @var array $utente @var array $righe @var array $maestri */
use Studio\Vista;

echo Vista::intestazione('Impostazioni', $utente, 'impostazioni');
?>
<h1>Impostazioni</h1>

<?= Vista::avviso('errore', $_GET['errore'] ?? null) ?>
<?= Vista::avviso('esito',  $_GET['esito']  ?? null) ?>

<p class="sommesso piccolo">
  Queste regole valgono da subito per tutte le nuove prenotazioni. Le
  lezioni gia' prenotate non cambiano.
</p>

<form method="post" action="<?= Vista::u('/admin/impostazioni') ?>" class="modulo-griglia">
  <?= Vista::campoGettone() ?>
  <?php foreach ($righe as $r): ?>
    <div>
      <label for="<?= Vista::e($r['chiave']) ?>"><?= Vista::e($r['etichetta']) ?></label>
      <input id="<?= Vista::e($r['chiave']) ?>" name="<?= Vista::e($r['chiave']) ?>"
             type="number" min="<?= (int) $r['min'] ?>" max="<?= (int) $r['max'] ?>"
             value="<?= (int) $r['valore'] ?>" required>
      <?php if ($r['nota']): ?>
        <p class="sommesso piccolo"><?= Vista::e($r['nota']) ?></p>
      <?php endif; ?>
    </div>
  <?php endforeach; ?>
  <button type="submit" class="principale">Salva</button>
</form>

<h2 class="sezione">Maestri</h2>
<p class="sommesso piccolo">
  Da qui in poi puoi indicare, quando pubblichi una lezione, quale maestro
  (o quali) sono liberi a quell'ora. Con uno solo l'assegnazione e'
  automatica; con due o piu' il cliente sceglie chi preferisce in
  prenotazione. Con nessuno indicato, come oggi, non cambia nulla.
</p>

<?php if ($maestri === []): ?>
  <p class="vuoto">Nessun maestro ancora.</p>
<?php else: ?>
  <ul class="clienti">
  <?php foreach ($maestri as $m): ?>
    <li class="<?= $m['attivo'] ? '' : 'inattivo' ?>">
      <span class="nome">
        <?= Vista::e($m['nome']) ?>
        <?php if (!$m['attivo']): ?><span class="segno">disattivato</span><?php endif; ?>
      </span>
      <form method="post" action="<?= Vista::u('/admin/maestro/attivazione') ?>">
        <?= Vista::campoGettone() ?>
        <input type="hidden" name="maestro" value="<?= Vista::e($m['id']) ?>">
        <input type="hidden" name="attivo" value="<?= $m['attivo'] ? '0' : '1' ?>">
        <button type="submit" class="testuale piccolo"><?= $m['attivo'] ? 'Disattiva' : 'Riattiva' ?></button>
      </form>
    </li>
  <?php endforeach; ?>
  </ul>
<?php endif; ?>

<form method="post" action="<?= Vista::u('/admin/maestri') ?>" class="modulo-griglia">
  <?= Vista::campoGettone() ?>
  <div class="larga">
    <label for="nome-maestro">Nuovo maestro</label>
    <input id="nome-maestro" name="nome" required autocomplete="off">
  </div>
  <button type="submit" class="principale">Aggiungi</button>
</form>
<?php
echo Vista::chiusura();
