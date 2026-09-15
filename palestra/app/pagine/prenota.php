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
  <?php foreach ($giorni as $data => $slot):
    $relativo = Vista::giornoRelativo($slot[0]['locale']);
    // "oggi"/"domani" da soli non dicono la data: qui la aggiungiamo,
    // altrove giornoRelativo() la include gia' (es. "giovedi' 19 marzo").
    $intestazione = in_array($relativo, ['oggi', 'domani'], true)
        ? ucfirst($relativo) . ', ' . Vista::giornoBreve($slot[0]['locale'])
        : ucfirst($relativo);
  ?>
    <section class="giorno">
      <h2><?= Vista::e($intestazione) ?></h2>

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
            <span class="tipo">
              <?= $gruppo ? 'Gruppo' : 'Individuale' ?>
              <?php if (count($s['maestri']) === 1): ?>
                · con <?= Vista::e($s['maestri'][0]['nome']) ?>
              <?php endif; ?>
            </span>
          </div>

          <!-- L'etichetta non e' decorativa: il colore da solo non basta
               a distinguere libero, pieno e gia' prenotato. Per
               un'individuale libera, pero', non c'e' altro da dire oltre
               "c'e' posto": un pallino basta, il testo resta per chi usa
               uno screen reader. -->
          <?php if ($stato === 'libero' && !$gruppo): ?>
            <span class="segno pallino"><span class="sr-only"><?= Vista::e($etichetta) ?></span></span>
          <?php else: ?>
            <span class="segno"><?= Vista::e($etichetta) ?></span>
          <?php endif; ?>

          <?php if (!$mia && $liberi > 0): ?>
            <form method="post" action="<?= Vista::u('/prenota') ?>" class="prenota-riga">
              <?= Vista::campoGettone() ?>
              <input type="hidden" name="slot" value="<?= Vista::e($s['id']) ?>">
              <?php if (count($s['maestri']) > 1): ?>
                <select name="maestro" aria-label="Scegli il maestro" required>
                  <option value="" disabled selected>Scegli il maestro</option>
                  <?php foreach ($s['maestri'] as $m): ?>
                    <option value="<?= Vista::e($m['id']) ?>"><?= Vista::e($m['nome']) ?></option>
                  <?php endforeach; ?>
                </select>
              <?php endif; ?>
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
