# Richieste simulate ai ruoli e nuova valutazione

Una proposta `TRATTIENI` o `ESCALA` non è ancora una richiesta al responsabile.
Con le richieste abilitate nella sezione 5, il laboratorio distingue quattro fatti:
la proposta del workflow, il task diretto al ruolo competente, la sua risposta
simulata e la review finale della nuova proposta. **Nel processo reale il
responsabile è una persona.** Nel laboratorio puoi interpretarlo tu o farlo
interpretare al modello: la seconda scelta è un gioco di ruolo didattico,
non un'approvazione reale né una verifica umana indipendente.

## Che cosa configuri e costruisci

Nella sezione 5 scegli `enabled` per le richieste ai ruoli e descrivi il passaggio
umano. Nel TODO-01 riporta `enabled` in `approval_requests` e includi nei tool
`approval-requests` e `request-approval`. Gli scope disponibili sono
`publication_owner` e `publication_steward`, con destinatari rispettivamente
`Publication Owner` e `Publication Steward`.

Nel TODO-01 scegli anche `role_response_mode`: `human` per rispondere tu oppure
`model_simulated` per la variante con modello. Quest'ultima richiede il tool
`simulate-role-response` e parte soltanto dopo l'importazione della classificazione.
La modalità `human` rimane disponibile anche nella variante con modello.

Nel TODO-09 la tua policy deve restituire, per ogni dataset, anche
`approval_requests`: una lista di oggetti con `scope` e `reason`, oppure `[]`.
Usa i fatti e gli scope presenti nel registro; non codificare gli ID dei cinque
dataset. La policy decide quando serve la conferma e il runtime crea il task.
La risposta richiama i gate e la stessa policy: non imposta direttamente PUBBLICA.

## Che cosa può fare l'operatore

Nel run esplicito l'operatore può consultare richieste, ruoli e gate di approvazione:

```powershell
python agent_tools.py --workspace workspace --run-id RUN_ID approval-requests
```

Può creare un task motivato, riferito a dataset, versione e scope:

```powershell
python agent_tools.py --workspace workspace --run-id RUN_ID request-approval --dataset DATASET_ID --scope publication_steward --reason "fatto da confermare e motivo della richiesta"
```

Il comando crea soltanto un record locale, marcato simulato. Non invia email,
non firma approvazioni e non modifica i gate. Ripetere la stessa richiesta non
crea un secondo task. Se deve attendere la persona, l'operatore usa `needs-input`
e si ferma; la persona potrà riprendere esplicitamente la sessione.
Dopo l'importazione, il runtime crea anche le richieste previste dalla policy.

## Come risponde la persona nel ruolo simulato

Controlla il task con `python runner.py approval-requests --run-id RUN_ID`.
Leggi dataset, versione, ruolo e motivo. Interpreta il ruolo destinatario e
decidi se confermare o rifiutare, con una motivazione basata sulle evidenze:

```powershell
python runner.py --workspace workspace respond-approval --run-id RUN_ID --task-id TASK_ID --actor "il tuo nome" --role "Publication Steward" --decision APPROVE --reason "motivazione della risposta dopo la verifica"
```

Usa `REJECT` per un rifiuto. `respond-approval` è un comando della persona e non
appartiene al catalogo dei tool operativi. Il ruolo deve coincidere con il destinatario del task. Il laboratorio
registra una simulazione dichiarata, non autentica l'identità di una persona reale.

Se la risposta arriva durante l'attesa AI viene conservata e applicata dopo
l'importazione della classificazione. Se arriva dopo l'importazione, la nuova
valutazione è immediata. Confronta i gate prima e dopo in `approval_reassessment.json`.
Fonti, richiesta AI e snapshot originali restano conservati.

Una conferma di pubblicazione può cambiare il gate `formal_approval`; non risolve
licenze incompatibili, qualità insufficiente, embargo o sensibilità. Un rifiuto
rimane bloccante. Una risposta non è la review finale e non produce effetti di
pubblicazione. Una risposta diversa sullo stesso task viene rifiutata; per un
nuovo contesto serve un nuovo run.

## Variante: il modello interpreta il responsabile

Dopo aver controllato e importato la classificazione con `continue`, assegna al
modello l'incarico in `agent/SIMULA_RESPONSABILE.md`. Il simulatore legge i task e
le evidenze del run, motiva `APPROVE` oppure `REJECT` e registra la risposta con:

```powershell
python agent_tools.py --workspace workspace --run-id RUN_ID simulate-role-response --task-id TASK_ID --role "Publication Steward" --decision REJECT --reason "motivazione basata sulle evidenze disponibili" --model-label "nome del modello e sessione"
```

Il comando è disponibile solo se lo hai autorizzato nel TODO-01. Il runtime
registra `source: model_simulated`, modello dichiarato, ruolo reale umano e
`is_real_approval: false`. Le risposte consumano il budget dell'agente. Puoi usare
lo stesso modello o una sessione diversa: non chiamare questo passaggio una
separazione indipendente dei controlli. Il simulatore non deve confermare tutto
per far avanzare il flusso e non esegue `continue` o `review`.

Se il modello risponde in una chat senza accesso ai tool, puoi registrare tu la
risposta con `respond-approval`, aggiungendo `--source model_simulated` e
`--model-label "nome del modello e sessione"`. Non attribuirla a una persona.
Controlla la risposta e spiega quale decisione spetterebbe al responsabile umano
nel processo reale. Il simulatore usa soltanto dati sintetici locali.

Rispondi ai task pendenti, confronta le nuove proposte e poi compila nuovamente
`decisions.txt` per la review. Non serve cambiare la spec per far diventare
positivo un gate rimasto negativo.

## Prova da conservare

Prima prevedi quale gate potrebbe cambiare. Conserva ID del task, scope, risposta
e sua provenienza (`human` o `model_simulated`), gate prima/dopo e proposta risultante. Spiega anche un gate che la risposta
non poteva cambiare. Se l'esito resta TRATTIENI o ESCALA, verifica gli altri vincoli:
non è necessariamente un errore della richiesta.
