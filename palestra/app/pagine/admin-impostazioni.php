<?php
/** @var array $utente @var array $righe */
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
<?php
echo Vista::chiusura();
