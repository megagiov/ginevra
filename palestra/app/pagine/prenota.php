<?php
/** @var array $utente @var array $giorni @var array $saldi */
use Studio\Vista;

echo Vista::intestazione('Prenota', $utente, 'prenota');
?>
<h1>Prenota una lezione</h1>

<p class="saldo-riga">
  Hai <strong><?= (int) $saldi['individuale'] ?></strong> lezioni individuali
  e <strong><?= (int) $saldi['gruppo'] ?></strong> di gruppo.
  <a href="<?= Vista::u('/saldo') ?>">Dettaglio</a>
</p>

<?= Vista::avviso('errore', $_GET['errore'] ?? null) ?>
<?= Vista::avviso('esito',  $_GET['esito']  ?? null) ?>

<?php if ($giorni === []): ?>
  <p class="vuoto">Non ci sono lezioni disponibili nei prossimi giorni.</p>
<?php else: ?>
  <?php foreach ($giorni as $data => $slot): ?>
    <section class="giorno">
      <h2><?= Vista::e(Vista::giornoRelativo($slot[0]['locale'])) ?></h2>

      <ul class="slot">
      <?php foreach ($slot as $s):
        $liberi = (int) $s['posti_liberi'];
        $mia    = (bool) $s['mia'];
        $gruppo = $s['tipo'] === 'gruppo';

        if     ($mia)         { $stato = 'mia';    $etichetta = 'Hai prenotato'; }
        elseif ($liberi <= 0) { $stato = 'pieno';  $etichetta = 'Completo'; }
        elseif ($gruppo)      { $stato = 'libero'; $etichetta = $liberi . ' post' . ($liberi === 1 ? 'o' : 'i') . ' liber' . ($liberi === 1 ? 'o' : 'i'); }
        else                  { $stato = 'libero'; $etichetta = 'Disponibile'; }
      ?>
        <li class="slot-voce <?= $stato ?>">
          <div class="quando">
            <span class="orario"><?= Vista::e(Vista::ora($s['locale'])) ?></span>
            <span class="tipo"><?= $gruppo ? 'Gruppo' : 'Individuale' ?></span>
          </div>

          <!-- L'etichetta non e' decorativa: il colore da solo non basta
               a distinguere libero, pieno e gia' prenotato. -->
          <span class="segno"><?= Vista::e($etichetta) ?></span>

          <?php if (!$mia && $liberi > 0): ?>
            <form method="post" action="<?= Vista::u('/prenota') ?>">
              <?= Vista::campoGettone() ?>
              <input type="hidden" name="slot" value="<?= Vista::e($s['id']) ?>">
              <button type="submit" class="principale">Prenota</button>
            </form>
          <?php endif; ?>
        </li>
      <?php endforeach; ?>
      </ul>
    </section>
  <?php endforeach; ?>
<?php endif; ?>
<?php
echo Vista::chiusura();
