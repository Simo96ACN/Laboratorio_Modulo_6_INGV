# Avvio dell'operatore

Il partecipante apre una **nuova sessione** del coding agent nella sola cartella del
laboratorio estratto, separata dal repository docente. Prima completa progettazione,
freeze e dodici TODO; avvia la baseline e conserva il suo RUN_ID.

La persona esegue dalla radice del laboratorio:

```powershell
python runner.py --workspace workspace prepare-agent --run-id RUN_ID
```

Il comando esegue prove pubbliche del validatore e genera un unico incarico da
incollare nella nuova sessione. L'operatore legge `AGENTS.md`,
`agent/MANDATO_OPERATORE.md` e il mandato del run indicato nel messaggio.
Non usare `AI_START.md` come incarico operativo: avvia il tutor.

Comando innocuo per controllare la postazione, prima della lezione:

```powershell
python agent_tools.py --help
```

Per il catalogo della sessione preparata:

```powershell
python agent_tools.py --workspace workspace --run-id RUN_ID catalog
```

L'operatore sceglie consultazioni e seguito dei risultati, senza una sequenza
prescritta di tool. Dopo consegna o richiesta di integrazione si ferma. La persona
controlla la risposta, autorizza `continue` e svolge la review.

Interrompere senza cancellare il lavoro (comando della persona):

```powershell
python runner.py --workspace workspace fallback-agent --run-id RUN_ID --reason "Quota esaurita"
```

Il percorso manuale usa `exchange/prompt.txt` e `exchange/response.txt` dello stesso
run e dello stesso snapshot. Una risposta diversa diventa una revisione manuale,
senza ereditare la provenienza agentica. Non modificare i JSON interni.

Dopo `resume-agent` il comando stampa il percorso del mandato revisionato. Forniscilo
esplicitamente alla nuova sessione; `prepare-agent` sullo stesso run ristampa anche
l'incarico aggiornato. Chiarimenti e budget precedenti restano registrati.

Se la sezione 5 abilita le richieste simulate, puoi consultare approval-requests e
creare task con request-approval entro il catalogo e il budget. Non rispondere
nei ruoli destinatari durante la classificazione. La persona usa respond-approval;
il successivo incarico SIMULA_RESPONSABILE.md può usare simulate-role-response
solo se configurato e dopo l'importazione. Nel processo reale il ruolo è umano;
la simulazione del modello non è un'approvazione reale. Non modificare i
file del registro, dei task o delle risposte; usa il tool per creare la richiesta.
Una richiesta non cambia un gate. Per attendere la persona usa needs-input e
fermati. Le risposte simulate vengono rivalutate prima della review finale.

Dopo l’importazione, con `model_simulated` nel TODO-01, puoi assegnare il gioco di ruolo separato `agent/SIMULA_RESPONSABILE.md`. Nel processo reale decide un responsabile umano; una risposta simulata dal modello non è un’approvazione reale. La review finale resta alla persona.
