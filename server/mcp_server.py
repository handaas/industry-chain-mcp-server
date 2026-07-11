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
import os
import sys
from hashlib import md5
from typing import Any, Dict, Optional, Union

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

load_dotenv()

DESCRIPTION = """
该MCP服务提供产业链分析相关的HandaaS数据接口封装，包括企业关键词搜索、企业基础信息、供应链下游产品与企业、专利信息、招投标信息、政策大数据和高级企业筛选等。
所有可用工具均为HandaaS已有数据接口的MCP封装。
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


@mcp.custom_route("/health", methods=["GET"])
@mcp.custom_route("/api/health", methods=["GET"])
async def health_check(_: Request) -> JSONResponse:
    """Credential-free readiness endpoint for local and hosted deployments."""
    return JSONResponse({
        "ok": True,
        "ready": bool(INTEGRATOR_ID and SECRET_ID and SECRET_KEY),
        "service": "handaas-industry-chain-mcp-server",
        "mcp_path": "/mcp",
        "tool_count": len(PRODUCT_IDS),
        "credentials_configured": bool(INTEGRATOR_ID and SECRET_ID and SECRET_KEY),
    })

PRODUCT_IDS = {
    # 企业大数据服务
    "enterprise_keyword_search": "675cea1f0e009a9ea37edaa1",
    "enterprise_base_info": "66dbccbec7a7e3460f5e613f",
    "enterprise_profile": "6682b0b370f56cb7d77701e0",
    "enterprise_business_info": "66e55613ae988a28c6db9259",
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
    "enterprise_business_info": "企业业务信息查询",
    "enterprise_tags": "企业标签信息查询",
    "enterprise_holder_info": "企业控股股东信息查询",
    "enterprise_invest_info": "企业对外投资信息查询",
    "enterprise_branch_info": "企业分支机构信息查询",
    "enterprise_main_person_info": "企业主要人员信息查询",
    "supply_downstream_products": "下游产品目录查询",
    "supply_downstream_enterprises": "下游企业清单查询",
    "advanced_filter_count": "高级筛选企业数量查询",
    "advanced_filter_list": "高级筛选企业清单查询",
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
def enterprise_get_enterprise_business_info(matchKeyword: str, keywordType: Optional[str] = None) -> dict:
    """
    查询企业业务相关信息，用于识别企业主营业务和产业链相关能力。

    请求参数:
    - matchKeyword: 企业名称/注册号/统一社会信用代码/企业id
    - keywordType: name、nameId、regNumber、socialCreditCode
    """
    return call_api(PRODUCT_IDS["enterprise_business_info"], _drop_none({"matchKeyword": matchKeyword, "keywordType": keywordType}))


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
    operStatus: Optional[str] = None,
    address: Optional[str] = None,
    industries: Optional[str] = None,
    enterpriseType: Optional[str] = None,
    name: Optional[str] = None,
    foundTimeGte: Optional[str] = None,
    foundTimeLte: Optional[str] = None,
    regCapitalRmbGte: Optional[float] = None,
    regCapitalRmbLte: Optional[float] = None,
    totalPayAmountGte: Optional[float] = None,
    totalPayAmountLte: Optional[float] = None,
    pageIndex: int = 1,
    pageSize: int = 10,
) -> dict:
    """
    通过高级筛选条件查询全国符合要求的企业数量。该接口只返回数量。

    请求参数:
    - operStatus: 营业状态，例如“营业,吊销”或“!吊销”
    - address: 地址筛选条件
    - industries: 行业筛选条件
    - enterpriseType: 企业类型筛选条件
    - name: 企业名称筛选条件
    - foundTimeGte/foundTimeLte: 成立时间范围
    - regCapitalRmbGte/regCapitalRmbLte: 注册资本范围，单位万元
    - totalPayAmountGte/totalPayAmountLte: 实缴资本范围，单位万元
    """
    product_id = PRODUCT_IDS["advanced_filter_count"]
    page, error = _normalize_pagination(product_id, pageIndex, pageSize, max_page_size=10)
    if error:
        return error
    params = _drop_none({
        "operStatus": operStatus,
        "address": address,
        "industries": industries,
        "enterpriseType": enterpriseType,
        "name": name,
        "foundTimeGte": foundTimeGte,
        "foundTimeLte": foundTimeLte,
        "regCapitalRmbGte": regCapitalRmbGte,
        "regCapitalRmbLte": regCapitalRmbLte,
        "totalPayAmountGte": totalPayAmountGte,
        "totalPayAmountLte": totalPayAmountLte,
        **(page or {}),
    })
    return call_api(product_id, params)


@mcp.tool()
def advanced_filter_get_enterprise_list(
    operStatus: Optional[str] = None,
    address: Optional[str] = None,
    industries: Optional[str] = None,
    enterpriseType: Optional[str] = None,
    name: Optional[str] = None,
    foundTimeGte: Optional[str] = None,
    foundTimeLte: Optional[str] = None,
    regCapitalRmbGte: Optional[float] = None,
    regCapitalRmbLte: Optional[float] = None,
    totalPayAmountGte: Optional[float] = None,
    totalPayAmountLte: Optional[float] = None,
    pageIndex: int = 1,
    pageSize: int = 10,
) -> dict:
    """
    通过高级筛选条件查询全国符合要求的企业清单列表，最多返回500条。

    请求参数同 advanced_filter_get_enterprise_count。
    """
    product_id = PRODUCT_IDS["advanced_filter_list"]
    page, error = _normalize_pagination(product_id, pageIndex, pageSize, max_page_size=10)
    if error:
        return error
    params = _drop_none({
        "operStatus": operStatus,
        "address": address,
        "industries": industries,
        "enterpriseType": enterpriseType,
        "name": name,
        "foundTimeGte": foundTimeGte,
        "foundTimeLte": foundTimeLte,
        "regCapitalRmbGte": regCapitalRmbGte,
        "regCapitalRmbLte": regCapitalRmbLte,
        "totalPayAmountGte": totalPayAmountGte,
        "totalPayAmountLte": totalPayAmountLte,
        **(page or {}),
    })
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
