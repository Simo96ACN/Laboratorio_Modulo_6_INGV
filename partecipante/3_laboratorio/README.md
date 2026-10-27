# Meridiano Workflow Lab

Runtime locale con dati interamente sintetici. Non richiede integrazioni API, app custom o
modifica manuale dei JSON interni. Il coding agent usa il servizio e il piano della propria
postazione: disponibilità, quote e permessi vanno provati prima dell'aula.

**Requisito:** Python 3.10 o superiore (`python --version` per verificare).

**Setup (Windows):** estrai il laboratorio in una cartella con percorso **corto**, ad es.
`C:\meridiano_lab`. Evita cartelle molto profonde o sincronizzate (percorsi lunghi tipo
`OneDrive - .../.../.../...`): Windows limita i percorsi a 260 caratteri e i file di lavoro dei run
potrebbero non venire creati. Il `preflight` avvisa se il percorso scelto è troppo profondo.

**Metodo:** il workbook con le 8 aree e le 27 domande di progettazione visto in aula è in
`workbook_metodo_progettazione.md`. È la checklist trasferibile ad altri casi; tienila come riferimento.

## Percorso completo

1. Controlla il pacchetto:

   ```powershell
   python runner.py preflight
   ```

   All'inizio lo stato atteso è `SPEC_NOT_FROZEN`.

2. Apri `templates/workflow_spec_compilabile.docx`: è il template generico che hai visto compilare
   in aula sul caso Aurora, con le stesse sezioni nello stesso ordine.

   Completa le sezioni da 1 a 6 e pianifica almeno una prova nella sezione 7, con l'**esito
   atteso** scritto prima di eseguire: fa parte del freeze e non si corregge dopo aver visto il
   risultato. Nella sezione 6, Parametri del workflow, usa le dimensioni e i valori elencati in
   `materiali/mandato_partecipante.md`. I campi segnati [non congelato] (perché automatizzare,
   misura, confini, processo attuale, alternativa scartata) servono a progettare e restano
   modificabili. Le scelte della spec guideranno la chat AI, il codice, il runtime e l'evaluator.

3. Congela la spec:

   ```powershell
   python runner.py freeze-spec
   ```

   Il comando legge i campi Word e genera:

   - `build/spec/workflow_design_summary.txt`, da controllare;
   - `build/ai/ai_build_brief.txt`, da fornire alla chat AI;
   - un prompt per ciascun TODO in `build/ai/todo_prompt_pack/`.

   I JSON in `build/spec/` sono contratti interni generati. Non modificarli a mano.

4. Parti dal **TODO-01 Il tuo incarico per l’agente**, prima degli altri nodi:
   `agent/TODO_CONFIGURAZIONE.md`. Dopo la compilazione, `python runner.py check-agent-config`
   genera `build/agent/il_tuo_agente.md`, da leggere e verificare.

   Avvia una nuova chat AI. Come primo messaggio incolla `AI_START.md` e `AGENTS.md`, poi fornisci
   `ai_build_brief.txt` e soltanto il prompt `TODO-xx.txt` del passaggio che vuoi affrontare.

   L'AI ti guida un TODO alla volta: prima chiarisci la tua previsione e proponi una strategia, poi valuta
   l'eventuale patch, esegui un test mirato e spiegane l'esito. Non chiederle di generare tutti i dodici TODO
   o la soluzione completa in blocco. Puoi continuare al TODO successivo dopo aver discusso il passaggio corrente.

5. Dopo ogni blocco prodotto controlla i progressi con il preflight e i test:

   ```powershell
   python runner.py preflight
   python -m unittest discover -s tests -v
   python -m unittest discover -s tests_custom -v
   ```

   Il preflight mostra il progresso: il conteggio dei TODO cala e lo stato resta
   `BUILD_IN_PROGRESS` finché la build è incompleta.

   La suite globale (`-s tests`) resta **rossa** finché non hai completato tutti i dodici TODO:
   `test_no_todos_remain` fallisce e gli altri si saltano. È il comportamento atteso, non un errore
   della tua patch.

   Per verificare il TODO appena chiuso usa i tuoi test mirati in `tests_custom/` (`-s tests_custom`).

   Prima della baseline lo stato deve diventare `READY_FOR_BASELINE`; allora anche la suite globale
   diventa verde.

   **Da qui inizia l'esecuzione.** Tieni aperta `ESECUZIONE.md`: riassume in una pagina chi
   agisce, dove e con quale comando. Dopo ogni passo esegui
   `python runner.py --workspace workspace status --run-id RUN_ID`: la mappa del run indica il
   passo corrente e stampa il prossimo comando già compilato. I passi 6-9 qui sotto sono il
   dettaglio di riferimento.

6. Dopo TODO-01 e costruzione degli altri nodi, avvia la baseline.
   Il runner crea la cartella `workspace/` se non esiste:

   ```powershell
   python runner.py start
   ```

7. Con la modalità `agent` congelata nella sezione 5, esegui con il run esplicito:

   ```powershell
   python runner.py --workspace workspace prepare-agent --run-id RUN_ID
   ```

   La readiness controlla il TODO-08 con casi pubblici positivi e negativi e registra
   gli hash di codice e design. Se fallisce, torna al tutor sul solo passaggio da correggere.
   Apri una nuova sessione con l'incarico stampato; `agent/START_OPERATORE.md` descrive
   consultazioni, bozza e arresto. Compila personalmente `agent/EVIDENZE_PARTECIPANTE.md`.
   Dopo la consegna controlla la risposta e prosegui tu con `continue --run-id RUN_ID`.

   In caso di quota o limite postazione dichiara il fallback senza cancellare il run:

   ```powershell
   python runner.py --workspace workspace fallback-agent --run-id RUN_ID --reason "Limite postazione"
   ```

   `stop-agent`, `resume-agent` e `reopen-agent` richiedono anch'essi run e motivo
   espliciti e sono comandi della persona. Resume chiarisce istruzioni senza aggiungere
   dati né azzerare budget; nuove evidenze, design o prompt sostanziali richiedono un
   nuovo run. Reopen conserva la consegna precedente e apre una revisione con nuove letture.
   Dopo continue nessuna revisione è ammessa. Per ogni configurazione usa la scheda
   `agent/VERIFICA_POSTAZIONE.md`; i test deterministici non provano un modello reale.

   Nel percorso `manual` scelto nella spec, oppure dopo fallback esplicito,
   il runner stampa il path completo del prompt. La struttura è:

   ```
   workspace/runs/<RUN_ID>/exchange/prompt.txt   ← incolla nella chat
   workspace/runs/<RUN_ID>/exchange/response.txt ← salva qui la risposta
   ```

   `<RUN_ID>` è un identificativo generato automaticamente; trovi la cartella navigando
   `workspace/runs/`.

8. Continua il run:

   ```powershell
   python runner.py --workspace workspace continue --run-id RUN_ID
   ```

   Il codice converte la risposta testuale nel contratto JSON interno.

9. Se hai abilitato le richieste di ruolo, consulta `approval-requests`, raccogli
   le risposte umane con `respond-approval` oppure, con `model_simulated` nel
   TODO-01, assegna al modello `agent/SIMULA_RESPONSABILE.md` dopo l'importazione.
   Nel processo reale il responsabile è umano: il gioco di ruolo del modello
   non è un'approvazione reale. Confronta i gate rivalutati e la provenienza.
   Segui `agent/RICHIESTE_AI_RUOLI.md`. Poi compila `exchange/decisions.txt` e registra la review:

   ```powershell
   python runner.py --workspace workspace review --run-id RUN_ID --actor partecipante
   ```

   Il file `decisions.txt` viene generato automaticamente con i blocchi da compilare. Il formato
   richiesto è uno per dataset (le righe che iniziano con `#` sono commenti ignorati dal runner):

   ```
   # Proposta <dataset_id>: <proposta AI>
   # Hard stop: <sì|no>
   DATASET: <dataset_id>
   DECISIONE: <APPROVA_PROPOSTA|RIFIUTA_PROPOSTA>
   MOTIVAZIONE:
   <spiega quali gate ed evidenze hai verificato prima di approvare o rifiutare>
   ```

   Il codice converte anche queste decisioni testuali nel contratto interno. La review resta
   sempre umana.

10. Quando il docente consegna un pacchetto reveal, crea la cartella `reveals/` nella radice
    del laboratorio (se non esiste), posiziona il pacchetto dentro e avvia un nuovo run con
    l'overlay. `--roundtrip-index 2` indica che è il secondo roundtrip AI della sessione
    (il primo era la baseline):

    ```powershell
    # Crea la cartella la prima volta
    mkdir reveals
    # Decomprimi il pacchetto del docente in reveals/reveal_1/
    python runner.py start `
      --overlay reveals/reveal_1/incident_overlay.json --roundtrip-index 2
    ```

11. Crea la prova collegata alla tua spec ed eseguila. Per esportarla e scambiarla con un
    collega, sostituisci `<nome>` con un identificativo tuo (es. `mario`):

    ```powershell
    python challenge_factory.py create-from-spec
    python challenge_factory.py run `
      --challenge workspace/challenges/break_my_spec `
      --workspace workspace/challenge_runs/break_my_spec
    python challenge_factory.py export `
      --challenge workspace/challenges/break_my_spec `
      --out <nome>.zip
    ```

    `run` esegue la challenge **fino al confine AI** e si ferma: il report corretto contiene
    `EXECUTED_TO_AI_BOUNDARY` e `workflow_status: WAITING_FOR_AI`. Non è ancora una prova. Completa il
    roundtrip nello stesso store, senza spostare file. Esegui prima `status` sul run
    della challenge: in modalità `agent` prepara l'operatore, oppure dichiara il
    fallback esplicito; in modalità `manual` usa prompt e risposta testuali:

    ```powershell
    python runner.py --workspace workspace/challenge_runs/break_my_spec status --run-id RUN_ID
    python runner.py --workspace workspace/challenge_runs/break_my_spec continue --run-id RUN_ID
    python runner.py --workspace workspace/challenge_runs/break_my_spec review --run-id RUN_ID --actor partecipante
    ```

    Usa sempre il run_id stampato per la challenge. Verifica se il risultato **distingue davvero** la tua scelta
    dall'alternativa: se non la distingue, la challenge non è superata e conviene proporre un input
    migliore. Registra ipotesi, osservazione ed esito in `reports/break_report.md`.

    Prova anche un workflow di un collega oppure usa la challenge fallback del docente.

12. Compila:

    - `reports/break_report.md`;
    - `reports/workflow_post_mortem.md`;
    - risultati, rischi residui e note nella sezione 8 (diario) del DOCX.

    La sezione 8 è il diario del laboratorio e si può aggiornare in qualsiasi momento senza toccare la
    spec congelata, come i campi segnati [non congelato] delle sezioni 1-3. Il resto delle sezioni
    da 1 a 7 è il progetto congelato: non modificarlo dopo il freeze, altrimenti il preflight segnala
    `SPEC_DRIFT`. Se devi cambiare un'ipotesi di test o il suo esito atteso (sezione 7), esegui di
    nuovo `python runner.py freeze-spec` e scrivi nel diario perché.

    Consegnare i file o completare i comandi non dimostra la comprensione: conta il razionale che
    registri. Un test fallito ma **diagnosticato correttamente** (causa, invariante, correzione) è un
    esito valido, diverso da un workflow completato senza spiegazione.

13. Controlla lo stato finale e crea la consegna:

    ```powershell
    python runner.py preflight
    python runner.py submit --out consegna.zip
    ```

    Il submit collega spec, design, codice, test, challenge, report e run tramite hash.

## Confini

- `meridiano_lab/` è infrastruttura fornita;
- `workflow/` contiene i dodici TODO;
- l'AI classifica testo non fidato, ma non decide e non approva;
- nessuna scelta può rimuovere un hard stop;
- tutte le ricevute restano `SIMULATED_FILE_ONLY` e `NOT_SENT`;
- non inserire dati reali, riservati o conversazioni complete della chat;
- non modificare direttamente file JSON per completare un intervento umano.

## Comandi avanzati

`--json`, `advanced-import-json` e `advanced-approve-json` servono soltanto per test, reference e
debug. Non fanno parte del percorso didattico.

## Coordinamento e MCP

Sono approfondimenti facoltativi fuori dalla scansione obbligatoria LCK3/LCK4.
`coordination/README.md` descrive il trasporto umano fra ruoli; `mcp_lab/README.md`
una chiamata MCP locale su stdio con client e server deterministici. I file di
evidenza si salvano in `reports/`, correlati al run. Una registrazione consente
interpretazione; la capacità di eseguire personalmente richiede una nuova prova.
Questi approfondimenti non richiedono coding agent né API key e non sostituiscono
la scelta dinamica osservata nella sessione operativa.
