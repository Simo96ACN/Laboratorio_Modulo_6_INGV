from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from meridiano_lab import LabError, WorkflowLabService  # noqa: E402
from meridiano_lab.preflight import run_preflight  # noqa: E402
from meridiano_lab.spec_bridge import load_frozen_design  # noqa: E402
from workflow import create_participant_workflow  # noqa: E402


class CompletedBuildTests(unittest.TestCase):
    def test_no_todos_remain(self) -> None:
        result = run_preflight(ROOT)
        self.assertEqual(
            result["todo_count"],
            0,
            "Completa gli dodici punti numerati prima della baseline.",
        )

    def test_partial_ai_response_fails_closed(self) -> None:
        if run_preflight(ROOT)["todo_count"]:
            self.skipTest("Disponibile dopo il completamento degli dodici punti.")
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
            design = load_frozen_design(ROOT)
            service = WorkflowLabService(
                Path(temporary),
                create_participant_workflow(design),
                design,
            )
            view = service.init_run(
                ROOT / "case",
                ROOT / "workflow" / "prompts" / "classify_evidence.txt",
            )
            response = copy.deepcopy(view["response_template"])
            response["outputs"].pop()
            for row in response["outputs"]:
                row["label"] = "UNKNOWN"
                row["rationale"] = "Fixture di test incompleta."
            with self.assertRaises(LabError):
                service.import_response(view["state"]["run_id"], response)
            self.assertEqual(
                service.resume(view["state"]["run_id"])["state"]["status"],
                "WAITING_FOR_AI",
            )


if __name__ == "__main__":
    unittest.main()
