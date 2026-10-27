# Eseguire il workflow: la mappa del run

Questa pagina vale **dopo la costruzione**, quando il preflight dice `READY_FOR_BASELINE`.
Da qui in poi non scrivi più codice: fai girare il workflow e osservi chi decide che cosa.

## Chi fa che cosa

| Chi | Dove | Che cosa fa |
|---|---|---|
| **Tu** | terminale | avvii il run, importi i risultati, fai la review finale |
| **Operatore** | una **nuova** chat del coding agent | legge le evidenze con i tool e consegna la bozza di classificazione, poi si ferma |
| **Simulatore** (facoltativo) | un'**altra nuova** chat | interpreta il responsabile che risponde alle richieste di ruolo, poi si ferma |
| **Codice** | runtime | calcola gate, proposte e richieste ai ruoli; ricalcola dopo ogni risposta |

Operatore e simulatore stanno in chat separate da quella del tutor: devono lavorare solo con
quello che leggono tramite i tool, senza il contesto della costruzione.

## La regola d'oro

Dopo **ogni** passo, nel terminale:

```powershell
python runner.py --workspace workspace status --run-id RUN_ID
```

`status` mostra la mappa del run, segna il passo in corso con `-->` e stampa il **prossimo
comando già compilato** con run e workspace. Quando il passo spetta a una chat, stampa anche il
testo esatto da incollare. Se non sai cosa fare, esegui `status`.

Indica sempre `--run-id`: se nel workspace ci sono più run, i comandi senza `--run-id`
prendono l'ultimo creato, che potrebbe non essere quello che stai seguendo.

## I passi di un run

| # | Passo | Chi | Comando o file | Prima di andare avanti controlla |
|---|---|---|---|---|
| 1 | Avvio | Tu | `python runner.py --workspace workspace start` | annota il **RUN_ID** stampato; se il run esiste già usa `status`, senza riavviarlo |
| 2 | Prepara l'operatore | Tu | `prepare-agent --run-id RUN_ID` | la readiness passa e viene stampato il testo per la chat |
| 3 | Classificazione | Operatore | nuova chat: incolla il testo stampato | osservi le chiamate ai tool; l'operatore si ferma dopo `submit-draft` o `needs-input` |
| 4 | Importa | Tu | leggi `agent/draft.txt` del run, poi `continue --run-id RUN_ID` | lo stato diventa `WAITING_FOR_APPROVAL` e compaiono le proposte |
| 5 | Risposte ai ruoli | Simulatore oppure tu | nuova chat con il testo stampato da `status`, oppure `respond-approval` | nessuna richiesta pendente; in `approval_reassessment.json` cambia solo il gate `formal_approval`; le proposte possono cambiare di conseguenza |
| 6 | Review finale | Tu | compila `exchange/decisions.txt`, poi `review --run-id RUN_ID --actor "nome"` | lo stato diventa `COMPLETED`; solo le proposte di pubblicazione approvate e senza hard stop producono un'azione **simulata** |
| 7 | Osservazioni | Tu | `agent/EVIDENZE_PARTECIPANTE.md` | hai scritto che cosa hai visto, non che cosa ti aspettavi |

Il passo 5 compare solo se la spec abilita le richieste ai ruoli. Se nessun dataset ne ha
bisogno, è già completo.

La tabella descrive la modalità `agent`. In modalità `manual`, oppure dopo un fallback
esplicito, i passi 2-4 diventano: incolla `exchange/prompt.txt` in chat, salva la risposta
in `exchange/response.txt`, poi esegui `continue --run-id RUN_ID`. La mappa mostra questa
variante. Tutti i sottocomandi abbreviati nella tabella e qui sotto vanno preceduti da
`python runner.py --workspace workspace`; usa il workspace effettivo stampato da `status`.

La classificazione `UNKNOWN` riguarda l'incertezza sulla sensibilità del testo. Licenza,
embargo, qualità e approvazioni hanno gate distinti. Un dataset in `ESCALA` o `TRATTIENI`
può essere un esito corretto: non devi rimuovere blocchi per arrivare a `PUBBLICA`.

## Stati e cosa significano

| Stato del workflow | Significa | Chi deve muoversi |
|---|---|---|
| `WAITING_FOR_AI` | il codice ha preparato le evidenze e aspetta la classificazione | tu (passo 2) o l'operatore (passo 3) |
| `WAITING_FOR_APPROVAL` | la classificazione è importata, le proposte sono pronte | il simulatore o tu (passo 5), poi tu (passo 6) |
| `COMPLETED` | la review è registrata | tu (passo 7) |

La sessione dell'operatore ha uno stato suo, visibile in `status`: `OPEN` (sta lavorando),
`DRAFT_SUBMITTED` (bozza consegnata), `NEEDS_INPUT` o `STOPPED` (si è fermato e aspetta te),
`FALLBACK` (hai dichiarato il percorso manuale).

## Se qualcosa si ferma

- **L'operatore chiede un chiarimento** (`NEEDS_INPUT`): leggi la richiesta e usa
  `resume-agent --run-id RUN_ID --reason "..."`. `status` stampa il comando.
- **Quota o postazione non disponibile**: dichiara il fallback sullo stesso run con
  `fallback-agent --run-id RUN_ID --reason "..."`, poi segui lo scambio manuale
  (`exchange/prompt.txt` → chat → `exchange/response.txt` → `continue`). Annota il motivo:
  un run in fallback non è una prova agentica.
- **Hai sbagliato run**: non cancellare nulla. Usa `status --run-id` sul run giusto.
- **Errore `Operazione non completata [...]`**: il workflow ha rifiutato in modo sicuro. Il
  codice tra parentesi dice perché. Leggi il messaggio e ricontrolla `status` sullo stesso
  run: log e artefatti di recupero possono essere stati scritti. Non correggere i JSON a mano.
- **Errore `agent_snapshot_drift` dopo un aggiornamento dell'infrastruttura**: conserva il
  vecchio run e avviane uno nuovo con il pacchetto aggiornato. Non copiare sessioni, mandati
  o ricevute fra versioni; la readiness del codice non aggiorna lo snapshot dell'operatore.

Le chiamate ai tool, i consumi e gli arresti dell'operatore si leggono negli `events` di
`workspace/runs/RUN_ID/agent/session.json`; `trace.ndjson` registra gli eventi del workflow.
Consulta questi file per osservare, senza modificarli. Le prove deterministiche e il
fallback non dimostrano il funzionamento di un modello reale.

## Dopo il run

1. **Challenge** (passo 11 del README): `challenge_factory.py create-from-spec`, poi un run
   sulla challenge con gli stessi passi di questa pagina, nel workspace della challenge.
2. **Report**: `reports/break_report.md` e `reports/workflow_post_mortem.md`.
3. **Consegna**: `python runner.py preflight` deve dire `READY_TO_SUBMIT`, poi
   `python runner.py submit --out consegna.zip`.

Approfondimenti: `agent/START_OPERATORE.md` (operatore), `agent/RICHIESTE_AI_RUOLI.md` e
`agent/SIMULA_RESPONSABILE.md` (risposte ai ruoli).
