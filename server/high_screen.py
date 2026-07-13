"""Configuration-driven validation for HandaaS high-screen condition groups."""
from __future__ import annotations

import json
import re
from datetime import date
from difflib import get_close_matches
from functools import lru_cache
from importlib import resources
from typing import Any, Dict, Iterable, Optional


MAX_DEPTH = 12
MAX_CONDITIONS = 500
MAX_FILTER_CHARS = 200_000

COMMON_DIMENSION_GROUPS = (
    ("企业基础", ("name", "operStatus_v2", "address", "addressValue", "enterpriseType", "foundTime", "industriesV2")),
    ("主营业务与产品", ("businessKeywords", "businessTags", "business", "desc", "ecShopProducts", "brandProductList")),
    ("规模与资本", ("regCapitalRmb", "totalPayAmount", "enterpriseScaleAlgV2", "annualTurnoverAlgV2", "arInsuranceNumber")),
    ("成长与资质", ("isHighTechEnt", "isSpecializedAndNewV2", "isSpecializedAndNewGiantV2", "isUnicornEnt", "hasStock", "isTopEnterprise", "financingSeries")),
    ("知识产权与市场", ("hasPatent", "patentNumber", "patentNameList", "hasBidding", "biddingAnncTitleList")),
)

COMMON_FIELD_EXAMPLES = {
    "name": ("in", ["无人机"]),
    "operStatus_v2": ("eq", [["营业"]]),
    "address": ("eq", [["广东"]]),
    "addressValue": ("in", ["南山区"]),
    "enterpriseType": ("eq", [["民营"]]),
    "foundTime": ("gte", "2020-01-01"),
    "industriesV2": ("eq", [["制造业"]]),
    "businessKeywords": ("in", ["无人机"]),
    "businessTags": ("in", ["无人机"]),
    "business": ("in", ["无人机"]),
    "desc": ("in", ["无人机"]),
    "ecShopProducts": ("in", ["无人机"]),
    "brandProductList": ("in", ["无人机"]),
    "regCapitalRmb": ("gte", 1000),
    "totalPayAmount": ("gte", 100),
    "enterpriseScaleAlgV2": ("gte", 50),
    "annualTurnoverAlgV2": ("gte", 1000),
    "arInsuranceNumber": ("gte", 50),
    "patentNumber": ("gte", 1),
    "patentNameList": ("in", ["飞控系统"]),
    "biddingAnncTitleList": ("in", ["无人机"]),
}


class HighScreenValidationError(ValueError):
    """Condition validation error with an actionable JSON path."""

    def __init__(self, message: str, path: str) -> None:
        super().__init__(message)
        self.path = path


@lru_cache(maxsize=1)
def load_field_config() -> Dict[str, Any]:
    text = resources.files("server.config").joinpath("high_screen_fields.json").read_text(encoding="utf-8")
    config = json.loads(text)
    if config.get("schema_version") != 1 or not isinstance(config.get("fields"), dict):
        raise RuntimeError("Bundled high-screen field config is invalid.")
    return config


@lru_cache(maxsize=1)
def load_option_config() -> Dict[str, Any]:
    text = resources.files("server.config").joinpath("high_screen_options.json").read_text(encoding="utf-8")
    config = json.loads(text)
    if config.get("schema_version") != 1 or not isinstance(config.get("options"), dict):
        raise RuntimeError("Bundled high-screen option config is invalid.")
    return config


def config_version() -> str:
    return str(load_field_config().get("platform_config_version") or "unknown")


def field_definition(field: str) -> Optional[Dict[str, Any]]:
    value = load_field_config()["fields"].get(field)
    return value if isinstance(value, dict) else None


def _option_tree_paths(value: Any, prefix: tuple[str, ...] = ()) -> set[tuple[str, ...]]:
    paths: set[tuple[str, ...]] = set()
    if isinstance(value, list):
        for item in value:
            paths.update(_option_tree_paths(item, prefix))
        return paths
    if isinstance(value, dict):
        first_level = value.get("first_level")
        if isinstance(first_level, str) and first_level:
            current = prefix + (first_level,)
            paths.add(current)
            second_level = value.get("second_level")
            if isinstance(second_level, list):
                for child in second_level:
                    if isinstance(child, str) and child:
                        paths.add(current + (child,))
            return paths

        node_value = value.get("value")
        if not isinstance(node_value, str) or not node_value:
            node_value = value.get("title")
        if isinstance(node_value, str) and node_value:
            current = prefix + (node_value,)
            paths.add(current)
            paths.update(_option_tree_paths(value.get("children") or [], current))
            return paths

        for item in value.values():
            paths.update(_option_tree_paths(item, prefix))
        return paths
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        paths.add(prefix + (str(value),))
    return paths


@lru_cache(maxsize=None)
def option_paths(options_from: str) -> frozenset[tuple[str, ...]]:
    value = load_option_config()["options"].get(options_from)
    return frozenset(_option_tree_paths(value)) if value is not None else frozenset()


@lru_cache(maxsize=None)
def option_values(options_from: str) -> frozenset[str]:
    return frozenset(segment for path in option_paths(options_from) for segment in path)


def _sorted_option_paths(options_from: str) -> list[list[str]]:
    return [
        list(path)
        for path in sorted(option_paths(options_from), key=lambda item: (len(item), item))
    ]


def _field_summary(field: str, definition: Dict[str, Any]) -> Dict[str, Any]:
    action_type = str(definition.get("action", {}).get("type"))
    input_config = definition.get("input", {})
    operators = load_field_config()["condition_contract"]["action_type_operators"].get(action_type, [])
    return {
        "field": field,
        "label": definition.get("label") or field,
        "category_path": definition.get("category_path") or [],
        "operators": operators,
        "action_type": action_type,
        "input_type": input_config.get("type"),
        "options_from": input_config.get("options_from"),
        "unit": definition.get("unit"),
        "default_can_use": bool(definition.get("default_can_use")),
        "hint": definition.get("hint"),
    }


def _generic_example(field: str, definition: Dict[str, Any]) -> Dict[str, Any]:
    configured = COMMON_FIELD_EXAMPLES.get(field)
    if configured:
        operator, value = configured
        return {field: [{operator: value}]}

    action_type = str(definition.get("action", {}).get("type"))
    input_config = definition.get("input", {})
    options_from = str(input_config.get("options_from") or "")
    examples = _sorted_option_paths(options_from)[:1] if options_from else []
    if action_type == "0":
        value: Any = "2020-01-01" if input_config.get("type") == 6 else input_config.get("min", 1)
        operator = "gte"
    elif action_type == "1":
        value = "1"
        operator = "exist"
    elif action_type == "3":
        value = examples or [["选项路径"]]
        operator = "eq"
    elif action_type in {"2", "9", "10"}:
        value = [examples[0][-1]] if examples else ["选项"]
        operator = "in"
    elif action_type in {"4", "7"}:
        value = ["关键词"]
        operator = "in"
    else:
        value = "配置值"
        operator = "eq"
    return {field: [{operator: value}]}


def high_screen_field_usage(field: str) -> Dict[str, Any]:
    """Return the configured operators, shape, examples and options for one field."""
    definition = field_definition(field)
    if definition is None:
        matches = get_close_matches(field, load_field_config()["fields"].keys(), n=5, cutoff=0.4)
        return {
            "error": "未知高筛字段",
            "field": field,
            "suggestions": matches,
            "catalog_resource": "handaas://high-screen/fields",
        }

    detail = _field_summary(field, definition)
    input_config = definition.get("input", {})
    options_from = str(input_config.get("options_from") or "")
    option_examples = _sorted_option_paths(options_from) if options_from else []
    detail.update({
        "example_condition": _generic_example(field, definition),
        "input_constraints": {
            key: input_config[key]
            for key in ("min", "max", "maxLength", "maxKeywordLength", "placeholder")
            if key in input_config
        },
        "option_path_count": len(option_examples),
        "option_examples": option_examples[:12],
        "options_resource": f"handaas://high-screen/options/{options_from}" if options_from else None,
        "correlation_dimensions": definition.get("correlation_dimension") or [],
    })
    return detail


def high_screen_field_catalog() -> Dict[str, Any]:
    """Return a compact catalog of every configured high-screen dimension."""
    fields = load_field_config()["fields"]
    summaries = [_field_summary(field, definition) for field, definition in fields.items()]
    summaries.sort(key=lambda item: (item["category_path"], item["label"], item["field"]))
    category_counts: Dict[str, int] = {}
    for item in summaries:
        category = " / ".join(item["category_path"]) or "未分类"
        category_counts[category] = category_counts.get(category, 0) + 1
    return {
        "schema_version": 1,
        "platform_config_version": config_version(),
        "field_count": len(summaries),
        "category_counts": category_counts,
        "field_detail_template": "handaas://high-screen/fields/{field}",
        "fields": summaries,
    }


def high_screen_option_catalog(source: str) -> Dict[str, Any]:
    """Return every configured path for one enum/tree option source."""
    options = load_option_config()["options"]
    if source not in options:
        return {
            "error": "未知高筛选项源",
            "source": source,
            "suggestions": get_close_matches(source, options.keys(), n=5, cutoff=0.4),
        }
    paths = _sorted_option_paths(source)
    return {
        "schema_version": 1,
        "platform_config_version": config_version(),
        "source": source,
        "path_count": len(paths),
        "paths": paths,
    }


def high_screen_common_guide() -> Dict[str, Any]:
    """Return common dimensions, examples and the recommended discovery flow."""
    groups = []
    for label, fields in COMMON_DIMENSION_GROUPS:
        groups.append({
            "group": label,
            "fields": [high_screen_field_usage(field) for field in fields],
        })
    return {
        "schema_version": 1,
        "platform_config_version": config_version(),
        "purpose": "查询高筛支持的维度和用法；条件规划与 ES/filter 拼装由伴随 Skill 负责。",
        "workflow": [
            "先读取 handaas://high-screen/guide 选择常用维度。",
            "需要完整清单时读取 handaas://high-screen/fields。",
            "读取 handaas://high-screen/fields/{field} 获取操作符、值形状和示例。",
            "枚举字段再读取 handaas://high-screen/options/{source} 获取合法路径。",
            "由 companion Skill 组装 must/should filter，再调用 advanced_filter_get_enterprise_list。",
        ],
        "rules": load_field_config()["condition_contract"],
        "compatibility": {
            "multi_field_condition_objects": (
                "同一 must/should 数组项中的多字段对象会按原顺序自动拆分为单字段条件；"
                "例如 must:[{a:[...],b:[...]}] 归一化为 must:[{a:[...]},{b:[...]}]。"
            ),
        },
        "common_dimensions": groups,
        "query_examples": {
            "广东营业且名称含无人机": {
                "must": [
                    {"operStatus_v2": [{"eq": [["营业"]]}]},
                    {"address": [{"eq": [["广东"]]}]},
                    {"name": [{"in": ["无人机"]}]},
                ]
            },
            "无人机主营业务多证据召回": {
                "must": [
                    {"operStatus_v2": [{"eq": [["营业"]]}]},
                    {"should": [
                        {"businessKeywords": [{"in": ["无人机"]}]},
                        {"businessTags": [{"in": ["无人机"]}]},
                        {"business": [{"in": ["无人机"]}]},
                        {"desc": [{"in": ["无人机"]}]},
                        {"ecShopProducts": [{"in": ["无人机"]}]},
                    ]},
                ]
            },
        },
        "resources": {
            "field_catalog": "handaas://high-screen/fields",
            "field_detail": "handaas://high-screen/fields/{field}",
            "option_paths": "handaas://high-screen/options/{source}",
        },
    }


def _nearest(values: Iterable[str], target: str) -> str:
    matches = get_close_matches(target, list(values), n=3, cutoff=0.55)
    return f"；相近值：{', '.join(matches)}" if matches else ""


def _normalize_field_name(field: Any, path: str) -> tuple[str, Dict[str, Any]]:
    if not isinstance(field, str) or not field.strip():
        raise HighScreenValidationError("字段名不能为空。", path)
    field = field.strip()
    config = load_field_config()
    aliases = config.get("normalizations", {}).get("field_aliases", {})
    normalized = aliases.get(field, field)
    definition = field_definition(normalized)
    if definition is None:
        known = config["fields"].keys()
        suggestion = _nearest(known, normalized)
        raise HighScreenValidationError(
            f"未知高筛字段 {field!r}（配置版本 {config_version()}）{suggestion}。",
            path,
        )
    return normalized, definition


def _split_path_string(value: str) -> list[list[str]]:
    raw_paths = [part.strip() for part in re.split(r"[;；|\n]+", value) if part.strip()]
    return [
        [segment.strip() for segment in re.split(r"[,，/>]+", raw_path) if segment.strip()]
        for raw_path in raw_paths
    ]


def _normalize_path_value(field: str, definition: Dict[str, Any], value: Any, path: str) -> list[list[str]]:
    paths: list[list[Any]]
    flat_list_input = False
    if isinstance(value, str):
        paths = _split_path_string(value)
    elif isinstance(value, list) and value and all(isinstance(item, str) for item in value):
        paths = [value]
        flat_list_input = True
    elif isinstance(value, list) and value and all(isinstance(item, list) for item in value):
        paths = value
    else:
        label = definition.get("label") or field
        raise HighScreenValidationError(
            f"{label}（{field}）的 eq/neq 必须是路径数组的数组；也可传路径字符串。",
            path,
        )

    aliases = (
        load_field_config()
        .get("normalizations", {})
        .get("option_aliases", {})
        .get(field, {})
    )
    options_from = str(definition.get("input", {}).get("options_from") or "")
    valid_paths = option_paths(options_from) if options_from else frozenset()
    normalized: list[list[str]] = []
    for index, item in enumerate(paths):
        item_path = f"{path}[{index}]"
        if not item or not all(isinstance(segment, str) and segment.strip() for segment in item):
            raise HighScreenValidationError("每条枚举路径必须是非空字符串数组。", item_path)
        clean = [aliases.get(segment.strip(), segment.strip()) for segment in item]
        clean_tuple = tuple(clean)
        if valid_paths and clean_tuple not in valid_paths:
            singleton_paths = [(segment,) for segment in clean]
            if flat_list_input and all(candidate in valid_paths for candidate in singleton_paths):
                normalized.extend([[candidate[0]] for candidate in singleton_paths])
                continue
            leaf_values = {candidate[-1] for candidate in valid_paths if candidate}
            suggestion = _nearest(leaf_values, clean[-1])
            label = definition.get("label") or field
            raise HighScreenValidationError(
                f"{label}路径不在配置版本 {config_version()} 的可选值中：{clean}{suggestion}。",
                item_path,
            )
        normalized.append(clean)
    return normalized


def normalize_legacy_address_paths(value: Any, path: str = "address") -> list[list[str]]:
    """Validate legacy flat-filter addresses and restore official province names.

    Full high-screen filters use platform tree values such as ``广东``. The
    legacy advanced-filter products instead expect a JSON string containing
    paths such as ``[["广东省"], ["广东省", "深圳市"]]``.
    """
    definition = field_definition("address")
    if definition is None:
        raise RuntimeError("Bundled address field config is missing.")
    normalized = _normalize_path_value("address", definition, value, path)
    aliases = (
        load_field_config()
        .get("normalizations", {})
        .get("option_aliases", {})
        .get("address", {})
    )
    official_names = {canonical: alias for alias, canonical in aliases.items()}
    return [
        [official_names.get(segments[0], segments[0]), *segments[1:]]
        for segments in normalized
    ]


def _normalize_keyword_values(
    field: str,
    definition: Dict[str, Any],
    value: Any,
    path: str,
) -> list[str]:
    values = [value] if isinstance(value, str) else value
    if not isinstance(values, list) or not values:
        raise HighScreenValidationError("关键词条件值必须是非空字符串数组。", path)
    if not all(isinstance(item, str) and item.strip() for item in values):
        raise HighScreenValidationError("关键词数组只能包含非空字符串。", path)
    normalized = list(dict.fromkeys(item.strip() for item in values))
    input_config = definition.get("input", {})
    max_keywords = input_config.get("maxKeywordLength")
    if isinstance(max_keywords, int) and len(normalized) > max_keywords:
        label = definition.get("label") or field
        raise HighScreenValidationError(
            f"{label}（{field}）最多允许 {max_keywords} 个关键词，当前 {len(normalized)} 个。",
            path,
        )
    max_length = input_config.get("maxLength")
    if isinstance(max_length, int) and sum(len(item) for item in normalized) > max_length:
        raise HighScreenValidationError(
            f"{field} 关键词总长度不能超过 {max_length} 个字符。",
            path,
        )
    return normalized


def _normalize_multi_select(
    field: str,
    definition: Dict[str, Any],
    value: Any,
    path: str,
) -> list[Any]:
    values = value if isinstance(value, list) else [value]
    if not values:
        raise HighScreenValidationError("多选条件值不能为空。", path)
    options_from = str(definition.get("input", {}).get("options_from") or "")
    valid_values = option_values(options_from) if options_from else frozenset()
    for index, item in enumerate(values):
        if item is None or item == "":
            raise HighScreenValidationError("多选条件不能包含空值。", f"{path}[{index}]")
        if valid_values and isinstance(item, str) and item not in valid_values:
            suggestion = _nearest(valid_values, item)
            raise HighScreenValidationError(
                f"{definition.get('label') or field}不支持选项 {item!r}{suggestion}。",
                f"{path}[{index}]",
            )
    return values


def _normalize_range_value(definition: Dict[str, Any], operator: str, value: Any, path: str) -> Any:
    if isinstance(value, bool) or isinstance(value, (dict, list)) or value in {None, ""}:
        raise HighScreenValidationError(f"{operator} 的值必须是数字或日期字符串。", path)
    input_config = definition.get("input", {})
    if input_config.get("type") == 6:
        if not isinstance(value, str):
            raise HighScreenValidationError("日期范围值必须是 YYYY-MM-DD 字符串。", path)
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise HighScreenValidationError("日期格式必须是有效的 YYYY-MM-DD。", path) from exc
    if isinstance(value, (int, float)):
        minimum = input_config.get("min")
        maximum = input_config.get("max")
        if isinstance(minimum, (int, float)) and value < minimum:
            raise HighScreenValidationError(f"数值不能小于配置下限 {minimum}。", path)
        if isinstance(maximum, (int, float)) and value > maximum:
            raise HighScreenValidationError(f"数值不能大于配置上限 {maximum}。", path)
    return value


def _normalize_operator(action_type: str, operator: str, path: str) -> str:
    contract = load_field_config()["condition_contract"]
    allowed = set(contract.get("action_type_operators", {}).get(action_type, []))
    if operator in allowed:
        return operator
    correction = contract.get("safe_operator_corrections", {}).get(action_type, {}).get(operator)
    if correction in allowed:
        return correction
    allowed_text = ", ".join(sorted(allowed)) or "无已配置操作符"
    raise HighScreenValidationError(
        f"字段控件类型 action.type={action_type} 不支持 {operator}；允许：{allowed_text}。",
        path,
    )


def _normalize_rule(
    field: str,
    definition: Dict[str, Any],
    rule: Dict[str, Any],
    path: str,
) -> Dict[str, Any]:
    if not isinstance(rule, dict) or not rule:
        raise HighScreenValidationError("操作符规则必须是非空 JSON object。", path)
    action_type = str(definition.get("action", {}).get("type"))
    input_type = definition.get("input", {}).get("type")
    normalized: Dict[str, Any] = {}
    for operator, value in rule.items():
        operator_path = f"{path}.{operator}"
        corrected = _normalize_operator(action_type, str(operator), operator_path)
        if corrected in normalized:
            raise HighScreenValidationError(f"操作符修正后重复：{corrected}。", operator_path)

        if action_type in {"3"} and input_type in {2, 4, 8}:
            normalized[corrected] = _normalize_path_value(field, definition, value, operator_path)
        elif action_type in {"4", "7"}:
            normalized[corrected] = _normalize_keyword_values(field, definition, value, operator_path)
        elif action_type in {"2", "9", "10"}:
            normalized[corrected] = _normalize_multi_select(field, definition, value, operator_path)
        elif action_type == "1":
            if value not in {"0", "1", 0, 1, False, True}:
                raise HighScreenValidationError("exist 仅支持 0/1、\"0\"/\"1\" 或布尔值。", operator_path)
            normalized[corrected] = "1" if value in {"1", 1, True} else "0"
        elif action_type == "0":
            normalized[corrected] = _normalize_range_value(definition, corrected, value, operator_path)
        else:
            if value is None or value == "" or value == []:
                raise HighScreenValidationError("条件值不能为空。", operator_path)
            normalized[corrected] = value

    if action_type == "5":
        preset_values = [item.get("value") for item in definition.get("action", {}).get("options", [])]
        if preset_values and normalized not in preset_values:
            raise HighScreenValidationError(
                f"{definition.get('label') or field} 必须使用配置中的预设条件：{preset_values}。",
                path,
            )
    return normalized


def _normalize_group(
    group: Dict[str, Any],
    *,
    path: str = "$",
    depth: int = 0,
    counter: Optional[list[int]] = None,
) -> Dict[str, Any]:
    if depth > MAX_DEPTH:
        raise HighScreenValidationError(f"条件嵌套不能超过 {MAX_DEPTH} 层。", path)
    if counter is None:
        counter = [0]
    if not isinstance(group, dict) or not group:
        raise HighScreenValidationError("条件组必须是非空 JSON object。", path)

    contract = load_field_config()["condition_contract"]
    group_keys = set(contract["group_keys"])
    unknown_groups = set(group) - group_keys
    if unknown_groups:
        if "must_not" in unknown_groups:
            raise HighScreenValidationError(
                "旷湖高筛不执行顶层 must_not；请把排除条件改为字段级 nin/neq，并放入 must。",
                f"{path}.must_not",
            )
        unknown = ", ".join(sorted(str(key) for key in unknown_groups))
        raise HighScreenValidationError(
            f"条件组仅支持 must/should，不能使用 {unknown}；不要添加包装层。",
            path,
        )

    normalized_group: Dict[str, Any] = {}
    for group_key, conditions in group.items():
        group_path = f"{path}.{group_key}"
        if not isinstance(conditions, list) or not conditions:
            raise HighScreenValidationError(f"{group_key} 必须是非空数组。", group_path)
        normalized_conditions = []
        for index, condition in enumerate(conditions):
            condition_path = f"{group_path}[{index}]"
            if not isinstance(condition, dict) or not condition:
                raise HighScreenValidationError(
                    "每个条件必须是包含字段或嵌套 must/should 的非空 JSON object。",
                    condition_path,
                )
            for field, rules in condition.items():
                counter[0] += 1
                field_path = f"{condition_path}.{field}"
                if counter[0] > MAX_CONDITIONS:
                    raise HighScreenValidationError(f"条件数量不能超过 {MAX_CONDITIONS} 个。", field_path)
                if field in group_keys:
                    nested = _normalize_group(
                        {field: rules},
                        path=condition_path,
                        depth=depth + 1,
                        counter=counter,
                    )
                    normalized_conditions.append(nested)
                    continue
                normalized_field, definition = _normalize_field_name(field, field_path)
                if not isinstance(rules, list) or not rules:
                    raise HighScreenValidationError(
                        "字段条件必须是非空规则数组。",
                        f"{condition_path}.{normalized_field}",
                    )
                normalized_rules = [
                    _normalize_rule(
                        normalized_field,
                        definition,
                        rule,
                        f"{condition_path}.{normalized_field}[{rule_index}]",
                    )
                    for rule_index, rule in enumerate(rules)
                ]
                normalized_conditions.append({normalized_field: normalized_rules})
        normalized_group[group_key] = normalized_conditions
    return normalized_group


def normalize_filter(value: Any) -> str:
    """Return a validated, corrected and compact HandaaS filter JSON string."""
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            raise HighScreenValidationError("filter 不能为空。", "$")
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, str):
                parsed = json.loads(parsed)
        except json.JSONDecodeError as exc:
            raise HighScreenValidationError("filter 必须是合法 JSON object。", f"字符位置 {exc.pos}") from exc
    elif isinstance(value, dict):
        try:
            parsed = json.loads(json.dumps(value, ensure_ascii=False))
        except (TypeError, ValueError) as exc:
            raise HighScreenValidationError("filter 包含不可序列化的值。", "$") from exc
    else:
        raise HighScreenValidationError("filter 必须是 JSON object 或 JSON object 字符串。", "$")

    if not isinstance(parsed, dict):
        raise HighScreenValidationError("filter 顶层必须是 JSON object。", "$")
    normalized = _normalize_group(parsed)
    compact = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))
    if len(compact) > MAX_FILTER_CHARS:
        raise HighScreenValidationError(f"filter 不能超过 {MAX_FILTER_CHARS} 个字符。", "$")
    return compact
