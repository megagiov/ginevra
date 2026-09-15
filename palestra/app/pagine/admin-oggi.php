<?php
/** @var array $utente @var DateTimeImmutable $giorno @var array $agenda @var array $riepilogo */
use Studio\Vista;

$ieri  = $giorno->modify('-1 day')->format('Y-m-d');
$domani = $giorno->modify('+1 day')->format('Y-m-d');
$oggiVero = (new DateTimeImmutable('now', new DateTimeZone('Europe/Rome')));

echo Vista::intestazione('Oggi', $utente, 'oggi');
?>
<div class="navigazione-giorno">
  <a class="freccia" href="<?= Vista::u('/admin') ?>?giorno=<?= $ieri ?>" aria-label="Giorno precedente">&larr;</a>
  <h1><?= Vista::e(ucfirst(Vista::giornoRelativo($giorno))) ?></h1>
  <a class="freccia" href="<?= Vista::u('/admin') ?>?giorno=<?= $domani ?>" aria-label="Giorno successivo">&rarr;</a>
</div>

<?= Vista::avviso('errore', $_GET['errore'] ?? null) ?>
<?= Vista::avviso('esito',  $_GET['esito']  ?? null) ?>

<div class="riepilogo">
  <div><strong><?= (int) $riepilogo['lezioni'] ?></strong> lezioni</div>
  <div><strong><?= (int) $riepilogo['persone'] ?></strong> persone</div>
  <?php if ($riepilogo['da_registrare'] > 0): ?>
    <div class="attenzione"><strong><?= (int) $riepilogo['da_registrare'] ?></strong> da registrare</div>
  <?php endif; ?>
  <?php if ($riepilogo['in_esaurimento'] > 0): ?>
    <div class="attenzione">
      <a href="<?= Vista::u('/admin/clienti') ?>"><strong><?= (int) $riepilogo['in_esaurimento'] ?></strong> in esaurimento</a>
    </div>
  <?php endif; ?>
</div>

<?php if ($agenda === []): ?>
  <p class="vuoto">Nessuna lezione in calendario.
     <a href="<?= Vista::u('/admin/calendario') ?>?da=<?= $giorno->format('Y-m-d') ?>">Pubblica disponibilita'</a>.</p>
<?php else: ?>
  <?php foreach ($agenda as $s):
    $passata = $s['locale'] < $oggiVero;
  ?>
    <section class="lezione <?= $passata ? 'passata' : '' ?>">
      <header>
        <span class="orario"><?= Vista::e(Vista::ora($s['locale'])) ?></span>
        <span class="tipo">
          <?= $s['tipo'] === 'gruppo' ? 'Gruppo' : 'Individuale' ?>
          · <?= count($s['partecipanti']) ?>/<?= (int) $s['capienza'] ?>
          <?php if ($s['stato'] === 'chiuso'): ?><em>· chiusa</em><?php endif; ?>
        </span>
      </header>

      <?php if ($s['partecipanti'] === []): ?>
        <p class="vuoto piccolo">Nessuno prenotato.</p>
      <?php else: ?>
        <ul class="partecipanti">
        <?php foreach ($s['partecipanti'] as $p): ?>
          <li>
            <a class="nome" href="<?= Vista::u('/admin/cliente') ?>?id=<?= Vista::e($p['cliente_id']) ?>">
              <?= Vista::e($p['nome']) ?>
            </a>
            <?php if ($p['maestro_nome']): ?>
              <span class="sommesso piccolo">con <?= Vista::e($p['maestro_nome']) ?></span>
            <?php endif; ?>

            <?php if ($p['stato'] === 'prenotata'): ?>
              <!-- Due pulsanti, non una spunta: in sala si tocca una volta
                   sola e si va avanti, senza menu da aprire. -->
              <form method="post" action="<?= Vista::u('/admin/presenza') ?>" class="presenza">
                <?= Vista::campoGettone() ?>
                <input type="hidden" name="prenotazione" value="<?= Vista::e($p['id']) ?>">
                <input type="hidden" name="giorno" value="<?= $giorno->format('Y-m-d') ?>">
                <button type="submit" name="presente" value="1" class="principale piccolo">Presente</button>
                <button type="submit" name="presente" value="0" class="secondaria piccolo">Assente</button>
              </form>
            <?php else: ?>
              <span class="esito-presenza <?= Vista::e($p['stato']) ?>">
                <?= $p['stato'] === 'presente' ? 'Presente' : 'Assente' ?>
              </span>
              <form method="post" action="<?= Vista::u('/admin/presenza') ?>" class="presenza">
                <?= Vista::campoGettone() ?>
                <input type="hidden" name="prenotazione" value="<?= Vista::e($p['id']) ?>">
                <input type="hidden" name="giorno" value="<?= $giorno->format('Y-m-d') ?>">
                <button type="submit" name="presente" value="<?= $p['stato'] === 'presente' ? '0' : '1' ?>"
                        class="testuale piccolo">correggi</button>
              </form>
            <?php endif; ?>
          </li>
        <?php endforeach; ?>
        </ul>
      <?php endif; ?>
    </section>
  <?php endforeach; ?>
<?php endif; ?>

<form method="post" action="<?= Vista::u('/esci') ?>" class="esci">
  <?= Vista::campoGettone() ?>
  <button type="submit" class="testuale">Esci</button>
</form>
<?php
echo Vista::chiusura();
