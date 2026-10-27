# Fonte sintetica attraverso MCP — approfondimento facoltativo

Dalla radice del laboratorio, sostituisci RUN_ID con quello della baseline:

```powershell
python mcp_lab/client.py --run-id RUN_ID --out reports/mcp_trace.json
```

Il client avvia davvero un server in un processo separato e scambia JSON-RPC su stdio: initialize, notifica initialized, tools/list, tools/call. `reports/mcp_trace.json` conserva messaggi e correlazione al run. La sorgente è una variante dichiarata di Meridiano, non modifica i fatti della baseline. Il client non legge la fonte direttamente: la consulta attraverso il server.

Tre esiti: record disponibile; record inesistente (`isError: true`, errore tool); strumento non disponibile (errore di protocollo `-32602`). Un errore non vale come evidenza: il comportamento del dimostratore è arrestare la proposta, mantenere HUMAN_REQUIRED e non inviare nulla. Nessuna di queste risposte entra automaticamente nel motore di policy del laboratorio: è un'estensione osservabile da collegare alla review, non un nuovo permesso. Salva nel break report il messaggio che prova questo confine.

L'host è questo programma dimostrativo; il client mantiene la connessione; il server espone il tool. Sono software deterministici, **non agenti**. Nessun modello, credenziale, rete o SDK necessario. Sottoinsieme didattico MCP **2025-06-18**, non dichiarato implementazione completa né ultima versione. Verificato sulla specifica primaria: [lifecycle](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle), [stdio](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports), [tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools).

Prima: prevedi quale dei tre esiti permette di proseguire alla valutazione (mai all'approvazione automatica). Dopo: mostra richiesta e risposta correlate, spiega perché errore tool e errore di protocollo sono diversi. Trasferisci il risultato disponibile al manager seguendo coordination/README.md; il contesto mancante deve provocare richiesta di integrazione.
# Collocazione nella scaletta corrente

Approfondimento facoltativo, fuori dalla scansione obbligatoria LCK3/LCK4.
Client e server locali restano deterministici: questa prova non diventa esecuzione
agentica del modello. Una registrazione consente interpretazione; per dimostrare
la capacità individuale occorre una chiamata effettivamente eseguita e documentata.
