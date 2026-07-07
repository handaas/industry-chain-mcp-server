#!/usr/bin/env python3
"""MCP server for industry-chain analysis and enterprise linking.

This service follows the HANDAAS Python FastMCP style used by public MCP
servers such as patent-mcp-server, while exposing workflow-level tools for the
industry-chain-processing skill:
- build a deterministic enterprise-search condition for a refined chain node;
- query configured enterprise-search / high-screen data;
- collect evidence products for candidate enterprises;
- classify and link enterprises to industry-chain segments.
"""
from __future__ import annotations

import json
import os
import re
import sys
from hashlib import md5
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

load_dotenv()

SERVICE_NAME = "HANDAAS产业链分析服务"
SERVICE_VERSION = "1.0.0"
SERVICE_DESCRIPTION = """
该 MCP 服务提供产业链分析和企业挂链辅助能力：根据行业/赛道/细分环节生成企业检索条件，
调用企业搜索接口获取候选企业，结合工商、招聘、知识产权、招投标等证据产品进行匹配判断。
用户侧推荐通过官方 Remote MCP token 使用；本地自托管时才需要配置 INTEGRATOR_ID、SECRET_ID、SECRET_KEY
以及 HIGH_SCREEN_* 企业搜索参数。
"""

DEFAULT_TIMEOUT = 30
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 50
CHARACTER_LIMIT = 25000

DAAS_BASE_URL = os.environ.get("DAAS_BASE_URL", "https://console.handaas.com").rstrip("/")
API_BASE_URL = f"{DAAS_BASE_URL}/api/v1/integrator/call_api"

INTEGRATOR_ID = os.environ.get("INTEGRATOR_ID")
SECRET_ID = os.environ.get("SECRET_ID")
SECRET_KEY = os.environ.get("SECRET_KEY")

HIGH_SCREEN_URL = os.environ.get("HIGH_SCREEN_URL")
HIGH_SCREEN_PRODUCT_ID = os.environ.get("HIGH_SCREEN_PRODUCT_ID")
HIGH_SCREEN_SECRET_ID = os.environ.get("HIGH_SCREEN_SECRET_ID")
HIGH_SCREEN_SECRET_KEY = os.environ.get("HIGH_SCREEN_SECRET_KEY")

DEFAULT_EVIDENCE_PRODUCT_IDS = {
    "工商照面": os.environ.get("PRODUCT_BUSINESS_PROFILE_ID", "66dbccbec7a7e3460f5e613f"),
    "企业简介": os.environ.get("PRODUCT_ENTERPRISE_PROFILE_ID", "6682b0b370f56cb7d77701e0"),
    "企业业务": os.environ.get("PRODUCT_ENTERPRISE_BUSINESS_ID", "66e55613ae988a28c6db9259"),
    "企业标签": os.environ.get("PRODUCT_ENTERPRISE_TAG_ID", "669e531ce1fd7bff82321d8d"),
    "招聘明细": os.environ.get("PRODUCT_RECRUITING_DETAIL_ID", "66d5b7e0537c3f61d646c346"),
    "知识产权统计": os.environ.get("PRODUCT_IP_STATS_ID", "66d5b7df537c3f61d646c230"),
    "企业招投标信息": os.environ.get("PRODUCT_BIDDING_INFO_ID", "66bf124bf134a4c21b4fc2fa"),
}
DEFAULT_EVIDENCE_PRODUCTS = ["工商照面", "招聘明细", "知识产权统计", "企业招投标信息"]

GENERIC_TERMS = {
    "平台", "系统", "服务", "软件", "产品", "解决方案", "方案", "企业", "公司", "产业链",
    "上游", "中游", "下游", "环节", "业务", "技术", "研发", "生产", "制造", "开发",
}
BASE_NOISE = ["培训", "咨询", "贸易", "商贸", "代理", "零售", "批发", "维修", "营销策划", "信息咨询", "企业管理咨询"]
BUSINESS_FIELDS = ["businessKeywords", "business", "desc", "domainTitle", "domainKeywords", "domainDesc"]
STRONG_FIELDS = ["recruitingName", "recruitingDesc", "patentNameList", "biddingAnncTitleList", "appNames", "appDescList", "srName"]
STRONG_EVIDENCE_SOURCES = ["招聘明细", "知识产权统计", "企业招投标信息"]


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


mcp = FastMCP(
    SERVICE_NAME,
    instructions=SERVICE_DESCRIPTION,
    dependencies=["python-dotenv", "requests"],
    host=os.environ.get("HOST", "127.0.0.1"),
    port=_int_env("PORT", 8000),
    json_response=True,
    stateless_http=True,
)


def json_dumps(value: Any, *, pretty: bool = False) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2 if pretty else None, separators=None if pretty else (",", ":"))


def md5_hex(text: str) -> str:
    return md5(text.encode("utf-8")).hexdigest()


def redact_url(value: str) -> str:
    if "token=" not in value and "signature=" not in value:
        return value
    try:
        parsed = urlparse(value)
        query = []
        for key, item in parse_qsl(parsed.query, keep_blank_values=True):
            if key.lower() in {"token", "signature", "secret", "secret_key", "secret_id"}:
                query.append((key, "REDACTED"))
            else:
                query.append((key, item))
        return urlunparse(parsed._replace(query=urlencode(query)))
    except Exception:
        return re.sub(r"(token|signature|secret(?:_id|_key)?)=[^&\s]+", r"\1=***REDACTED***", value, flags=re.I)


def redact(value: Any) -> Any:
    secret_keywords = ("secret", "signature", "token", "api_key", "apikey", "password")
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(token in lowered for token in secret_keywords):
                out[key] = "***REDACTED***"
            else:
                out[key] = redact(item)
        return out
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return redact_url(value)
    return value


def is_placeholder(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return (not text) or text.startswith("your_") or text in {"todo", "replace_me", "changeme", "xxx"} or "example.com" in text


def parse_terms(values: Optional[Sequence[str] | str]) -> List[str]:
    if values is None:
        return []
    if isinstance(values, str):
        text = values.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                pass
        return [item.strip() for item in re.split(r"[,，;；、\n]+", text) if item.strip()]
    return [str(item).strip() for item in values if str(item).strip()]


def normalize_keyword(value: str) -> str:
    text = str(value).strip().replace(" ", "")
    text = re.sub(r"产业链$", "", text)
    text = re.sub(r"产业$", "", text) if len(text) > 4 else text
    return text


def clean_token(value: str) -> List[str]:
    value = re.sub(r"[()（）]", " ", value.strip())
    parts = re.split(r"[>›/、，,;；:：|\s]+", value)
    result = []
    for part in parts:
        part = normalize_keyword(part)
        if 2 <= len(part) <= 32 and part not in GENERIC_TERMS and not re.match(r"^L[1-6]$", part, re.I):
            result.append(part)
    return result


def dedupe(values: Iterable[str], limit: int = 24) -> List[str]:
    seen = set()
    out = []
    for value in values:
        text = normalize_keyword(str(value))
        if not (2 <= len(text) <= 32) or text in GENERIC_TERMS:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= limit:
            break
    return out


def expand_keywords(node: str, path: Sequence[str], user_keywords: Sequence[str] = ()) -> Dict[str, List[str]]:
    text = " ".join([node, *path, *user_keywords])
    base = dedupe([node, *user_keywords, *sum((clean_token(item) for item in path[-3:]), [])], 18)
    product: List[str] = [*base]
    evidence: List[str] = []
    recruiting: List[str] = []
    noise: List[str] = [*BASE_NOISE]

    def add(*items: str) -> None:
        product.extend(items)
        evidence.extend(items)

    def add_evidence(*items: str) -> None:
        evidence.extend(items)

    if re.search(r"eVTOL|垂直起降|低空|航空器|飞行器", text, re.I):
        add("eVTOL", "电动垂直起降飞行器", "低空飞行器", "航空器制造", "飞行器总装", "适航取证")
        add_evidence("飞控系统", "航电系统", "机体结构", "动力系统", "适航认证", "低空飞行服务")
        recruiting.extend(["飞控工程师", "航电工程师", "适航工程师", "结构工程师", "飞行器总体设计"])
        noise.extend(["航空培训", "旅游观光", "票务代理", "模型玩具"])
    if re.search(r"无人机|UAV|巡检|航拍", text, re.I):
        add("无人机", "工业无人机", "无人机制造", "无人机巡检", "无人机系统")
        recruiting.extend(["无人机工程师", "飞控算法工程师", "嵌入式工程师"])
    if re.search(r"飞控|导航|航电", text):
        add("飞控系统", "飞行控制系统", "航电系统", "导航控制", "惯性导航", "组合导航")
        recruiting.extend(["飞控算法工程师", "导航算法工程师", "航电工程师"])
    if re.search(r"电池|PACK|动力", text, re.I):
        add("动力电池", "电池PACK", "电池管理系统", "BMS", "电池热管理")
        recruiting.extend(["BMS工程师", "电池系统工程师", "PACK工程师"])
    if re.search(r"复合材料|碳纤维|结构件", text):
        add("碳纤维复合材料", "复合材料结构件", "轻量化结构件", "航空复合材料")
        recruiting.extend(["复合材料工程师", "结构设计工程师"])
    if re.search(r"数据中心|IDC|机房", text, re.I):
        add("数据中心机房建设", "IDC机房建设", "机房工程", "数据中心运维", "机房托管", "基础设施集成")
        recruiting.extend(["数据中心运维工程师", "IDC运维工程师", "暖通工程师"])
    if re.search(r"AI|人工智能|大模型|RAG|智能体", text, re.I):
        add("人工智能", "大模型", "RAG知识库", "智能体平台", "模型训练", "模型推理", "AI应用开发")
        recruiting.extend(["算法工程师", "大模型工程师", "NLP工程师", "AI产品经理"])
    if re.search(r"机器人|具身智能|机械臂", text):
        add("机器人", "智能机器人", "机器人控制系统", "机械臂", "具身智能")
        recruiting.extend(["机器人工程师", "运动控制工程师", "嵌入式工程师"])
    if re.search(r"传感器|雷达|视觉", text):
        add("传感器", "智能传感器", "激光雷达", "机器视觉", "视觉检测")
        recruiting.extend(["传感器工程师", "视觉算法工程师", "光学工程师"])

    stripped = re.sub(r"(服务平台|解决方案|服务|平台|系统|软件|设备|产品)$", "", node).strip()
    if stripped and stripped != node:
        if node.endswith("服务"):
            add(f"{stripped}服务", f"{stripped}建设", f"{stripped}运维", f"{stripped}实施", f"{stripped}集成", f"{stripped}交付")
        if re.search(r"(平台|系统|软件)$", node):
            add(f"{stripped}平台", f"{stripped}系统", f"{stripped}开发", f"{stripped}实施", f"{stripped}运维", f"{stripped}SaaS")
        if node.endswith("设备"):
            add(f"{stripped}设备", f"{stripped}制造", f"{stripped}生产", f"{stripped}研发", f"{stripped}集成")

    if not evidence:
        evidence.extend([f"{kw}研发" for kw in base[:6]] + [f"{kw}生产" for kw in base[:4]] + [f"{kw}项目" for kw in base[:4]])
    if not recruiting:
        recruiting.extend([f"{node}工程师", f"{node}产品经理", f"{node}销售", f"{node}研发"])

    return {
        "core": dedupe(product, 20),
        "evidence": dedupe(evidence, 28),
        "recruiting": dedupe(recruiting, 16),
        "noise": dedupe(noise, 24),
    }


def parse_path(path_text: Optional[str], chain: str, node: str) -> List[str]:
    if not path_text:
        return [chain, node]
    return [item.strip() for item in re.split(r">|›|/", path_text) if item.strip()]


def industry_condition(paths: Sequence[str]) -> Optional[Dict[str, Any]]:
    clean = []
    for path in paths:
        parts = [item.strip() for item in re.split(r">|/", path) if item.strip()]
        if parts:
            clean.append(parts)
    if not clean:
        return None
    return {"industriesV2": [{"eq": clean}]}


def should_group(fields: Sequence[str], keywords: Sequence[str]) -> Dict[str, Any]:
    return {"should": [{field: [{"in": list(keywords)}]} for field in fields if keywords]}


def build_condition_group(
    chain: str,
    node: str,
    path: Optional[Sequence[str]] = None,
    keywords: Sequence[str] = (),
    industries: Sequence[str] = (),
    exclude: Sequence[str] = (),
) -> Dict[str, Any]:
    path = list(path or [chain, node])
    profile = expand_keywords(node, path, keywords)
    must: List[Dict[str, Any]] = [
        {"operStatus_v2": [{"eq": [["营业"]]}]},
        {"enterpriseType": [{"neq": [["个体户"]]}]},
    ]
    industry = industry_condition(industries)
    if industry:
        must.append(industry)
    must.append(should_group(BUSINESS_FIELDS, profile["core"]))
    must.append(should_group(STRONG_FIELDS, dedupe([*profile["evidence"], *profile["recruiting"]], 32)))
    noise = dedupe([*profile["noise"], *exclude], 28)
    return {
        "must": must,
        "must_not": [
            {"name": [{"nin": noise}]},
            {"business": [{"nin": noise}]},
            {"desc": [{"nin": noise}]},
        ],
    }


def python_string(value: Any, nested: bool = False) -> str:
    """Mimic the enterprise-search signing string used by high-screen exports."""
    if isinstance(value, dict):
        return "{" + ", ".join(f"'{key}': {python_string(item, True)}" for key, item in value.items()) + "}"
    if isinstance(value, list):
        return "[" + ", ".join(python_string(item, True) for item in value) + "]"
    if isinstance(value, str):
        if not nested:
            return value
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"
    return str(value)


def high_screen_signature(secret_key: str, call_params: Mapping[str, Any]) -> str:
    material = "".join(python_string(call_params[key]) for key in sorted(call_params)) + secret_key
    return md5_hex(material)


def daas_signature(secret_key: str, call_params: Mapping[str, Any]) -> str:
    material = "".join(str(call_params[key]) for key in sorted(call_params)) + secret_key
    return md5_hex(material)


def has_high_screen_config() -> bool:
    return all([HIGH_SCREEN_URL, HIGH_SCREEN_PRODUCT_ID, HIGH_SCREEN_SECRET_ID, HIGH_SCREEN_SECRET_KEY]) and not any(
        is_placeholder(v) for v in [HIGH_SCREEN_URL, HIGH_SCREEN_PRODUCT_ID, HIGH_SCREEN_SECRET_ID, HIGH_SCREEN_SECRET_KEY]
    )


def has_daas_config() -> bool:
    return all([INTEGRATOR_ID, SECRET_ID, SECRET_KEY]) and not any(is_placeholder(v) for v in [INTEGRATOR_ID, SECRET_ID, SECRET_KEY])


def evidence_product_ids() -> Dict[str, str]:
    out = dict(DEFAULT_EVIDENCE_PRODUCT_IDS)
    raw = os.environ.get("INDUSTRY_CHAIN_EVIDENCE_PRODUCTS")
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                out.update({str(k): str(v) for k, v in parsed.items() if v})
        except json.JSONDecodeError:
            pass
    return out


def build_enterprise_search_request(condition: Any, page_index: int = 1, page_size: int = DEFAULT_PAGE_SIZE) -> Dict[str, Any]:
    filter_string = json_dumps(condition)
    params: Dict[str, Any] = {"filter": filter_string, "pageIndex": page_index, "pageSize": page_size}
    call_params: Dict[str, Any] = {
        "product_id": HIGH_SCREEN_PRODUCT_ID or "your_real_product_id_for_enterprise_search",
        "secret_id": HIGH_SCREEN_SECRET_ID or "your_high_screen_secret_id",
        "params": params,
    }
    secret_key = HIGH_SCREEN_SECRET_KEY or "your_high_screen_secret_key"
    call_params["signature"] = high_screen_signature(secret_key, call_params)
    return {
        "url": HIGH_SCREEN_URL or "https://example.com/enterprise-search-endpoint",
        "params": params,
        "call_params": call_params,
    }


def normalize_rows(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for row in rows:
        out.append({
            "id": row.get("nameId") or row.get("_id") or row.get("id") or row.get("eid") or row.get("enterpriseId"),
            "name": row.get("name") or row.get("enterpriseName") or "未命名企业",
            "socialCreditCode": row.get("socialCreditCode") or row.get("scCode"),
            "regCapital": row.get("regCapitalRmb") if row.get("regCapitalRmb") is not None else row.get("regCapital"),
            "raw": row,
        })
    return out


def call_enterprise_search(condition: Any, page_index: int = 1, page_size: int = DEFAULT_PAGE_SIZE, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    if not has_high_screen_config():
        return {
            "error": "HIGH_SCREEN_URL/HIGH_SCREEN_PRODUCT_ID/HIGH_SCREEN_SECRET_ID/HIGH_SCREEN_SECRET_KEY 未配置；官方 Remote MCP 模式下请使用平台 token，本地自托管才需要这些变量。",
            "code": "HIGH_SCREEN_CONFIG_MISSING",
            "next_step": "在平台创建 Remote MCP 服务获取 token，或为本地服务补齐 HIGH_SCREEN_* 环境变量。",
        }
    request = build_enterprise_search_request(condition, max(page_index, 1), min(max(page_size, 1), MAX_PAGE_SIZE))
    try:
        response = requests.post(request["url"], json=request["call_params"], timeout=timeout)
        if response.status_code != 200:
            return {"error": f"企业搜索接口调用失败，状态码：{response.status_code}", "code": "HTTP_ERROR"}
        payload = response.json()
    except requests.Timeout:
        return {"error": "企业搜索接口请求超时，请减小 pageSize 或稍后重试。", "code": "TIMEOUT"}
    except requests.RequestException as exc:
        return {"error": f"企业搜索接口请求失败：{exc}", "code": "REQUEST_ERROR"}
    except ValueError:
        return {"error": "企业搜索接口响应不是合法 JSON。", "code": "INVALID_JSON"}

    code = str(payload.get("code", "")) if isinstance(payload, dict) and payload.get("code") is not None else ""
    message = str(payload.get("msgCN") or payload.get("msgCn") or payload.get("message") or "") if isinstance(payload, dict) else ""
    if code and code != "10000":
        return {"error": message or f"企业搜索接口返回异常：{code}", "code": code, "response": redact(payload)}
    data = payload.get("data") if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else {}
    rows = data.get("resultList") or data.get("list") or data.get("records") or []
    total = int(data.get("total") or len(rows) or 0)
    page_size = min(max(page_size, 1), MAX_PAGE_SIZE)
    return {
        "total": total,
        "pageIndex": max(page_index, 1),
        "pageSize": page_size,
        "totalPages": max((total + page_size - 1) // page_size, 1),
        "samples": normalize_rows(rows),
        "code": code,
        "message": message,
    }


def build_daas_request(product_name: str, product_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    call_params: Dict[str, Any] = {
        "product_id": product_id,
        "secret_id": SECRET_ID or "your_secret_id",
        "params": json_dumps(params),
    }
    secret_key = SECRET_KEY or "your_secret_key"
    call_params["signature"] = daas_signature(secret_key, call_params)
    return {
        "url": f"{API_BASE_URL}/{INTEGRATOR_ID or 'your_integrator_id'}",
        "product_name": product_name,
        "product_id": product_id,
        "params": params,
        "call_params": call_params,
    }


def call_daas_product(product_name: str, keyword: str, keyword_type: str = "nameId", extra: Optional[Dict[str, Any]] = None, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    products = evidence_product_ids()
    product_id = products.get(product_name)
    if not product_id:
        return {
            "error": f"未找到证据产品：{product_name}",
            "code": "PRODUCT_NOT_CONFIGURED",
            "available_products": sorted(products.keys()),
        }
    params: Dict[str, Any] = {"matchKeyword": keyword, "keywordType": keyword_type}
    if extra:
        params.update({key: value for key, value in extra.items() if value is not None})
    request = build_daas_request(product_name, product_id, params)
    if not has_daas_config():
        return {
            "error": "INTEGRATOR_ID/SECRET_ID/SECRET_KEY 未配置；官方 Remote MCP 模式下请使用平台 token，本地自托管才需要这些变量。",
            "code": "DAAS_CONFIG_MISSING",
            "request": redact(request),
            "next_step": "在平台创建 Remote MCP 服务获取 token，或为本地服务补齐 INTEGRATOR_ID、SECRET_ID、SECRET_KEY。",
        }
    try:
        response = requests.post(request["url"], data=request["call_params"], timeout=timeout)
        if response.status_code != 200:
            return {"error": f"证据接口调用失败，状态码：{response.status_code}", "code": "HTTP_ERROR"}
        payload = response.json()
    except requests.Timeout:
        return {"error": "证据接口请求超时，请稍后重试。", "code": "TIMEOUT"}
    except requests.RequestException as exc:
        return {"error": f"证据接口请求失败：{exc}", "code": "REQUEST_ERROR"}
    except ValueError:
        return {"error": "证据接口响应不是合法 JSON。", "code": "INVALID_JSON"}

    code = str(payload.get("code", "")) if isinstance(payload, dict) and payload.get("code") is not None else ""
    message = str(payload.get("msgCN") or payload.get("msgCn") or payload.get("message") or "") if isinstance(payload, dict) else ""
    if code and code != "10000":
        return {"error": message or f"证据接口返回异常：{code}", "code": code, "response": redact(payload)}
    return {
        "product": product_name,
        "product_id": product_id,
        "params": params,
        "code": code,
        "message": message,
        "data": payload.get("data") if isinstance(payload, dict) else payload,
        "response": payload,
    }


def keyword_hits(payload: Any, keywords: Sequence[str]) -> List[str]:
    text = json.dumps(payload, ensure_ascii=False)
    return [kw for kw in keywords if kw and kw in text][:12]


def classify_candidate(company: Mapping[str, Any], evidence: Mapping[str, Any], node: str, keywords: Sequence[str]) -> Dict[str, Any]:
    strong_hits: List[str] = []
    medium_hits: List[str] = []
    for product, payload in evidence.items():
        hits = keyword_hits(payload, [node, *keywords])
        if not hits:
            continue
        if product in STRONG_EVIDENCE_SOURCES:
            strong_hits.extend(hits)
        else:
            medium_hits.extend(hits)
    if strong_hits:
        decision, strength, action = "confirmed", "strong", "confirm link"
        reason = f"强证据产品命中：{'、'.join(sorted(set(strong_hits))[:6])}"
    elif medium_hits:
        decision, strength, action = "uncertain", "medium", "manual review"
        reason = f"中证据命中：{'、'.join(sorted(set(medium_hits))[:6])}"
    else:
        decision, strength, action = "uncertain", "weak", "manual review"
        reason = "候选来自企业搜索召回，但尚未采集到明确强证据"
    return {
        "enterprise_name": company.get("name"),
        "enterprise_id": company.get("id"),
        "decision": decision,
        "evidence_strength": strength,
        "matched_segment": node,
        "reason": reason,
        "next_action": action,
    }


def truncate_large_response(result: Dict[str, Any]) -> Dict[str, Any]:
    text = json_dumps(result)
    if len(text) <= CHARACTER_LIMIT:
        return result
    out = dict(result)
    if isinstance(out.get("evidence"), dict):
        out["evidence"] = {key: "已省略：响应过大，请缩小 evidenceSampleSize 或单独调用 evidence 工具。" for key in out["evidence"]}
    out["truncated"] = True
    out["truncation_message"] = f"响应超过 {CHARACTER_LIMIT} 字符，已省略大体积 evidence。"
    return out


@mcp.tool(
    name="industry_chain_health_check",
    annotations=ToolAnnotations(title="产业链 MCP 配置检查", readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False),
)
def industry_chain_health_check() -> Dict[str, Any]:
    """检查产业链 MCP 服务本地自托管配置是否齐全。

    Returns:
        dict: 配置状态，不包含明文密钥。官方 Remote MCP token 模式由平台托管凭证，用户侧无需本地配置这些环境变量。
    """
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "remote_token_mode": "用户通过 https://mcp.handaas.com/industry-chain/industry_chain?token={token} 使用时，无需本地 INTEGRATOR_ID/SECRET_ID/SECRET_KEY。",
        "local_daas_configured": has_daas_config(),
        "local_high_screen_configured": has_high_screen_config(),
        "configured_evidence_products": sorted(k for k, v in evidence_product_ids().items() if v and not is_placeholder(v)),
        "missing_for_local_search": [] if has_high_screen_config() else ["HIGH_SCREEN_URL", "HIGH_SCREEN_PRODUCT_ID", "HIGH_SCREEN_SECRET_ID", "HIGH_SCREEN_SECRET_KEY"],
        "missing_for_local_evidence": [] if has_daas_config() else ["INTEGRATOR_ID", "SECRET_ID", "SECRET_KEY"],
    }


@mcp.tool(
    name="industry_chain_build_search_condition",
    annotations=ToolAnnotations(title="生成产业链企业搜索条件", readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False),
)
def industry_chain_build_search_condition(
    chain: str,
    node: str,
    path: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    industries: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """为一个产业链细分环节生成企业搜索条件 JSON。

    Args:
        chain: 产业链或赛道名称，例如“低空经济”。
        node: 可匹配企业的细分产品/技术/服务/能力，例如“eVTOL整机制造”。
        path: 可选完整链路，用 > 或 / 分隔，例如“低空经济产业链>航空器制造>eVTOL整机制造”。
        keywords: 可选补充业务词列表。
        industries: 可选行业边界路径列表。
        exclude: 可选排除噪声词列表。

    Returns:
        dict: 包含 condition、keyword_profile、path，可直接传给 industry_chain_search_enterprises。
    """
    if not chain or not chain.strip():
        return {"error": "chain 不能为空", "code": "INVALID_CHAIN"}
    if not node or not node.strip():
        return {"error": "node 不能为空", "code": "INVALID_NODE"}
    keyword_list = parse_terms(keywords)
    industry_list = parse_terms(industries)
    exclude_list = parse_terms(exclude)
    parsed_path = parse_path(path, chain.strip(), node.strip())
    condition = build_condition_group(chain.strip(), node.strip(), parsed_path, keyword_list, industry_list, exclude_list)
    return {
        "chain": chain.strip(),
        "node": node.strip(),
        "path": parsed_path,
        "keyword_profile": expand_keywords(node.strip(), parsed_path, keyword_list),
        "condition": condition,
    }


@mcp.tool(
    name="industry_chain_search_enterprises",
    annotations=ToolAnnotations(title="搜索产业链候选企业", readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True),
)
def industry_chain_search_enterprises(
    chain: str,
    node: str,
    path: Optional[str] = None,
    condition: Optional[Dict[str, Any]] = None,
    keywords: Optional[List[str]] = None,
    industries: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
    pageIndex: int = 1,
    pageSize: int = DEFAULT_PAGE_SIZE,
    dryRun: bool = False,
) -> Dict[str, Any]:
    """根据产业链细分环节搜索候选企业。

    Args:
        chain: 产业链或赛道名称。
        node: 细分产品/技术/服务/能力。
        path: 可选完整链路。
        condition: 可选已生成的企业搜索条件；不传时由 chain/node/path/keywords 自动生成。
        keywords: 可选补充业务词列表。
        industries: 可选行业边界路径列表。
        exclude: 可选排除噪声词列表。
        pageIndex: 页码，从 1 开始。
        pageSize: 分页大小，1-50。
        dryRun: 为 true 时只返回脱敏请求，不真实调用接口。

    Returns:
        dict: total、samples、分页信息；dryRun 时返回 redacted_request。
    """
    built = industry_chain_build_search_condition(chain, node, path, keywords, industries, exclude)
    if "error" in built:
        return built
    actual_condition = condition or built["condition"]
    page_index = max(int(pageIndex or 1), 1)
    page_size = min(max(int(pageSize or DEFAULT_PAGE_SIZE), 1), MAX_PAGE_SIZE)
    if dryRun:
        request = build_enterprise_search_request(actual_condition, page_index, page_size)
        return {
            "dry_run": True,
            "chain": chain,
            "node": node,
            "path": built["path"],
            "condition": actual_condition,
            "redacted_request": redact(request),
            "note": "dryRun 未调用网络；Remote MCP token 模式下平台会托管真实凭证。",
        }
    result = call_enterprise_search(actual_condition, page_index, page_size)
    result.update({"chain": chain, "node": node, "path": built["path"], "condition": actual_condition})
    return result


@mcp.tool(
    name="industry_chain_evidence_call",
    annotations=ToolAnnotations(title="查询企业挂链证据", readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True),
)
def industry_chain_evidence_call(
    productName: str,
    matchKeyword: str,
    keywordType: str = "nameId",
    extraParams: Optional[Dict[str, Any]] = None,
    dryRun: bool = False,
) -> Dict[str, Any]:
    """调用配置的企业证据产品，用于验证企业是否匹配某个产业链环节。

    Args:
        productName: 证据产品名，例如“工商照面”“招聘明细”“知识产权统计”“企业招投标信息”。
        matchKeyword: 企业名称、企业 ID、注册号或统一社会信用代码。
        keywordType: 主体类型，常用 name、nameId、regNumber、socialCreditCode。
        extraParams: 可选额外参数，例如 {"pageIndex": 1, "pageSize": 5}。
        dryRun: 为 true 时只返回脱敏请求，不真实调用接口。

    Returns:
        dict: 证据产品响应；不会暴露 secret、signature 或 token。
    """
    product_ids = evidence_product_ids()
    product_id = product_ids.get(productName)
    if not product_id:
        return {"error": f"未找到证据产品：{productName}", "code": "PRODUCT_NOT_CONFIGURED", "available_products": sorted(product_ids.keys())}
    params: Dict[str, Any] = {"matchKeyword": matchKeyword, "keywordType": keywordType}
    if extraParams:
        params.update({key: value for key, value in extraParams.items() if value is not None})
    if dryRun:
        return {"dry_run": True, "request": redact(build_daas_request(productName, product_id, params))}
    return call_daas_product(productName, matchKeyword, keywordType, extraParams)


@mcp.tool(
    name="industry_chain_link_enterprises",
    annotations=ToolAnnotations(title="产业链候选企业挂链判断", readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True),
)
def industry_chain_link_enterprises(
    chain: str,
    node: str,
    path: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    industries: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
    pageSize: int = 10,
    withEvidence: bool = False,
    evidenceProducts: Optional[List[str]] = None,
    evidenceSampleSize: int = 3,
    dryRun: bool = False,
) -> Dict[str, Any]:
    """完成一个产业链细分环节的候选企业搜索与挂链判断。

    Args:
        chain: 产业链或赛道名称。
        node: 细分产品/技术/服务/能力。
        path: 可选完整链路。
        keywords: 可选补充业务词列表。
        industries: 可选行业边界路径列表。
        exclude: 可选排除噪声词列表。
        pageSize: 企业搜索返回数量，1-50。
        withEvidence: 是否对样本企业继续调用证据产品。
        evidenceProducts: 证据产品名列表；默认工商照面、招聘明细、知识产权统计、企业招投标信息。
        evidenceSampleSize: withEvidence=true 时最多核验多少个候选企业，避免一次调用过多付费接口。
        dryRun: 为 true 时只生成条件和脱敏请求。

    Returns:
        dict: condition、preview、decisions、evidence、next_actions。
    """
    search_result = industry_chain_search_enterprises(
        chain=chain,
        node=node,
        path=path,
        keywords=keywords,
        industries=industries,
        exclude=exclude,
        pageIndex=1,
        pageSize=pageSize,
        dryRun=dryRun,
    )
    if dryRun or "error" in search_result:
        return search_result

    candidates = search_result.get("samples", []) if isinstance(search_result.get("samples"), list) else []
    products = parse_terms(evidenceProducts) or DEFAULT_EVIDENCE_PRODUCTS
    keyword_list = parse_terms(keywords)
    evidence_results: Dict[str, Dict[str, Any]] = {}
    decisions: List[Dict[str, Any]] = []

    if withEvidence and candidates:
        for company in candidates[: max(1, min(int(evidenceSampleSize or 3), 10))]:
            company_id = company.get("id") or company.get("name")
            key_type = "nameId" if company.get("id") else "name"
            per_company: Dict[str, Any] = {}
            for product in products:
                per_company[product] = call_daas_product(product, str(company_id), key_type, {"pageIndex": 1, "pageSize": 5})
            evidence_results[str(company.get("name"))] = per_company
            decisions.append(classify_candidate(company, per_company, node, [node, *keyword_list]))
    else:
        decisions = [classify_candidate(company, {}, node, keyword_list) for company in candidates]

    return truncate_large_response({
        "chain": chain,
        "node": node,
        "path": search_result.get("path"),
        "condition": search_result.get("condition"),
        "preview": {
            "total": search_result.get("total"),
            "pageIndex": search_result.get("pageIndex"),
            "pageSize": search_result.get("pageSize"),
            "samples": candidates,
        },
        "decisions": decisions,
        "evidence": evidence_results,
        "next_actions": [
            "抽查 confirmed/uncertain 企业证据",
            "对跑偏样本补充 exclude 排除词",
            "对高价值细分环节启用 withEvidence 做二次证据核验",
        ],
    })


if __name__ == "__main__":
    start_type = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    if start_type not in {"stdio", "sse", "streamable-http"}:
        print("请输入正确的启动方式: stdio、sse 或 streamable-http", file=sys.stderr)
        raise SystemExit(1)
    print(f"正在启动{SERVICE_NAME}，启动方式: {start_type}", file=sys.stderr)
    mcp.run(transport=start_type)
