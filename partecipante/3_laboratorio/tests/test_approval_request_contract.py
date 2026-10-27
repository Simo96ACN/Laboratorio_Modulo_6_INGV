"""Contratto pubblico con identità sintetica estranea al caso del laboratorio."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from meridiano_lab.preflight import run_preflight
from meridiano_lab.spec_bridge import load_frozen_design
from workflow import create_participant_workflow


class ApprovalRequestContractTests(unittest.TestCase):
    def test_missing_roles_generate_tasks_and_confirmation_preserves_quality_failure(self):
        status = run_preflight(ROOT)
        if not status["spec"]["valid"] or status["todo_count"]:
            self.skipTest("Completa freeze e TODO prima del contratto di instradamento.")
        design = load_frozen_design(ROOT)
        if design["ai_delegation"]["approval_requests"] != "enabled":
            self.skipTest("Richieste di ruolo disabilitate nella spec.")
        dataset = "PUBLIC-SYNTHETIC-ROLE"
        normalized = {"dataset_ids": [dataset], "by_dataset": {dataset: {
            "registry": {"approvals": [], "current_version": {"version": "synthetic-1"}},
            "texts": [],
        }}, "evidence": [], "stats": {}}
        gates = {dataset: {name: {"result": "PASS", "reasons": [], "evidence_refs": []}
                          for name in ("metadata", "quality", "checksum", "license", "embargo", "formal_approval", "freshness")}}
        gates[dataset]["formal_approval"]["result"] = "UNKNOWN"
        ai = {dataset: {"label": "SAFE", "rationale": "Fixture sintetica del contratto.", "uncertainties": [], "evidence_refs": []}}
        workflow = create_participant_workflow(design)
        proposals = workflow.decide(deepcopy(gates), deepcopy(ai), deepcopy(normalized), design)
        self.assertEqual({row["scope"] for row in proposals[dataset]["approval_requests"]}, {"publication_owner", "publication_steward"})
        self.assertIn(proposals[dataset]["proposal"], {"TRATTIENI", "ESCALA"})
        normalized["by_dataset"][dataset]["registry"]["approvals"] = [
            {"scope": scope, "decision": "APPROVE", "decided_at": "2026-10-01T12:00:00+02:00"}
            for scope in ("publication_owner", "publication_steward")
        ]
        gates[dataset]["formal_approval"]["result"] = "PASS"
        gates[dataset]["quality"]["result"] = "FAIL"
        changed = workflow.decide(gates, ai, normalized, design)[dataset]
        self.assertEqual(changed["approval_requests"], [])
        self.assertIn(changed["proposal"], {"TRATTIENI", "ESCALA"})


if __name__ == "__main__":
    unittest.main()
