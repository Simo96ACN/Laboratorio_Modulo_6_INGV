"""Verifica del contratto compilato nel TODO-01, senza modello o soluzioni del caso."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from meridiano_lab.agent_config import load_agent_config
from meridiano_lab.spec_bridge import load_frozen_design, freeze_status


class AgentConfigurationTests(unittest.TestCase):
    def test_configuration_matches_frozen_spec(self):
        if not freeze_status(ROOT)["valid"]:
            self.skipTest("Prima compila e congela la spec.")
        if "[TODO-01]" in (ROOT / "workflow/agent_config.json").read_text(encoding="utf-8"):
            self.skipTest("Completa TODO-01, poi verifica la configurazione.")
        load_agent_config(ROOT, load_frozen_design(ROOT))


if __name__ == "__main__":
    unittest.main()
