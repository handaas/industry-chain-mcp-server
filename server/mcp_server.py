#!/usr/bin/env python3
"""HandaaS industry-chain MCP server.

This server only exposes wrappers around existing HandaaS data interfaces that
are useful for industry-chain analysis. It does not register custom workflow
or planning tools.
"""
from __future__ import annotations

import json
import os
import sys
from hashlib import md5
from typing import Any, Dict, Optional, Union

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

DESCRIPTION = """
该MCP服务提供产业链分析相关的HandaaS数据接口封装，包括企业关键词搜索、企业基础信息、供应链下游产品与企业、专利信息、招投标信息和高级企业筛选等。
所有可用工具均为HandaaS已有数据接口的MCP封装。
"""

mcp = FastMCP("HANDAAS产业链分析服务", instructions=DESCRIPTION, dependencies=["python-dotenv", "requests"])

INTEGRATOR_ID = os.environ.get("INTEGRATOR_ID")
SECRET_ID = os.environ.get("SECRET_ID")
SECRET_KEY = os.environ.get("SECRET_KEY")
DAAS_BASE_URL = os.environ.get("DAAS_BASE_URL", "https://console.handaas.com").rstrip("/")
DEFAULT_TIMEOUT = int(os.environ.get("HANDAAS_TIMEOUT", "30"))

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
}


def _drop_none(params: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in params.items() if value is not None}


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


def _signature(call_params: Dict[str, Any], secret_key: str) -> str:
    material = "".join(str(call_params[key]) for key in sorted(call_params)) + secret_key
    return md5(material.encode("utf-8")).hexdigest()


def call_api(product_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any] | str:
    """Call a HandaaS data product by product_id."""
    if params is None:
        params = {}
    if not INTEGRATOR_ID:
        return {"error": "对接器ID不能为空"}
    if not SECRET_ID:
        return {"error": "密钥ID不能为空"}
    if not SECRET_KEY:
        return {"error": "密钥不能为空"}
    if not product_id:
        return {"error": "产品ID不能为空"}

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
            response_json = response.json()
            return response_json.get("data", None) or response_json.get("msgCN", None) or response_json
        return f"接口调用失败，状态码：{response.status_code}"
    except Exception:
        return "查询失败"


@mcp.tool()
def enterprise_get_keyword_search(matchKeyword: str, pageIndex: int = 1, pageSize: int = 10) -> dict:
    """
    关键词模糊查询企业。

    请求参数:
    - matchKeyword: 匹配关键词，查询各类信息包含匹配关键词的企业
    - pageIndex: 页码，从1开始
    - pageSize: 分页大小，一页最多获取50条数据
    """
    return call_api(PRODUCT_IDS["enterprise_keyword_search"], _drop_none({
        "matchKeyword": matchKeyword,
        "pageIndex": pageIndex,
        "pageSize": pageSize,
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
    return call_api(PRODUCT_IDS["enterprise_invest_info"], _drop_none({
        "matchKeyword": matchKeyword,
        "keywordType": keywordType,
        "pageIndex": pageIndex,
        "pageSize": pageSize,
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
    return call_api(PRODUCT_IDS["enterprise_branch_info"], _drop_none({
        "matchKeyword": matchKeyword,
        "keywordType": keywordType,
        "pageIndex": pageIndex,
        "pageSize": pageSize,
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
    return call_api(PRODUCT_IDS["enterprise_main_person_info"], _drop_none({
        "matchKeyword": matchKeyword,
        "keywordType": keywordType,
        "pageIndex": pageIndex,
        "pageSize": pageSize,
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
    return call_api(PRODUCT_IDS["supply_downstream_enterprises"], _drop_none({
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
        "pageIndex": pageIndex,
        "pageSize": pageSize,
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
    return call_api(PRODUCT_IDS["advanced_filter_count"], _drop_none(locals()))


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
    return call_api(PRODUCT_IDS["advanced_filter_list"], _drop_none(locals()))


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
    return call_api(PRODUCT_IDS["patent_search"], _drop_none({
        "matchKeyword": matchKeyword,
        "pageSize": pageSize,
        "patentType": patentType,
        "keywordType": keywordType,
        "pageIndex": pageIndex,
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
    return call_api(PRODUCT_IDS["bidding_info"], _drop_none({
        "matchKeyword": matchKeyword,
        "pageSize": pageSize,
        "keywordType": keywordType,
        "pageIndex": pageIndex,
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
    bidding_type, bidding_type_error = _normalize_json_string_param(biddingType, "biddingType")
    if bidding_type_error:
        return bidding_type_error
    bidding_region, bidding_region_error = _normalize_json_string_param(biddingRegion, "biddingRegion")
    if bidding_region_error:
        return bidding_region_error
    return call_api(PRODUCT_IDS["bid_search"], _drop_none({
        "matchKeyword": matchKeyword,
        "biddingType": bidding_type,
        "biddingRegion": bidding_region,
        "biddingAnncPubStartTime": biddingAnncPubStartTime,
        "biddingAnncPubEndTime": biddingAnncPubEndTime,
        "searchMode": searchMode,
        "biddingProjectMaxAmount": biddingProjectMaxAmount,
        "biddingPurchasingType": biddingPurchasingType,
        "biddingProjectMinAmount": biddingProjectMinAmount,
        "pageIndex": pageIndex,
        "pageSize": pageSize,
    }))


@mcp.tool()
def bid_bigdata_planned_projects(matchKeyword: str, pageIndex: int = 1, pageSize: int = 10, keywordType: Optional[str] = None) -> dict:
    """
    查询企业拟建公告信息。
    """
    return call_api(PRODUCT_IDS["planned_projects"], _drop_none({
        "matchKeyword": matchKeyword,
        "pageIndex": pageIndex,
        "pageSize": pageSize,
        "keywordType": keywordType,
    }))


if __name__ == "__main__":
    print("正在启动MCP服务...", file=sys.stderr)
    start_type = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    print(f"启动方式: {start_type}", file=sys.stderr)
    if start_type == "stdio":
        print("正在使用stdio方式启动MCP服务器...", file=sys.stderr)
        mcp.run(transport="stdio")
    elif start_type == "sse":
        print("正在使用sse方式启动MCP服务器...", file=sys.stderr)
        mcp.run(transport="sse")
    elif start_type == "streamable-http":
        print("正在使用streamable-http方式启动MCP服务器...", file=sys.stderr)
        mcp.run(transport="streamable-http")
    else:
        print("请输入正确的启动方式: stdio 或 sse 或 streamable-http", file=sys.stderr)
        raise SystemExit(1)
