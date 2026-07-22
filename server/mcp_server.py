#!/usr/bin/env python3
"""HandaaS industry-chain MCP server.

This server only exposes wrappers around existing HandaaS data interfaces that
are useful for industry-chain analysis. It does not register custom workflow
or planning tools.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import sys
from datetime import datetime
from hashlib import md5
from typing import Any, Dict, Optional, Union

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

if __package__ in {None, ""}:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.high_screen import (
    HighScreenValidationError,
    high_screen_common_guide,
    high_screen_field_catalog,
    high_screen_field_usage,
    high_screen_option_catalog,
    normalize_filter,
    normalize_legacy_address_paths,
)

load_dotenv()

DESCRIPTION = """
该MCP服务提供产业链分析相关的HandaaS数据接口封装，包括企业关键词搜索、企业基础信息、供应链下游产品与企业、专利信息、招投标信息、政策大数据和高级企业筛选等。
所有可用工具均为HandaaS已有数据接口的MCP封装。
高级筛选前可读取 handaas://high-screen/guide、handaas://high-screen/fields、
handaas://high-screen/fields/{field} 和 handaas://high-screen/options/{source} 资源了解字段用法。
条件规划与 ES/filter 拼装属于伴随 Skill；MCP 工具只负责执行现有 HandaaS 数据产品。
"""

INTEGRATOR_ID = os.environ.get("INTEGRATOR_ID")
SECRET_ID = os.environ.get("SECRET_ID")
SECRET_KEY = os.environ.get("SECRET_KEY")
DAAS_BASE_URL = os.environ.get("DAAS_BASE_URL", "https://console.handaas.com").rstrip("/")
DEFAULT_TIMEOUT = int(os.environ.get("HANDAAS_TIMEOUT", "30"))
MCP_HOST = os.environ.get("MCP_HOST") or os.environ.get("HANDAAS_MCP_HOST") or "127.0.0.1"
MCP_PORT = int(os.environ.get("MCP_PORT") or os.environ.get("HANDAAS_MCP_PORT") or "8000")

mcp = FastMCP(
    "HANDAAS产业链分析服务",
    instructions=DESCRIPTION,
    dependencies=["python-dotenv", "requests"],
    host=MCP_HOST,
    port=MCP_PORT,
)


def _json_resource(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


@mcp.resource(
    "handaas://high-screen/guide",
    name="high_screen_common_guide",
    title="HandaaS 高筛常用维度指南",
    description="常用企业筛选维度、操作符、示例和推荐的资源发现流程。",
    mime_type="application/json",
)
def high_screen_common_guide_resource() -> str:
    return _json_resource(high_screen_common_guide())


@mcp.resource(
    "handaas://high-screen/fields",
    name="high_screen_field_catalog",
    title="HandaaS 高筛完整字段目录",
    description="配置版本内全部高筛字段、分类、操作符、输入类型和枚举来源。",
    mime_type="application/json",
)
def high_screen_field_catalog_resource() -> str:
    return _json_resource(high_screen_field_catalog())


@mcp.resource(
    "handaas://high-screen/fields/{field}",
    name="high_screen_field_usage",
    title="HandaaS 高筛字段用法",
    description="按字段名读取操作符、输入约束、示例条件及枚举资源地址。",
    mime_type="application/json",
)
def high_screen_field_usage_resource(field: str) -> str:
    return _json_resource(high_screen_field_usage(field))


@mcp.resource(
    "handaas://high-screen/options/{source}",
    name="high_screen_option_catalog",
    title="HandaaS 高筛枚举路径",
    description="按 options_from 名称读取完整合法枚举或树形路径。",
    mime_type="application/json",
)
def high_screen_option_catalog_resource(source: str) -> str:
    return _json_resource(high_screen_option_catalog(source))


@mcp.custom_route("/health", methods=["GET"])
@mcp.custom_route("/api/health", methods=["GET"])
async def health_check(_: Request) -> JSONResponse:
    """Credential-free readiness endpoint for local and hosted deployments."""
    tool_manager = getattr(mcp, "_tool_manager", None)
    registered_tools = getattr(tool_manager, "_tools", {})
    return JSONResponse({
        "ok": True,
        "ready": bool(INTEGRATOR_ID and SECRET_ID and SECRET_KEY),
        "service": "handaas-industry-chain-mcp-server",
        "mcp_path": "/mcp",
        "tool_count": len(registered_tools),
        "credentials_configured": bool(INTEGRATOR_ID and SECRET_ID and SECRET_KEY),
    })

PRODUCT_IDS = {
    # 企业大数据服务
    "enterprise_keyword_search": "675cea1f0e009a9ea37edaa1",
    "enterprise_base_info": "66dbccbec7a7e3460f5e613f",
    "enterprise_profile": "6682b0b370f56cb7d77701e0",
    "enterprise_tags": "669e531ce1fd7bff82321d8d",
    "enterprise_holder_info": "66b485eadaf8c77fb249a441",
    "enterprise_invest_info": "669e5ee54efb02e6f96c7c9c",
    "enterprise_branch_info": "669fa757c629692bdb8d80b7",
    "enterprise_main_person_info": "669fa60021b2cee211ad3ef2",
    # 供应链潜客推荐服务
    "supply_downstream_products": "68c02b268cc760ff46ee93c3",
    "supply_downstream_enterprises": "68c02fb58cc760ff46ee948e",
    "advanced_filter_count": "690342962e32082a0cfd003a",
    "advanced_filter_list": "690367b52e32082a0cfd00ba",
    "advanced_filter_condition_list": "690dcb1b9c9dc8d0ff3c40eb",
    # 专利大数据服务
    "patent_search": "66b338e274bf098447db7f37",
    "patent_stats": "66d5b7df537c3f61d646c230",
    # 招投标大数据服务
    "bid_win_stats": "6707813f7427e966078e391d",
    "bidding_info": "66bf124bf134a4c21b4fc2fa",
    "tender_stats": "6707813f7427e966078e392f",
    "procurement_stats": "6725e5b9ba65854594baebbc",
    "bid_search": "66bf124bf134a4c21b4fc34c",
    "planned_projects": "66f3d8c064bd2be52d68a134",
    # 政策大数据服务
    "policy_approved_project_stats": "66c702b725f04ab44cd24c9c",
    "policy_info": "66c702b725f04ab44cd24cd6",
    "policy_search": "66c702b725f04ab44cd24ceb",
}

PRODUCT_NAMES = {
    "enterprise_keyword_search": "企业关键词模糊查询",
    "enterprise_base_info": "企业基础信息查询",
    "enterprise_profile": "企业简介查询",
    "enterprise_tags": "企业标签信息查询",
    "enterprise_holder_info": "企业控股股东信息查询",
    "enterprise_invest_info": "企业对外投资信息查询",
    "enterprise_branch_info": "企业分支机构信息查询",
    "enterprise_main_person_info": "企业主要人员信息查询",
    "supply_downstream_products": "下游产品目录查询",
    "supply_downstream_enterprises": "下游企业清单查询",
    "advanced_filter_count": "高级筛选企业数量查询",
    "advanced_filter_list": "高级筛选企业清单查询",
    "advanced_filter_condition_list": "高筛条件组企业清单查询",
    "patent_search": "专利信息搜索",
    "patent_stats": "企业专利统计分析",
    "bid_win_stats": "企业中标统计",
    "bidding_info": "企业招投标信息查询",
    "tender_stats": "企业招标统计",
    "procurement_stats": "企业采购统计",
    "bid_search": "招投标公告搜索",
    "planned_projects": "企业拟建项目查询",
    "policy_approved_project_stats": "企业获批政策项目统计",
    "policy_info": "政策详情查询",
    "policy_search": "政策搜索",
}


def _product_meta(product_id: str) -> Dict[str, str]:
    for key, value in PRODUCT_IDS.items():
        if value == product_id:
            return {
                "product_key": key,
                "product_name": PRODUCT_NAMES.get(key, key),
                "product_id": product_id,
            }
    return {"product_key": "", "product_name": "", "product_id": product_id}


def _drop_none(params: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in params.items() if value is not None}


def _normalize_pagination(
    product_id: str,
    page_index: int,
    page_size: int,
    *,
    max_page_size: int = 50,
) -> tuple[Optional[Dict[str, int]], Optional[Dict[str, Any]]]:
    """Validate paging and cap page size to the upstream product limit."""
    if isinstance(page_index, bool) or not isinstance(page_index, int) or page_index < 1:
        return None, _api_error(
            product_id,
            "参数错误",
            "pageIndex 必须是从 1 开始的整数。",
            field="pageIndex",
        )
    if isinstance(page_size, bool) or not isinstance(page_size, int) or page_size < 1:
        return None, _api_error(
            product_id,
            "参数错误",
            f"pageSize 必须是 1-{max_page_size} 的整数。",
            field="pageSize",
        )
    return {"pageIndex": page_index, "pageSize": min(page_size, max_page_size)}, None


def _normalize_json_string_param(value: Any, field_name: str) -> tuple[Optional[str], Optional[Dict[str, str]]]:
    if value is None:
        return None, None
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False), None
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None, {"error": f"{field_name}格式错误，请输入合法JSON字符串或JSON数组"}
        if isinstance(parsed, str):
            try:
                json.loads(parsed)
                return parsed, None
            except json.JSONDecodeError:
                return value, None
        return value, None
    return None, {"error": f"{field_name}格式错误，请输入合法JSON字符串或JSON数组"}


def _normalize_policy_address_param(value: Any) -> tuple[Optional[str], Optional[Dict[str, str]]]:
    """Normalize policy address to HandaaS list-of-list JSON string.

    Accepts [["广东省"], ["上海"]], a JSON string, "广东省", "广东省,深圳市",
    "国家部委", or one of the municipalities.
    """
    if value is None or value == "":
        return None, None
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False), None
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None, None
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                return None, {"error": "address格式错误，请输入list of list JSON，例如：[[\"福建省\"],[\"贵州省\",\"安顺市\",\"平坝县\"]]"}
            if not isinstance(parsed, list):
                return None, {"error": "address格式错误，顶层必须是list"}
            return json.dumps(parsed, ensure_ascii=False), None
        parts = [part.strip() for part in raw.replace("，", ",").split(",") if part.strip()]
        return json.dumps([parts or [raw]], ensure_ascii=False), None
    return None, {"error": "address格式错误，请输入list、JSON字符串或地区名称"}


def _normalize_advanced_filter_address_param(
    product_id: str,
    value: Any,
) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Normalize legacy advanced-filter address input to list-of-paths JSON."""
    if value is None:
        return None, None
    parsed = value
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None, None
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                return None, _api_error(
                    product_id,
                    "参数错误",
                    'address 必须是合法的二维地区路径 JSON，例如 [["广东省"]]。',
                    field="address",
                    path=f"字符位置 {exc.pos}",
                )
        else:
            parsed = raw
    elif not isinstance(value, list):
        return None, _api_error(
            product_id,
            "参数错误",
            'address 必须是地区字符串、JSON 数组字符串或二维路径数组，例如 "广东省" 或 [["广东省"]]。',
            field="address",
        )

    try:
        paths = normalize_legacy_address_paths(parsed)
    except HighScreenValidationError as exc:
        return None, _api_error(
            product_id,
            "参数错误",
            f"address 格式错误；非直辖市必须包含省级路径，例如广东省或广东省,深圳市：{exc}",
            field="address",
            path=exc.path,
        )
    return json.dumps(paths, ensure_ascii=False, separators=(",", ":")), None


def _normalize_advanced_filter_string_param(
    product_id: str,
    field: str,
    value: Any,
) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Normalize legacy comma-delimited filters from strings or JSON arrays."""
    if value is None:
        return None, None

    parsed = value
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None, None
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                return None, _api_error(
                    product_id,
                    "参数错误",
                    f"{field} 必须是逗号分隔字符串或合法 JSON 字符串数组。",
                    field=field,
                    path=f"字符位置 {exc.pos}",
                )
        else:
            return raw, None

    if not isinstance(parsed, list) or not parsed:
        return None, _api_error(
            product_id,
            "参数错误",
            f"{field} 必须是非空字符串或字符串数组。",
            field=field,
        )
    if not all(isinstance(item, str) and item.strip() for item in parsed):
        return None, _api_error(
            product_id,
            "参数错误",
            f"{field} 数组只能包含非空字符串。",
            field=field,
        )
    return ",".join(item.strip() for item in parsed), None


def _normalize_advanced_filter_date_param(
    product_id: str,
    field: str,
    value: Any,
) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
    if value is None:
        return None, None
    if not isinstance(value, str) or not value.strip():
        return None, _api_error(
            product_id,
            "参数错误",
            f"{field} 必须是 YYYY-MM-DD 日期字符串。",
            field=field,
        )
    normalized = value.strip()
    try:
        datetime.strptime(normalized, "%Y-%m-%d")
    except ValueError:
        return None, _api_error(
            product_id,
            "参数错误",
            f"{field} 必须是有效的 YYYY-MM-DD 日期字符串。",
            field=field,
        )
    return normalized, None


def _normalize_advanced_filter_number_param(
    product_id: str,
    field: str,
    value: Any,
) -> tuple[Optional[float], Optional[Dict[str, Any]]]:
    if value is None or value == "":
        return None, None
    if isinstance(value, bool):
        value = None
    else:
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = None
    if value is None or not math.isfinite(value) or value < 0:
        return None, _api_error(
            product_id,
            "参数错误",
            f"{field} 必须是大于等于 0 的有限数字。",
            field=field,
        )
    return value, None


def _signature(call_params: Dict[str, Any], secret_key: str) -> str:
    material = "".join(str(call_params[key]) for key in sorted(call_params)) + secret_key
    return md5(material.encode("utf-8")).hexdigest()


def _api_error(product_id: str, error: str, message: str, **details: Any) -> Dict[str, Any]:
    return {
        "error": error,
        "message": message,
        **_product_meta(product_id),
        **details,
    }


def _normalize_high_screen_filter(
    product_id: str,
    value: Any,
) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Validate and correct an MCP condition using the bundled field config."""
    try:
        return normalize_filter(value), None
    except HighScreenValidationError as exc:
        return None, _api_error(
            product_id,
            "参数错误",
            str(exc),
            field="filter",
            path=exc.path,
        )


def _advanced_filter_flat_params(**values: Any) -> Dict[str, Any]:
    return _drop_none({
        key: value
        for key, value in values.items()
        if value is not None and value != "" and value != []
    })


def _normalize_advanced_filter_flat_params(
    product_id: str,
    values: Dict[str, Any],
) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Normalize every legacy flat parameter before calling count/list products."""
    normalized: Dict[str, Any] = {}

    address, error = _normalize_advanced_filter_address_param(product_id, values.get("address"))
    if error:
        return None, error
    if address is not None:
        normalized["address"] = address

    for field in ("operStatus", "industries", "enterpriseType", "name"):
        value, error = _normalize_advanced_filter_string_param(product_id, field, values.get(field))
        if error:
            return None, error
        if value is not None:
            normalized[field] = value

    for field in ("foundTimeGte", "foundTimeLte"):
        value, error = _normalize_advanced_filter_date_param(product_id, field, values.get(field))
        if error:
            return None, error
        if value is not None:
            normalized[field] = value

    for field in (
        "regCapitalRmbGte",
        "regCapitalRmbLte",
        "totalPayAmountGte",
        "totalPayAmountLte",
    ):
        value, error = _normalize_advanced_filter_number_param(product_id, field, values.get(field))
        if error:
            return None, error
        if value is not None:
            normalized[field] = value

    ranges = (
        ("foundTimeGte", "foundTimeLte"),
        ("regCapitalRmbGte", "regCapitalRmbLte"),
        ("totalPayAmountGte", "totalPayAmountLte"),
    )
    for lower, upper in ranges:
        if lower in normalized and upper in normalized and normalized[lower] > normalized[upper]:
            return None, _api_error(
                product_id,
                "参数错误",
                f"{lower} 不能大于 {upper}。",
                field=f"{lower}/{upper}",
            )
    return normalized, None


def _validate_advanced_filter_mode(
    product_id: str,
    filter_value: Any,
    flat_params: Dict[str, Any],
    page_index: int,
    page_size: int,
) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
    if filter_value is None:
        return None, None
    if flat_params:
        return None, _api_error(
            product_id,
            "参数冲突",
            "使用 filter 条件组时不能同时传入 operStatus、address、industries、name 等扁平条件。",
            field="filter",
            conflicting_fields=sorted(flat_params),
        )
    valid_page_index = isinstance(page_index, int) and not isinstance(page_index, bool) and page_index == 1
    valid_page_size = isinstance(page_size, int) and not isinstance(page_size, bool) and page_size in {10, 50}
    if not valid_page_index or not valid_page_size:
        return None, _api_error(
            product_id,
            "参数冲突",
            "完整高筛条件组固定返回第一页前50条；仅接受 pageIndex=1，以及 pageSize=10（默认）或 pageSize=50。",
            field="pageIndex/pageSize",
        )
    return _normalize_high_screen_filter(product_id, filter_value)


def call_api(product_id: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """Call a HandaaS data product by product_id."""
    if params is None:
        params = {}
    if not INTEGRATOR_ID:
        return _api_error(product_id, "配置缺失", "INTEGRATOR_ID 未配置。", field="INTEGRATOR_ID")
    if not SECRET_ID:
        return _api_error(product_id, "配置缺失", "SECRET_ID 未配置。", field="SECRET_ID")
    if not SECRET_KEY:
        return _api_error(product_id, "配置缺失", "SECRET_KEY 未配置。", field="SECRET_KEY")
    if not product_id:
        return _api_error(product_id, "参数错误", "产品 ID 不能为空。", field="product_id")

    call_params: Dict[str, Any] = {
        "product_id": product_id,
        "secret_id": SECRET_ID,
        "params": json.dumps(params, ensure_ascii=False),
    }
    call_params["signature"] = _signature(call_params, SECRET_KEY)
    url = f"{DAAS_BASE_URL}/api/v1/integrator/call_api/{INTEGRATOR_ID}"

    try:
        response = requests.post(url, data=call_params, timeout=DEFAULT_TIMEOUT)
        if response.status_code == 200:
            try:
                response_json = response.json()
            except ValueError:
                return _api_error(product_id, "响应解析失败", "HandaaS 返回了非 JSON 响应。")
            if not isinstance(response_json, dict):
                return _api_error(product_id, "响应格式错误", "HandaaS 响应顶层不是 JSON object。")
            if "data" in response_json and response_json.get("data") is not None:
                return response_json["data"]
            message = response_json.get("msgCN", None) or response_json.get("msgCn", None) or response_json.get("message", None)
            if message == "产品不存在":
                return _api_error(product_id, "产品不存在", "当前本地账号未开通该 HandaaS 商品，或商品 ID 与账号权限不匹配。")
            if message:
                return _api_error(product_id, str(message), "HandaaS 接口未返回数据。")
            return response_json
        return _api_error(
            product_id,
            "接口调用失败",
            f"HandaaS 返回 HTTP {response.status_code}。",
            status_code=response.status_code,
        )
    except requests.Timeout:
        return _api_error(product_id, "请求超时", f"HandaaS 接口在 {DEFAULT_TIMEOUT} 秒内未响应。")
    except requests.RequestException as exc:
        return _api_error(product_id, "网络请求失败", f"无法连接 HandaaS：{exc.__class__.__name__}。")
    except Exception as exc:  # pragma: no cover - defensive boundary
        return _api_error(product_id, "查询失败", f"未预期的调用异常：{exc.__class__.__name__}。")


@mcp.tool()
def enterprise_get_keyword_search(matchKeyword: str, pageIndex: int = 1, pageSize: int = 10) -> dict:
    """
    关键词模糊查询企业。

    请求参数:
    - matchKeyword: 匹配关键词，查询各类信息包含匹配关键词的企业
    - pageIndex: 页码，从1开始
    - pageSize: 分页大小，一页最多获取50条数据
    """
    product_id = PRODUCT_IDS["enterprise_keyword_search"]
    page, error = _normalize_pagination(product_id, pageIndex, pageSize)
    if error:
        return error
    return call_api(product_id, _drop_none({
        "matchKeyword": matchKeyword,
        **(page or {}),
    }))


@mcp.tool()
def enterprise_get_enterprise_base_info(matchKeyword: str, keywordType: Optional[str] = None) -> dict:
    """
    查询企业基础工商信息。

    请求参数:
    - matchKeyword: 企业名称/注册号/统一社会信用代码/企业id
    - keywordType: name、nameId、regNumber、socialCreditCode
    """
    return call_api(PRODUCT_IDS["enterprise_base_info"], _drop_none({"matchKeyword": matchKeyword, "keywordType": keywordType}))


@mcp.tool()
def enterprise_get_enterprise_profile(matchKeyword: str, keywordType: Optional[str] = None) -> dict:
    """
    查询企业简介信息。

    请求参数:
    - matchKeyword: 企业名称/注册号/统一社会信用代码/企业id
    - keywordType: name、nameId、regNumber、socialCreditCode
    """
    return call_api(PRODUCT_IDS["enterprise_profile"], _drop_none({"matchKeyword": matchKeyword, "keywordType": keywordType}))


@mcp.tool()
def enterprise_get_enterprise_tags(matchKeyword: str, keywordType: Optional[str] = None) -> dict:
    """
    查询企业标签信息，包括主营业务、融资、规模、高新、专精特新等标签。

    请求参数:
    - matchKeyword: 企业名称/注册号/统一社会信用代码/企业id
    - keywordType: name、nameId、regNumber、socialCreditCode
    """
    return call_api(PRODUCT_IDS["enterprise_tags"], _drop_none({"matchKeyword": matchKeyword, "keywordType": keywordType}))


@mcp.tool()
def enterprise_get_enterprise_holder_info(matchKeyword: str, keywordType: Optional[str] = None) -> dict:
    """
    查询企业控股股东信息。

    请求参数:
    - matchKeyword: 企业名称/注册号/统一社会信用代码/企业id
    - keywordType: name、nameId、regNumber、socialCreditCode
    """
    return call_api(PRODUCT_IDS["enterprise_holder_info"], _drop_none({"matchKeyword": matchKeyword, "keywordType": keywordType}))


@mcp.tool()
def enterprise_get_enterprise_invest_info(matchKeyword: str, keywordType: Optional[str] = None, pageIndex: int = 1, pageSize: int = 10) -> dict:
    """
    查询企业对外投资信息。

    请求参数:
    - matchKeyword: 企业名称/注册号/统一社会信用代码/企业id
    - keywordType: name、nameId、regNumber、socialCreditCode
    - pageIndex: 页码，从1开始
    - pageSize: 分页大小
    """
    product_id = PRODUCT_IDS["enterprise_invest_info"]
    page, error = _normalize_pagination(product_id, pageIndex, pageSize)
    if error:
        return error
    return call_api(product_id, _drop_none({
        "matchKeyword": matchKeyword,
        "keywordType": keywordType,
        **(page or {}),
    }))


@mcp.tool()
def enterprise_get_enterprise_branch_info(matchKeyword: str, keywordType: Optional[str] = None, pageIndex: int = 1, pageSize: int = 10) -> dict:
    """
    查询企业分支机构信息。

    请求参数:
    - matchKeyword: 企业名称/注册号/统一社会信用代码/企业id
    - keywordType: name、nameId、regNumber、socialCreditCode
    - pageIndex: 页码，从1开始
    - pageSize: 分页大小
    """
    product_id = PRODUCT_IDS["enterprise_branch_info"]
    page, error = _normalize_pagination(product_id, pageIndex, pageSize)
    if error:
        return error
    return call_api(product_id, _drop_none({
        "matchKeyword": matchKeyword,
        "keywordType": keywordType,
        **(page or {}),
    }))


@mcp.tool()
def enterprise_get_enterprise_main_person_info(matchKeyword: str, keywordType: Optional[str] = None, pageIndex: int = 1, pageSize: int = 10) -> dict:
    """
    查询企业主要人员信息。

    请求参数:
    - matchKeyword: 企业名称/注册号/统一社会信用代码/企业id
    - keywordType: name、nameId、regNumber、socialCreditCode
    - pageIndex: 页码，从1开始
    - pageSize: 分页大小
    """
    product_id = PRODUCT_IDS["enterprise_main_person_info"]
    page, error = _normalize_pagination(product_id, pageIndex, pageSize)
    if error:
        return error
    return call_api(product_id, _drop_none({
        "matchKeyword": matchKeyword,
        "keywordType": keywordType,
        **(page or {}),
    }))


@mcp.tool()
def supply_get_down_stream_products(keywords: str) -> dict:
    """
    根据产品名称查询下游产品列表。产品名称是指参与供应链环节中的产品。

    请求参数:
    - keywords: 供应链产品关键词，多个词中间用英文逗号分隔
    """
    return call_api(PRODUCT_IDS["supply_downstream_products"], {"keywords": keywords})


@mcp.tool()
def supply_get_down_stream_enterprises(
    keywords: str,
    mainProducts: Optional[str] = None,
    isForeignTrade: Optional[str] = None,
    factoryInspectionType: Optional[str] = None,
    foundTimeStart: Optional[str] = None,
    foundTimeEnd: Optional[str] = None,
    address: Optional[str] = None,
    isTopEnterprise: Optional[str] = None,
    isHighTechEnterprise: Optional[str] = None,
    isGazelleEnterprise: Optional[str] = None,
    isUnicornEnterprise: Optional[str] = None,
    hasStock: Optional[str] = None,
    hasDevice: Optional[str] = None,
    hasPack: Optional[str] = None,
    regCapitalMin: Optional[int] = None,
    regCapitalMax: Optional[int] = None,
    pageIndex: int = 1,
    pageSize: int = 50,
) -> dict:
    """
    根据具体产品名称查询下游企业列表。

    请求参数:
    - keywords: 供应链产品关键词，多个词中间用英文逗号分隔
    - mainProducts: 下游产品，多个词中间用英文逗号分隔
    - isForeignTrade: 是否外贸企业，可选值：是、否
    - factoryInspectionType: 是否验厂，可选值：是、否
    - foundTimeStart/foundTimeEnd: 成立时间范围，格式yyyy-mm-dd
    - address: 地区，例如“广东省,深圳市”或“广东省”
    - pageIndex: 页码，从1开始
    - pageSize: 分页大小
    """
    product_id = PRODUCT_IDS["supply_downstream_enterprises"]
    page, error = _normalize_pagination(product_id, pageIndex, pageSize)
    if error:
        return error
    return call_api(product_id, _drop_none({
        "keywords": keywords,
        "mainProducts": mainProducts,
        "isForeignTrade": isForeignTrade,
        "factoryInspectionType": factoryInspectionType,
        "foundTimeStart": foundTimeStart,
        "foundTimeEnd": foundTimeEnd,
        "address": address,
        "isTopEnterprise": isTopEnterprise,
        "isHighTechEnterprise": isHighTechEnterprise,
        "isGazelleEnterprise": isGazelleEnterprise,
        "isUnicornEnterprise": isUnicornEnterprise,
        "hasStock": hasStock,
        "hasDevice": hasDevice,
        "hasPack": hasPack,
        "regCapitalMin": regCapitalMin,
        "regCapitalMax": regCapitalMax,
        **(page or {}),
    }))


@mcp.tool()
def advanced_filter_get_enterprise_count(
    filter: Optional[Union[str, Dict[str, Any]]] = None,
    operStatus: Optional[Union[str, list[str]]] = None,
    address: Optional[Union[str, list[Any]]] = None,
    industries: Optional[Union[str, list[str]]] = None,
    enterpriseType: Optional[Union[str, list[str]]] = None,
    name: Optional[Union[str, list[str]]] = None,
    foundTimeGte: Optional[str] = None,
    foundTimeLte: Optional[str] = None,
    regCapitalRmbGte: Optional[Union[float, str]] = None,
    regCapitalRmbLte: Optional[Union[float, str]] = None,
    totalPayAmountGte: Optional[Union[float, str]] = None,
    totalPayAmountLte: Optional[Union[float, str]] = None,
    pageIndex: int = 1,
    pageSize: int = 10,
) -> dict:
    """
    查询符合高级筛选条件的企业数量。

    推荐直接传入旷湖高筛条件组 filter。MCP 可接收 JSON object 或 JSON 字符串，
    校验后会按上游要求序列化为紧凑 JSON 字符串。为兼容旧调用，也可继续使用扁平字段。

    请求参数:
    - filter: 完整高筛条件组，例如 {"must":[{"operStatus_v2":[{"eq":[["营业"]]}]}]}
    - operStatus: 营业状态，例如“营业,吊销”、["营业","吊销"] 或“!吊销”
    - address: 仅扁平模式使用。上游格式是二维地区路径 JSON 字符串，例如
      [["广东省"]] 或 [["北京市"],["广东省","广州市"]]。也可直接传
      "广东省"、"广东省,深圳市" 或对应数组，MCP 会校验并转换。
    - industries: 行业筛选条件，接受逗号分隔字符串、JSON 字符串数组或字符串数组
    - enterpriseType: 企业类型筛选条件，输入形式同 industries
    - name: 企业名称筛选条件，输入形式同 industries
    - foundTimeGte/foundTimeLte: 成立时间范围
    - regCapitalRmbGte/regCapitalRmbLte: 注册资本范围，单位万元
    - totalPayAmountGte/totalPayAmountLte: 实缴资本范围，单位万元

    注意:
    - filter 顶层只支持 must/should。
    - 排除条件使用字段级 nin/neq 并放入 must，不能使用 must_not。
    - filter 不能与扁平字段混用；完整条件组固定返回前50条，pageIndex 仅支持1，
      pageSize 可保留默认值10或显式传50。
    """
    flat_params = _advanced_filter_flat_params(
        operStatus=operStatus,
        address=address,
        industries=industries,
        enterpriseType=enterpriseType,
        name=name,
        foundTimeGte=foundTimeGte,
        foundTimeLte=foundTimeLte,
        regCapitalRmbGte=regCapitalRmbGte,
        regCapitalRmbLte=regCapitalRmbLte,
        totalPayAmountGte=totalPayAmountGte,
        totalPayAmountLte=totalPayAmountLte,
    )
    if filter is not None:
        product_id = PRODUCT_IDS["advanced_filter_condition_list"]
        filter_string, error = _validate_advanced_filter_mode(
            product_id,
            filter,
            flat_params,
            pageIndex,
            pageSize,
        )
        if error:
            return error
        result = call_api(product_id, {"filter": filter_string})
        if not isinstance(result, dict) or "error" in result:
            return result
        total = result.get("total")
        if isinstance(total, bool) or not isinstance(total, (int, float, str)):
            return _api_error(product_id, "响应格式错误", "高筛接口响应缺少可识别的 total。")
        try:
            return {"total": int(total)}
        except (TypeError, ValueError):
            return _api_error(product_id, "响应格式错误", "高筛接口返回的 total 不是整数。")

    product_id = PRODUCT_IDS["advanced_filter_count"]
    normalized_params, error = _normalize_advanced_filter_flat_params(product_id, flat_params)
    if error:
        return error
    page, error = _normalize_pagination(product_id, pageIndex, pageSize, max_page_size=10)
    if error:
        return error
    params = {**(normalized_params or {}), **(page or {})}
    return call_api(product_id, params)


@mcp.tool()
def advanced_filter_get_enterprise_list(
    filter: Optional[Union[str, Dict[str, Any]]] = None,
    operStatus: Optional[Union[str, list[str]]] = None,
    address: Optional[Union[str, list[Any]]] = None,
    industries: Optional[Union[str, list[str]]] = None,
    enterpriseType: Optional[Union[str, list[str]]] = None,
    name: Optional[Union[str, list[str]]] = None,
    foundTimeGte: Optional[str] = None,
    foundTimeLte: Optional[str] = None,
    regCapitalRmbGte: Optional[Union[float, str]] = None,
    regCapitalRmbLte: Optional[Union[float, str]] = None,
    totalPayAmountGte: Optional[Union[float, str]] = None,
    totalPayAmountLte: Optional[Union[float, str]] = None,
    pageIndex: int = 1,
    pageSize: int = 10,
) -> dict:
    """
    通过高级筛选条件查询全国符合要求的企业清单。

    推荐传入完整旷湖高筛条件组 filter；同时兼容旧版扁平字段。
    filter 可以是 JSON object 或 JSON 字符串，顶层只允许 must/should。
    排除条件必须使用字段级 nin/neq，不能使用顶层 must_not。
    完整条件组产品返回总命中数与前50条企业；旧版扁平模式可分页获取最多500条。
    推荐每个 must/should 数组项只写一个字段；若模型传入多字段对象，MCP 会按原顺序自动拆分为单字段条件。
    filter 模式固定返回第一页前50条，接受 pageIndex=1 和 pageSize=10（默认）或 pageSize=50；不向上游转发分页字段。

    扁平模式参数:
    - operStatus: 营业状态。可传逗号分隔字符串、JSON 字符串数组或字符串数组；排除状态使用 !。
    - address: 注册地区。上游要求二维地区路径 JSON 字符串；本工具同时接受以下常见输入并自动转换：
      1. 省份字符串："广东省" -> [["广东省"]]
      2. 省市路径字符串："广东省,深圳市" -> [["广东省","深圳市"]]
      3. 多地区字符串："北京市;广东省,广州市"
      4. JSON 字符串或数组：[["北京市"],["广东省","广州市"]]
      直辖市可单独写“北京市/上海市/天津市/重庆市”；其他城市必须带省份，不能只写“深圳市”。
    - industries: 行业；输入形式同 operStatus，排除值前加 !。
    - enterpriseType: 企业类型；输入形式同 operStatus，排除值前加 !。
    - name: 企业名称包含/排除关键词；输入形式同 operStatus，例如“无人机”或 ["汽车","!专卖店"]。
    - foundTimeGte/foundTimeLte: 成立日期下限/上限，格式 YYYY-MM-DD。
    - regCapitalRmbGte/regCapitalRmbLte: 注册资本范围，单位万元。
    - totalPayAmountGte/totalPayAmountLte: 实缴资本范围，单位万元。
    - pageIndex/pageSize: 扁平模式页码从1开始、每页最多10条；filter 模式只接受
      pageIndex=1，pageSize 可为默认10或固定返回量50。

    “查询广东省营业状态且名称包含无人机的企业清单”可直接使用扁平参数：
    operStatus="营业", address="广东省", name="无人机"。

    filter 模式中的 address 格式不同，使用平台树形值（省级不带“省”）：
    {"must":[
      {"operStatus_v2":[{"eq":[["营业"]]}]},
      {"address":[{"eq":[["广东"]]}]},
      {"name":[{"in":["无人机"]}]}
    ]}
    不要把 filter 与 operStatus/address/name 等扁平参数混用。

    常用 filter 筛选维度:
    - 企业基础: name（企业名称）、operStatus_v2（营业状态）、address/addressValue、
      enterpriseType、foundTime、industriesV2（所属行业）。
    - 主营业务与产品: businessKeywords（业务关键词）、businessTags（主营业务）、
      business（经营范围）、desc（企业简介）、ecShopProducts（电商主营产品）、
      brandProductList（品牌主营产品）。关键词字段使用 in/nin 字符串数组。
    - 规模资本: regCapitalRmb、totalPayAmount、enterpriseScaleAlgV2、
      annualTurnoverAlgV2、arInsuranceNumber，使用 gte/lte/gt/lt。
    - 资质成长: isHighTechEnt、isSpecializedAndNewV2、isUnicornEnt、hasStock、
      hasPatent、hasBidding 等存在型字段，使用 exist="1"/"0"。

    查询更多维度及其合法操作符、值形状和枚举路径时，读取 MCP Resources：
    - handaas://high-screen/guide：常用维度与组合示例
    - handaas://high-screen/fields：369 个字段的完整目录
    - handaas://high-screen/fields/{field}：单字段详细用法
    - handaas://high-screen/options/{source}：枚举/树形字段合法路径
    条件规划和 filter 拼装由伴随 Skill 完成，本工具执行拼装后的 filter。

    示例:
    {"must":[
      {"operStatus_v2":[{"eq":[["营业"]]}]},
      {"enterpriseType":[{"neq":[["个体户"]]}]},
      {"should":[
        {"businessKeywords":[{"in":["工业机器人"]}]},
        {"business":[{"in":["工业机器人"]}]}
      ]}
    ]}
    """
    flat_params = _advanced_filter_flat_params(
        operStatus=operStatus,
        address=address,
        industries=industries,
        enterpriseType=enterpriseType,
        name=name,
        foundTimeGte=foundTimeGte,
        foundTimeLte=foundTimeLte,
        regCapitalRmbGte=regCapitalRmbGte,
        regCapitalRmbLte=regCapitalRmbLte,
        totalPayAmountGte=totalPayAmountGte,
        totalPayAmountLte=totalPayAmountLte,
    )
    if filter is not None:
        product_id = PRODUCT_IDS["advanced_filter_condition_list"]
        filter_string, error = _validate_advanced_filter_mode(
            product_id,
            filter,
            flat_params,
            pageIndex,
            pageSize,
        )
        if error:
            return error
        return call_api(product_id, {"filter": filter_string})

    product_id = PRODUCT_IDS["advanced_filter_list"]
    normalized_params, error = _normalize_advanced_filter_flat_params(product_id, flat_params)
    if error:
        return error
    page, error = _normalize_pagination(product_id, pageIndex, pageSize, max_page_size=10)
    if error:
        return error
    params = {**(normalized_params or {}), **(page or {})}
    return call_api(product_id, params)


@mcp.tool()
def patent_bigdata_patent_search(
    matchKeyword: str,
    pageSize: int = 10,
    patentType: Optional[str] = None,
    keywordType: Optional[str] = None,
    pageIndex: int = 1,
) -> dict:
    """
    专利信息搜索。

    请求参数:
    - matchKeyword: 专利名称/专利申请号/公布公告号/申请人/代理机构
    - pageSize: 分页大小，一页最多获取50条数据
    - patentType: 发明申请、实用新型、发明授权、外观设计
    - keywordType: 专利名称、申请号/公开号、申请人、代理机构
    - pageIndex: 页码，从1开始
    """
    product_id = PRODUCT_IDS["patent_search"]
    page, error = _normalize_pagination(product_id, pageIndex, pageSize)
    if error:
        return error
    return call_api(product_id, _drop_none({
        "matchKeyword": matchKeyword,
        "patentType": patentType,
        "keywordType": keywordType,
        **(page or {}),
    }))


@mcp.tool()
def patent_bigdata_patent_stats(matchKeyword: str, keywordType: Optional[str] = None) -> dict:
    """
    企业专利统计分析。

    请求参数:
    - matchKeyword: 企业名称/注册号/统一社会信用代码/企业id
    - keywordType: name、nameId、regNumber、socialCreditCode
    """
    return call_api(PRODUCT_IDS["patent_stats"], _drop_none({"matchKeyword": matchKeyword, "keywordType": keywordType}))


@mcp.tool()
def bid_bigdata_bid_win_stats(matchKeyword: str, keywordType: Optional[str] = None) -> dict:
    """
    根据企业名称、统一社会信用代码等获取企业标讯信息中中标信息统计项。
    """
    return call_api(PRODUCT_IDS["bid_win_stats"], _drop_none({"matchKeyword": matchKeyword, "keywordType": keywordType}))


@mcp.tool()
def bid_bigdata_bidding_info(matchKeyword: str, pageSize: int = 10, keywordType: Optional[str] = None, pageIndex: int = 1) -> dict:
    """
    查询企业参与的招投标信息。
    """
    product_id = PRODUCT_IDS["bidding_info"]
    page, error = _normalize_pagination(product_id, pageIndex, pageSize)
    if error:
        return error
    return call_api(product_id, _drop_none({
        "matchKeyword": matchKeyword,
        "keywordType": keywordType,
        **(page or {}),
    }))


@mcp.tool()
def bid_bigdata_tender_stats(matchKeyword: str, keywordType: Optional[str] = None) -> dict:
    """
    根据企业名称、统一社会信用代码等获取企业标讯信息中招标信息统计项。
    """
    return call_api(PRODUCT_IDS["tender_stats"], _drop_none({"matchKeyword": matchKeyword, "keywordType": keywordType}))


@mcp.tool()
def bid_bigdata_procurement_stats(matchKeyword: str, keywordType: Optional[str] = None) -> dict:
    """
    根据企业名称或ID，获取企业采购统计信息，包括采购产品分布、采购区域分布等。
    """
    return call_api(PRODUCT_IDS["procurement_stats"], _drop_none({"matchKeyword": matchKeyword, "keywordType": keywordType}))


@mcp.tool()
def bid_bigdata_bid_search(
    matchKeyword: Optional[str] = None,
    biddingType: Optional[Union[str, list]] = None,
    biddingRegion: Optional[Union[str, list]] = None,
    biddingAnncPubStartTime: Optional[str] = None,
    biddingAnncPubEndTime: Optional[str] = None,
    searchMode: Optional[str] = None,
    biddingProjectMaxAmount: Optional[float] = None,
    biddingPurchasingType: Optional[str] = None,
    biddingProjectMinAmount: Optional[float] = None,
    pageIndex: int = 1,
    pageSize: int = 10,
) -> dict:
    """
    查询和筛选招投标公告信息。

    请求参数:
    - matchKeyword: 搜索关键词
    - biddingType: 招标类型JSON数组字符串，例如 ["招标公告","中标公告"]
    - biddingRegion: 项目地区JSON数组字符串，例如 [["福建省","厦门市"]]
    - biddingAnncPubStartTime/biddingAnncPubEndTime: 公告发布时间范围
    - searchMode: 标题匹配、标的物匹配、全文匹配
    - pageIndex: 页码
    - pageSize: 分页大小，一页最多获取50条
    """
    product_id = PRODUCT_IDS["bid_search"]
    page, page_error = _normalize_pagination(product_id, pageIndex, pageSize)
    if page_error:
        return page_error
    bidding_type, bidding_type_error = _normalize_json_string_param(biddingType, "biddingType")
    if bidding_type_error:
        return _api_error(product_id, "参数错误", bidding_type_error["error"], field="biddingType")
    bidding_region, bidding_region_error = _normalize_json_string_param(biddingRegion, "biddingRegion")
    if bidding_region_error:
        return _api_error(product_id, "参数错误", bidding_region_error["error"], field="biddingRegion")
    return call_api(product_id, _drop_none({
        "matchKeyword": matchKeyword,
        "biddingType": bidding_type,
        "biddingRegion": bidding_region,
        "biddingAnncPubStartTime": biddingAnncPubStartTime,
        "biddingAnncPubEndTime": biddingAnncPubEndTime,
        "searchMode": searchMode,
        "biddingProjectMaxAmount": biddingProjectMaxAmount,
        "biddingPurchasingType": biddingPurchasingType,
        "biddingProjectMinAmount": biddingProjectMinAmount,
        **(page or {}),
    }))


@mcp.tool()
def bid_bigdata_planned_projects(matchKeyword: str, pageIndex: int = 1, pageSize: int = 10, keywordType: Optional[str] = None) -> dict:
    """
    查询企业拟建公告信息。
    """
    product_id = PRODUCT_IDS["planned_projects"]
    page, error = _normalize_pagination(product_id, pageIndex, pageSize)
    if error:
        return error
    return call_api(product_id, _drop_none({
        "matchKeyword": matchKeyword,
        "keywordType": keywordType,
        **(page or {}),
    }))


@mcp.tool()
def policy_bigdata_approved_project_stats(matchKeyword: str, keywordType: Optional[str] = None) -> dict:
    """
    查询企业获批政策项目统计，用于了解企业获得国家/省/市/区各级政策项目、主管机构、补贴金额和年度趋势。

    请求参数:
    - matchKeyword: 企业名称/注册号/统一社会信用代码/企业id；如果没有企业全称，可先用 enterprise_get_keyword_search 查询。
    - keywordType: name、nameId、regNumber、socialCreditCode。
    """
    return call_api(PRODUCT_IDS["policy_approved_project_stats"], _drop_none({
        "matchKeyword": matchKeyword,
        "keywordType": keywordType,
    }))


@mcp.tool()
def policy_bigdata_policy_info(matchKeyword: str) -> dict:
    """
    根据政策ID查询政策详情，包括发布机构、正文、原文链接、附件、关联项目、资助金额和申报时间等。

    请求参数:
    - matchKeyword: 政策ID。
    """
    return call_api(PRODUCT_IDS["policy_info"], {"matchKeyword": matchKeyword})


@mcp.tool()
def policy_bigdata_policy_search(
    matchKeyword: str,
    pnType: str = "全部",
    agency: Optional[str] = None,
    address: Optional[Union[str, list]] = None,
    policyPubStartTime: Optional[str] = None,
    policyPubEndTime: Optional[str] = None,
    pageSize: int = 10,
    pageIndex: int = 1,
) -> dict:
    """
    搜索政策法规、申报指南或公示公告，可按关键词、政策类型、发布机构、地区和发布时间筛选。

    请求参数:
    - matchKeyword: 政策关键词，例如“智能网联汽车”“自动驾驶”“低空经济”“机器人”。
    - pnType: 政策类型，枚举：全部、申报指南、公示公开、其他政策。
    - agency: 发布机构。
    - address: 地区，支持 list/list JSON/地区字符串。示例：[["福建省"],["贵州省","安顺市","平坝县"]]；国家政策输入“国家部委”；直辖市输入“北京/上海/天津/重庆”。
    - policyPubStartTime/policyPubEndTime: 发布时间范围，格式 yyyy-mm-dd。
    - pageSize: 分页大小，一页最多50条。
    - pageIndex: 页码，从1开始。
    """
    product_id = PRODUCT_IDS["policy_search"]
    page, page_error = _normalize_pagination(product_id, pageIndex, pageSize)
    if page_error:
        return page_error
    normalized_address, address_error = _normalize_policy_address_param(address)
    if address_error:
        return _api_error(product_id, "参数错误", address_error["error"], field="address")
    return call_api(product_id, _drop_none({
        "matchKeyword": matchKeyword,
        "pnType": pnType,
        "agency": agency,
        "address": normalized_address,
        "policyPubStartTime": policyPubStartTime,
        "policyPubEndTime": policyPubEndTime,
        **(page or {}),
    }))


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="HandaaS 产业链分析 MCP 服务")
    parser.add_argument(
        "transport",
        nargs="?",
        default="stdio",
        choices=["stdio", "sse", "streamable-http"],
        help="MCP transport，默认 stdio",
    )
    args = parser.parse_args(argv)
    print("正在启动MCP服务...", file=sys.stderr)
    start_type = args.transport
    print(f"启动方式: {start_type}", file=sys.stderr)
    try:
        if start_type == "stdio":
            print("正在使用stdio方式启动MCP服务器...", file=sys.stderr)
            mcp.run(transport="stdio")
        elif start_type == "sse":
            print("正在使用sse方式启动MCP服务器...", file=sys.stderr)
            mcp.run(transport="sse")
        elif start_type == "streamable-http":
            print("正在使用streamable-http方式启动MCP服务器...", file=sys.stderr)
            mcp.run(transport="streamable-http")
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("MCP服务已停止。", file=sys.stderr)


if __name__ == "__main__":
    main()
