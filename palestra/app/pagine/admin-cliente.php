<?php
/** @var array $utente @var array $scheda @var array $prenotabili */
use Studio\Vista;

$c = $scheda['anagrafica'];

echo Vista::intestazione($c['nome'], $utente, 'clienti');
?>
<p class="briciole"><a href="<?= Vista::u('/admin/clienti') ?>">&larr; Clienti</a></p>

<h1><?= Vista::e($c['nome']) ?><?= $c['attivo'] ? '' : ' <span class="segno">disattivato</span>' ?></h1>

<p class="sommesso">
  <a href="mailto:<?= Vista::e($c['email']) ?>"><?= Vista::e($c['email']) ?></a>
  <?php if ($c['telefono']): ?>
    · <a href="tel:<?= Vista::e($c['telefono']) ?>"><?= Vista::e($c['telefono']) ?></a>
  <?php endif; ?>
</p>

<?php if ($c['note']): ?>
  <!-- Le note stanno in alto: obiettivi e limitazioni servono prima della
       lezione, non in fondo alla pagina. -->
  <p class="note-cliente"><?= Vista::e($c['note']) ?></p>
<?php endif; ?>

<?= Vista::avviso('errore', $_GET['errore'] ?? null) ?>
<?= Vista::avviso('esito',  $_GET['esito']  ?? null) ?>

<div class="saldi">
  <div class="carta">
    <span class="numero"><?= (int) $scheda['saldi']['individuale'] ?></span>
    <span class="voce">individuali</span>
  </div>
  <div class="carta">
    <span class="numero"><?= (int) $scheda['saldi']['gruppo'] ?></span>
    <span class="voce">di gruppo</span>
  </div>
</div>

<details class="riquadro pubblica" <?= isset($_GET['errore']) ? 'open' : '' ?>>
  <summary>Registra un movimento</summary>

  <form method="post" action="<?= Vista::u('/admin/accredita') ?>" class="modulo-griglia">
    <?= Vista::campoGettone() ?>
    <input type="hidden" name="cliente" value="<?= Vista::e($c['id']) ?>">

    <div>
      <label for="quantita">Quante lezioni</label>
      <input id="quantita" name="quantita" type="number" required value="10" step="1">
    </div>
    <div>
      <label for="tipo-mov">Tipo</label>
      <select id="tipo-mov" name="tipo">
        <option value="individuale">Individuali</option>
        <option value="gruppo">Di gruppo</option>
      </select>
    </div>
    <div>
      <label for="causale">Causale</label>
      <select id="causale" name="causale">
        <option value="acquisto">Acquisto</option>
        <option value="omaggio">Omaggio / prova</option>
        <option value="rettifica">Rettifica (anche negativa)</option>
      </select>
    </div>
    <div>
      <label for="importo">Importo incassato (&euro;)</label>
      <input id="importo" name="importo" type="number" step="0.01" min="0">
    </div>
    <div class="larga">
      <label for="nota">Nota</label>
      <input id="nota" name="nota" placeholder="Pacchetto 10 lezioni, saldato in contanti">
    </div>

    <button type="submit" class="principale">Registra</button>
  </form>

  <p class="sommesso piccolo">
    Solo una rettifica puo' togliere lezioni. Il movimento resta nello
    storico per sempre: per correggere un errore se ne registra un altro di
    segno opposto, non si cancella il primo.
  </p>
</details>

<details class="riquadro pubblica">
  <summary>Piano alimentare e allenamento a casa</summary>

  <form method="post" action="<?= Vista::u('/admin/cliente/piano') ?>" class="modulo-griglia">
    <?= Vista::campoGettone() ?>
    <input type="hidden" name="cliente" value="<?= Vista::e($c['id']) ?>">

    <div class="larga">
      <label for="alimentare">Alimentazione</label>
      <textarea id="alimentare" name="alimentare" rows="5"
                placeholder="Consigli su cosa e come mangiare"><?= Vista::e($c['piano_alimentare'] ?? '') ?></textarea>
    </div>
    <div class="larga">
      <label for="allenamento">Allenamento a casa</label>
      <textarea id="allenamento" name="allenamento" rows="5"
                placeholder="Esercizi da fare senza attrezzi, tra una lezione e l'altra"><?= Vista::e($c['piano_allenamento'] ?? '') ?></textarea>
    </div>

    <button type="submit" class="principale">Salva piano</button>
  </form>

  <p class="sommesso piccolo">
    Il cliente lo vede subito nella sua sezione "Piano". Lascia un campo
    vuoto se per ora non c'e' nulla da scrivere in quella parte.
  </p>
</details>

<?php if ($c['attivo'] && $prenotabili !== []): ?>
<details class="riquadro pubblica">
  <summary>Prenota per suo conto</summary>

  <!-- Meta' dei clienti prenotera' per telefono o WhatsApp. Se non puoi
       farlo tu in tre tocchi, l'app viene abbandonata. -->
  <form method="post" action="<?= Vista::u('/admin/prenota') ?>" class="modulo-griglia">
    <?= Vista::campoGettone() ?>
    <input type="hidden" name="cliente" value="<?= Vista::e($c['id']) ?>">

    <div class="larga">
      <label for="slot">Lezione</label>
      <select id="slot" name="slot" required>
      <?php foreach ($prenotabili as $giornoSlot): ?>
        <?php foreach ($giornoSlot as $s):
          if ((int) $s['posti_liberi'] <= 0 || $s['mia']) { continue; } ?>
          <option value="<?= Vista::e($s['id']) ?>">
            <?= Vista::e(Vista::giorno($s['locale'])) ?>,
            <?= Vista::e(Vista::ora($s['locale'])) ?> —
            <?= $s['tipo'] === 'gruppo' ? 'gruppo' : 'individuale' ?>
            (<?= (int) $s['posti_liberi'] ?> liberi)
          </option>
        <?php endforeach; ?>
      <?php endforeach; ?>
      </select>
    </div>

    <button type="submit" class="principale">Prenota</button>
  </form>
</details>
<?php endif; ?>

<?php if ($scheda['prossime'] !== []): ?>
  <h2 class="sezione">Prossime lezioni</h2>
  <ul class="storico">
  <?php foreach ($scheda['prossime'] as $p): ?>
    <li>
      <span><?= Vista::e(Vista::giorno($p['locale'])) ?>, <?= Vista::e(Vista::ora($p['locale'])) ?></span>
      <span class="tipo"><?= $p['tipo'] === 'gruppo' ? 'Gruppo' : 'Individuale' ?></span>
      <span></span>
    </li>
  <?php endforeach; ?>
  </ul>
<?php endif; ?>

<h2 class="sezione">Movimenti</h2>
<?php if ($scheda['movimenti'] === []): ?>
  <p class="vuoto">Nessun movimento.</p>
<?php else: ?>
  <ul class="movimenti">
  <?php foreach ($scheda['movimenti'] as $m): $delta = (int) $m['delta']; ?>
    <li>
      <span class="delta <?= $delta > 0 ? 'piu' : 'meno' ?>"><?= $delta > 0 ? '+' : '' ?><?= $delta ?></span>
      <span class="descrizione">
        <?= Vista::e($m['etichetta']) ?>
        <span class="tipo">
          <?= $m['tipo'] === 'gruppo' ? 'gruppo' : 'individuale' ?>
          <?php if ($m['importo_eur'] !== null): ?>
            · &euro; <?= number_format((float) $m['importo_eur'], 2, ',', '.') ?>
          <?php endif; ?>
        </span>
        <?php if ($m['nota']): ?><span class="nota"><?= Vista::e($m['nota']) ?></span><?php endif; ?>
      </span>
      <span class="data"><?= Vista::e($m['locale']->format('d/m/Y')) ?></span>
    </li>
  <?php endforeach; ?>
  </ul>
<?php endif; ?>

<form method="post" action="<?= Vista::u('/admin/cliente/attivazione') ?>" class="esci"
      onsubmit="return confirm(<?= $c['attivo']
        ? "'Disattivare questo cliente? Perdera\\' subito l\\'accesso all\\'app.'"
        : "'Riattivare questo cliente?'" ?>)">
  <?= Vista::campoGettone() ?>
  <input type="hidden" name="cliente" value="<?= Vista::e($c['id']) ?>">
  <input type="hidden" name="attivo" value="<?= $c['attivo'] ? '0' : '1' ?>">
  <button type="submit" class="testuale"><?= $c['attivo'] ? 'Disattiva cliente' : 'Riattiva cliente' ?></button>
</form>
<?php
echo Vista::chiusura();
