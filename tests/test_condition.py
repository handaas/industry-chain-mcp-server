import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server import mcp_server as server


class ExistingInterfaceWrapperTests(unittest.TestCase):
    def test_missing_credentials_returns_actionable_error(self):
        result = server.call_api("product-id", {})
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)

    def test_drop_none_keeps_falsey_values(self):
        self.assertEqual(server._drop_none({"a": None, "b": 0, "c": ""}), {"b": 0, "c": ""})

    def test_no_custom_workflow_tool_functions_are_registered(self):
        custom_names = [
            "industry_chain_health_check",
            "industry_chain_build_search_condition",
            "industry_chain_search_enterprises",
            "industry_chain_evidence_call",
            "industry_chain_link_enterprises",
        ]
        for name in custom_names:
            self.assertFalse(hasattr(server, name), name)

    def test_existing_handaas_product_ids_present(self):
        self.assertEqual(server.PRODUCT_IDS["enterprise_keyword_search"], "675cea1f0e009a9ea37edaa1")
        self.assertEqual(server.PRODUCT_IDS["supply_downstream_products"], "68c02b268cc760ff46ee93c3")
        self.assertEqual(server.PRODUCT_IDS["patent_stats"], "66d5b7df537c3f61d646c230")

    def test_bid_search_keeps_json_string_params(self):
        captured = {}
        original = server.call_api

        def fake_call_api(product_id, params=None):
            captured["product_id"] = product_id
            captured["params"] = params or {}
            return {"ok": True}

        try:
            server.call_api = fake_call_api
            result = server.bid_bigdata_bid_search(
                matchKeyword="无人机",
                biddingType='["招标公告"]',
                biddingRegion='[["广东省"]]',
                pageIndex=1,
                pageSize=3,
            )
        finally:
            server.call_api = original

        self.assertEqual(result, {"ok": True})
        self.assertEqual(captured["product_id"], server.PRODUCT_IDS["bid_search"])
        self.assertEqual(captured["params"]["biddingType"], '["招标公告"]')
        self.assertEqual(captured["params"]["biddingRegion"], '[["广东省"]]')

    def test_bid_search_rejects_invalid_json_string_params(self):
        result = server.bid_bigdata_bid_search(matchKeyword="无人机", biddingType="招标公告")
        self.assertEqual(result, {"error": "biddingType格式错误，请输入合法JSON字符串"})


if __name__ == "__main__":
    unittest.main()
