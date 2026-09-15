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

    <div>
      <label for="data">Giorno</label>
      <input id="data" name="data" type="date" required
             value="<?= $qui ?>" min="<?= (new DateTimeImmutable('today'))->format('Y-m-d') ?>">
      <p class="sommesso piccolo" id="giorno-nome"></p>
    </div>

    <div>
      <label for="ora">Ora d'inizio</label>
      <select id="ora" name="ora" required>
        <?php foreach (range(7, 20) as $h): $val = sprintf('%02d:00', $h); ?>
          <option value="<?= $val ?>" <?= $val === '18:00' ? 'selected' : '' ?>><?= $val ?></option>
        <?php endforeach; ?>
      </select>
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
        <?php foreach ($maestri as $m): ?>
          <label class="scelta">
            <input type="checkbox" name="maestri_individuale[]" value="<?= Vista::e($m['id']) ?>">
            <?= Vista::e($m['nome']) ?>
          </label>
        <?php endforeach; ?>
      </div>
      <div class="larga">
        <span class="etichetta-gruppo">Maestri liberi per il gruppo</span>
        <?php foreach ($maestri as $m): ?>
          <label class="scelta">
            <input type="checkbox" name="maestri_gruppo[]" value="<?= Vista::e($m['id']) ?>">
            <?= Vista::e($m['nome']) ?>
          </label>
        <?php endforeach; ?>
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
    Le lezioni durano 60 minuti. Le ripetizioni che cadono su un orario gia'
    occupato vengono saltate e te lo dico quali. "Entrambi" serve quando hai
    un secondo maestro disponibile: pubblica un'individuale e un gruppo
    nello stesso orario in un colpo solo.
  </p>
</details>

<script>
  // Solo per mostrare "lun", "mar", ecc. accanto alla data scelta: non
  // cambia cosa viene inviato al server, che riceve sempre la data intera.
  (function () {
    var giorni = ['dom', 'lun', 'mar', 'mer', 'gio', 'ven', 'sab'];
    var campo = document.getElementById('data');
    var etichetta = document.getElementById('giorno-nome');
    function aggiorna() {
      if (!campo.value) { etichetta.textContent = ''; return; }
      var d = new Date(campo.value + 'T00:00:00');
      etichetta.textContent = giorni[d.getDay()];
    }
    campo.addEventListener('input', aggiorna);
    aggiorna();
  })();
</script>

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
