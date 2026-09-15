<?php
/** @var array $utente @var array $prossime @var array $passate */
use Studio\Vista;

echo Vista::intestazione('Le mie lezioni', $utente, 'prenotazioni');
?>
<h1>Le mie lezioni</h1>

<?= Vista::avviso('errore', $_GET['errore'] ?? null) ?>
<?= Vista::avviso('esito',  $_GET['esito']  ?? null) ?>

<?php if ($prossime === []): ?>
  <p class="vuoto">Non hai lezioni in programma.
     <a href="<?= Vista::u('/') ?>">Prenotane una</a>.</p>
<?php else: ?>
  <ul class="slot">
  <?php foreach ($prossime as $p): ?>
    <li class="slot-voce mia">
      <div class="quando">
        <span class="orario"><?= Vista::e(Vista::ora($p['locale'])) ?></span>
        <span class="tipo">
          <?= Vista::e(Vista::giornoRelativo($p['locale'])) ?> ·
          <?= $p['tipo'] === 'gruppo' ? 'Gruppo' : 'Individuale' ?>
          <?php if ($p['maestro_nome']): ?> · con <?= Vista::e($p['maestro_nome']) ?><?php endif; ?>
        </span>
      </div>

      <form method="post" action="<?= Vista::u('/disdici') ?>"
            onsubmit="return confirm(<?= $p['disdetta_gratuita']
              ? "'Disdire questa lezione? La lezione torna sul tuo saldo.'"
              : "'Sei fuori dai termini: disdicendo ora la lezione viene scalata. Confermi?'" ?>)">
        <?= Vista::campoGettone() ?>
        <input type="hidden" name="prenotazione" value="<?= Vista::e($p['id']) ?>">
        <button type="submit" class="secondaria">Disdici</button>
      </form>

      <!-- Il termine si dice prima, non dopo: e' la differenza fra una
           regola capita e una discussione in sala. -->
      <p class="termine <?= $p['disdetta_gratuita'] ? '' : 'scaduto' ?>">
        <?php if ($p['disdetta_gratuita']): ?>
          Disdetta gratuita entro
          <?= Vista::e(Vista::giornoRelativo($p['scadenza_disdetta'])) ?>
          alle <?= Vista::e(Vista::ora($p['scadenza_disdetta'])) ?>
        <?php else: ?>
          Termine scaduto: disdicendo ora la lezione viene scalata
        <?php endif; ?>
      </p>
    </li>
  <?php endforeach; ?>
  </ul>
<?php endif; ?>

<?php if ($passate !== []): ?>
  <h2 class="sezione">Gia' svolte</h2>
  <ul class="storico">
  <?php foreach ($passate as $p): ?>
    <li>
      <span><?= Vista::e(Vista::giorno($p['locale'])) ?>,
            <?= Vista::e(Vista::ora($p['locale'])) ?></span>
      <span class="tipo"><?= $p['tipo'] === 'gruppo' ? 'Gruppo' : 'Individuale' ?></span>
      <span class="esito-presenza <?= Vista::e($p['stato']) ?>">
        <?= ['presente' => 'Presente', 'assente' => 'Assente',
             'prenotata' => 'Da registrare'][$p['stato']] ?? '' ?>
      </span>
    </li>
  <?php endforeach; ?>
  </ul>
<?php endif; ?>
<?php
echo Vista::chiusura();
