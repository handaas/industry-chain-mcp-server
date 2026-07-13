import asyncio
import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server import mcp_server as server  # noqa: E402
from server import high_screen  # noqa: E402


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

    def test_advanced_filter_list_tool_describes_and_accepts_address_forms(self):
        tools = asyncio.run(server.mcp.list_tools())
        tool = next(item for item in tools if item.name == "advanced_filter_get_enterprise_list")

        self.assertIn('address="广东省"', tool.description)
        self.assertIn('[["广东省"]]', tool.description)
        self.assertIn('不能只写“深圳市”', tool.description)
        self.assertIn("businessKeywords", tool.description)
        self.assertIn("businessTags", tool.description)
        self.assertIn("handaas://high-screen/guide", tool.description)
        address_types = {
            option.get("type")
            for option in tool.inputSchema["properties"]["address"]["anyOf"]
        }
        self.assertIn("string", address_types)
        self.assertIn("array", address_types)

    def test_high_screen_resources_expose_catalog_field_usage_and_options(self):
        resources = asyncio.run(server.mcp.list_resources())
        resource_uris = {str(resource.uri) for resource in resources}
        self.assertIn("handaas://high-screen/guide", resource_uris)
        self.assertIn("handaas://high-screen/fields", resource_uris)

        templates = asyncio.run(server.mcp.list_resource_templates())
        template_uris = {template.uriTemplate for template in templates}
        self.assertIn("handaas://high-screen/fields/{field}", template_uris)
        self.assertIn("handaas://high-screen/options/{source}", template_uris)

        guide_contents = asyncio.run(server.mcp.read_resource("handaas://high-screen/guide"))
        guide = json.loads(guide_contents[0].content)
        common_fields = {
            item["field"]
            for group in guide["common_dimensions"]
            for item in group["fields"]
        }
        self.assertIn("businessKeywords", common_fields)
        self.assertIn("businessTags", common_fields)
        self.assertIn("ecShopProducts", common_fields)
        for group in guide["common_dimensions"]:
            for item in group["fields"]:
                normalized = high_screen.normalize_filter({"must": [item["example_condition"]]})
                self.assertIsInstance(normalized, str)
        for condition in guide["query_examples"].values():
            self.assertIsInstance(high_screen.normalize_filter(condition), str)

        catalog_contents = asyncio.run(server.mcp.read_resource("handaas://high-screen/fields"))
        catalog = json.loads(catalog_contents[0].content)
        self.assertEqual(catalog["field_count"], 369)
        self.assertTrue(any(item["field"] == "name" for item in catalog["fields"]))

        detail_contents = asyncio.run(
            server.mcp.read_resource("handaas://high-screen/fields/businessTags")
        )
        detail = json.loads(detail_contents[0].content)
        self.assertEqual(detail["label"], "主营业务")
        self.assertEqual(detail["operators"], ["in", "nin"])
        self.assertEqual(
            detail["example_condition"],
            {"businessTags": [{"in": ["无人机"]}]},
        )

        option_contents = asyncio.run(
            server.mcp.read_resource("handaas://high-screen/options/operStatus_v2")
        )
        option_detail = json.loads(option_contents[0].content)
        self.assertIn(["营业"], option_detail["paths"])

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
        self.assertEqual(server.PRODUCT_IDS["advanced_filter_condition_list"], "690dcb1b9c9dc8d0ff3c40eb")
        self.assertEqual(server.PRODUCT_IDS["patent_stats"], "66d5b7df537c3f61d646c230")
        self.assertEqual(server.PRODUCT_IDS["policy_search"], "66c702b725f04ab44cd24ceb")

    def test_bundled_high_screen_config_has_field_descriptions_and_options(self):
        config = high_screen.load_field_config()
        options = high_screen.load_option_config()
        self.assertEqual(config["platform_config_version"], "0.14.3")
        self.assertEqual(len(config["fields"]), 369)
        self.assertEqual(config["fields"]["address"]["label"], "注册地址")
        self.assertEqual(config["fields"]["address"]["input"]["options_from"], "addressV2")
        self.assertEqual(config["fields"]["businessKeywords"]["input"]["maxKeywordLength"], 10)
        self.assertIn("广东", {path[0] for path in high_screen.option_paths("addressV2")})
        self.assertIn("industriesV2", options["options"])

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

    def test_advanced_filter_list_normalizes_simple_address_for_upstream(self):
        captured = {}
        original = server.call_api

        def fake_call_api(product_id, params=None):
            captured["product_id"] = product_id
            captured["params"] = params or {}
            return {"resultList": [], "total": 0}

        try:
            server.call_api = fake_call_api
            result = server.advanced_filter_get_enterprise_list(
                operStatus="营业",
                address="广东省",
                name="无人机",
            )
        finally:
            server.call_api = original

        self.assertEqual(result, {"resultList": [], "total": 0})
        self.assertEqual(captured["product_id"], server.PRODUCT_IDS["advanced_filter_list"])
        self.assertEqual(captured["params"]["address"], '[["广东省"]]')
        self.assertEqual(captured["params"]["operStatus"], "营业")
        self.assertEqual(captured["params"]["name"], "无人机")

    def test_advanced_filter_list_accepts_address_arrays_and_path_strings(self):
        captured = []
        original = server.call_api

        def fake_call_api(product_id, params=None):
            captured.append((product_id, params or {}))
            return {"resultList": [], "total": 0}

        try:
            server.call_api = fake_call_api
            server.advanced_filter_get_enterprise_list(
                address=[["北京市"], ["广东省", "广州市"]],
            )
            server.advanced_filter_get_enterprise_list(
                address="广东省,深圳市;江苏省,南京市",
            )
        finally:
            server.call_api = original

        self.assertEqual(
            captured[0][1]["address"],
            '[["北京市"],["广东省","广州市"]]',
        )
        self.assertEqual(
            captured[1][1]["address"],
            '[["广东省","深圳市"],["江苏省","南京市"]]',
        )

    def test_advanced_filter_list_rejects_city_without_province(self):
        original = server.call_api
        try:
            server.call_api = lambda *args, **kwargs: self.fail("upstream must not be called")
            result = server.advanced_filter_get_enterprise_list(address="深圳市")
        finally:
            server.call_api = original

        self.assertEqual(result["error"], "参数错误")
        self.assertEqual(result["field"], "address")
        self.assertEqual(result["product_key"], "advanced_filter_list")
        self.assertIn("省级路径", result["message"])

    def test_high_screen_object_is_validated_and_compacted_for_upstream(self):
        captured = {}
        original = server.call_api
        condition = {
            "must": [
                {"operStatus_v2": [{"eq": [["营业"]]}]},
                {"regCapitalRmb": [{"gte": 10, "lte": 10000}]},
                {"should": [
                    {"businessKeywords": [{"in": ["工业机器人"]}]},
                    {"business": [{"in": ["工业机器人"]}]},
                ]},
                {"name": [{"nin": ["贸易", "培训"]}]},
            ]
        }

        def fake_call_api(product_id, params=None):
            captured["product_id"] = product_id
            captured["params"] = params or {}
            return {"resultList": [], "total": 0}

        try:
            server.call_api = fake_call_api
            result = server.advanced_filter_get_enterprise_list(filter=condition)
        finally:
            server.call_api = original

        self.assertEqual(result, {"resultList": [], "total": 0})
        self.assertEqual(captured["product_id"], server.PRODUCT_IDS["advanced_filter_condition_list"])
        self.assertIsInstance(captured["params"]["filter"], str)
        self.assertEqual(json.loads(captured["params"]["filter"]), condition)
        self.assertNotIn(" ", captured["params"]["filter"])

    def test_high_screen_json_string_is_not_double_encoded(self):
        captured = {}
        original = server.call_api
        condition = {"must": [{"name": [{"in": ["汇川技术"]}]}]}

        def fake_call_api(product_id, params=None):
            captured["params"] = params or {}
            return {"resultList": [], "total": 0}

        try:
            server.call_api = fake_call_api
            server.advanced_filter_get_enterprise_list(
                filter=json.dumps(condition, ensure_ascii=False, indent=2),
            )
        finally:
            server.call_api = original

        self.assertEqual(captured["params"]["filter"], json.dumps(condition, ensure_ascii=False, separators=(",", ":")))

    def test_high_screen_normalizes_complex_address_paths(self):
        product_id = server.PRODUCT_IDS["advanced_filter_condition_list"]
        value, error = server._normalize_high_screen_filter(product_id, {
            "must": [
                {"address": [{"eq": "广东省,深圳市"}]},
                {"address": [{"neq": "广东省,广州市;江苏省,南京市"}]},
                {"addressValue": [{"in": ["南山区", "工业园"]}]},
            ]
        })

        self.assertIsNone(error)
        parsed = json.loads(value)
        self.assertEqual(parsed["must"][0]["address"][0]["eq"], [["广东", "深圳市"]])
        self.assertEqual(
            parsed["must"][1]["address"][0]["neq"],
            [["广东", "广州市"], ["江苏", "南京市"]],
        )
        self.assertEqual(parsed["must"][2]["addressValue"][0]["in"], ["南山区", "工业园"])

    def test_high_screen_normalizes_single_address_path_array(self):
        product_id = server.PRODUCT_IDS["advanced_filter_condition_list"]
        value, error = server._normalize_high_screen_filter(product_id, {
            "must": [{"address": [{"eq": ["广东省", "深圳市", "南山区"]}]}],
        })
        self.assertIsNone(error)
        self.assertEqual(
            json.loads(value)["must"][0]["address"][0]["eq"],
            [["广东", "深圳市", "南山区"]],
        )

    def test_high_screen_rejects_address_without_province_path(self):
        result = server.advanced_filter_get_enterprise_list(filter={
            "must": [{"address": [{"eq": "深圳市"}]}],
        })
        self.assertEqual(result["error"], "参数错误")
        self.assertEqual(result["field"], "filter")
        self.assertIn("不在配置版本", result["message"])

    def test_high_screen_safely_corrects_operator_and_value_shapes_from_config(self):
        product_id = server.PRODUCT_IDS["advanced_filter_condition_list"]
        value, error = server._normalize_high_screen_filter(product_id, {
            "must": [
                {"address": [{"in": ["广东省", "深圳市"]}]},
                {"addressValue": [{"eq": "南山区"}]},
                {"operStatus_v2": [{"in": ["营业", "吊销"]}]},
                {"hasMobile": [{"exist": True}]},
            ]
        })
        self.assertIsNone(error)
        parsed = json.loads(value)
        self.assertEqual(parsed["must"][0], {"address": [{"eq": [["广东", "深圳市"]]}]})
        self.assertEqual(parsed["must"][1], {"addressValue": [{"in": ["南山区"]}]})
        self.assertEqual(parsed["must"][2], {"operStatus_v2": [{"eq": [["营业"], ["吊销"]]}]})
        self.assertEqual(parsed["must"][3], {"hasMobile": [{"exist": "1"}]})

    def test_high_screen_rejects_unknown_field_with_suggestion(self):
        result = server.advanced_filter_get_enterprise_list(filter={
            "must": [{"businessKeyword": [{"in": ["机器人"]}]}],
        })
        self.assertEqual(result["error"], "参数错误")
        self.assertIn("未知高筛字段", result["message"])
        self.assertIn("businessKeywords", result["message"])

    def test_high_screen_enforces_configured_keyword_and_numeric_limits(self):
        too_many_keywords = server.advanced_filter_get_enterprise_list(filter={
            "must": [{"businessKeywords": [{"in": [f"关键词{i}" for i in range(11)]}]}],
        })
        below_minimum = server.advanced_filter_get_enterprise_list(filter={
            "must": [{"regCapitalRmb": [{"gte": 0}]}],
        })
        self.assertEqual(too_many_keywords["error"], "参数错误")
        self.assertIn("最多允许 10 个关键词", too_many_keywords["message"])
        self.assertEqual(below_minimum["error"], "参数错误")
        self.assertIn("配置下限 1", below_minimum["message"])

    def test_high_screen_rejects_ignored_must_not_without_calling_upstream(self):
        original = server.call_api
        try:
            server.call_api = lambda *args, **kwargs: self.fail("upstream must not be called")
            result = server.advanced_filter_get_enterprise_list(filter={
                "must": [{"operStatus_v2": [{"eq": [["营业"]]}]}],
                "must_not": [{"name": [{"nin": ["贸易"]}]}],
            })
        finally:
            server.call_api = original

        self.assertEqual(result["error"], "参数错误")
        self.assertEqual(result["field"], "filter")
        self.assertEqual(result["path"], "$.must_not")
        self.assertEqual(result["product_key"], "advanced_filter_condition_list")
        self.assertIn("nin/neq", result["message"])

    def test_high_screen_rejects_condition_wrapper_and_unsupported_operator(self):
        wrapped = server.advanced_filter_get_enterprise_list(filter={
            "condition": {"must": [{"name": [{"in": ["机器人"]}]}]},
        })
        unsupported = server.advanced_filter_get_enterprise_list(filter={
            "must": [{"name": [{"match": "机器人"}]}],
        })

        self.assertEqual(wrapped["error"], "参数错误")
        self.assertIn("包装层", wrapped["message"])
        self.assertEqual(unsupported["error"], "参数错误")
        self.assertIn("不支持 match", unsupported["message"])

    def test_high_screen_rejects_mixed_flat_and_condition_modes(self):
        result = server.advanced_filter_get_enterprise_list(
            filter={"must": [{"name": [{"in": ["机器人"]}]}]},
            name="机器人",
        )
        self.assertEqual(result["error"], "参数冲突")
        self.assertEqual(result["conflicting_fields"], ["name"])

    def test_high_screen_count_uses_full_condition_product_total(self):
        captured = {}
        original = server.call_api

        def fake_call_api(product_id, params=None):
            captured["product_id"] = product_id
            captured["params"] = params or {}
            return {"resultList": [{"name": "企业A"}], "total": "27"}

        try:
            server.call_api = fake_call_api
            result = server.advanced_filter_get_enterprise_count(filter={
                "must": [{"businessKeywords": [{"in": ["伺服驱动器"]}]}],
            })
        finally:
            server.call_api = original

        self.assertEqual(result, {"total": 27})
        self.assertEqual(captured["product_id"], server.PRODUCT_IDS["advanced_filter_condition_list"])
        self.assertIsInstance(captured["params"]["filter"], str)

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

    def test_package_includes_bundled_high_screen_json_configs(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('[tool.setuptools.package-data]', pyproject)
        self.assertIn('"server.config" = ["*.json"]', pyproject)
        self.assertTrue((ROOT / "server/config/high_screen_fields.json").is_file())
        self.assertTrue((ROOT / "server/config/high_screen_options.json").is_file())

    def test_direct_script_entrypoint_can_import_bundled_config(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "server/mcp_server.py"), "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("streamable-http", result.stdout)

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
