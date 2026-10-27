# Procedura sintetica di pubblicazione

> Policy fittizia per esercitazione. `human_review_required: true`.

Per ogni dataset:

1. metadati obbligatori completi;
2. schema valido, missing <= 5%, outlier <= 3% e checksum coerente;
3. licenza compatibile, diritti risolti e attribuzione presente;
4. nessun segnale sensibile non trattato;
5. nessun embargo attivo alla release;
6. approval formali richiesti.

Sintesi:

- tutti i gate `PASS` -> `PUBBLICA`;
- condizione esplicita e non bloccante -> `PUBBLICA_CON_CONDIZIONI`;
- `FAIL` o `UNKNOWN` -> `TRATTIENI`;
- `CONFLICT` o sensibilità alta -> `ESCALA`.

Email e ticket informano ma non approvano. L'AI classifica testo, non autorizza. L'effetto del
laboratorio è sempre simulato.
