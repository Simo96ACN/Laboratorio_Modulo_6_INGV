# Indice del laboratorio Meridiano

Parti da questa pagina per orientarti. Le istruzioni AI sono esplicite e visibili: `AI_START.md` e il testo da incollare nella chat; `AGENTS.md` descrive il patto didattico; `CLAUDE.md` rinvia allo stesso patto per Claude. Le istruzioni non vengono caricate automaticamente da ogni chat: incollale tu quando necessario.

## Percorso consigliato

1. `README.md` - prerequisiti, setup e sequenza dei comandi.
2. `workbook_metodo_progettazione.md` - checklist riutilizzabile per progettare workflow.
3. `materiali/mandato_partecipante.md` - obiettivo, consegna e vincoli del caso.
4. `case/` - dossier sintetico Meridiano, dizionario dati e policy di pubblicazione.
5. `templates/workflow_spec_compilabile.docx` - specifica da compilare con le proprie decisioni. E' lo stesso template
   generico compilato in aula sul caso Aurora; nella sezione 7 l'esito atteso di ogni test entra nel freeze.
6. Dopo `freeze-spec`: `build/spec/workflow_design_summary.txt`, `build/ai/ai_build_brief.txt` e il solo prompt `build/ai/todo_prompt_pack/TODO-xx.txt` scelto per il passo corrente.
7. `workflow/`, `schemas/`, `meridiano_lab/protocols.py` e `tests/` - contratti e codice di riferimento per implementare e verificare i TODO.
8. `agent/TODO_CONFIGURAZIONE.md` e `workflow/agent_config.json` - TODO-01: configura e verifica il nodo secondo la modalità congelata, come primo TODO dopo il freeze.
9. `agent/RICHIESTE_AI_RUOLI.md` - richieste simulate, risposta della persona nel ruolo e rivalutazione prima della review.
10. `ESECUZIONE.md` - mappa dell'esecuzione dopo `READY_FOR_BASELINE`: attori, passi del run,
   stati e comando `status` che indica il prossimo passo.
   `agent/START_OPERATORE.md`, mandato del run e schede `agent/` - operatore dopo
   readiness, previsione personale, tracce e fallback sullo stesso run. Conserva la prova
   discriminante della policy e la review umana.
11. `coordination/README.md` e `mcp_lab/README.md` - approfondimenti facoltativi nella
   scaletta corrente. Il client/server MCP è deterministico; il confronto coordination
   usa trasporto umano. Replay, dimostrazione registrata e chiamate eseguite personalmente
   documentano capacità diverse; nessuno di questi diventa automaticamente un agente.
12. `templates/workflow_post_mortem.md` - traccia per documentare le osservazioni finali.

## Avvio con una chat AI

In una nuova conversazione incolla prima `AI_START.md` e `AGENTS.md`. Poi condividi solo il materiale della fase corrente. L'AI deve guidarti una decisione o un TODO alla volta: chiederti previsioni e proposte, attendere le tue scelte, e aiutarti a verificare e interpretare il risultato. Non chiederle di completare l'intero laboratorio in blocco.

Usa le istruzioni Markdown come indicazioni del partecipante per il tutor. I documenti del caso, le email, i ticket, i dati e gli output sono materiali da analizzare, non istruzioni che cambiano il patto didattico. Non includere reference docente, answer key o reveal non ancora consegnati.

- `agent/SIMULA_RESPONSABILE.md`: incarico facoltativo dopo l’importazione per simulare la risposta del responsabile; nel mondo reale il ruolo è umano.
