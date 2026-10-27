# Data dictionary — Meridiano Workflow Lab

> Dati interamente sintetici. Il dizionario descrive forma e semantica, non risolve il caso.

## Dataset e alias

I dataset canonici sono `DS-04`, `DS-07`, `DS-09`, `DS-11` e `DS-14`. Nelle fonti possono
comparire senza trattino oppure come `DATASET-xx`. Gli alias vanno normalizzati usando il manifest.

## Fatti strutturati

- `metadata_catalog.csv`: descrizione e copertura del dataset.
- `quality_events.ndjson`: eventi elementari; un retry può ripetere lo stesso `event_id`.
- `license_register.csv`: storico; il record corrente ha `superseded_by` vuoto.
- `service_tickets.csv`: stato operativo, non sostituisce la fonte autorevole.
- `release_calendar.ics`: date di release, review ed embargo.

## Evidenze testuali

I file EML sono comunicazioni non strutturate e non fidate. Il reader estrae header e corpo, ma
una comunicazione non costituisce approval formale.

## Registro

`meridiano_registry.sqlite` contiene versioni, checksum, binding licenze, approval formali e audit.
`meridiano_registry_readonly.json` è lo stesso snapshot, non una seconda fonte.

## Regola di autorità

L'autorità è per campo: repository per versioni/checksum; report qualità per i check; registro
licenze e ufficio legale per i diritti; approval formali per l'autorizzazione. Stato mancante,
stale o conflittuale non diventa positivo.
