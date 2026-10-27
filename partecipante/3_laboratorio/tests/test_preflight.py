from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from meridiano_lab.preflight import run_preflight  # noqa: E402


class PreflightTests(unittest.TestCase):
    def test_case_is_synthetic_and_complete(self) -> None:
        result = run_preflight(ROOT)
        self.assertTrue(result["python_supported"])
        self.assertTrue(result["simulated_effects_only"])
        self.assertTrue(result["human_review_required"])
        self.assertEqual(len(result["datasets"]), 5)
        self.assertGreaterEqual(result["source_counts"]["quality_events"], 20)
        self.assertGreaterEqual(result["source_counts"]["text_evidence"], 15)
        self.assertEqual(result["forbidden_import_hits"], [])

    def test_schemas_are_valid_json(self) -> None:
        schemas = sorted((ROOT / "schemas").glob("*.schema.json"))
        self.assertGreaterEqual(len(schemas), 10)
        for path in schemas:
            with self.subTest(path=path.name):
                value = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(value["$schema"], "https://json-schema.org/draft/2020-12/schema")


if __name__ == "__main__":
    unittest.main()
