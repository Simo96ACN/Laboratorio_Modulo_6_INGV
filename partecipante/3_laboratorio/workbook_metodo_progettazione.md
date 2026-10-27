# Workbook del metodo: checklist di progettazione (8 aree, 27 domande)

Questo è il workbook del metodo di progettazione dell'automazione presentato nel modulo: otto aree che
coprono l'intero ciclo di progettazione, con ventisette domande in tutto. Le aree non hanno lo stesso
numero di domande: dove due domande chiedevano la stessa cosa sono state unite, e i criteri di verifica
della domanda assorbita sono passati a quella che resta.
Usalo come checklist trasferibile a casi diversi: non va compilato in ordine meccanico, serve a verificare
che una scelta non abbia lasciato un buco nel contratto complessivo.

Per ogni domanda rispondi con quattro elementi: **risposta_o_decisione**, **evidenza**, **owner**, **esito**.
Ogni voce può chiudersi con un esito tra: `completa`, `aperta`, `escala`.

> Nota: il numero di domande è una scelta didattica da verificare con l'uso in aula, non uno standard o
> una checklist di conformità. Le fonti sostengono la copertura dei temi in ogni area, non il numero esatto
> di domande. Gli identificativi delle domande non sono stati rinumerati dopo le fusioni: per questo in
> alcune aree la numerazione salta (per esempio A2 ha Q2.2 e Q2.4).

## Dove si scrive la risposta

Il workbook è il metodo; la workflow spec (`templates/workflow_spec_compilabile.docx`) è il contratto in
cui scrivi le risposte. Sotto ogni domanda trovi **Dove nel template**: la sezione e il campo della spec
in cui va la risposta. Le sezioni sono queste:

| Sezione | Che cosa contiene |
|---|---|
| 1 | Case card: identità, caso, perché automatizzare, risultato atteso e come si misura, inizio, fine e arresto, fuori perimetro, attori e responsabilità |
| 2 | Exception map: processo attuale, poi failure mode, fallback e owner |
| 3 | Workflow diagram, stati e gate: tabella degli stati, identificativi automatici, alternativa scartata e motivo, fatto che farebbe cambiare scelta |
| 4a | Authority map: fonti e regola in caso di conflitto |
| 4b | Decision map: chi decide, con quali input e quali hard stop; decisioni sempre umane |
| 4c | Schema dei tool: input, effetto, permesso, errori attesi, evidenza prodotta |
| 5 | Interazione: touchpoint umani e accessibilità |
| 6 | Parametri del workflow |
| 7 | Ipotesi di test, con l'esito atteso scritto prima di eseguire |
| 8 | Diario di laboratorio: risultati dei test, rischi residui, note post-mortem |

Le sezioni da 1 a 7 sono il progetto e si congelano con `freeze-spec`; restano aggiornabili anche dopo
la sezione 8 e i campi segnati [non congelato], che servono a progettare ma il codice non usa. Una domanda può rimandare a più sezioni: in quel caso la risposta è distribuita, e conviene
controllare che le parti siano coerenti tra loro.

L'area A8 riguarda la messa in esercizio. Nel laboratorio i dati sono sintetici e il workflow non va in
produzione, quindi le sue tre domande si affrontano dopo, quando porti il metodo su un processo reale, e
non hanno una sezione dedicata nel template.

In aula hai visto lo stesso template compilato sul caso Aurora: le domande portano alle stesse sezioni
anche sul tuo caso.

## A1. Risultato e confini (4 domande)

*Scopo: Chiarire il cambiamento atteso prima di scegliere la soluzione.*

- **Q1.1** Quale risultato osservabile deve produrre il workflow e come sarà misurato?
  - _Criteri di verifica: baseline, target o criterio, finestra temporale._
  - _Dove nel template: sezione 1, campi "Risultato atteso" e "Come si misura il risultato"._
- **Q1.2** Chi riceve il risultato e chi risponde del suo raggiungimento?
  - _Criteri di verifica: destinatario, process owner, decision owner._
  - _Dove nel template: sezione 1, tabella "Attori e responsabilità"._
- **Q1.3** Quali eventi delimitano l'inizio, la fine e l'arresto del workflow, e che cosa resta fuori?
  - _Criteri di verifica: evento iniziale, stati terminali, stop condition, out of scope._
  - _Dove nel template: sezione 1, campi "Inizio, fine e arresto" e "Fuori perimetro"; gli stati
    terminali compaiono anche nella tabella degli stati della sezione 3._
- **Q1.4** Quali evidenze mostrano che automatizzare questo perimetro è preferibile a mantenerlo manuale o semplificarlo?
  - _Criteri di verifica: problema osservato, alternative non automatizzate, benefici attesi, costi e rischi._
  - _Dove nel template: sezione 1, campo "Perché automatizzare", in due o tre righe._

## A2. Processo attuale (2 domande)

*Scopo: Progettare a partire dal lavoro reale, comprese attese e deviazioni.*

- **Q2.2** Come attraversa oggi un caso il processo, da che cosa parte, chi lo passa a chi e dove si perde tempo o contesto?
  - _Criteri di verifica: trigger osservabile, caso identificabile, esito corrente, passi e responsabili,
    handoff, attese e rilavorazioni, canali laterali e informazioni perse._
  - _Dove nel template: sezione 2, tabella "Processo attuale" (Passo, Chi, Passa a, Dove si perde),
    una riga per passaggio._
- **Q2.4** Quali varianti ed eccezioni sono osservate e quali parti della mappa restano assunzioni da verificare?
  - _Criteri di verifica: varianti frequenti, eccezioni ad alto impatto, fatti, assunzioni._
  - _Dove nel template: sezione 2, una riga Failure mode, Fallback, Owner per ogni variante o eccezione;
    nei campi della sezione 1 scrivi come tali le assunzioni ancora da verificare, separate dai fatti._

## A3. Dati e fonti (4 domande)

*Scopo: Rendere verificabili provenienza, qualità e limiti delle informazioni.*

- **Q3.1** Quali informazioni servono a ciascuna decisione o azione e da quali fonti provengono?
  - _Criteri di verifica: dato necessario, uso, source_id, collegamento alla decisione o azione._
  - _Dove nel template: sezione 4a, colonne "Tipo fonte" e "Fatti che conferma"; sezione 4b, colonna
    "Input"._
- **Q3.2** Chi è responsabile di ogni fonte e che cosa autorizza il workflow ad accedervi e usarla?
  - _Criteri di verifica: owner, accesso, finalità, limitazioni d'uso._
  - _Dove nel template: sezione 4a, colonna "Autorità per claim"; sezione 4c, colonna "Permesso"._
- **Q3.3** Come verifichiamo provenienza, aggiornamento, versione e qualità delle informazioni critiche?
  - _Criteri di verifica: provenienza, observed_at, versione, qualità attesa e osservata._
  - _Dove nel template: sezione 4a, colonne "Limiti" e "Validità"._
- **Q3.4** Che cosa accade quando un'informazione è mancante, obsoleta o in conflitto?
  - _Criteri di verifica: stato esplicito, fonte autorevole, stop o fallback, evidenza dell'esito._
  - _Dove nel template: sezione 4a, campo "Regola in caso di conflitto"; sezione 2, una riga per
    l'informazione mancante, obsoleta o in conflitto. L'informazione duplicata si tratta in Q5.3._

## A4. Decisioni e responsabilità (4 domande)

*Scopo: Separare preparazione, proposta, autorità ed escalation.*

- **Q4.1** Quali decisioni deve sostenere il workflow e con quali opzioni e criteri espliciti?
  - _Criteri di verifica: domanda decisionale, opzioni, criteri, input con provenienza._
  - _Dove nel template: sezione 4b, colonne "Decisione", "Input" e "Output"._
- **Q4.2** Quale parte del lavoro affidiamo a persone, regole, AI e strumenti, e per quale motivo?
  - _Criteri di verifica: capacità necessaria, prevedibilità, incertezza, limite di autorità._
  - _Dove nel template: sezione 4b, colonna "Responsabile" (CODICE, AI, PERSONA)._
- **Q4.3** Chi può approvare, rifiutare o sospendere ogni decisione ad impatto e quali evidenze deve ricevere?
  - _Criteri di verifica: authority owner, contesto, diritto di stop, traccia della decisione._
  - _Dove nel template: sezione 4b, campo "Decisioni sempre umane"; sezione 5, colonna "Dato
    strutturato" del touchpoint in cui la persona decide._
- **Q4.4** Quale fallback o escalation si applica quando i criteri non bastano o l'incertezza è troppo alta?
  - _Criteri di verifica: soglia, fallback, destinatario, tempo di risposta, contestazione._
  - _Dove nel template: sezione 4b, colonna "Hard stop"; sezione 2, colonna "Owner"._

## A5. Stati, eccezioni ed effetti (4 domande)

*Scopo: Governare la memoria del caso e i fallimenti prima di scegliere la tecnologia.*

- **Q5.1** In quali stati può trovarsi ogni caso e quali eventi e condizioni autorizzano le transizioni?
  - _Criteri di verifica: stati significativi, evento, guardia, transizioni vietate._
  - _Dove nel template: sezione 3, tabella degli stati e delle transizioni._
- **Q5.2** Quali effetti esterni produce il workflow e come proviamo che ciascuno è autorizzato e completato?
  - _Criteri di verifica: effetto, autorizzazione, ricevuta, correlazione al caso._
  - _Dove nel template: sezione 4c, colonne "Effetto" ed "Evidenza prodotta"._
- **Q5.3** Come riconosce duplicati, tentativi ripetuti ed eventi tardivi o fuori ordine senza moltiplicare gli effetti?
  - _Criteri di verifica: chiave del caso, deduplicazione di richieste e informazioni duplicate, retry,
    idempotenza, ordinamento._
  - _Dove nel template: sezione 3, campo "Identificativi automatici", con le chiavi di deduplica e di
    idempotenza._
- **Q5.4** Come gestisce timeout e fallimenti parziali, inclusi arresto, ripresa, riconciliazione e compensazione?
  - _Criteri di verifica: timeout, stato intermedio, restart, riconciliazione, compensazione._
  - _Dove nel template: sezione 2, almeno una riga dedicata a un timeout o a una compensazione._

## A6. Soluzione, rischi e controlli (3 domande)

*Scopo: Scegliere una soluzione implementabile confrontando alternative e rischi.*

- **Q6.1** Quali alternative praticabili soddisfano i requisiti e con quali criteri ne scegliamo una?
  - _Criteri di verifica: almeno due opzioni, forze del problema, compromessi, motivazione._
  - _Dove nel template: sezione 3, campo "Alternativa scartata e motivo"._
- **Q6.2** Quali componenti, interfacce e contratti servono e che cosa scambia ciascun confine?
  - _Criteri di verifica: componenti, producer e consumer, dati, errori, autorizzazioni._
  - _Dove nel template: sezione 4c, una riga per tool con input, effetto, permesso `read`/`propose`/`write`,
    errori attesi ed evidenza prodotta; i confini tra componenti si leggono nella tabella degli stati della
    sezione 3._
- **Q6.4** Quali rischi restano dopo i controlli, chi li accetta e quale fatto farebbe riaprire la scelta?
  - _Criteri di verifica: rischio, controllo e segnale, test del controllo, rischio residuo, owner e
    accettazione, trigger di riapertura._
  - _Dove nel template: sezione 3, campo "Fatto che farebbe cambiare scelta"; sezione 8, campo "Rischi
    residui". I controlli sono già le righe Fallback della sezione 2._

## A7. Prova e validazione (3 domande)

*Scopo: Cercare presto evidenze che possano confermare o smentire il disegno.*

- **Q7.1** Quale ipotesi rischiosa dobbiamo provare per prima e quale piccolo percorso end-to-end può smentirla?
  - _Criteri di verifica: ipotesi, rischio collegato, confine della prova, effetto controllato._
  - _Dove nel template: sezione 7, prima riga: è l'ipotesi più rischiosa._
- **Q7.2** Quali scenari nominali, limite e di fallimento proveremo e quali risultati attesi fissiamo prima dell'esecuzione?
  - _Criteri di verifica: fixture, expected state, expected decision, expected evidence._
  - _Dove nel template: sezione 7, colonna "Esito atteso", da scrivere prima di eseguire la prova._
- **Q7.3** Quali evidenze registrano i risultati osservati e collegano ogni pass o fail a requisiti, rischi e decisioni?
  - _Criteri di verifica: risultato osservato, pass o fail, evidence_ref, tracciabilità._
  - _Dove nel template: sezione 8, campo "Risultati test"._

## A8. Messa in esercizio e miglioramento (3 domande, dopo il laboratorio)

*Scopo: Rendere il workflow osservabile, arrestabile, recuperabile ed evolvibile.*

*Quest'area non si compila durante il laboratorio e non ha una sezione nel template: le domande servono
quando il workflow deve andare in esercizio su un processo reale.*

- **Q8.1** Chi può rilasciare, operare, approvare, arrestare e modificare il workflow e i suoi componenti, e come si arresta e si riprende in sicurezza?
  - _Criteri di verifica: ruoli e permessi, separazione dei compiti, escalation, stop e rollback, replay e
    riconciliazione, ripresa._
  - _Dove nel template: fuori dal template._
- **Q8.2** Quali segnali, metriche, log e trace mostrano lo stato del caso, la salute del sistema e l'outcome, e come si vede se l'outcome migliora?
  - _Criteri di verifica: vista caso, vista sistema, vista outcome, soglie e finestre, miglioramento
    rispetto alla baseline, dataset di valutazione e analisi errori dei componenti AI._
  - _Dove nel template: fuori dal template. In parte la risposta esiste già: gli identificativi della
    sezione 3 e, se tra i parametri della sezione 6 c'è il livello di trace, quella riga._
- **Q8.4** Come versioni, test, revisioni periodiche e segnali operativi guidano modifica, miglioramento e ritiro del workflow?
  - _Criteri di verifica: versione, regressione, cadenza di review, backlog, ritiro._
  - _Dove nel template: fuori dal template._
