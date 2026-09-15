<?php
/** @var array $utente @var DateTimeImmutable $lunedi @var array $settimana @var array $maestri */
use Studio\Vista;

$prima = $lunedi->modify('-7 days')->format('Y-m-d');
$dopo  = $lunedi->modify('+7 days')->format('Y-m-d');
$qui   = $lunedi->format('Y-m-d');

echo Vista::intestazione('Calendario', $utente, 'calendario');
?>
<div class="navigazione-giorno">
  <a class="freccia" href="<?= Vista::u('/admin/calendario') ?>?da=<?= $prima ?>" aria-label="Settimana precedente">&larr;</a>
  <h1 class="intervallo"><?= Vista::e(Vista::intervallo($lunedi, $lunedi->modify('+6 days'))) ?></h1>
  <a class="freccia" href="<?= Vista::u('/admin/calendario') ?>?da=<?= $dopo ?>" aria-label="Settimana successiva">&rarr;</a>
</div>

<?= Vista::avviso('errore', $_GET['errore'] ?? null) ?>
<?= Vista::avviso('esito',  $_GET['esito']  ?? null) ?>

<details class="riquadro pubblica" <?= isset($_GET['errore']) ? 'open' : '' ?>>
  <summary>Pubblica disponibilita'</summary>

  <form method="post" action="<?= Vista::u('/admin/slot') ?>" class="modulo-griglia">
    <?= Vista::campoGettone() ?>
    <input type="hidden" name="da" value="<?= $qui ?>">

    <div class="larga">
      <span class="etichetta-gruppo">Giorni (nella settimana qui sopra)</span>
      <div class="scelte-griglia">
        <?php foreach (['1'=>'Lun','2'=>'Mar','3'=>'Mer','4'=>'Gio','5'=>'Ven','6'=>'Sab','7'=>'Dom'] as $val => $etichetta): ?>
          <label class="scelta">
            <input type="checkbox" name="giorni[]" value="<?= $val ?>">
            <?= $etichetta ?>
          </label>
        <?php endforeach; ?>
      </div>
    </div>

    <div class="larga">
      <span class="etichetta-gruppo">Ore</span>
      <div class="scelte-griglia">
        <?php foreach (range(7, 20) as $h): $val = sprintf('%02d:00', $h); ?>
          <label class="scelta">
            <input type="checkbox" name="ore[]" value="<?= $val ?>">
            <?= $val ?>
          </label>
        <?php endforeach; ?>
      </div>
    </div>

    <div>
      <label for="tipo">Tipo</label>
      <select id="tipo" name="tipo">
        <option value="individuale">Individuale</option>
        <option value="gruppo">Gruppo</option>
        <option value="entrambi">Entrambi (due maestri)</option>
      </select>
    </div>

    <div>
      <label for="capienza">Posti (solo gruppo)</label>
      <select id="capienza" name="capienza">
        <option>2</option><option>3</option><option selected>4</option>
      </select>
    </div>

    <div>
      <label for="ripetizioni">Ripeti per</label>
      <select id="ripetizioni" name="ripetizioni">
        <option value="1">una volta sola</option>
        <option value="4">4 settimane</option>
        <option value="8">8 settimane</option>
        <option value="12">12 settimane</option>
      </select>
    </div>

    <?php if ($maestri !== []): ?>
      <div class="larga">
        <span class="etichetta-gruppo">Maestri liberi per l'individuale</span>
        <div class="scelte-griglia">
          <?php foreach ($maestri as $m): ?>
            <label class="scelta">
              <input type="checkbox" name="maestri_individuale[]" value="<?= Vista::e($m['id']) ?>">
              <?= Vista::e($m['nome']) ?>
            </label>
          <?php endforeach; ?>
        </div>
      </div>
      <div class="larga">
        <span class="etichetta-gruppo">Maestri liberi per il gruppo</span>
        <div class="scelte-griglia">
          <?php foreach ($maestri as $m): ?>
            <label class="scelta">
              <input type="checkbox" name="maestri_gruppo[]" value="<?= Vista::e($m['id']) ?>">
              <?= Vista::e($m['nome']) ?>
            </label>
          <?php endforeach; ?>
        </div>
      </div>
    <?php else: ?>
      <p class="sommesso piccolo larga">
        Nessun maestro configurato: la lezione si pubblica comunque, senza
        chiedere nulla al cliente. Puoi aggiungerne dalle
        <a href="<?= Vista::u('/admin/impostazioni') ?>">Impostazioni</a>.
      </p>
    <?php endif; ?>

    <button type="submit" class="principale">Pubblica</button>
  </form>

  <p class="sommesso piccolo">
    Le lezioni durano 60 minuti. Spunta piu' giorni e piu' ore per pubblicare
    tutta una settimana tipo in un colpo solo: ogni combinazione giorno/ora
    diventa una lezione. "Ripeti per" ripete lo stesso schema anche nelle
    settimane successive. Le combinazioni che cadono su un orario gia'
    occupato vengono saltate e te lo dico quali. "Entrambi" serve quando hai
    un secondo maestro disponibile: pubblica un'individuale e un gruppo
    nello stesso orario.
  </p>
</details>

<details class="riquadro pubblica">
  <summary>Cancella disponibilita'</summary>

  <form method="post" action="<?= Vista::u('/admin/slot/cancella') ?>" class="modulo-griglia"
        onsubmit="return confirm('Eliminare tutte le lezioni vuote che corrispondono a questa scelta? Quelle gia\' prenotate non vengono toccate.')">
    <?= Vista::campoGettone() ?>
    <input type="hidden" name="da" value="<?= $qui ?>">

    <div class="larga">
      <span class="etichetta-gruppo">Giorni (nella settimana qui sopra)</span>
      <div class="scelte-griglia">
        <?php foreach (['1'=>'Lun','2'=>'Mar','3'=>'Mer','4'=>'Gio','5'=>'Ven','6'=>'Sab','7'=>'Dom'] as $val => $etichetta): ?>
          <label class="scelta">
            <input type="checkbox" name="giorni[]" value="<?= $val ?>">
            <?= $etichetta ?>
          </label>
        <?php endforeach; ?>
      </div>
    </div>

    <div class="larga">
      <span class="etichetta-gruppo">Ore</span>
      <div class="scelte-griglia">
        <?php foreach (range(7, 20) as $h): $val = sprintf('%02d:00', $h); ?>
          <label class="scelta">
            <input type="checkbox" name="ore[]" value="<?= $val ?>">
            <?= $val ?>
          </label>
        <?php endforeach; ?>
      </div>
    </div>

    <div>
      <label for="tipo-cancella">Tipo</label>
      <select id="tipo-cancella" name="tipo">
        <option value="individuale">Individuale</option>
        <option value="gruppo">Gruppo</option>
        <option value="entrambi">Entrambi</option>
      </select>
    </div>

    <div>
      <label for="ripetizioni-cancella">Nelle prossime</label>
      <select id="ripetizioni-cancella" name="ripetizioni">
        <option value="1">questa settimana sola</option>
        <option value="4">4 settimane</option>
        <option value="8">8 settimane</option>
        <option value="12">12 settimane</option>
      </select>
    </div>

    <button type="submit" class="secondaria">Elimina</button>
  </form>

  <p class="sommesso piccolo">
    Cancella tutte le lezioni vuote che corrispondono a giorni, ore e tipo
    scelti. Le lezioni gia' prenotate non vengono mai toccate da qui: vanno
    disdette prima, oppure eliminate una per una qui sotto.
  </p>
</details>

<?php foreach ($settimana as $data => $slot):
  $giorno = new DateTimeImmutable($data, new DateTimeZone('Europe/Rome'));
?>
  <section class="giorno">
    <h2><?= Vista::e(ucfirst(Vista::giornoRelativo($giorno))) ?></h2>

    <?php if ($slot === []): ?>
      <p class="vuoto piccolo">Sala libera.</p>
    <?php else: ?>
      <ul class="slot">
      <?php foreach ($slot as $s):
        $occupati = (int) $s['capienza'] - (int) $s['posti_liberi'];
        $chiuso   = $s['stato'] === 'chiuso';
      ?>
        <li class="slot-voce <?= $chiuso ? 'pieno' : ((int) $s['posti_liberi'] > 0 ? 'libero' : 'pieno') ?>">
          <div class="quando">
            <span class="orario"><?= Vista::e(Vista::ora($s['locale'])) ?></span>
            <span class="tipo"><?= $s['tipo'] === 'gruppo' ? 'Gruppo' : 'Individuale' ?></span>
          </div>

          <span class="segno">
            <?= $occupati ?>/<?= (int) $s['capienza'] ?><?= $chiuso ? ' · chiusa' : '' ?>
          </span>

          <div class="azioni">
            <form method="post" action="<?= Vista::u('/admin/slot/stato') ?>">
              <?= Vista::campoGettone() ?>
              <input type="hidden" name="slot" value="<?= Vista::e($s['id']) ?>">
              <input type="hidden" name="da" value="<?= $qui ?>">
              <input type="hidden" name="stato" value="<?= $chiuso ? 'aperto' : 'chiuso' ?>">
              <button type="submit" class="testuale piccolo"><?= $chiuso ? 'Riapri' : 'Chiudi' ?></button>
            </form>

            <?php if ($occupati === 0): ?>
              <form method="post" action="<?= Vista::u('/admin/slot/elimina') ?>"
                    onsubmit="return confirm('Eliminare questa lezione dal calendario?')">
                <?= Vista::campoGettone() ?>
                <input type="hidden" name="slot" value="<?= Vista::e($s['id']) ?>">
                <input type="hidden" name="da" value="<?= $qui ?>">
                <button type="submit" class="testuale piccolo pericolo">Elimina</button>
              </form>
            <?php endif; ?>
          </div>
        </li>
      <?php endforeach; ?>
      </ul>
    <?php endif; ?>
  </section>
<?php endforeach; ?>
<?php
echo Vista::chiusura();
