<?php
/** @var array $utente @var array $elenco */
use Studio\Vista;

echo Vista::intestazione('Clienti', $utente, 'clienti');
?>
<h1>Clienti</h1>

<?= Vista::avviso('errore', $_GET['errore'] ?? null) ?>
<?= Vista::avviso('esito',  $_GET['esito']  ?? null) ?>

<details class="riquadro pubblica" <?= isset($_GET['errore']) ? 'open' : '' ?>>
  <summary>Nuovo cliente</summary>

  <form method="post" action="<?= Vista::u('/admin/clienti') ?>" class="modulo-griglia">
    <?= Vista::campoGettone() ?>
    <div>
      <label for="nome">Nome e cognome</label>
      <input id="nome" name="nome" required autocomplete="off">
    </div>
    <div>
      <label for="email">Email</label>
      <input id="email" name="email" type="email" required autocomplete="off">
    </div>
    <div>
      <label for="telefono">Telefono</label>
      <input id="telefono" name="telefono" type="tel" autocomplete="off">
    </div>
    <div class="larga">
      <label for="note">Note (obiettivi, infortuni, limitazioni)</label>
      <input id="note" name="note" autocomplete="off">
    </div>
    <button type="submit" class="principale">Crea cliente</button>
  </form>

  <p class="sommesso piccolo">
    Il cliente entra da solo: gli basta scrivere la sua email nella pagina
    di accesso e riceve il link. Non serve comunicargli nessuna password.
  </p>
</details>

<?php if ($elenco === []): ?>
  <p class="vuoto">Nessun cliente ancora.</p>
<?php else: ?>
  <ul class="clienti">
  <?php foreach ($elenco as $c):
    if ($c['ruolo'] === 'admin') { continue; }

    // Un tipo mai acquistato non e' "a zero": semplicemente non lo usa.
    // Segnare in rosso lo 0 individuale di chi fa solo gruppo sarebbe un
    // allarme che suona sempre, e quindi un allarme che si smette di guardare.
    $usa = fn(?string $saldo): bool => $saldo !== null;
    $scarso = fn(?string $saldo): bool => $saldo !== null && (int) $saldo <= 2;
    $inEsaurimento = $scarso($c['saldo_individuale']) || $scarso($c['saldo_gruppo']);
  ?>
    <li class="<?= $c['attivo'] ? '' : 'inattivo' ?>">
      <a class="nome" href="<?= Vista::u('/admin/cliente') ?>?id=<?= Vista::e($c['id']) ?>">
        <?= Vista::e($c['nome']) ?>
        <?php if (!$c['attivo']): ?><span class="segno">disattivato</span><?php endif; ?>
      </a>

      <!-- Il saldo va letto a colpo d'occhio: e' il dato che dice se un
           pacchetto sta finendo, cioe' se c'e' un rinnovo da proporre. -->
      <span class="saldini">
        <?php if ($usa($c['saldo_individuale'])): ?>
          <span class="<?= $scarso($c['saldo_individuale']) ? 'scarso' : '' ?>">
            <?= (int) $c['saldo_individuale'] ?> ind.
          </span>
        <?php endif; ?>
        <?php if ($usa($c['saldo_gruppo'])): ?>
          <span class="<?= $scarso($c['saldo_gruppo']) ? 'scarso' : '' ?>">
            <?= (int) $c['saldo_gruppo'] ?> gr.
          </span>
        <?php endif; ?>
        <?php if (!$usa($c['saldo_individuale']) && !$usa($c['saldo_gruppo'])): ?>
          <span>nessun pacchetto</span>
        <?php endif; ?>
      </span>

      <?php if ($inEsaurimento): ?>
        <span class="segno attenzione-segno">in esaurimento</span>
      <?php endif; ?>
    </li>
  <?php endforeach; ?>
  </ul>
<?php endif; ?>

<p class="sommesso piccolo">
  <?php if (isset($_GET['tutti'])): ?>
    <a href="<?= Vista::u('/admin/clienti') ?>">Mostra solo i clienti attivi</a>
  <?php else: ?>
    <a href="<?= Vista::u('/admin/clienti?tutti=1') ?>">Mostra anche i disattivati</a>
  <?php endif; ?>
</p>
<?php
echo Vista::chiusura();
