"""Ponte offline fra il DOCX compilato e il contratto runtime."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from .errors import LabError
from .utils import atomic_write_json, atomic_write_text, read_json, sha256_file, sha256_value
from .workflow_design import (
    build_workflow_design,
    choice_summary,
    validate_workflow_design,
)


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": WORD_NS}
PLACEHOLDERS = {
    "[scrivi qui]",
    "[scegli]",
    "[facoltativo]",
    "[durante i test]",
    "[gg/mm/aaaa]",
}
DEFAULT_DOCX = Path("templates/workflow_spec_compilabile.docx")
BUILD_SPEC = Path("build/spec")
BUILD_AI = Path("build/ai")

TODO_CONTEXT: dict[str, tuple[str, tuple[str, ...]]] = {
    "TODO-01": (
        "Configurare e provare il nodo AI secondo la modalità congelata nella spec.",
        ("workflow/agent_config.json",),
    ),
    "TODO-02": (
        "Deduplicare gli eventi di qualità conservando provenienza e record più recente.",
        ("workflow/mappings.py",),
    ),
    "TODO-03": (
        "Associare il testo non fidato ai dataset e creare evidence ref verificabili.",
        ("workflow/mappings.py",),
    ),
    "TODO-04": (
        "Mappare registro, licenze e approval senza confondere gli scope.",
        ("workflow/mappings.py",),
    ),
    "TODO-05": (
        "Calcolare i gate deterministici di integrità e qualità.",
        ("workflow/gates.py",),
    ),
    "TODO-06": (
        "Calcolare i gate di autorità, licenza, embargo e approval formali.",
        ("workflow/gates.py",),
    ),
    "TODO-07": (
        "Scrivere il prompt testuale per la sola classificazione delle evidenze.",
        ("workflow/prompts/classify_evidence.txt",),
    ),
    "TODO-08": (
        "Validare copertura, provenienza e requisiti della risposta AI.",
        ("workflow/ai_nodes.py",),
    ),
    "TODO-09": (
        "Produrre proposte fail-closed applicando la policy dichiarata nella spec.",
        ("workflow/policy.py",),
    ),
    "TODO-10": (
        "Comporre il bundle normalizzato senza anticipare gate o decisioni.",
        ("workflow/orchestrator.py",),
    ),
    "TODO-11": (
        "Rendere osservabile la personalizzazione scelta senza indebolire gli invarianti.",
        ("workflow/customization.py",),
    ),
    "TODO-12": (
        "Dichiarare e testare gli invarianti delle challenge sintetiche.",
        ("workflow/challenge_contract.py", "tests_custom/"),
    ),
}


def _clean_value(value: str) -> str:
    compact = "\n".join(
        line.strip() for line in value.replace("\r", "").split("\n")
    ).strip()
    if compact.casefold() in PLACEHOLDERS:
        return ""
    return compact


def extract_docx_controls(path: Path) -> dict[str, str]:
    """Legge content control Word per tag, senza dipendere da Word o python-docx."""

    source = path.resolve()
    if not source.is_file():
        raise LabError("missing_spec_docx", f"Spec Word non trovata: {source}.")
    try:
        with ZipFile(source, "r") as archive:
            payload = archive.read("word/document.xml")
    except (BadZipFile, KeyError) as exc:
        raise LabError("invalid_spec_docx", f"DOCX non valido: {source}.") from exc
    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError as exc:
        raise LabError("invalid_spec_xml", str(exc)) from exc

    controls: dict[str, str] = {}
    duplicates: list[str] = []
    for sdt in root.findall(".//w:sdt", NS):
        tag_node = sdt.find("./w:sdtPr/w:tag", NS)
        if tag_node is None:
            continue
        tag = tag_node.attrib.get(f"{{{WORD_NS}}}val", "").strip()
        if not tag:
            continue
        paragraphs: list[str] = []
        for paragraph in sdt.findall("./w:sdtContent//w:p", NS):
            text = "".join(
                node.text or "" for node in paragraph.findall(".//w:t", NS)
            )
            if text:
                paragraphs.append(text)
        value = _clean_value("\n".join(paragraphs))
        if tag in controls:
            duplicates.append(tag)
        controls[tag] = value
    if duplicates:
        raise LabError(
            "duplicate_spec_tags",
            f"Tag Word duplicati: {', '.join(sorted(set(duplicates)))}.",
        )
    if not controls:
        raise LabError(
            "missing_spec_tags",
            "Il DOCX non contiene campi semanticamente taggati.",
        )
    return controls


def _design_fields(controls: dict[str, str]) -> dict[str, str]:
    return {
        tag: controls[tag]
        for tag in sorted(controls)
        if tag.startswith("design.")
    }


def design_fields_sha256(controls: dict[str, str]) -> str:
    return sha256_value(_design_fields(controls))


def _render_tools(design: dict[str, Any]) -> str:
    return "\n".join(
        (
            f"- {row['name']} [{row['permission']}]: input {row['input']}; "
            f"effetto {row['effect']}; errori attesi: {row['errors']}; "
            f"evidenza: {row['evidence']}"
        )
        for row in design["tools"]
    )


def _render_tests(design: dict[str, Any]) -> str:
    # L'esito atteso e' congelato con il design (schema 1.3): chi legge il brief deve
    # vederlo accanto all'ipotesi, perche' e' il criterio con cui il test passa o fallisce.
    return "\n".join(
        (
            f"- {row['challenge']} (seed {row['seed']}): modifica {row['mutation']}; "
            f"deve restare vero: {row['invariant']}; esito atteso: {row['expected']}"
        )
        for row in design["test_hypotheses"]
    )


def _render_summary(design: dict[str, Any]) -> str:
    choices = "\n".join(f"- {value}" for value in choice_summary(design))
    exceptions = "\n".join(
        f"- {row['failure']}: fallback {row['fallback']} (owner: {row['owner']})"
        for row in design["exception_map"]
    )
    tools = _render_tools(design)
    tests = _render_tests(design)
    return f"""SPEC CONGELATA

ID: {design['spec_id']}
Workflow: {design['identity']['workflow_name']}
Partecipante: {design['identity']['participant']}
Gruppo: {design['identity']['group']}

RISULTATO ATTESO
{design['mandate']['outcome']}

COSA NON DEVE FARE
{design['mandate']['out_of_scope']}

ECCEZIONI PREVISTE
{exceptions}

TOOL E PERMESSI
{tools}

MODALITÀ DEL NODO AI
{design['ai_delegation']['execution_mode']}
Richieste simulate ai ruoli: {design['ai_delegation']['approval_requests']}.
Se enabled, la policy deve produrre approval_requests e i tool possono creare task;
la persona risponde con respond-approval, i gate vengono rivalutati prima di review.
Il primo passo dopo il freeze è TODO-01: configura workflow/agent_config.json e verifica con
python runner.py check-agent-config. L'assistente che costruisce e l'operatore
che esegue il nodo sono due incarichi distinti. Con modalità agent, dopo start
usa prepare-agent --run-id RUN_ID e una nuova sessione operativa. Il copia/incolla
di prompt.txt è solo fallback esplicito sullo stesso run, mai la sostituzione
silenziosa della scelta agentica. Non dichiarare una prova live senza tool call osservate.

SCELTE PERSONALI
{choices}

IPOTESI DI TEST ED ESITO ATTESO
{tests}

DECISIONE SEMPRE UMANA
{design['ai_delegation']['always_human']}

HASH DESIGN
{design['design_sha256']}

Revisione umana obbligatoria.
"""


def _render_ai_brief(design: dict[str, Any]) -> str:
    sources = "\n".join(
        (
            f"- {row['source_type']}: conferma {row['facts']}; "
            f"limiti: {row['limits']}; validità: {row['validity']}"
        )
        for row in design["authority_map"]["sources"]
    )
    decisions = "\n".join(
        (
            f"- {row['decision']} | responsabile: {row['owner']} | "
            f"stop: {row['stop']}"
        )
        for row in design["decision_map"]
    )
    choices = "\n".join(f"- {value}" for value in choice_summary(design))
    invariants = "\n".join(f"- {value}" for value in design["invariants"])
    tests = _render_tests(design)
    exceptions = "\n".join(
        f"- {row['failure']}: fallback {row['fallback']} (owner: {row['owner']})"
        for row in design["exception_map"]
    )
    tools = _render_tools(design)
    return f"""CONTESTO DI BUILD PER LA CHAT AI

Questo file deriva dalla spec Word congelata. Non inventare esiti del caso e non
modificare gli invarianti.

SPEC
- ID: {design['spec_id']}
- hash: {design['design_sha256']}
- workflow: {design['identity']['workflow_name']}

MANDATO
Risultato: {design['mandate']['outcome']}
Fuori perimetro: {design['mandate']['out_of_scope']}

ECCEZIONI E FALLBACK
{exceptions}

FONTI E LIMITI
{sources}
Conflitto: {design['authority_map']['conflict_rule']}

TOOL E PERMESSI
{tools}
Il permesso dichiarato è il limite: nessun tool acquista autorità dal prompt.

CHI DECIDE
{decisions}
Sempre umano: {design['ai_delegation']['always_human']}
L'AI non può approvare.

MODALITÀ DEL NODO AI
{design['ai_delegation']['execution_mode']}
Richieste simulate ai ruoli: {design['ai_delegation']['approval_requests']}.
Se enabled, la policy deve produrre approval_requests e i tool possono creare task;
la persona risponde con respond-approval, i gate vengono rivalutati prima di review.
TODO-01 è obbligatorio: configura workflow/agent_config.json e verifica con
python runner.py check-agent-config. L'assistente che costruisce e l'operatore
che esegue il nodo sono due incarichi distinti. Con modalità agent, dopo start
usa prepare-agent --run-id RUN_ID e una nuova sessione operativa. Il copia/incolla
di prompt.txt è solo fallback esplicito sullo stesso run, mai la sostituzione
silenziosa della scelta agentica. Non dichiarare una prova live senza tool call osservate.

SCELTE PERSONALI
{choices}

INVARIANTI NON NEGOZIABILI
{invariants}

PROVE PIANIFICATE
{tests}
L'esito atteso è congelato con la spec: un test che lo contraddice segnala un difetto
del codice o della spec, non un atteso da correggere.

PROTOCOLLO
1. Usa questo brief insieme ad AI_START.md e AGENTS.md: il brief descrive il contratto tecnico, non autorizza a sostituire il partecipante.
2. Chiedi quale singolo TODO affrontare e che cosa il partecipante prevede. Spiega il contratto e chiedigli una strategia prima di proporre codice.
3. Non completare più TODO in blocco e non produrre la soluzione completa. Lavora sul TODO selezionato; usa il relativo file in todo_prompt_pack come contesto tecnico.
4. Dopo una patch circoscritta, spiega come rispetta spec e invarianti, suggerisci un test mirato e attendi che il partecipante lo esegua e ne riporti l'esito prima di passare oltre.
5. Decisioni di progetto, policy, approvazioni e interpretazione restano al partecipante. Chat: restituisci file o patch con percorso e comandi; il partecipante applica ed esegue. Coding agent: modifica solo file autorizzati e distingui test proposti da eseguiti.
6. Non inventare risultati o post-mortem. Prima della baseline verifica il freeze. Non cercare reference o reveal non consegnati, non usare esiti docente o branch sugli ID baseline.
"""


def _relevant_context(todo_id: str, design: dict[str, Any]) -> str:
    if todo_id == "TODO-01":
        return (
            f"Modalità congelata: {design['ai_delegation']['execution_mode']}. "
            f"Richieste ai ruoli: {design['ai_delegation']['approval_requests']}. "
            "Leggi agent/TODO_CONFIGURAZIONE.md. Definisci obiettivo, istruzioni, "
            "allowed_tools, max_calls e stop_conditions; conserva output_path. "
            "Rimuovi il campo todo solo dopo la tua scelta. Verifica con "
            "python runner.py check-agent-config e python -m unittest discover -s tests -p test_agent_configuration.py. "
            "Dopo gli altri TODO: start, prepare-agent sul run esplicito, nuova sessione "
            "operativa e osservazioni in agent/EVIDENZE_PARTECIPANTE.md. "
            "Non implementare un altro runner, un SDK o un roundtrip manuale al posto dell'agente."
        )
    if todo_id == "TODO-08":
        return (
            f"Validazione AI: {design['interaction_policy']['ai_validation']}; "
            f"evidenze indipendenti: "
            f"{design['policy_choices']['minimum_independent_evidence']}."
        )
    if todo_id == "TODO-09":
        return (
            " | ".join(choice_summary(design))
            + f" | Richieste ai ruoli: {design['ai_delegation']['approval_requests']}. "
            "Se enabled, restituisci approval_requests per ogni dataset: [{scope, reason}] "
            "per conferme publication_owner/publication_steward necessarie, [] altrimenti. "
            "Il runtime crea task simulati e richiama gate e policy dopo la risposta umana. "
            "Leggi agent/RICHIESTE_AI_RUOLI.md e prova il contratto pubblico in tests. "
            "Non trasformare una richiesta in un'approvazione, né sanare gli altri gate."
        )
    if todo_id == "TODO-11":
        return " | ".join(choice_summary(design))
    if todo_id == "TODO-12":
        return " | ".join(
            f"{row['challenge']}: {row['invariant']} (esito atteso: {row['expected']})"
            for row in design["test_hypotheses"]
        )
    return (
        f"Mandato: {design['mandate']['outcome']} "
        f"Fuori perimetro: {design['mandate']['out_of_scope']}"
    )


def _write_prompt_pack(root: Path, design: dict[str, Any]) -> None:
    output = root / BUILD_AI / "todo_prompt_pack"
    output.mkdir(parents=True, exist_ok=True)
    for todo_id, (responsibility, files) in TODO_CONTEXT.items():
        text = f"""TODO {todo_id}

RESPONSABILITÀ
{responsibility}

FILE MODIFICABILI
{chr(10).join(f'- {value}' for value in files)}

CONTESTO DALLA SPEC
{_relevant_context(todo_id, design)}

VINCOLI
- design hash: {design['design_sha256']}
- non modificare gli invarianti comuni;
- nessuna API o custom app;
- ogni errore di contratto deve fallire chiuso;
- non usare gli ID dei cinque dataset come regole;
- l'AI classifica evidenze ma non approva;
- i tool ammessi e i loro permessi sono quelli della sezione 4c della spec congelata.

RICHIESTA ALLA CHAT
Prima descrivi la conformità alla spec. Poi proponi una modifica limitata ai file indicati e
almeno un test mirato. Fermati su questo TODO: il passaggio successivo lo sceglie il
partecipante, dopo aver eseguito il test e averne riportato l'esito.
"""
        atomic_write_text(output / f"{todo_id}.txt", text)


def freeze_spec(
    participant_root: Path,
    docx_path: Path | None = None,
    *,
    frozen_at: str | None = None,
) -> dict[str, Any]:
    root = participant_root.resolve()
    docx = (docx_path or (root / DEFAULT_DOCX)).resolve()
    if not docx.is_relative_to(root):
        # La receipt registra il percorso relativo e il preflight lo riapre per il controllo
        # di drift: una spec fuori dalla cartella non sarebbe piu' ritrovabile.
        raise LabError(
            "spec_outside_root",
            f"La spec Word deve stare dentro la cartella del laboratorio: copia {docx.name} "
            "in templates/ e rilancia freeze-spec.",
        )
    controls = extract_docx_controls(docx)
    design_fields_hash = design_fields_sha256(controls)
    document_hash = sha256_file(docx)
    design = build_workflow_design(
        controls,
        source_docx_sha256=document_hash,
        design_fields_sha256=design_fields_hash,
    )
    timestamp = frozen_at or datetime.now(timezone.utc).isoformat()
    receipt = {
        "schema_version": "1.0",
        "kind": "spec_freeze_receipt",
        "status": "FROZEN",
        "spec_id": design["spec_id"],
        "frozen_at": timestamp,
        "source_docx": str(docx.relative_to(root).as_posix()),
        "source_docx_sha256_at_freeze": document_hash,
        "design_fields_sha256": design_fields_hash,
        "design_sha256": design["design_sha256"],
        "schema_path": "schemas/workflow_design.schema.json",
        "tag_count": len(controls),
        "design_tags": sorted(
            tag for tag in controls if tag.startswith("design.")
        ),
        "lab_record_tags": sorted(
            tag for tag in controls if tag.startswith("lab_record.")
        ),
        "human_review_required": True,
    }

    spec_dir = root / BUILD_SPEC
    ai_dir = root / BUILD_AI
    spec_dir.mkdir(parents=True, exist_ok=True)
    ai_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(spec_dir / "workflow_design.json", design)
    atomic_write_json(spec_dir / "spec_freeze_receipt.json", receipt)
    atomic_write_text(
        spec_dir / "workflow_design_summary.txt",
        _render_summary(design),
    )
    atomic_write_text(ai_dir / "ai_build_brief.txt", _render_ai_brief(design))
    _write_prompt_pack(root, design)
    fixture_dir = root / "tests_custom"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(
        fixture_dir / "generated_spec_fixture.json",
        {
            "spec_id": design["spec_id"],
            "design_sha256": design["design_sha256"],
            "selected_dimensions": design["selected_dimensions"],
            "test_hypotheses": design["test_hypotheses"],
            "human_review_required": True,
        },
    )
    atomic_write_text(
        fixture_dir / "SPEC_TEST_INSTRUCTIONS.txt",
        (
            "Aggiungi almeno un test che distingua il valore scelto dall'alternativa "
            "senza disattivare gli hard stop. Usa generated_spec_fixture.json come "
            "contratto: non contiene le decisioni attese dei cinque dataset. Il campo "
            "expected di ogni ipotesi è l'esito che hai fissato tu in sezione 7 prima di "
            "eseguire: il test lo verifica, non lo riscrive.\n"
        ),
    )
    reports_dir = root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    for template_name in ("break_report.md", "workflow_post_mortem.md"):
        template = root / "templates" / template_name
        report = reports_dir / template_name
        if template.is_file() and not report.exists():
            atomic_write_text(
                report,
                template.read_text(encoding="utf-8"),
            )
    return {
        "status": "READY_FOR_AI_BUILD",
        "spec_id": design["spec_id"],
        "design_sha256": design["design_sha256"],
        "design_fields": len(receipt["design_tags"]),
        "lab_record_fields": len(receipt["lab_record_tags"]),
        "outputs": {
            "design": str((spec_dir / "workflow_design.json").relative_to(root)),
            "receipt": str(
                (spec_dir / "spec_freeze_receipt.json").relative_to(root)
            ),
            "summary": str(
                (spec_dir / "workflow_design_summary.txt").relative_to(root)
            ),
            "ai_brief": str(
                (ai_dir / "ai_build_brief.txt").relative_to(root)
            ),
            "todo_prompt_pack": str(
                (ai_dir / "todo_prompt_pack").relative_to(root)
            ),
        },
        "human_review_required": True,
    }


def load_frozen_design(
    participant_root: Path,
    *,
    verify_docx: bool = True,
) -> dict[str, Any]:
    root = participant_root.resolve()
    design_path = root / BUILD_SPEC / "workflow_design.json"
    receipt_path = root / BUILD_SPEC / "spec_freeze_receipt.json"
    if not design_path.is_file() or not receipt_path.is_file():
        raise LabError(
            "spec_not_frozen",
            "Completa il DOCX ed esegui python runner.py freeze-spec.",
        )
    design = read_json(design_path)
    receipt = read_json(receipt_path)
    validate_workflow_design(design)
    expected_receipt_keys = {
        "schema_version",
        "kind",
        "status",
        "spec_id",
        "frozen_at",
        "source_docx",
        "source_docx_sha256_at_freeze",
        "design_fields_sha256",
        "design_sha256",
        "schema_path",
        "tag_count",
        "design_tags",
        "lab_record_tags",
        "human_review_required",
    }
    if set(receipt) != expected_receipt_keys:
        raise LabError(
            "invalid_freeze_receipt",
            "La receipt contiene campi mancanti o non ammessi.",
        )
    if (
        receipt.get("schema_version") != "1.0"
        or receipt.get("kind") != "spec_freeze_receipt"
        or receipt.get("status") != "FROZEN"
        or receipt.get("spec_id") != design["spec_id"]
        or receipt.get("design_sha256") != design["design_sha256"]
        or receipt.get("design_fields_sha256")
        != design["design_fields_sha256"]
        or receipt.get("source_docx_sha256_at_freeze")
        != design["source_docx_sha256"]
        or receipt.get("schema_path")
        != "schemas/workflow_design.schema.json"
        or receipt.get("tag_count")
        != len(receipt.get("design_tags", []))
        + len(receipt.get("lab_record_tags", []))
        or not all(
            str(tag).startswith("design.")
            for tag in receipt.get("design_tags", [])
        )
        or not all(
            str(tag).startswith("lab_record.")
            for tag in receipt.get("lab_record_tags", [])
        )
        or receipt.get("human_review_required") is not True
    ):
        raise LabError(
            "invalid_freeze_receipt",
            "Receipt e workflow design non sono coerenti.",
        )
    if verify_docx:
        source = root / receipt["source_docx"]
        current_controls = extract_docx_controls(source)
        current_hash = design_fields_sha256(current_controls)
        if current_hash != receipt["design_fields_sha256"]:
            raise LabError(
                "spec_drift",
                "Una scelta di progetto nel DOCX è cambiata dopo il freeze. "
                "Ripristina la spec oppure esegui un nuovo freeze motivato.",
            )
    return design


def freeze_status(participant_root: Path) -> dict[str, Any]:
    try:
        design = load_frozen_design(participant_root)
    except LabError as exc:
        return {"valid": False, "code": exc.code, "message": exc.message}
    return {
        "valid": True,
        "spec_id": design["spec_id"],
        "design_sha256": design["design_sha256"],
    }
