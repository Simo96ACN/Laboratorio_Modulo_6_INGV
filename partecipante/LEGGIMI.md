# Modulo 6 - Materiali per il partecipante

Estrai questa cartella in un percorso breve (per esempio `C:\corso\modulo6`) e aprila
nell'ordine indicato dai numeri.

## 1_brief

`participant_brief.md` - obiettivo del laboratorio, vincoli e struttura delle otto sezioni
della specifica. Leggilo per primo.

`checklist_progettazione_workflow.docx` - domande e criteri per progettare il workflow,
con il collegamento ai campi della spec. Usala durante la compilazione; l'area A8
riguarda la messa in esercizio successiva al laboratorio.

## 2_esempio_aurora

Il caso Aurora visto in aula, compilato: `workflow_spec_aurora_compilato.docx` e il diagramma
del suo workflow. È scritto sullo stesso template che compilerai sul caso Meridiano, con le
stesse otto sezioni nello stesso ordine: usalo per confrontare metodo e livello di dettaglio
sezione per sezione. Non copiarne le decisioni: i due casi hanno dati, autorità e parametri
diversi.

## 3_laboratorio

L'ambiente di lavoro. Apri il suo `INDICE.md`: contiene il percorso consigliato, dal
`README.md` fino al post-mortem. Tutti i comandi si eseguono da questa cartella.

Se usi un assistente AI, incolla per primi `AI_START.md` e `AGENTS.md`, che contengono la
scaletta delle fasi e il patto di tutoring; poi condividi solo i materiali della fase
corrente.

Scegli la modalità AI nella sezione 5 della spec e completa il TODO-01 secondo
`agent/TODO_CONFIGURAZIONE.md`, verificando `workflow/agent_config.json`.
Dopo freeze, dodici TODO e avvio della baseline, con modalità `agent` il percorso operativo usa una nuova
sessione: esegui `python runner.py --workspace workspace prepare-agent --run-id RUN_ID`
e fornisci l'incarico stampato, insieme ad `agent/START_OPERATORE.md`. L'operatore
consulta e consegna soltanto una bozza; continue, prova della policy e review restano
tuoi. Il fallback manuale conserva lo stesso run. Prima dell'aula compila la verifica
postazione in `agent/VERIFICA_POSTAZIONE.md`.

## Note

I dati del caso sono sintetici e gli effetti sono simulati: nessun invio o pubblicazione
reale. I file restano tuoi, il laboratorio e' un esercizio e non viene valutato.
