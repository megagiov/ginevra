<?php
/** @var array $utente @var array $giorni @var array $saldi */
use Studio\Vista;

echo Vista::intestazione('Prenota', $utente, 'prenota');

// Raggruppate per giorno, una riga per orario: quando ci sono piu' maestri
// candidati non si duplica la riga (stesso orario ripetuto piu' volte), ma
// compare una tendina secondaria per scegliere chi, sotto l'orario gia'
// scelto — la lezione prima, il maestro dopo, non le due cose alla pari.
$righePerGiorno = [];
foreach ($giorni as $giornoChiave => $slot) {
    $relativo = Vista::giornoRelativo($slot[0]['locale']);
    // "oggi"/"domani" da soli non dicono la data: qui la aggiungiamo,
    // altrove giornoRelativo() la include gia' (es. "giovedi' 19 marzo").
    $intestazione = in_array($relativo, ['oggi', 'domani'], true)
        ? ucfirst($relativo) . ', ' . Vista::giornoBreve($slot[0]['locale'])
        : ucfirst($relativo);

    $righe = [];
    foreach ($slot as $s) {
        $liberi = (int) $s['posti_liberi'];
        $mia    = (bool) $s['mia'];
        $gruppo = $s['tipo'] === 'gruppo';

        if     ($mia)         { $stato = 'mia';    $etichetta = 'Hai prenotato'; }
        elseif ($liberi <= 0) { $stato = 'pieno';  $etichetta = 'Completo'; }
        elseif ($gruppo)      { $stato = 'libero'; $etichetta = $liberi . ' post' . ($liberi === 1 ? 'o' : 'i') . ' liber' . ($liberi === 1 ? 'o' : 'i'); }
        else                  { $stato = 'libero'; $etichetta = 'Disponibile'; }

        $selezionabile = !$mia && $liberi > 0;
        $tipoTesto     = $gruppo ? 'Gruppo' : 'Individuale';
        $conUnSolo      = count($s['maestri']) === 1 ? ' · con ' . $s['maestri'][0]['nome'] : '';
        $maestriDaScegliere = $selezionabile && count($s['maestri']) > 1 ? $s['maestri'] : [];

        $righe[] = [
            'valore'        => $s['id'],
            'orario'        => Vista::ora($s['locale']),
            'tipo'          => $tipoTesto . $conUnSolo,
            'stato'         => $stato,
            'etichetta'     => $etichetta,
            'pallino'       => $selezionabile && !$gruppo,
            'selezionabile' => $selezionabile,
            'maestri'       => $maestriDaScegliere,
        ];
    }

    $righePerGiorno[$giornoChiave] = ['intestazione' => $intestazione, 'righe' => $righe];
}
?>
<h1>Prenota una lezione</h1>

<p class="saldo-riga">
  Hai <strong><?= (int) $saldi['individuale'] ?></strong> lezioni individuali
  e <strong><?= (int) $saldi['gruppo'] ?></strong> di gruppo.
  <a href="<?= Vista::u('/saldo') ?>">Dettaglio</a>
</p>

<?= Vista::avviso('errore', $_GET['errore'] ?? null) ?>
<?= Vista::avviso('esito',  $_GET['esito']  ?? null) ?>

<?php if ($righePerGiorno === []): ?>
  <p class="vuoto">Non ci sono lezioni disponibili nei prossimi giorni.</p>
<?php else: ?>
  <form method="post" action="<?= Vista::u('/prenota') ?>">
    <?= Vista::campoGettone() ?>

    <label for="giorno-prenota">Giorno</label>
    <select id="giorno-prenota">
      <?php foreach ($righePerGiorno as $chiave => $g): ?>
        <option value="<?= Vista::e($chiave) ?>"><?= Vista::e($g['intestazione']) ?></option>
      <?php endforeach; ?>
    </select>

    <ul class="slot" id="elenco-slot"></ul>

    <button type="submit" class="principale conferma-prenota">Conferma</button>
  </form>

  <script type="application/json" id="dati-prenota"><?= json_encode($righePerGiorno) ?></script>
  <script>
    // Tocca un giorno, poi un orario: niente ricarica di pagina, i dati di
    // tutti i giorni sono gia' qui. Un solo pulsante "Conferma" alla fine,
    // invece di un modulo separato per ogni orario.
    (function () {
      var dati    = JSON.parse(document.getElementById('dati-prenota').textContent);
      var giorno  = document.getElementById('giorno-prenota');
      var elenco  = document.getElementById('elenco-slot');

      function creaRiga(r) {
        var li = document.createElement('li');
        li.className = 'slot-voce ' + r.stato;

        var contenitore = document.createElement(r.selezionabile ? 'label' : 'div');
        contenitore.className = 'slot-contenitore' + (r.selezionabile ? ' slot-scegli' : '');

        var quando = document.createElement('div');
        quando.className = 'quando';
        var orario = document.createElement('span');
        orario.className = 'orario';
        orario.textContent = r.orario;
        var tipo = document.createElement('span');
        tipo.className = 'tipo';
        tipo.textContent = r.tipo;
        quando.append(orario, tipo);

        var segno = document.createElement('span');
        segno.className = 'segno' + (r.pallino ? ' pallino' : '');
        if (r.pallino) {
          var nascosto = document.createElement('span');
          nascosto.className = 'sr-only';
          nascosto.textContent = r.etichetta;
          segno.appendChild(nascosto);
        } else {
          segno.textContent = r.etichetta;
        }

        contenitore.append(quando, segno);

        var radio = null;
        if (r.selezionabile) {
          radio = document.createElement('input');
          radio.type = 'radio';
          radio.name = 'slot';
          radio.value = r.valore;
          radio.required = true;
          contenitore.appendChild(radio);
        }

        li.appendChild(contenitore);

        // Il maestro si sceglie dopo, non alla pari dell'orario: una
        // tendina piu' piccola nella stessa riga, non un'altra riga
        // uguale ripetuta per ogni maestro possibile.
        if (r.maestri && r.maestri.length > 0) {
          var blocco = document.createElement('div');
          blocco.className = 'slot-maestro';

          var etichettaMaestro = document.createElement('label');
          etichettaMaestro.className = 'sommesso piccolo';
          etichettaMaestro.textContent = 'Maestro';
          var selectMaestro = document.createElement('select');
          selectMaestro.name = 'maestro_' + r.valore;
          etichettaMaestro.appendChild(selectMaestro);

          var vuota = document.createElement('option');
          vuota.value = '';
          vuota.disabled = true;
          vuota.selected = true;
          vuota.textContent = 'Scegli il maestro';
          selectMaestro.appendChild(vuota);

          r.maestri.forEach(function (m) {
            var opt = document.createElement('option');
            opt.value = m.id;
            opt.textContent = m.nome;
            selectMaestro.appendChild(opt);
          });

          // Scegliere il maestro qui seleziona anche l'orario: un tocco
          // solo, non due.
          if (radio) {
            selectMaestro.addEventListener('change', function () { radio.checked = true; });
          }

          blocco.appendChild(etichettaMaestro);
          li.appendChild(blocco);
        }

        return li;
      }

      function aggiorna() {
        var righe = (dati[giorno.value] || {}).righe || [];
        elenco.innerHTML = '';
        righe.forEach(function (r) { elenco.appendChild(creaRiga(r)); });
      }

      giorno.addEventListener('change', aggiorna);
      aggiorna();
    })();
  </script>
<?php endif; ?>
<?php
echo Vista::chiusura();
