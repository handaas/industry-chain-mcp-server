import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server.mcp_server import build_condition_group, industry_chain_build_search_condition, redact_url


class ConditionTests(unittest.TestCase):
    def test_build_condition_contains_business_and_strong_groups(self):
        result = industry_chain_build_search_condition(
            chain="低空经济",
            node="eVTOL整机制造",
            path="低空经济产业链>航空器制造>eVTOL整机制造",
            keywords=["适航取证"],
        )
        self.assertEqual(result["chain"], "低空经济")
        condition = result["condition"]
        self.assertIn("must", condition)
        serialized = str(condition)
        self.assertIn("eVTOL", serialized)
        self.assertIn("适航", serialized)

    def test_redact_url_token(self):
        self.assertNotIn("secret-token", redact_url("https://example.com/mcp?token=secret-token&x=1"))

    def test_condition_group_has_noise_exclusions(self):
        condition = build_condition_group("机器人", "机器人控制系统", exclude=["玩具"])
        serialized = str(condition)
        self.assertIn("must_not", condition)
        self.assertIn("玩具", serialized)


if __name__ == "__main__":
    unittest.main()
