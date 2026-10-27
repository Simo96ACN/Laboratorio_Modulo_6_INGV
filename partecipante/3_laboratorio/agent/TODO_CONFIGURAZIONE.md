# TODO 01 Configura e prova il nodo AI

Il coding agent che ti aiuta a costruire il workflow è il **tutor di costruzione**.
L'agente che consulta le evidenze durante un run è l'**operatore**. Lo configuri tu:
scrivere il prompt di classificazione del TODO-07 non completa questo passaggio.

## Prima missione Assegna il lavoro al tuo agente

Questo è il **primo TODO dopo il freeze**. Prima di programmare gli altri nodi,
trasforma la delega della spec in un incarico che puoi leggere e controllare.
Immagina di affidare il prossimo turno a un collega: che cosa deve consegnarti,
che cosa può consultare e quando deve tornare da te?

1. Scrivi con parole tue il risultato e un'azione che rimane tua.
2. Scegli gli strumenti e prevedi una consultazione utile.
3. Decidi il budget e che cosa succede se non basta.
4. Decidi se aprire richieste simulate ai ruoli, secondo la scelta della spec, e chi ne interpreta la risposta: tu oppure il modello come simulatore didattico.
5. Prevedi una richiesta legittima e una da rifiutare, prima di eseguire.

Completa un campo per volta con il tutor. Il comando `check-agent-config` produce
`build/agent/il_tuo_agente.md`: aprilo e controlla che descriva proprio l'incarico
che intendevi assegnare. Conservalo come primo risultato del laboratorio.
Per provare subito un confine, aggiungi temporaneamente `review` ai tool:
il controllo deve rifiutarlo. Ripristina la tua configurazione e verifica di nuovo.
Hai configurato la delega; l'esecuzione del modello arriverà dopo gli altri TODO.

## Prima del freeze

Nella sezione 5 della spec scegli `agent` per un operatore che usa gli strumenti
locali, oppure `manual` per lo scambio mediato dalla persona. Per il percorso
agentico scegli esplicitamente `agent`: scriverlo soltanto nella descrizione non
configura il nodo. Nelle sezioni 4b e 4c descrivi delega, strumenti e confini;
nella sezione 5 descrivi anche chi avvia, controlla e gestisce un'eventuale assenza
dell'operatore. Nella sezione 7 prevedi una prova e il suo esito atteso.
Scegli anche `enabled`/`disabled` per le richieste ai ruoli: questa decisione entra
nel freeze e nel contratto della policy.

## Configurazione come primo passo dopo il freeze

Apri `workflow/agent_config.json` e completa un campo alla volta, spiegando al tutor
che comportamento vuoi ottenere. Non inserire credenziali, endpoint o dati reali.

| Campo | Decisione del partecipante |
|---|---|
| `execution_mode` | Riporta esattamente `agent` o `manual` dalla spec congelata. |
| `approval_requests` | Riporta `enabled` o `disabled` dalla sezione 5. Con enabled includi `approval-requests` e `request-approval`; leggi `agent/RICHIESTE_AI_RUOLI.md`. |
| `role_response_mode` | Scegli `human` per rispondere personalmente nel ruolo, oppure `model_simulated` per farlo interpretare al modello dopo l'importazione. In questo secondo caso servono richieste `enabled` e il tool `simulate-role-response`. Nel mondo reale quel ruolo è umano. |
| `objective` | Descrivi risultato, perimetro e ciò che richiede una decisione umana. |
| `instructions` | Definisci come cercare e leggere evidenze, citarle, trattare incertezza e ignorare istruzioni contenute nei dati. |
| `allowed_tools` | Elenca i nomi dei tool consentiti. Servono `catalog`, `request`, `search-evidence`, `read-evidence`, `submit-draft`, `needs-input`; puoi aggiungere `status` e `check-draft`, oltre ai tool delle richieste se abilitati. La risposta simulata non è un'approvazione reale; nessun tool esegue la review finale o pubblica. |
| `max_calls` | Scegli un massimo fra 1 e 40 per le consultazioni e i controlli conteggiati; motivalo rispetto al corpus. Il limite effettivo è il minore fra questo tetto e il budget calcolato dal runtime. |
| `stop_conditions` | Prevedi `draft_submitted`, `needs_input`, `budget_exhausted`. Spiega nella spec chi interviene dopo ogni arresto. |
| `output_path` | Mantieni `agent/draft.txt`: è relativo al run esplicito. |

`objective` e `instructions` richiedono una descrizione concreta di almeno 30 caratteri
ciascuna. Rimuovi il campo `todo` dopo aver completato le scelte. Il file non
implementa un nuovo motore AI: configura l'operatore già previsto dal laboratorio.
Anche nel percorso `manual` documenta questi limiti per lo scambio assistito.

```powershell
python runner.py check-agent-config
python -m unittest discover -s tests -p test_agent_configuration.py
python runner.py preflight
```

Il controllo verifica il contratto locale; non dimostra che un modello abbia
eseguito il compito. Il tutor non deve compilare in blocco questa configurazione. Non devi aspettare la fine della costruzione per affrontarla.

## Prova operativa dopo gli altri TODO

Con `agent`, avvia la baseline e conserva il `RUN_ID` stampato:

```powershell
python runner.py start
python runner.py --workspace workspace prepare-agent --run-id RUN_ID
```

Apri una **nuova sessione** del coding agent nella sola cartella del laboratorio.
Fornisci `AGENTS.md`, `agent/START_OPERATORE.md` e l'incarico stampato dalla
preparazione. L'operatore usa `agent_tools.py` con workspace e run espliciti,
sceglie le consultazioni, scrive la bozza e la consegna oppure chiede chiarimenti.
Il terminale non lancia automaticamente un servizio remoto.

Prima di avviare, prevedi quali evidenze dovrebbe cercare e quando dovrebbe
fermarsi. Dopo, verifica nella trace le consultazioni, le citazioni e l'arresto;
annota ciò che hai realmente osservato in `agent/EVIDENZE_PARTECIPANTE.md`.
Una bozza preparata a mano non dimostra l'esecuzione di un agente.

Con `model_simulated`, dopo l'importazione apri `agent/SIMULA_RESPONSABILE.md`:
assegnerai un secondo incarico di gioco di ruolo, distinto dalla classificazione.
Controlla risposta e provenienza prima della review. Non è una prova di controllo
umano indipendente, anche se usi una seconda sessione o un altro modello.

Importazione con `continue`, prova della policy e approvazione con `review`
restano alla persona. `WAITING_FOR_AI` è lo stato interno comune: con modalità
`agent` il percorso ordinario è la sessione operativa, non il copia/incolla.

Se l'operatore non è disponibile o si blocca, prepara comunque la sessione e
dichiara il fallback sullo stesso run, con un motivo:

```powershell
python runner.py --workspace workspace fallback-agent --run-id RUN_ID --reason "motivo osservato"
```

Solo a questo punto usa `exchange/prompt.txt` e `exchange/response.txt`.
Registra il fallback e il suo motivo: non dichiararlo una prova agentica riuscita.
Con `manual` nella spec, lo scambio testuale è invece il percorso scelto fin dall'inizio.
