import asyncio
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server import mcp_server as server  # noqa: E402


class ExistingInterfaceWrapperTests(unittest.TestCase):
    def test_health_check_is_public_and_secret_free(self):
        response = asyncio.run(server.health_check(None))
        payload = json.loads(response.body)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["mcp_path"], "/mcp")
        self.assertGreaterEqual(payload["tool_count"], 24)
        self.assertIsInstance(payload["credentials_configured"], bool)
        self.assertEqual(payload["ready"], payload["credentials_configured"])
        self.assertNotIn("secret", response.body.decode("utf-8").lower())

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
        self.assertEqual(result["error"], "配置缺失")
        self.assertEqual(result["field"], "INTEGRATOR_ID")
        self.assertEqual(result["product_id"], "product-id")

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
        self.assertEqual(server.PRODUCT_IDS["policy_search"], "66c702b725f04ab44cd24ceb")

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
        self.assertEqual(result["error"], "参数错误")
        self.assertEqual(result["field"], "biddingType")
        self.assertEqual(result["product_key"], "bid_search")
        self.assertIn("合法JSON", result["message"])

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

    def test_policy_search_normalizes_simple_region(self):
        captured = {}
        original = server.call_api

        def fake_call_api(product_id, params=None):
            captured["product_id"] = product_id
            captured["params"] = params or {}
            return {"resultList": [], "total": 0}

        try:
            server.call_api = fake_call_api
            result = server.policy_bigdata_policy_search(
                matchKeyword="智能网联汽车",
                address="广东省,深圳市",
                pageSize=100,
            )
        finally:
            server.call_api = original

        self.assertEqual(result, {"resultList": [], "total": 0})
        self.assertEqual(captured["product_id"], server.PRODUCT_IDS["policy_search"])
        self.assertEqual(captured["params"]["address"], '[["广东省", "深圳市"]]')
        self.assertEqual(captured["params"]["pageSize"], 50)

    def test_list_tools_cap_page_size_to_upstream_limit(self):
        captured = {}
        original = server.call_api

        def fake_call_api(product_id, params=None):
            captured["product_id"] = product_id
            captured["params"] = params or {}
            return {"ok": True}

        try:
            server.call_api = fake_call_api
            result = server.advanced_filter_get_enterprise_list(name="机器人", pageIndex=2, pageSize=100)
        finally:
            server.call_api = original

        self.assertEqual(result, {"ok": True})
        self.assertEqual(captured["params"]["pageIndex"], 2)
        self.assertEqual(captured["params"]["pageSize"], 10)
        self.assertNotIn("product_id", captured["params"])

    def test_invalid_pagination_is_actionable_and_does_not_call_upstream(self):
        original = server.call_api
        try:
            server.call_api = lambda *args, **kwargs: self.fail("upstream must not be called")
            result = server.enterprise_get_keyword_search("机器人", pageIndex=0, pageSize=10)
        finally:
            server.call_api = original

        self.assertEqual(result["error"], "参数错误")
        self.assertEqual(result["field"], "pageIndex")
        self.assertEqual(result["product_key"], "enterprise_keyword_search")

    def test_signature_is_stable_and_secret_is_not_returned(self):
        params = {"product_id": "p", "secret_id": "s", "params": "{}"}
        first = server._signature(params, "private-key")
        second = server._signature(dict(reversed(list(params.items()))), "private-key")
        self.assertEqual(first, second)
        self.assertNotIn("private-key", first)

    def test_readme_documents_macos_linux_and_windows_commands(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("macOS / Linux", readme)
        self.assertIn("Windows PowerShell", readme)
        self.assertIn("Activate.ps1", readme)
        self.assertIn("Invoke-RestMethod", readme)
        self.assertIn("Get-Command handaas-industry-chain-mcp", readme)
        self.assertNotIn("{workdir}", readme)

    def test_empty_data_is_preserved(self):
        original_credentials = (server.INTEGRATOR_ID, server.SECRET_ID, server.SECRET_KEY)
        original_post = server.requests.post

        class FakeResponse:
            status_code = 200

            @staticmethod
            def json():
                return {"data": []}

        try:
            server.INTEGRATOR_ID = "integrator"
            server.SECRET_ID = "secret-id"
            server.SECRET_KEY = "secret-key"
            server.requests.post = lambda *args, **kwargs: FakeResponse()
            result = server.call_api(server.PRODUCT_IDS["policy_search"], {})
        finally:
            server.INTEGRATOR_ID, server.SECRET_ID, server.SECRET_KEY = original_credentials
            server.requests.post = original_post

        self.assertEqual(result, [])

    def test_http_error_is_structured_and_identifies_product(self):
        original_credentials = (server.INTEGRATOR_ID, server.SECRET_ID, server.SECRET_KEY)
        original_post = server.requests.post

        class FakeResponse:
            status_code = 503

        try:
            server.INTEGRATOR_ID = "integrator"
            server.SECRET_ID = "secret-id"
            server.SECRET_KEY = "secret-key"
            server.requests.post = lambda *args, **kwargs: FakeResponse()
            result = server.call_api(server.PRODUCT_IDS["policy_search"], {})
        finally:
            server.INTEGRATOR_ID, server.SECRET_ID, server.SECRET_KEY = original_credentials
            server.requests.post = original_post

        self.assertEqual(result["error"], "接口调用失败")
        self.assertEqual(result["status_code"], 503)
        self.assertEqual(result["product_key"], "policy_search")


if __name__ == "__main__":
    unittest.main()
