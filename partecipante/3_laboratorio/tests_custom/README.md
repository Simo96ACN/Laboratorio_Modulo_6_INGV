# Test creati dal partecipante

Questa cartella raccoglie i test che dimostrano le scelte della spec. Non inserire dati reali,
reference docente o esiti attesi dei cinque dataset baseline.

Il freeze genera:

- `generated_spec_fixture.json`, con scelta e alternativa;
- `SPEC_TEST_INSTRUCTIONS.txt`, con il contratto minimo.

Il test principale deve usare un caso sintetico nel quale il valore scelto e l'alternativa
producono una differenza osservabile. Entrambi devono conservare hard stop, review umana,
tracciabilità e soli effetti simulati.

Esegui anche:

1. una variante con ID permutati;
2. un input incompleto o incoerente;
3. la challenge generata con `create-from-spec`;
4. una prova preparata da un collega oppure il fallback docente.

Il solo completamento del comando non dimostra nulla. Registra ipotesi, osservazione,
correzione e rischio residuo in `reports/break_report.md`.
