# Manager, delega e handoff su Meridiano

Variante didattica: una fonte nuova contiene un conflitto da interpretare sull'ambito della licenza e sulle coordinate in un allegato. Le verifiche necessarie dipendono dal testo; il workflow originale può restare la soluzione più semplice per i passaggi già noti. Non trasformiamo funzioni Python in agenti.

## Percorso chat ordinario (stessi obiettivi con coding agent opzionale)

Usa tre conversazioni separate, con contesti di ruolo: manager, specialista fonti, specialista rischi. Sono ruoli interpretati da un modello reale; il partecipante trasporta i messaggi. è coordinamento mediato dalla persona, non orchestrazione autonoma. Nessun requisito di tre account o di API: le conversazioni possono essere sequenziali. Con coding agent puoi usare subagenti se l'interfaccia li offre; registra nome dell'interfaccia, modello dichiarato, prompt, risposte, ordine e tempi effettivi. Non chiamare replay una prova con modello reale o viceversa.

1. Nell'approfondimento facoltativo scegli il risultato MCP registrato dal docente, dichiarandone la provenienza, oppure esegui una nuova chiamata con il tuo run_id seguendo `mcp_lab/README.md`. Copia solo il risultato sintetico riuscito, il run_id e il riferimento alla traccia. Apri una chat manager con `manager_prompt.txt`. Il manager sceglie quali specialisti coinvolgere e formula incarichi; tu verifica i contratti prima di trasportarli.
2. Apri le chat specialistiche con `specialist_prompt.txt` e il contratto ricevuto. Salva incarico e risposta, poi riportali al manager. Il manager conserva il controllo e ricompone la proposta; lo specialista restituisce un risultato circoscritto. Nessuno approva pubblicazioni.
3. Nella variante handoff, usa `handoff_prompt.txt` in una nuova chat. Questa chat diventa responsabile del prossimo passo di analisi e interagisce direttamente con te: il manager precedente non deve più impartire il passo successivo. Rimuovi deliberatamente evidence_ref dal contratto: osserva se il ricevente chiede il contesto mancante prima di procedere. Ripristinalo e ripeti. Il trasferimento di controllo è esplicito e mediato dalla persona; non trasferisce l'autorità umana.
4. Registra nel template `evidence_template.json` (copia in reports/coordination_evidence.json) input/output effettivi, agente attivo prima/dopo, previsione, osservazione e spiegazione. Non limitarti a scrivere PASS. Allegalo alla consegna del lab. In modalità chat salva i messaggi sintetici rilevanti, senza esportare conversazioni personali.

## Tempi e checkpoint

Questo confronto resta fuori dai minuti obbligatori di baseline, reveal e challenge. Usa lo stesso input per i due coordinamenti. Prima prevedi chi avrà il controllo; dopo mostra il messaggio che lo prova. I tempi umani e della specifica interfaccia chat restano da misurare: tre finestre non garantiscono rapidità. Il docente può proporre una dimostrazione separata o una registrazione dichiarata; nessuna delle due prova che ciascun partecipante abbia eseguito personalmente l'handoff.

Il replay di supporto può essere fornito dal docente dopo la demo: va etichettato `recorded_model_run` oppure `synthetic_replay`, con origine e limiti. Leggere un replay prova capacità di interpretazione, non esecuzione autonoma di agenti. La consegna finale dei file rimane distinta dall'handoff di controllo fra agenti.

## Replay disponibile

`recorded_model_run.json` contiene quattro risposte reali osservate tramite subagente con strumenti della sessione di manutenzione. Ruoli sequenziali nello stesso contesto, senza prova di isolamento; instradamento esplicito del manutentore. `mcp_recorded_trace.json` è una chiamata locale reale registrata separatamente sul medesimo testo, non una chiamata MCP scelta dal modello. Queste fonti si usano nell'approfondimento facoltativo, separato dalla prova della policy di L10 e dalla review di L11. Non ripetere i campi del replay come osservazioni personali: formulare prima la propria previsione e dichiarare il tipo di prova.
# Collocazione nella scaletta corrente

Approfondimento facoltativo, fuori dai 32 minuti LCK3 e dai 25 minuti LCK4.
La nuova pratica principale osserva un nodo con consultazioni scelte dal coding agent,
conservando prova individuale della policy, diagnosi e review. Un handoff osservato
in registrazione non prova la capacità di eseguirlo personalmente. Le istruzioni
seguenti descrivono la prova separata e mantengono il loro significato originario.
