import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server import mcp_server as server


class ExistingInterfaceWrapperTests(unittest.TestCase):
    def test_missing_credentials_returns_actionable_error(self):
        original = (server.INTEGRATOR_ID, server.SECRET_ID, server.SECRET_KEY)
        try:
            server.INTEGRATOR_ID = None
            server.SECRET_ID = None
            server.SECRET_KEY = None
            result = server.call_api("product-id", {})
        finally:
            server.INTEGRATOR_ID, server.SECRET_ID, server.SECRET_KEY = original
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

    def test_product_missing_response_includes_product_identity(self):
        original_credentials = (server.INTEGRATOR_ID, server.SECRET_ID, server.SECRET_KEY)
        original_post = server.requests.post

        class FakeResponse:
            status_code = 200

            @staticmethod
            def json():
                return {"msgCN": "产品不存在"}

        try:
            server.INTEGRATOR_ID = "integrator"
            server.SECRET_ID = "secret-id"
            server.SECRET_KEY = "secret-key"
            server.requests.post = lambda *args, **kwargs: FakeResponse()
            result = server.call_api(server.PRODUCT_IDS["enterprise_business_info"], {"matchKeyword": "广州探迹科技有限公司"})
        finally:
            server.INTEGRATOR_ID, server.SECRET_ID, server.SECRET_KEY = original_credentials
            server.requests.post = original_post

        self.assertEqual(result["error"], "产品不存在")
        self.assertEqual(result["product_key"], "enterprise_business_info")
        self.assertEqual(result["product_name"], "企业业务信息查询")
        self.assertEqual(result["product_id"], "66e55613ae988a28c6db9259")

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
        self.assertEqual(result, {"error": "biddingType格式错误，请输入合法JSON字符串或JSON数组"})

    def test_bid_search_accepts_array_params_from_mcp_clients(self):
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
                biddingType=["招标公告"],
                biddingRegion=[["广东省"]],
                pageIndex=1,
                pageSize=3,
            )
        finally:
            server.call_api = original

        self.assertEqual(result, {"ok": True})
        self.assertEqual(captured["params"]["biddingType"], '["招标公告"]')
        self.assertEqual(captured["params"]["biddingRegion"], '[["广东省"]]')


if __name__ == "__main__":
    unittest.main()
