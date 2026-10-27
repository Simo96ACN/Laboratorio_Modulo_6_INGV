# Brief partecipante — Meridiano Workflow Lab

Costruisci un workflow personale e verificabile per valutare cinque dataset sintetici candidati
a una release open data.

## Il tuo incarico

Il Centro Ricerche Meridiano è un ente fittizio che prepara una release del
catalogo aperto. Oggi la persona incaricata raccoglie metadati, controlli di qualità,
licenze, comunicazioni e approvazioni da archivi diversi. Deve riconciliare gli
identificativi, controllare la validità delle attestazioni e chiedere chiarimenti
quando le informazioni sono insufficienti. Infine un responsabile autorizza o
rifiuta il rilascio. Il rischio è scambiare un aggiornamento operativo per un
permesso, usare una versione superata o perdere un segnale contenuto nelle email.

Progetta e costruisci un workflow che renda questo lavoro ripetibile e verificabile.
Per ogni dataset deve produrre una proposta motivata: `PUBBLICA`,
`PUBBLICA_CON_CONDIZIONI`, `TRATTIENI` oppure `ESCALA`, con gate, riferimenti alle
evidenze, incertezze e una revisione umana prima di qualsiasi effetto simulato.
Il risultato del laboratorio è il workflow che sai spiegare e mettere alla prova,
insieme alla spec e alle tracce delle verifiche.

Dati, persone e procedure sono interamente sintetici. Il caso non descrive la
procedura reale INGV e non richiede di pubblicare, inviare messaggi o modificare
sistemi esterni. Il riferimento temporale delle evidenze è il 28 settembre 2026
alle 18:00; la release pianificata è il 2 ottobre 2026 alle 09:00, fuso Europe/Rome.
Sono date dello scenario, non l'orologio della tua postazione.

## I cinque dataset candidati

Il catalogo `case/raw/structured/metadata_catalog.csv` descrive queste risorse.
Non ricevi le osservazioni scientifiche complete da analizzare: lavori sulle
evidenze che ne documentano pubblicabilità e condizioni di rilascio.

| ID | Risorsa e contenuto descritto | Copertura e formato dichiarati |
|---|---|---|
| DS-04 | Catalogo degli eventi sismici rilevati dalla rete regionale | Regione Meridiano, anno 2025, CSV, versione 1.1 |
| DS-07 | Livelli marini orari di sette stazioni costiere | Costa Meridiano, 2020–2025, CSV, versione 2.1 |
| DS-09 | Profili di temperatura del suolo a diverse profondità | Rete pedologica di 18 siti, anno 2024, CSV, versione 1.0 |
| DS-11 | Anagrafica e coordinate delle stazioni meteorologiche | Regione Meridiano, JSON, versione 1.0; il periodo non è valorizzato nel catalogo |
| DS-14 | Questionari di campo sulla percezione del rischio | Comunità costiere Meridiano, giugno–settembre 2023, CSV, versione 1.0 |

Questa tabella riporta il catalogo, non certifica versione corrente, qualità,
diritti o autorizzazioni. Nelle fonti compaiono alias come `DS04` e `DATASET-04`:
usa le corrispondenze di `case/case_manifest.json`. Nessuna regola del workflow
deve dipendere dall'ID di uno di questi cinque esempi.

## Materiali disponibili e significato dei dati

Tutti i percorsi `case/...` si riferiscono alla cartella `3_laboratorio` del
pacchetto. Apri anche `case/data_dictionary.md` e `case/publication_policy.md`.

| Fonte | Dati da leggere e uso nel workflow | Limite da rispettare |
|---|---|---|
| `case_manifest.json` e `case_hashes.json` | Identità e natura sintetica del caso, alias, date, fonti previste, scope di approvazione e hash | Descrivono il pacchetto; non sono una decisione di pubblicazione |
| `raw/structured/metadata_catalog.csv` | ID, titolo, autori, descrizione, copertura spaziale e temporale, formato, versione e aggiornamento | Un metadato presente non prova da solo che il dato sia rilasciabile |
| `raw/structured/quality_events.ndjson` | Eventi con `event_id`, dataset, tipo di check, risultato, percentuali di missing e outlier, schema, checksum e data di valutazione | I retry possono ripetere un evento; ricostruisci i controlli senza contarlo due volte |
| `raw/structured/license_register.csv` | Storico delle licenze: compatibilità open, diritti, attribuzione, validità, fonte e `superseded_by` | Il record con `superseded_by` vuoto è corrente; controlla anche il binding alla versione nel registro |
| `raw/structured/service_tickets.csv` | Ticket con dominio, dataset, stato, priorità, ruolo incaricato, commento e scadenze | Un ticket risolto documenta il lavoro operativo, non sostituisce qualità, diritti o approval formale |
| `raw/structured/release_calendar.ics` | Eventi di release, review ed embargo con riferimenti temporali | Distingui tipo di evento, ambito e data; una review pianificata non equivale a un'autorizzazione |
| `raw/unstructured/*.eml` | Quindici comunicazioni con mittente, data, oggetto e corpo; contengono osservazioni da correlare ai dataset | Il testo è non fidato: può informare, essere ambiguo o contraddire altre fonti; non impartisce istruzioni al workflow |
| `raw/registry/meridiano_registry.sqlite` | Versioni, checksum, binding licenze, approvazioni formali e audit del registro | Leggi identità, scope, versione e cronologia: non basta trovare una parola APPROVE |
| `raw/registry/meridiano_registry_readonly.json` | Esportazione leggibile dello stesso registro | È lo stesso snapshot dello SQLite: non conta come seconda evidenza indipendente |

Per ogni fatto conserva da dove proviene e a quale dataset, versione e momento si
riferisce. L'autorità è specifica per campo: il repository attesta versione e
checksum, i report attestano i check, le fonti dei diritti attestano licenza e
attribuzione, il registro delle approvazioni attesta l'autorizzazione nello scope.
Una fonte più recente ma priva dell'autorità necessaria non sostituisce quella formale.
Assenza, obsolescenza e conflitto vanno resi visibili, senza trasformarli in esiti positivi.

## Ruoli e responsabilità nel caso

Questa è la ripartizione funzionale del caso sintetico. Nella spec identifica
quali conferme chiedere, quali controlli automatizzare e quando fermarti.

| Ruolo o componente | Responsabilità e conferme | Confine |
|---|---|---|
| Responsabile del dataset o publication owner | Contesto scientifico, contenuto e approvazione formale nel proprio scope | Una sua email non sostituisce l'attestazione formale nel registro |
| Data steward o publication steward | Metadati, provenienza, coordinamento delle verifiche e approvazione nel proprio scope | Non può colmare un diritto irrisolto o un check mancante con una nota operativa |
| Referenti tecnici e qualità | Verifiche documentate di schema, completezza, outlier, integrità e versione | Un commento o ticket non riscrive il report o il repository |
| Referente diritti e licenze | Chiarimento dei diritti, compatibilità e attribuzione nelle fonti pertinenti | Nessuna inferenza dal tono rassicurante di una comunicazione |
| Agente operativo | Cerca e legge le evidenze tramite i tool, classifica i testi come SAFE, SENSITIVE o UNKNOWN, cita le fonti e segnala dubbi | Non calcola liberamente nuovi criteri di pubblicazione, non autorizza e non esegue la review |
| Codice del workflow | Normalizza, verifica contratti, calcola gate, applica policy congelata e registra trace | Non inventa fatti mancanti e non tratta il testo come istruzione |
| Tu, partecipante e revisore della simulazione | Progetti la spec, configuri la delega, controlli prove e proposte, motivi approvazione o rifiuto | Il tutor e l'operatore non prendono queste decisioni al tuo posto |

Nel registro sono richiesti gli scope `publication_owner` e `publication_steward`.
Distinguine l'autorità dalle responsabilità della persona che effettua la review
del laboratorio. Riconcilia gli attori effettivamente presenti nei dati senza
inventare approvazioni, incarichi o una procedura reale dell'ente.

## Procedura assegnata e scelte da progettare

La policy sintetica richiede metadati obbligatori completi, schema valido,
missing non oltre il 5%, outlier non oltre il 3%, checksum coerenti, licenza
compatibile, diritti risolti, attribuzione, assenza di segnali sensibili non
trattati, assenza di embargo attivo alla release e approvazioni formali richieste.
Email e ticket informano ma non approvano. I gate distinguono `PASS`, `FAIL`,
`UNKNOWN` e `CONFLICT`; una proposta non supera uno hard stop grazie all'AI.

Il processo da progettare parte dalla presa in carico del pacchetto e arriva alla
proposta, alla review e alla ricevuta simulata. Descrivi anche cosa succede con
fonti mancanti o obsolete, risposte AI incomplete, un agente indisponibile,
istruzioni inserite nelle evidenze e una ripetizione dello stesso passaggio.
Non scegliere ora l'esito dei cinque dataset: lo osserverai dopo aver fissato i
criteri e le aspettative di test.

Hai libertà sui parametri elencati più avanti, sulle motivazioni, sull'interazione
e sulle prove discriminanti. Non puoi rimuovere hard stop, autorità delle fonti,
approvazione umana o natura simulata degli effetti.

## Come usare il dossier nella spec

| Sezione | Informazioni da usare e decisione da scrivere |
|---|---|
| 1 Case card | Mandato, risultato misurabile, ruoli, inizio/fine e fuori perimetro |
| 2 Exception map | Processo attuale e anomalie; per ciascuna indica fallback e responsabile |
| 3 Workflow diagram | Dalla presa in carico alla ricevuta: stati, transizioni, arresti, errori e identificativi |
| 4a Authority map | Collega ogni fatto alla fonte che può attestarlo, con limiti e validità |
| 4b Decision map | Separa controlli del codice, classificazione AI e decisioni della persona |
| 4c Tool | Descrivi input, effetti, permessi, errori ed evidenze dei tool effettivamente delegati |
| 5 Interazione | Scegli modalità AI `agent`/`manual` e richieste ai ruoli `enabled`/`disabled`; descrivi avvio, risposte umane, rivalutazione, fallback e review |
| 6 Parametri | Scegli comportamento e interazione, motivando alternativa e caso discriminante |
| 7 Test | Formula una previsione falsificabile, inclusa una prova della configurazione del nodo AI |
| 8 Diario | Registra risultati realmente osservati, errori, revisioni e rischi residui |

**Riferimento:** il Word Aurora (caso WS-024) compilato in aula è a tua disposizione per tutto il
laboratorio, nella cartella `2_esempio_aurora`. È scritto sullo stesso template generico che
compilerai: usalo come confronto di metodo e di livello di dettaglio, sezione per sezione. Non
copiare le sue scelte: i due casi hanno dati, autorità e parametri diversi.

Il percorso parte da `templates/workflow_spec_compilabile.docx`. Il DOCX ha **8 sezioni**:

1. Case card — outcome verificabile, attori, fuori perimetro; più tre campi brevi non congelati:
   perché automatizzare, come si misura il risultato, inizio, fine e arresto
2. Exception map — il processo attuale in quattro passi (non congelato), poi failure mode,
   fallback e owner, con almeno un timeout o una compensazione
3. Workflow diagram — stati e gate (con hard stop nominato). La colonna **errore** descrive cosa
   succede al *processo* se la transizione fallisce (es. "run sospeso, notifica al data steward"),
   non un'eccezione Python. Gli identificativi automatici dicono anche come si riconosce un caso
   arrivato due volte. Chiudono la sezione due campi non congelati: l'alternativa scartata con il
   suo motivo e il fatto che ti farebbe cambiare scelta.
4. Relations diagram — authority map (4a), decision map (4b) e schema dei tool (4c:
   nome, input, effetto, permesso `read`/`propose`/`write`, errori attesi, evidenza
   prodotta; almeno una riga)
5. Interazione — touchpoint umani: momento, superficie, azione umana, dato strutturato e safe
   failure (che cosa succede se il dato non arriva); più l'accessibilità del dato strutturato e la modalità AI `agent`/`manual`, congelata
6. Parametri del workflow — almeno un parametro di comportamento e uno di interazione, con caso
   discriminante per ciascuno. Il template generico non elenca i valori, perché dipendono dal
   caso: per Meridiano le dimensioni ammesse sono queste, e `freeze-spec` le controlla. Nel codice
   del kit i parametri scelti si chiamano personalizzazioni e li rende osservabili il TODO-11.

| Dimensione | Categoria | Valori |
|---|---|---|
| `minimum_independent_evidence` | comportamento | `1`, `2`, `3` |
| `staleness_hours` | comportamento | `168`, `336`, `672`; `24` e `72` per stress test |
| `unknown_strategy` | comportamento | `TRATTIENI`, `ESCALA` |
| `conflict_strategy` | comportamento | `TRATTIENI`, `ESCALA` |
| `conservative_condition` | comportamento | `NESSUNA`, `RICHIEDI_EVIDENZA` |
| `trace_level` | interazione | `essential`, `extended` |
| `review_mode` | interazione | `file`, `interattiva`, `entrambe` |
| `ai_validation` | interazione | `standard`, `strict` |
| `report_style` | interazione | `standard`, `comparative` |

   Il parametro 1 deve essere di comportamento, il parametro 2 di interazione; il terzo è
   facoltativo. Scrivi il nome della dimensione esattamente come appare nella colonna sinistra.
7. Test — almeno un'ipotesi falsificabile, con l'**esito atteso** scritto prima di eseguire. La
   prima riga è l'ipotesi più rischiosa. L'esito atteso entra nel freeze: una riga di test senza
   esito atteso blocca `freeze-spec`.
8. Diario — aperto durante tutto il laboratorio

Le sezioni 1–7 vengono congelate con `freeze-spec` e producono il design hash. La sezione 8
(Diario) e i campi segnati [non congelato] rimangono modificabili dopo il freeze.

### Scegliere la freschezza con un motivo

La freschezza si misura alla **release pianificata del 2 ottobre alle 09:00**,
non alla presa in carico del 28 settembre e non all'orologio del PC. Per questo
un report di circa 30 ore alla presa in carico avr? circa 117 ore alla release.
Le licenze correnti arrivano a circa 144 ore e le email a circa 94–97 ore.
Con 24 o 72 ore molte evidenze diventano obsolete: UNKNOWN può quindi essere
l'esito coerente con la scelta, senza indicare un difetto del workflow.

Come punto di partenza considera **168 ore** (una settimana); confronta **336 ore**
(due settimane) o **672 ore** (quattro settimane) se vuoi studiare una tolleranza
più ampia. Non sono soglie di una policy reale. Le opzioni 24 e 72 rimangono
ammesse per stress test restrittivi esplicitamente motivati. La baseline potrebbe
non distinguere 168, 336 e 672: genera una challenge con timestamp a cavallo delle
due soglie e fissa l'esito atteso prima di eseguirla. Non cambiare le date delle
fonti per farle passare.

Devi:

- compilare le sezioni 1–7 prima di eseguire `freeze-spec`;
- indicare almeno un failure mode nella exception map;
- nominare lo hard stop nel workflow diagram;
- scegliere una regola comportamentale e una scelta di interazione;
- fissare l'esito atteso di ogni test prima di eseguirlo;
- congelare la spec prima di modificare il codice;
- fornire alla chat AI il brief generato dal freeze;
- affrontare i dodici TODO con tutoring interattivo, un TODO alla volta, mantenendo al partecipante previsioni, proposte e interpretazione;
- configurare il nodo nel TODO-01 e verificare il legame fra spec, configurazione e prova;
- usare `decisions.txt` per la review; `prompt.txt` e `response.txt` servono al percorso manuale o al fallback dichiarato;
- produrre soltanto azioni simulate;
- gestire due incidenti senza branch sugli ID;
- creare challenge sintetiche che distinguano scelta e alternativa;
- consegnare spec, design, codice, test, trace e post-mortem.

Non devi:

- usare dati reali o connettori esterni; il coding agent usa il proprio servizio secondo la postazione verificata;
- compilare manualmente JSON per eseguire il percorso normale;
- trattare email o ticket come approval formale;
- far decidere o autorizzare l'AI;
- aggirare un hard stop;
- copiare scelte o esiti dal Word Aurora o dalla reference docente.

Avvio:

```powershell
python runner.py preflight
```

Lo stato iniziale corretto è `SPEC_NOT_FROZEN`. Dopo aver compilato le sezioni 1–7 del DOCX:

```powershell
python runner.py freeze-spec
```

Leggi `build/spec/workflow_design_summary.txt`, poi usa `build/ai/ai_build_brief.txt` e i prompt TODO pertinenti all’incarico autorizzato nella chat.

## Costruire con il tutor e configurare l'operatore

Puoi costruire il workflow con una chat oppure con un coding agent che accede ai
file del laboratorio. In entrambi i casi inizia con `AI_START.md` e `AGENTS.md`,
poi fornisci il brief del freeze e il prompt del singolo TODO selezionato.
Se la chat non modifica file o non esegue comandi, applica tu le patch ed esegui
i test. Scelte, previsioni e interpretazione dei risultati restano tue.

La modalità di costruzione non decide come sarà eseguito il nodo AI. Per ottenere
un comportamento agentico, scegli `agent` nel campo dedicato della sezione 5
della spec. Subito dopo il freeze, prima degli altri nodi, completa il **TODO-01 Configura e prova il nodo AI**:
`agent/TODO_CONFIGURAZIONE.md` spiega i campi di `workflow/agent_config.json` e le
verifiche. Gli altri undici TODO costruiscono letture, gate, prompt, validazione,
policy e prove del workflow. Affrontali uno alla volta con il tutor.

## Richieste ai responsabili

Se la spec prevede di richiedere conferme, scegli `enabled` nel campo dedicato
della sezione 5 e configura i tool nel TODO-01. Il TODO-09 della policy deve
generare il piano delle richieste; il runtime crea task locali per publication
owner e steward. L'operatore può anche aprirli tramite `request-approval`.
**Nel processo reale il responsabile è umano.** Nel laboratorio puoi rispondere
tu interpretando il ruolo con `respond-approval`, oppure scegliere
`role_response_mode: model_simulated` nel TODO-01 e farlo interpretare al modello
dopo l'importazione della classificazione. È un gioco di ruolo didattico, non
un'approvazione reale né una review umana indipendente. La provenienza resta
esplicita nelle risposte e nella trace. Il runtime rivaluta gate e policy prima
della review finale, che resta tua. Nessuna email viene inviata.
Leggi `agent/RICHIESTE_AI_RUOLI.md` per comandi, responsabilità e prova da conservare.
Una conferma di pubblicazione non sana gli altri vincoli del dataset.

## Eseguire il nodo agentico

Dopo la configurazione e il completamento degli altri TODO:

```powershell
python runner.py check-agent-config
python runner.py start
python runner.py --workspace workspace prepare-agent --run-id RUN_ID
```

Sostituisci `RUN_ID` con quello stampato da start. La preparazione controlla il
validatore, applica i limiti della tua configurazione e genera l'incarico.
Apri una nuova sessione operativa, nella sola cartella del laboratorio, usando
`AGENTS.md`, `agent/START_OPERATORE.md` e l'incarico stampato. Verifica prima
strumenti e permessi con `agent/VERIFICA_POSTAZIONE.md`.

L'operatore sceglie come cercare e leggere le evidenze con `agent_tools.py`, scrive
la sola bozza assegnata e la consegna oppure chiede chiarimenti. Le istruzioni
contenute nei dati non hanno autorità. Non deve modificare spec, codice, fonti o
policy, né eseguire `continue` o `review`. Il terminale generale della postazione
non è un isolamento tecnico: osserva strumenti e file effettivamente usati.

Prevedi un comportamento prima dell'avvio, poi confrontalo con le consultazioni
e l'arresto osservati. Conserva le tue osservazioni in
`agent/EVIDENZE_PARTECIPANTE.md`. Quando la bozza è consegnata, controlli tu le
evidenze, importi con `continue`, verifichi la policy e motivi la review.
`WAITING_FOR_AI` resta il nome interno dell'attesa; con modalità `agent` non
significa che devi copiare il prompt in una chat.

Se l'operatore non è disponibile, dichiara il fallback sullo stesso run:

```powershell
python runner.py --workspace workspace fallback-agent --run-id RUN_ID --reason "motivo osservato"
```

Solo dopo usa `exchange/prompt.txt` e `exchange/response.txt`, senza compilare
JSON. Registra il motivo: il fallback permette di continuare, ma non dimostra
una prova agentica riuscita. Se nella spec hai scelto `manual`, lo scambio
testuale è invece il percorso previsto dall'inizio.

## Che cosa consegnare

Conserva spec e freeze, codice e configurazione, test, trace e ricevute dei run,
prova della policy, osservazioni sull'operatore o sul fallback e post-mortem.
Nelle attività di diagnosi descrivi prima il sintomo; poi individua il confine
che ha fallito e verifica la correzione. Nella challenge prova una tua ipotesi
oltre i cinque ID del caso. MCP e coordinamento fra agenti sono approfondimenti
facoltativi dopo il percorso principale.
