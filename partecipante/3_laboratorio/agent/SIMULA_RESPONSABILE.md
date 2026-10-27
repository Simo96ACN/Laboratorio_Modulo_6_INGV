# Gioco di ruolo: rispondi a una richiesta come responsabile simulato

Questo incarico inizia **dopo** che il partecipante ha controllato e importato la
classificazione. Richiede `role_response_mode: model_simulated` nel TODO-01 e il
tool `simulate-role-response`. Non riprendere il compito di classificazione.

**Nel mondo reale questo ruolo è umano.** Qui il modello interpreta un personaggio
del caso sintetico per esercitare richiesta, attesa, risposta e rivalutazione.
La risposta non è un'approvazione reale e non dimostra una review indipendente.
La review finale del laboratorio resta al partecipante.

Il partecipante assegna workspace e RUN_ID espliciti, indica il modello/sessione
da dichiarare e può limitare l'incarico a uno specifico TASK_ID. Consegna questa
istruzione al modello, completando soltanto tali riferimenti:

> Interpreta il destinatario delle richieste simulate nel run assegnato. Usa
> agent_tools.py con workspace e run espliciti. Consulta catalog e approval-requests:
> leggi dataset, versione, scope, destinatario, motivo e gate. Consulta request, search-evidence e read-evidence per leggere
> le evidenze pertinenti del run, entro il budget condiviso con la classificazione.
> Se il budget non basta, fermati e chiedi al partecipante di proseguire. Non accedere
> a fonti estranee o modificare i file del laboratorio.
> Sei tu il destinatario del task: la tua risposta è l'atto di conferma richiesto,
> quindi non cercare nelle evidenze una tua conferma precedente. Per ogni task
> assegnato ancora pendente decidi APPROVE oppure REJECT valutando, entro lo scope
> del ruolo, se i fatti disponibili sul dataset e sulla versione indicata consentono
> la pubblicazione, e segnala le lacune. Non inventare deleghe, identità, verifiche
> eseguite o fatti assenti dalle evidenze. Se i fatti disponibili non bastano a
> sostenere la conferma, rifiuta indicando quali mancano.
> Registra la risposta tramite simulate-role-response, con il ruolo esatto del
> task e il modello/sessione dichiarato. Non usare respond-approval, non modificare
> registri o JSON, non eseguire continue o review e non compilare decisions.txt.
> Presenta ID task, decisione, evidenze e limite della simulazione, poi fermati.
> Chiudi ricordando: «Risposta simulata dal modello per il laboratorio; nel
> processo reale decide un responsabile umano».

Dopo l'arresto, il partecipante legge la risposta e confronta i gate prima/dopo
in `approval_reassessment.json`. Un APPROVE può incidere solo su `formal_approval`:
licenze, qualità, embargo e sensibilità restano vincoli distinti. Registra la
provenienza nel workbook e verifica le nuove proposte prima della review.
