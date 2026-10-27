"""Contratti pubblici: eseguire dopo la costruzione e prima di prepare-agent.

Le prove usano esclusivamente dataset sintetici, senza classificazioni del caso.
Lo starter resta da implementare: questi contratti non completano il TODO-08.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from meridiano_lab.agent_readiness import run_public_validation_probes  # noqa: E402
from meridiano_lab.preflight import run_preflight  # noqa: E402
from meridiano_lab.spec_bridge import load_frozen_design  # noqa: E402
from workflow import create_participant_workflow  # noqa: E402


class AgentValidationContractTests(unittest.TestCase):
    def test_public_validation_contract(self) -> None:
        readiness = run_preflight(ROOT)
        if not readiness["spec"]["valid"] or readiness["todo_count"]:
            self.skipTest("Contratti TODO-08: eseguire dopo freeze e costruzione degli dodici TODO.")
        design = load_frozen_design(ROOT)
        report = run_public_validation_probes(
            create_participant_workflow(design), design, observed_root=ROOT / "workspace",
        )
        self.assertEqual(report["status"], "PASS")
        self.assertIn("positive", report["probes"])
        self.assertIn("missing_dataset", report["probes"])
        self.assertIn("duplicate_dataset", report["probes"])
        self.assertIn("cross_dataset_reference", report["probes"])
        self.assertIn("insufficient_support", report["probes"])
        self.assertIn("repeat_without_mutation", report["probes"])


if __name__ == "__main__":
    unittest.main()
