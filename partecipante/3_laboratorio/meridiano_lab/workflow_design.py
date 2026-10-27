"""Contratto interno generato dalla spec Word.

Il partecipante non modifica questo modulo né il JSON risultante a mano.
"""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from .errors import LabError
from .utils import sha256_value


# 1.2 (25 settembre 2026): aggiunge design.tools, la sezione 4c della spec Word.
# Il bump e' deliberato: `validate_workflow_design` confronta `schema_version` con
# questa costante, quindi un design congelato con la 1.1 fallisce in modo leggibile
# invece di passare a meta'.
# 1.3 (2 ottobre 2026): ogni riga di test porta `expected`, l'esito atteso della
# sezione 7. Sta dentro il freeze ed e' obbligatorio: fissare l'atteso prima di
# eseguire e' il punto della domanda 7.2 della checklist, e un atteso fuori
# dall'hash si potrebbe correggere dopo aver visto il risultato.
# 1.4: modalità AI esplicita, congelata; nessuna deduzione dal testo libero.
DESIGN_SCHEMA_VERSION = "1.4"

TEST_FIELDS = ("challenge", "seed", "mutation", "invariant", "expected")

TOOL_PERMISSIONS = ("read", "propose", "write")

INVARIANTS = (
    "synthetic_data_only",
    "offline_runtime",
    "no_api_keys",
    "ai_cannot_approve",
    "hard_stops_not_configurable",
    "simulated_file_effects_only",
    "untrusted_text_not_authoritative",
    "evidence_refs_required",
    "human_approval_required",
    "idempotent_replay",
    "no_baseline_id_branching",
)

BEHAVIOR_VALUES: dict[str, tuple[str, ...]] = {
    "minimum_independent_evidence": ("1", "2", "3"),
    "staleness_hours": ("24", "72", "168", "336", "672"),
    "unknown_strategy": ("TRATTIENI", "ESCALA"),
    "conflict_strategy": ("TRATTIENI", "ESCALA"),
    "conservative_condition": ("NESSUNA", "RICHIEDI_EVIDENZA"),
}

SECONDARY_VALUES: dict[str, tuple[str, ...]] = {
    "trace_level": ("essential", "extended"),
    "review_mode": ("file", "interattiva", "entrambe"),
    "ai_validation": ("standard", "strict"),
    "report_style": ("standard", "comparative"),
}

DEFAULT_POLICY: dict[str, Any] = {
    "minimum_independent_evidence": 1,
    "staleness_hours": 168,
    "unknown_strategy": "TRATTIENI",
    "conflict_strategy": "ESCALA",
    "conservative_condition": "NESSUNA",
}

DEFAULT_INTERACTION: dict[str, str] = {
    "trace_level": "essential",
    "review_mode": "file",
    "ai_validation": "standard",
    "report_style": "standard",
}


def _required(controls: dict[str, str], tag: str) -> str:
    value = controls.get(tag, "").strip()
    if not value:
        raise LabError(
            "spec_required_field",
            f"Completa il campo Word collegato a {tag}.",
        )
    return value


def _rows(
    controls: dict[str, str],
    prefix: str,
    fields: tuple[str, ...],
    *,
    first_required: bool,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index in range(1, 20):
        values = {
            field: controls.get(f"{prefix}.{index}.{field}", "").strip()
            for field in fields
        }
        if not any(values.values()):
            continue
        if not all(values.values()):
            missing = [field for field, value in values.items() if not value]
            hint = (
                " L'esito atteso si scrive prima di eseguire il test."
                if "expected" in missing
                else ""
            )
            raise LabError(
                "spec_partial_row",
                f"Riga incompleta in {prefix}.{index}: {', '.join(missing)}.{hint}",
            )
        values["row_id"] = str(index)
        rows.append(values)
    if first_required and not rows:
        raise LabError(
            "spec_required_row",
            f"Compila almeno una riga nella sezione {prefix}.",
        )
    return rows


def _normalize_choice(dimension: str, raw: str) -> str:
    allowed = BEHAVIOR_VALUES.get(dimension) or SECONDARY_VALUES.get(dimension)
    if not allowed:
        raise LabError(
            "spec_unknown_dimension",
            f"Dimensione non ammessa nella sezione 6 (Parametri del workflow): {dimension}. "
            "Usa i nomi elencati nel mandato.",
        )
    value = raw.strip()
    if dimension in {
        "unknown_strategy",
        "conflict_strategy",
        "conservative_condition",
    }:
        value = value.upper()
    else:
        value = value.lower()
    if value not in allowed:
        raise LabError(
            "spec_invalid_choice",
            f"Valore {raw!r} non ammesso per {dimension}: {', '.join(allowed)}.",
        )
    return value


def _personalization(
    controls: dict[str, str],
) -> tuple[list[dict[str, str]], dict[str, Any], dict[str, str]]:
    selected: list[dict[str, str]] = []
    policy = deepcopy(DEFAULT_POLICY)
    interaction = deepcopy(DEFAULT_INTERACTION)
    seen: set[str] = set()
    for index in range(1, 4):
        prefix = f"design.personalization.{index}"
        dimension = controls.get(f"{prefix}.dimension", "").strip()
        values = {
            "dimension": dimension,
            "value": controls.get(f"{prefix}.value", "").strip(),
            "alternative": controls.get(f"{prefix}.alternative", "").strip(),
            "rationale": controls.get(f"{prefix}.rationale", "").strip(),
            "discriminating_case": controls.get(
                f"{prefix}.discriminating_case", ""
            ).strip(),
        }
        if index == 3 and not any(values.values()):
            continue
        if not all(values.values()):
            missing = [field for field, value in values.items() if not value]
            raise LabError(
                "spec_partial_personalization",
                f"Completa il parametro {index} della sezione 6: {', '.join(missing)}.",
            )
        if dimension in seen:
            raise LabError(
                "spec_duplicate_dimension",
                f"La dimensione {dimension} è stata scelta più di una volta.",
            )
        if index == 1 and dimension not in BEHAVIOR_VALUES:
            raise LabError(
                "spec_behavior_required",
                "Il parametro 1 della sezione 6 deve cambiare il comportamento: "
                "scegli una dimensione di comportamento del mandato.",
            )
        if index == 2 and dimension not in SECONDARY_VALUES:
            raise LabError(
                "spec_interaction_required",
                "Il parametro 2 della sezione 6 deve riguardare interazione o osservabilità.",
            )
        value = _normalize_choice(dimension, values["value"])
        alternative = _normalize_choice(dimension, values["alternative"])
        if value == alternative:
            raise LabError(
                "spec_same_alternative",
                f"Per {dimension}, valore scelto e alternativa devono essere diversi.",
            )
        category = (
            "behavior" if dimension in BEHAVIOR_VALUES else "interaction"
        )
        normalized = {
            **values,
            "value": value,
            "alternative": alternative,
            "category": category,
        }
        selected.append(normalized)
        seen.add(dimension)
        if category == "behavior":
            policy[dimension] = (
                int(value)
                if dimension in {"minimum_independent_evidence", "staleness_hours"}
                else value
            )
        else:
            interaction[dimension] = value
    return selected, policy, interaction


def build_workflow_design(
    controls: dict[str, str],
    *,
    source_docx_sha256: str,
    design_fields_sha256: str,
) -> dict[str, Any]:
    """Converte i campi Word già puliti nel contratto runtime."""

    actors = _rows(
        controls,
        "design.mandate.actors",
        ("subject", "can_confirm", "cannot_decide"),
        first_required=True,
    )
    sources = _rows(
        controls,
        "design.authority.sources",
        ("source_type", "facts", "authority", "limits", "validity"),
        first_required=True,
    )
    decisions = _rows(
        controls,
        "design.decisions",
        ("decision", "owner", "inputs", "output", "stop"),
        first_required=True,
    )
    for row in decisions:
        if row["owner"] not in {"CODICE", "AI", "PERSONA"}:
            raise LabError(
                "spec_invalid_decision_owner",
                f"Responsabile non ammesso nella decisione {row['row_id']}.",
            )
    states = _rows(
        controls,
        "design.states",
        ("state", "input", "output", "transition", "error"),
        first_required=True,
    )
    touchpoints = _rows(
        controls,
        "design.interaction.touchpoints",
        ("moment", "surface", "human_action", "structured_data", "safe_failure"),
        first_required=True,
    )
    tests = _rows(
        controls,
        "design.tests",
        TEST_FIELDS,
        first_required=True,
    )
    exceptions = _rows(
        controls,
        "design.exceptions",
        ("failure", "fallback", "owner"),
        first_required=True,
    )
    tools = _rows(
        controls,
        "design.tools",
        ("name", "input", "effect", "permission", "errors", "evidence"),
        first_required=True,
    )
    for row in tools:
        permission = row["permission"].strip().lower()
        if permission not in TOOL_PERMISSIONS:
            raise LabError(
                "spec_invalid_tool_permission",
                f"Permesso non ammesso nel tool {row['row_id']}: "
                f"scegli fra {', '.join(TOOL_PERMISSIONS)}.",
            )
        row["permission"] = permission
    selected, policy, interaction = _personalization(controls)

    design: dict[str, Any] = {
        "schema_version": DESIGN_SCHEMA_VERSION,
        "kind": "workflow_design",
        "identity": {
            "participant": _required(controls, "design.identity.participant"),
            "group": _required(controls, "design.identity.group"),
            "date": controls.get("design.identity.date", "").strip(),
            "workflow_name": _required(
                controls, "design.identity.workflow_name"
            ),
            "spec_version": _required(
                controls, "design.identity.spec_version"
            ),
        },
        "mandate": {
            "outcome": _required(controls, "design.mandate.outcome"),
            "out_of_scope": _required(
                controls, "design.mandate.out_of_scope"
            ),
            "actors": actors,
        },
        "exception_map": exceptions,
        "authority_map": {
            "sources": sources,
            "conflict_rule": _required(
                controls, "design.authority.conflict_rule"
            ),
        },
        "decision_map": decisions,
        "tools": tools,
        "ai_delegation": {
            "execution_mode": _required(controls, "design.interaction.execution_mode").lower(),
            "approval_requests": _required(controls, "design.interaction.approval_requests").lower(),
            "ai_decisions": [
                row["decision"] for row in decisions if row["owner"] == "AI"
            ],
            "always_human": _required(
                controls, "design.decisions.always_human"
            ),
            "may_approve": False,
        },
        "states": {
            "flow": states,
            "automatic_identifiers": _required(
                controls, "design.states.automatic_identifiers"
            ),
        },
        "policy_choices": policy,
        "interaction_policy": {
            **interaction,
            "accessibility": _required(
                controls, "design.interaction.accessibility"
            ),
            "touchpoints": touchpoints,
        },
        "selected_dimensions": selected,
        "test_hypotheses": tests,
        "invariants": list(INVARIANTS),
        "source_docx_sha256": source_docx_sha256,
        "design_fields_sha256": design_fields_sha256,
        "human_review_required": True,
    }
    design["spec_id"] = f"SPEC-{design_fields_sha256[:16].upper()}"
    design["design_sha256"] = sha256_value(design)
    validate_workflow_design(design)
    return design


def validate_workflow_design(design: dict[str, Any]) -> None:
    def exact_keys(
        value: Any,
        expected: set[str],
        context: str,
    ) -> None:
        if not isinstance(value, dict):
            raise LabError(
                "invalid_design",
                f"{context} deve essere un oggetto.",
            )
        observed = set(value)
        if observed != expected:
            missing = sorted(expected - observed)
            unknown = sorted(observed - expected)
            details: list[str] = []
            if missing:
                details.append(f"mancanti: {', '.join(missing)}")
            if unknown:
                details.append(f"non ammesse: {', '.join(unknown)}")
            raise LabError(
                "invalid_design_keys",
                f"Chiavi non valide in {context} ({'; '.join(details)}).",
            )

    if design.get("kind") != "workflow_design":
        raise LabError("invalid_design", "kind workflow_design mancante.")
    if design.get("schema_version") != DESIGN_SCHEMA_VERSION:
        raise LabError("invalid_design", "Versione del design non supportata.")
    exact_keys(
        design,
        {
            "schema_version",
            "kind",
            "spec_id",
            "identity",
            "mandate",
            "exception_map",
            "authority_map",
            "decision_map",
            "tools",
            "ai_delegation",
            "states",
            "policy_choices",
            "interaction_policy",
            "selected_dimensions",
            "test_hypotheses",
            "invariants",
            "source_docx_sha256",
            "design_fields_sha256",
            "design_sha256",
            "human_review_required",
        },
        "workflow_design",
    )
    exact_keys(
        design["identity"],
        {"participant", "group", "date", "workflow_name", "spec_version"},
        "identity",
    )
    exact_keys(
        design["mandate"],
        {"outcome", "out_of_scope", "actors"},
        "mandate",
    )
    for row in design["mandate"]["actors"]:
        exact_keys(
            row,
            {"subject", "can_confirm", "cannot_decide", "row_id"},
            "mandate.actors",
        )
    if not design.get("exception_map"):
        raise LabError("spec_required_row", "Compila almeno una riga nella exception map.")
    for row in design["exception_map"]:
        exact_keys(
            row,
            {"failure", "fallback", "owner", "row_id"},
            "exception_map",
        )
    exact_keys(
        design["authority_map"],
        {"sources", "conflict_rule"},
        "authority_map",
    )
    for row in design["authority_map"]["sources"]:
        exact_keys(
            row,
            {
                "source_type",
                "facts",
                "authority",
                "limits",
                "validity",
                "row_id",
            },
            "authority_map.sources",
        )
    for row in design["decision_map"]:
        exact_keys(
            row,
            {"decision", "owner", "inputs", "output", "stop", "row_id"},
            "decision_map",
        )
    if not design.get("tools"):
        raise LabError(
            "spec_required_row",
            "Compila almeno una riga nello schema dei tool (sezione 4c).",
        )
    for row in design["tools"]:
        exact_keys(
            row,
            {
                "name",
                "input",
                "effect",
                "permission",
                "errors",
                "evidence",
                "row_id",
            },
            "tools",
        )
        if row["permission"] not in TOOL_PERMISSIONS:
            raise LabError(
                "invalid_design_choice",
                f"Permesso non ammesso nel tool {row['row_id']}: {row['permission']}.",
            )
    exact_keys(
        design["ai_delegation"],
        {"ai_decisions", "always_human", "may_approve", "execution_mode", "approval_requests"},
        "ai_delegation",
    )
    if design["ai_delegation"]["approval_requests"] not in {"enabled", "disabled"}:
        raise LabError("spec_approval_requests", "Sezione 5: scegli enabled o disabled per le richieste simulate ai ruoli.")
    if design["ai_delegation"]["execution_mode"] not in {"agent", "manual"}:
        raise LabError("spec_execution_mode", "Sezione 5: scegli agent oppure manual; il testo libero non configura il nodo.")
    exact_keys(
        design["states"],
        {"flow", "automatic_identifiers"},
        "states",
    )
    for row in design["states"]["flow"]:
        exact_keys(
            row,
            {
                "state",
                "input",
                "output",
                "transition",
                "error",
                "row_id",
            },
            "states.flow",
        )
    exact_keys(
        design["policy_choices"],
        set(DEFAULT_POLICY),
        "policy_choices",
    )
    exact_keys(
        design["interaction_policy"],
        {
            *DEFAULT_INTERACTION,
            "accessibility",
            "touchpoints",
        },
        "interaction_policy",
    )
    for row in design["interaction_policy"]["touchpoints"]:
        exact_keys(
            row,
            {
                "moment",
                "surface",
                "human_action",
                "structured_data",
                "safe_failure",
                "row_id",
            },
            "interaction_policy.touchpoints",
        )
    for row in design["selected_dimensions"]:
        exact_keys(
            row,
            {
                "dimension",
                "value",
                "alternative",
                "rationale",
                "discriminating_case",
                "category",
            },
            "selected_dimensions",
        )
    for row in design["test_hypotheses"]:
        exact_keys(
            row,
            {*TEST_FIELDS, "row_id"},
            "test_hypotheses",
        )
        if not all(str(row[field]).strip() for field in TEST_FIELDS):
            raise LabError(
                "invalid_design",
                f"Ipotesi di test {row['row_id']} incompleta: "
                "servono tutti i campi, esito atteso compreso.",
            )
    for dimension, allowed in BEHAVIOR_VALUES.items():
        observed = str(design["policy_choices"][dimension])
        if observed not in allowed:
            raise LabError(
                "invalid_design_choice",
                f"Valore non ammesso per {dimension}: {observed}.",
            )
    for dimension, allowed in SECONDARY_VALUES.items():
        observed = str(design["interaction_policy"][dimension])
        if observed not in allowed:
            raise LabError(
                "invalid_design_choice",
                f"Valore non ammesso per {dimension}: {observed}.",
            )
    if not 2 <= len(design["selected_dimensions"]) <= 3:
        raise LabError(
            "invalid_design",
            "Sono richieste due o tre personalizzazioni.",
        )
    selected_dimensions: set[str] = set()
    categories: set[str] = set()
    for row in design["selected_dimensions"]:
        dimension = row["dimension"]
        if dimension in selected_dimensions:
            raise LabError(
                "invalid_design_choice",
                f"Dimensione duplicata: {dimension}.",
            )
        selected_dimensions.add(dimension)
        expected_category = (
            "behavior"
            if dimension in BEHAVIOR_VALUES
            else "interaction"
            if dimension in SECONDARY_VALUES
            else ""
        )
        if not expected_category or row["category"] != expected_category:
            raise LabError(
                "invalid_design_choice",
                f"Categoria non coerente per {dimension}.",
            )
        categories.add(expected_category)
        selected = _normalize_choice(dimension, row["value"])
        alternative = _normalize_choice(dimension, row["alternative"])
        if selected == alternative:
            raise LabError(
                "invalid_design_choice",
                f"Valore e alternativa coincidono per {dimension}.",
            )
        effective = (
            design["policy_choices"][dimension]
            if expected_category == "behavior"
            else design["interaction_policy"][dimension]
        )
        if str(effective) != selected:
            raise LabError(
                "invalid_design_choice",
                f"La scelta {dimension} non coincide con la policy effettiva.",
            )
    if categories != {"behavior", "interaction"}:
        raise LabError(
            "invalid_design_choice",
            "Serve almeno una scelta comportamentale e una di interazione.",
        )
    if (
        design["ai_delegation"]["may_approve"] is not False
        or design["human_review_required"] is not True
    ):
        raise LabError(
            "invariant_drift",
            "La spec non può autorizzare l'AI o rimuovere la review umana.",
        )
    for key in (
        "source_docx_sha256",
        "design_fields_sha256",
        "design_sha256",
    ):
        if not re.fullmatch(r"[a-f0-9]{64}", str(design[key])):
            raise LabError(
                "invalid_design",
                f"Hash non valido: {key}.",
            )
    for key in (
        "spec_id",
        "identity",
        "mandate",
        "authority_map",
        "decision_map",
        "tools",
        "policy_choices",
        "interaction_policy",
        "selected_dimensions",
        "test_hypotheses",
        "invariants",
        "source_docx_sha256",
        "design_fields_sha256",
        "design_sha256",
    ):
        if key not in design:
            raise LabError("invalid_design", f"Campo design mancante: {key}.")
    if tuple(design["invariants"]) != INVARIANTS:
        raise LabError(
            "invariant_drift",
            "Gli invarianti comuni non possono essere modificati dalla spec.",
        )
    candidate = deepcopy(design)
    recorded = candidate.pop("design_sha256")
    if sha256_value(candidate) != recorded:
        raise LabError(
            "design_hash_mismatch",
            "Il workflow design è stato modificato dopo il freeze.",
        )


def choice_summary(design: dict[str, Any]) -> list[str]:
    return [
        (
            f"{row['dimension']} = {row['value']} "
            f"(alternativa: {row['alternative']})"
        )
        for row in design["selected_dimensions"]
    ]
