# 产业链分析服务

[![CI](https://github.com/handaas/industry-chain-mcp-server/actions/workflows/ci.yml/badge.svg)](https://github.com/handaas/industry-chain-mcp-server/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[该MCP服务封装产业链分析常用的HandaaS已有数据接口，包括企业大数据、供应链潜客推荐、专利大数据、招投标大数据和政策大数据等，帮助用户进行产业研究、企业发现、供应链拓展、知识产权分析、招投标线索分析和区域政策分析。](https://www.handaas.com/)


## 主要功能

- 🔍 企业关键词模糊搜索
- 🏢 企业基础信息与业务标签查询
- 🔗 供应链下游产品与企业查询
- 📄 专利信息搜索与企业专利统计
- 📊 招投标信息与采购统计分析
- 📜 政策搜索、政策详情与企业获批政策项目统计
- 🧭 高级企业筛选
- 🧩 高筛字段目录、单字段用法与枚举路径 Resources

## 环境要求

- Python 3.10+
- 依赖包：python-dotenv, requests, mcp

## 本地快速启动

### 1. 克隆项目
```bash
git clone https://github.com/handaas/industry-chain-mcp-server
cd industry-chain-mcp-server
```

### 2. 创建虚拟环境&安装依赖

#### macOS / Linux

```bash
python3 -m venv mcp_env
source mcp_env/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e .
```

#### Windows PowerShell

```powershell
py -3 -m venv mcp_env
Set-ExecutionPolicy -Scope Process Bypass
.\mcp_env\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e .
```

### 3. 环境配置

复制环境变量模板并配置：

#### macOS / Linux

```bash
cp .env.example .env
nano .env
```

#### Windows PowerShell

```powershell
Copy-Item .env.example .env
notepad .env
```

编辑 `.env` 文件，配置以下环境变量：

```env
INTEGRATOR_ID=your_integrator_id
SECRET_ID=your_secret_id
SECRET_KEY=your_secret_key
```

### 4. streamable-http启动服务

#### macOS / Linux

```bash
python server/mcp_server.py streamable-http
```

#### Windows PowerShell

```powershell
python .\server\mcp_server.py streamable-http
```

服务将在 `http://localhost:8000` 启动。

如果 8000 端口已被占用，可以指定本地端口：

macOS / Linux：

```bash
MCP_PORT=8011 python server/mcp_server.py streamable-http
```

Windows PowerShell：

```powershell
$env:MCP_PORT = "8011"
python .\server\mcp_server.py streamable-http
```

对应 MCP 地址为 `http://127.0.0.1:8011/mcp`。

健康检查：

macOS / Linux：

```bash
curl http://127.0.0.1:8011/health
# 或 /api/health
```

Windows PowerShell：

```powershell
Invoke-RestMethod http://127.0.0.1:8011/health
```

健康检查中的 `ok` 表示服务进程可访问，`ready` / `credentials_configured` 表示本地 HandaaS 凭证已经配置；响应不会返回任何凭证内容。

安装为命令后也可以运行：

```bash
handaas-industry-chain-mcp streamable-http
```

#### 支持启动方式 stdio 或 sse 或 streamable-http

### 5. Cursor / Cherry Studio MCP配置

```json
{
  "mcpServers": {
    "industry-chain-mcp-server": {
      "type": "streamableHttp",
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

## STDIO版安装部署

### 设置Cursor / Cherry Studio MCP配置

先查询安装后的命令位置：

macOS / Linux：

```bash
command -v handaas-industry-chain-mcp
```

Windows PowerShell：

```powershell
(Get-Command handaas-industry-chain-mcp).Source
```

把输出的完整命令路径填入 `command`，不需要手工拼接虚拟环境路径：

```json
{
  "mcpServers": {
    "industry-chain-mcp-server": {
      "command": "<上一步输出的 handaas-industry-chain-mcp 完整路径>",
      "args": ["stdio"],
      "env": {
        "INTEGRATOR_ID": "your_integrator_id",
        "SECRET_ID": "your_secret_id",
        "SECRET_KEY": "your_secret_key"
      }
    }
  }
}
```

## 使用官方Remote服务

### 1. 直接设置Cursor / Cherry Studio MCP配置

```json
{
  "mcpServers": {
    "industry-chain-mcp-server":{
      "type": "streamableHttp",
      "url": "https://mcp.handaas.com/industry-chain/industry_chain?token={token}"
      }
  }
}
```

### 注意：integrator_id、secret_id、secret_key及token需要登录 https://www.handaas.com/ 进行注册开通平台获取

## 与产业链分析 Skill 联动

本仓库只负责把 HandaaS 已有数据产品封装为 MCP 工具。产业链层级拆解、ES 条件生成、企业证据评分、节点挂链和报告渲染由 [`industry-chain-processing-skill`](https://github.com/handaas/industry-chain-processing-skill) 完成，不会在 MCP 中重复注册工作流工具。

使用官方 Remote MCP 时，Skill 只需要平台 token：

macOS / Linux：

```bash
git clone https://github.com/handaas/industry-chain-processing-skill.git
cd industry-chain-processing-skill
python -m pip install -r requirements.txt
export INDUSTRY_CHAIN_MCP_TOKEN="<platform-token>"
python industry-chain-processing/scripts/mcp_client.py list-tools
```

Windows PowerShell：

```powershell
git clone https://github.com/handaas/industry-chain-processing-skill.git
Set-Location industry-chain-processing-skill
python -m pip install -r requirements.txt
$env:INDUSTRY_CHAIN_MCP_TOKEN = "<platform-token>"
python .\industry-chain-processing\scripts\mcp_client.py list-tools
```

使用本地 MCP 时，先启动本服务，再给 Skill 设置本地地址：

macOS / Linux：

终端 1（MCP 仓库）：

```bash
./start_mcp_server.sh
```

终端 2（Skill 仓库）：

```bash
export INDUSTRY_CHAIN_MCP_URL="http://127.0.0.1:8000/mcp"
cd ../industry-chain-processing-skill
python industry-chain-processing/scripts/mcp_client.py list-tools
```

Windows PowerShell：

PowerShell 窗口 1（MCP 仓库）：

```powershell
python .\server\mcp_server.py streamable-http
```

PowerShell 窗口 2（Skill 仓库）：

```powershell
$env:INDUSTRY_CHAIN_MCP_URL = "http://127.0.0.1:8000/mcp"
Set-Location ..\industry-chain-processing-skill
python .\industry-chain-processing\scripts\mcp_client.py list-tools
```

Remote token 模式不需要在 Skill 中再次配置 `integrator_id`、`secret_id`、`secret_key` 或各个商品 ID。本地 MCP 模式的凭证只保存在本仓库未提交的 `.env` 中。


## 可用工具

### 1. enterprise_get_keyword_search
**功能**: 企业关键词模糊查询

根据提供的企业名称、人名、品牌、产品、岗位等关键词模糊查询相关企业列表。

**参数**:
- `matchKeyword` (必需): 匹配关键词 - 查询各类信息包含匹配关键词的企业
- `pageIndex` (可选): 页码 - 从1开始
- `pageSize` (可选): 分页大小 - 一页最多获取50条数据

**返回值**:
- `total`: 总数
- `resultList`: 企业列表
- 其他企业基础信息、命中原因等

### 2. enterprise_get_enterprise_base_info
**功能**: 企业基础工商信息查询

根据企业名称、注册号、统一社会信用代码或企业ID查询企业工商基础信息。

**参数**:
- `matchKeyword` (必需): 企业名称/注册号/统一社会信用代码/企业id
- `keywordType` (可选): 主体类型 - name、nameId、regNumber、socialCreditCode

**返回值**:
- `name`: 企业名称
- `operStatus`: 经营状态
- `business`: 经营范围
- `industry`: 行业信息
- `regCapital`: 注册资本
- 其他工商基础字段

### 3. enterprise_get_enterprise_profile
**功能**: 企业简介查询

根据企业标识查询企业简介信息。

**参数**:
- `matchKeyword` (必需): 企业名称/注册号/统一社会信用代码/企业id
- `keywordType` (可选): 主体类型 - name、nameId、regNumber、socialCreditCode

**返回值**:
- `desc`: 企业简介描述

### 4. enterprise_get_enterprise_tags
**功能**: 企业标签查询

查询企业主营业务、融资、规模、高新、专精特新等标签。

**参数**:
- `matchKeyword` (必需): 企业名称/注册号/统一社会信用代码/企业id
- `keywordType` (可选): 主体类型 - name、nameId、regNumber、socialCreditCode

**返回值**:
- `businessTags`: 主营业务标签
- `financingSeries`: 融资轮次
- `enterpriseScaleAlgValue`: 企业规模
- `isHighTechEnterprise`: 是否高新企业
- `isSpecializedAndNew`: 是否专精特新
- 其他企业标签字段

### 5. enterprise_get_enterprise_holder_info
**功能**: 企业控股股东信息查询

根据企业标识查询企业控股股东信息。

**参数**:
- `matchKeyword` (必需): 企业名称/注册号/统一社会信用代码/企业id
- `keywordType` (可选): 主体类型 - name、nameId、regNumber、socialCreditCode

**返回值**:
- `holderList`: 股东列表
- `stockHolderList`: 最新公示股东列表

### 6. enterprise_get_enterprise_invest_info
**功能**: 企业对外投资信息查询

根据企业标识查询企业对外投资信息。

**参数**:
- `matchKeyword` (必需): 企业名称/注册号/统一社会信用代码/企业id
- `keywordType` (可选): 主体类型 - name、nameId、regNumber、socialCreditCode
- `pageIndex` (可选): 页码 - 从1开始
- `pageSize` (可选): 分页大小

**返回值**:
- `total`: 总数
- `resultList`: 对外投资企业列表

### 7. enterprise_get_enterprise_branch_info
**功能**: 企业分支机构信息查询

根据企业标识查询企业分支机构信息。

**参数**:
- `matchKeyword` (必需): 企业名称/注册号/统一社会信用代码/企业id
- `keywordType` (可选): 主体类型 - name、nameId、regNumber、socialCreditCode
- `pageIndex` (可选): 页码 - 从1开始
- `pageSize` (可选): 分页大小

**返回值**:
- `total`: 总数
- `resultList`: 分支机构列表

### 8. enterprise_get_enterprise_main_person_info
**功能**: 企业主要人员信息查询

根据企业标识查询企业主要人员信息。

**参数**:
- `matchKeyword` (必需): 企业名称/注册号/统一社会信用代码/企业id
- `keywordType` (可选): 主体类型 - name、nameId、regNumber、socialCreditCode
- `pageIndex` (可选): 页码 - 从1开始
- `pageSize` (可选): 分页大小

**返回值**:
- `total`: 总数
- `resultList`: 主要人员列表

### 9. supply_get_down_stream_products
**功能**: 下游产品目录查询

根据供应链产品关键词查询下游产品目录。

**参数**:
- `keywords` (必需): 供应链产品关键词，多个词中间用英文逗号分隔

**返回值**:
- `total`: 总数
- `resultList`: 下游产品目录
  - `industry`: 下游行业名称
  - `products`: 下游产品列表

### 10. supply_get_down_stream_enterprises
**功能**: 下游企业清单查询

根据具体产品名称查询下游企业列表。

**参数**:
- `keywords` (必需): 供应链产品关键词，多个词中间用英文逗号分隔
- `mainProducts` (可选): 下游产品，多个词中间用英文逗号分隔
- `isForeignTrade` (可选): 是否外贸企业 - 是、否
- `factoryInspectionType` (可选): 是否验厂 - 是、否
- `foundTimeStart` (可选): 成立时间开始，格式 yyyy-mm-dd
- `foundTimeEnd` (可选): 成立时间截至，格式 yyyy-mm-dd
- `address` (可选): 地区，例如“广东省,深圳市”或“广东省”
- `isTopEnterprise` (可选): 是否500强企业 - 是、否
- `isHighTechEnterprise` (可选): 是否高新企业 - 是、否
- `isGazelleEnterprise` (可选): 是否瞪羚企业 - 是、否
- `isUnicornEnterprise` (可选): 是否独角兽企业 - 是、否
- `hasStock` (可选): 是否上市企业 - 是、否
- `hasDevice` (可选): 是否机械设备企业 - 是、否
- `hasPack` (可选): 是否包装包材企业 - 是、否
- `regCapitalMin` (可选): 注册资本最小值，单位万元
- `regCapitalMax` (可选): 注册资本最大值，单位万元
- `pageIndex` (可选): 页码 - 从1开始
- `pageSize` (可选): 分页大小

**返回值**:
- `total`: 总数
- `resultList`: 下游企业列表
  - `enterpriseId`: 企业ID
  - `name`: 企业名称
  - `city`: 城市
  - `province`: 省份
  - `mainProducts`: 主营产品
  - `factoryRecommendReason`: 推荐理由
  - `regCapital`: 注册资本信息

### 11. advanced_filter_get_enterprise_count
**功能**: 高级筛选获取企业数量

通过旷湖高筛条件组查询符合要求的企业数量。`filter` 可直接传 JSON object，也可传 JSON 字符串；MCP 会校验并转换为高筛产品要求的紧凑 JSON 字符串。旧版扁平字段继续兼容。

**参数**:
- `filter` (推荐): 顶层直接包含 `must` / `should` 的高筛条件组
- `operStatus` (可选): 营业状态，接受逗号分隔字符串、JSON 字符串数组或字符串数组，例如 `"营业,吊销"`、`["营业","吊销"]` 或 `"!吊销"`
- `address` (可选，仅旧版扁平模式): 上游要求二维地区路径 JSON 字符串，例如 `[["广东省"]]`、`[["北京市"],["广东省","广州市"]]`。也可传 `"广东省"`、`"广东省,深圳市"` 或对应数组，MCP 会自动校验并转换
- `industries` (可选): 行业筛选条件，输入形式同 `operStatus`
- `enterpriseType` (可选): 企业类型筛选条件，输入形式同 `operStatus`
- `name` (可选): 企业名称包含/排除条件，输入形式同 `operStatus`
- `foundTimeGte` (可选): 成立时间起始，必须是有效的 `yyyy-mm-dd`
- `foundTimeLte` (可选): 成立时间截至，必须是有效的 `yyyy-mm-dd`
- `regCapitalRmbGte` (可选): 注册资本最小值，单位万元，接受 JSON number 或数值字符串
- `regCapitalRmbLte` (可选): 注册资本最大值，单位万元，接受 JSON number 或数值字符串
- `totalPayAmountGte` (可选): 实缴资本最小值，单位万元，接受 JSON number 或数值字符串
- `totalPayAmountLte` (可选): 实缴资本最大值，单位万元，接受 JSON number 或数值字符串

两个旧版高级筛选商品共用同一套适配逻辑：多值数组转换为上游逗号分隔字符串，`address` 转换为紧凑二维路径 JSON，日期和非负数值在调用前校验，且下限不能大于上限。非法参数返回带商品身份的结构化 `参数错误`，不会调用上游。

使用 `filter` 时不要同时传扁平字段。完整条件组查询产品 ID 为 `690dcb1b9c9dc8d0ff3c40eb`，上游只接收 `filter`、`pageIndex`、`pageSize`；页码从 `1` 开始，每页最多 `50` 条。

**返回值**:
- `total`: 符合条件的企业数量

### 12. advanced_filter_get_enterprise_list
**功能**: 高级筛选获取企业清单

通过高级筛选条件查询全国符合要求的企业清单。推荐直接传入 `filter` 条件组；完整条件组产品支持 `pageIndex` / `pageSize` 分页。旧版扁平模式可分页获取最多500条。

**参数**:
- `filter` (推荐): JSON object 或 JSON 字符串
- `operStatus` / `industries` / `enterpriseType` / `name` 支持逗号分隔字符串、JSON 字符串数组或字符串数组；日期、金额参数的校验和适配同 `advanced_filter_get_enterprise_count`
- `address` (旧版扁平模式): 接受以下输入，传给上游时统一转换为紧凑二维路径 JSON 字符串：
  - 省份：`"广东省"`、`["广东省"]` 或 `[["广东省"]]` -> `[["广东省"]]`
  - 省市：`"广东省,深圳市"` 或 `[["广东省","深圳市"]]`
  - 多地区：`"北京市;广东省,广州市"` 或 `[["北京市"],["广东省","广州市"]]`
  - 直辖市可单独传 `"北京市"`、`"上海市"`、`"天津市"`、`"重庆市"`；非直辖市不能脱离省份单独传入，例如不要只传 `"深圳市"`
- `pageIndex` / `pageSize`: 页码从1开始；旧版扁平模式一页最大10条，`filter` 模式一页最大50条。`filter` 模式会把两个分页字段传给上游，且上游参数严格限制为 `filter`、`pageIndex`、`pageSize`

查询“广东省营业状态且名称包含无人机”的最简扁平调用为：

```json
{"operStatus":"营业","address":"广东省","name":"无人机"}
```

MCP 会把其中的 `address` 转换为上游所需的 `[["广东省"]]`。若使用推荐的 `filter` 模式，则省级树形值不带“省”，且不能再同时传扁平参数：

```json
{"filter":{"must":[{"operStatus_v2":[{"eq":[["营业"]]}]},{"address":[{"eq":[["广东"]]}]},{"name":[{"in":["无人机"]}]}]}}
```

**返回值**:
- `total`: 总数
- `resultList`: 企业清单列表

#### 高筛条件组规则

- 顶层只允许 `must` / `should`，不要添加 `filter`、`condition`、`query` 包装层。
- 字段条件格式为 `{"字段名":[{"操作符":值}]}`。
- 推荐每个 `must` / `should` 数组项只放一个字段；若传入 `{"字段A":[...],"字段B":[...]}`，MCP 会按原顺序自动拆分为两个单字段条件再校验。
- 支持 `in`、`nin`、`eq`、`neq`、`gte`、`lte`、`gt`、`lt`、`exist`。
- 高筛不会执行顶层 `must_not`。排除条件必须使用字段级 `nin` / `neq` 并放入 `must`。
- `address`、`industriesV2`、`operStatus_v2`、`enterpriseType` 的 `eq` / `neq` 使用路径数组的数组。
- `addressValue` 是详细地址关键词字段，使用 `in` / `nin` 字符串数组，不要与注册地址树形字段混用。

#### 高筛维度发现 Resources

MCP 当前提供 23 个 HandaaS 数据工具，另提供只读 Resources 帮助模型在组装 `filter` 前查询支持的维度。Resources 只公开随包发布的平台字段配置，不执行查询、不消耗产品调用次数，也不替代伴随 Skill 的条件规划。

| Resource | 用途 |
| --- | --- |
| `handaas://high-screen/guide` | 常用维度分组、操作符、输入示例和常见组合 |
| `handaas://high-screen/fields` | 369 个高筛字段的完整目录、分类、操作符和 `options_from` |
| `handaas://high-screen/fields/{field}` | 单字段的操作符、输入约束、示例条件、枚举样例及枚举资源地址 |
| `handaas://high-screen/options/{source}` | 指定枚举源或树形选项源的全部合法路径 |

推荐流程：

1. 读取 `handaas://high-screen/guide` 选择常用筛选维度。
2. 对不熟悉的字段读取 `handaas://high-screen/fields/{field}`。
3. 若字段详情包含 `options_resource`，继续读取该资源确认合法枚举路径。
4. 由 [产业链处理 Skill](https://github.com/handaas/industry-chain-processing-skill) 组装 `must` / `should` 条件。
5. 调用 `advanced_filter_get_enterprise_list(filter=...)` 执行现有高筛产品。

常用维度包括：

- 企业基础：`name`、`operStatus_v2`、`address`、`addressValue`、`enterpriseType`、`foundTime`、`industriesV2`
- 主营业务与产品：`businessKeywords`（业务关键词）、`businessTags`（主营业务）、`business`（经营范围）、`desc`（企业简介）、`ecShopProducts`（电商主营产品）、`brandProductList`（品牌主营产品）
- 规模资本：`regCapitalRmb`、`totalPayAmount`、`enterpriseScaleAlgV2`、`annualTurnoverAlgV2`、`arInsuranceNumber`
- 成长资质：`isHighTechEnt`、`isSpecializedAndNewV2`、`isSpecializedAndNewGiantV2`、`isUnicornEnt`、`hasStock`、`isTopEnterprise`、`financingSeries`
- 知识产权与市场：`hasPatent`、`patentNumber`、`patentNameList`、`hasBidding`、`biddingAnncTitleList`

#### 配置驱动校验与修正

高筛字段契约随 Python 包发布，不依赖部署机器上的额外文件：

- `server/config/high_screen_fields.json`：369 个字段的中文名称、分类、`action.type`、`input.type`、单位、关键词数量、数值范围、枚举来源和允许操作符。
- `server/config/high_screen_options.json`：97 组枚举和树形选项，包括注册地址、行业、企业类型、营业状态、专利类型和招投标角色等。
- 当前平台配置版本：`0.14.3`。

组装 `filter` 时 MCP 会依据配置执行：

1. 拒绝未知字段，并返回相近字段名建议。
2. 按字段控件限制操作符，例如存在型字段只允许 `exist`，范围字段允许 `gte/lte/gt/lt/eq/neq`。
3. 对语义明确的错误安全修正，例如树形枚举 `in` → `eq`、关键词字段 `eq` → `in`、字符串关键词 → 字符串数组。
4. 校验树形路径是否存在于平台枚举中，避免省市层级、行业层级或枚举值传错。
5. 校验字段配置中的关键词数量、总长度、数字上下限、日期格式和预设条件。
6. 将修正后的条件序列化为上游要求的紧凑 `params.filter` JSON 字符串。

不能确定语义的错误不会猜测修正，例如未知字段、错误省市组合、无效行业路径和超出字段限制的关键词会直接返回 `参数错误` 与具体 JSON 路径。

注册地址示例：

```json
{"must":[{"address":[{"eq":[["广东"]]}]}]}
```

深圳市示例：

```json
{"must":[{"address":[{"eq":[["广东","深圳市"]]}]}]}
```

在 `filter.address` 内，MCP 也会把 `"广东省"`、`"广东省,深圳市"` 或 `["广东省","深圳市"]` 归一化为上述无“省”后缀的平台树形路径；多个地区字符串用分号分隔，例如 `"广东省,深圳市;江苏省,苏州市"`。城市不能脱离省级路径单独传入。注意这与扁平 `address` 最终传给旧版产品的 `[["广东省"]]` 格式不同。

工商、业务关键词与地址组合示例：

```json
{
  "must": [
    {"operStatus_v2": [{"eq": [["营业"]]}]},
    {"enterpriseType": [{"neq": [["个体户"]]}]},
    {"address": [{"eq": [["广东"]]}]},
    {"name": [{"nin": ["贸易", "培训"]}]},
    {"should": [
      {"businessKeywords": [{"in": ["工业机器人", "机器人控制器"]}]},
      {"businessTags": [{"in": ["工业机器人", "机器人控制器"]}]},
      {"business": [{"in": ["工业机器人", "机器人控制器"]}]},
      {"desc": [{"in": ["工业机器人", "机器人控制器"]}]},
      {"ecShopProducts": [{"in": ["工业机器人", "机器人控制器"]}]}
    ]}
  ]
}
```

### 13. patent_bigdata_patent_search
**功能**: 专利信息搜索

通过输入专利名称、申请号、申请人或代理机构等信息进行精准或模糊搜索，并按指定专利类型进行筛选。

**参数**:
- `matchKeyword` (必需): 专利名称/专利申请号/公布公告号/申请人/代理机构
- `pageSize` (可选): 分页大小 - 一页最多获取50条数据
- `patentType` (可选): 专利类型 - 发明申请、实用新型、发明授权、外观设计
- `keywordType` (可选): 搜索方式 - 专利名称、申请号/公开号、申请人、代理机构
- `pageIndex` (可选): 页码 - 从1开始

**返回值**:
- `total`: 专利总数
- `resultList`: 专利列表

### 14. patent_bigdata_patent_stats
**功能**: 企业专利统计分析

根据企业信息查询企业专利情况，包括专利状态分布、专利申请与授权趋势、按专利类型分布等。

**参数**:
- `matchKeyword` (必需): 企业名称/注册号/统一社会信用代码/企业id
- `keywordType` (可选): 主体类型 - name、nameId、regNumber、socialCreditCode

**返回值**:
- `patentDivAppLegalStat`: 专利状态分布
- `patentTypeAppTimeStat`: 专利申请趋势
- `patentTypePubTimeStat`: 专利授权趋势
- `patentTypeStat`: 专利类型分布

### 15. bid_bigdata_bid_win_stats
**功能**: 企业中标统计分析

根据企业名称、统一社会信用代码等获取企业标讯信息中中标统计项。

**参数**:
- `matchKeyword` (必需): 企业名称/注册号/统一社会信用代码/企业id
- `keywordType` (可选): 主体类型 - name、nameId、regNumber、socialCreditCode

**返回值**:
- `winbidAmountStatList`: 中标金额分布
- `winbidAreaStat`: 区域分布
- `winbidStatList`: 中标标的分布
- `winbidTrend`: 中标趋势

### 16. bid_bigdata_bidding_info
**功能**: 企业招投标信息查询

查询企业参与的招投标信息，包括公告类型、项目地区、公告详情及相关企业信息。

**参数**:
- `matchKeyword` (必需): 企业名称/注册号/统一社会信用代码/企业id
- `pageSize` (可选): 分页大小 - 一页最多获取50条数据
- `keywordType` (可选): 主体类型 - name、nameId、regNumber、socialCreditCode
- `pageIndex` (可选): 页码 - 从1开始

**返回值**:
- `total`: 总数
- `resultList`: 招投标信息列表

### 17. bid_bigdata_tender_stats
**功能**: 企业招标统计分析

根据企业名称、统一社会信用代码等获取企业标讯信息中招标统计项。

**参数**:
- `matchKeyword` (必需): 企业名称/注册号/统一社会信用代码/企业id
- `keywordType` (可选): 主体类型 - name、nameId、regNumber、socialCreditCode

**返回值**:
- `tenderAmountStatList`: 招标金额分布
- `tenderAreaStat`: 区域分布
- `tenderStatList`: 招标标的分布
- `tenderTrend`: 招标趋势

### 18. bid_bigdata_procurement_stats
**功能**: 企业采购统计分析

根据企业名称或ID获取企业采购统计信息，包括采购产品分布、采购区域分布等。

**参数**:
- `matchKeyword` (必需): 企业名称/注册号/统一社会信用代码/企业id
- `keywordType` (可选): 主体类型 - name、nameId、regNumber、socialCreditCode

**返回值**:
- `purchasingProductStatList`: 采购产品分布
- `purchasingAreaStatList`: 采购区域分布

### 19. bid_bigdata_bid_search
**功能**: 招投标公告搜索

查询和筛选招投标公告信息，支持按公告类型、地区、发布时间、搜索模式、项目金额等过滤。

**参数**:
- `matchKeyword` (可选): 搜索关键词
- `biddingType` (可选): 招标类型JSON数组字符串，例如 `["招标公告","中标公告"]`
- `biddingRegion` (可选): 项目地区JSON数组字符串，例如 `[["福建省","厦门市"]]`
- `biddingAnncPubStartTime` (可选): 公告发布开始时间，格式 yyyy-mm-dd
- `biddingAnncPubEndTime` (可选): 公告发布结束时间，格式 yyyy-mm-dd
- `searchMode` (可选): 搜索模式 - 标题匹配、标的物匹配、全文匹配
- `biddingProjectMaxAmount` (可选): 项目金额最大值，单位万元
- `biddingPurchasingType` (可选): 招标单位类型，例如“政府,学校”
- `biddingProjectMinAmount` (可选): 项目金额最小值，单位万元
- `pageIndex` (可选): 页码
- `pageSize` (可选): 分页大小 - 一页最多获取50条

**返回值**:
- `total`: 总数
- `resultList`: 招投标公告列表

### 20. bid_bigdata_planned_projects
**功能**: 企业拟建公告查询

查询企业拟建公告信息，包括项目内容、建设地点、待采设备、发布时间等。

**参数**:
- `matchKeyword` (必需): 企业名称/注册号/统一社会信用代码/企业id
- `pageIndex` (可选): 页码 - 从1开始
- `pageSize` (可选): 分页大小 - 一页最多获取50条数据
- `keywordType` (可选): 主体类型 - name、nameId、regNumber、socialCreditCode

**返回值**:
- `total`: 总数
- `resultList`: 拟建项目列表

### 21. policy_bigdata_policy_search
**功能**: 政策搜索

根据关键词、政策类型、发布机构、地区和发布时间，搜索政策法规、申报指南或公示公告。

**参数**:
- `matchKeyword` (必需): 政策关键词，例如“智能网联汽车”“自动驾驶”“低空经济”“机器人”
- `pnType` (可选): 全部 / 申报指南 / 公示公开 / 其他政策
- `agency` (可选): 发布机构
- `address` (可选): 地区，支持 `[["福建省"],["贵州省","安顺市","平坝县"]]`、`"广东省"`、`"广东省,深圳市"`、`"国家部委"`、`"北京/上海/天津/重庆"`
- `policyPubStartTime` / `policyPubEndTime` (可选): 发布时间范围，格式 `yyyy-mm-dd`
- `pageSize` / `pageIndex` (可选): 分页参数

**返回值**:
- `total`: 总数
- `resultList`: 政策列表，通常包含 `pnId`、`pnTitle`、`pnAgency`、`pnType`、`pnPublishDate`、`pnRegion`、`pnText`

### 22. policy_bigdata_policy_info
**功能**: 政策详情查询

根据政策 ID 查询政策详情，包括发布机构、正文、原文链接、附件、关联项目、资助金额和申报时间等。

**参数**:
- `matchKeyword` (必需): 政策 ID

### 23. policy_bigdata_approved_project_stats
**功能**: 企业获批政策项目统计

根据企业名称、注册号、统一社会信用代码或企业 ID，查询企业获批国家/省/市/区各级政策项目、主管机构、补贴金额和年度趋势。

**参数**:
- `matchKeyword` (必需): 企业名称/注册号/统一社会信用代码/企业id
- `keywordType` (可选): `name`、`nameId`、`regNumber`、`socialCreditCode`

## 使用场景

1. **产业研究**: 使用企业搜索、企业业务信息和企业标签识别产业链相关企业
2. **供应链拓展**: 根据上游产品查询下游产品和下游企业清单
3. **招商线索挖掘**: 结合高级筛选、企业标签、供应链企业清单发现潜在招商对象
4. **技术与创新分析**: 查询企业专利信息和专利统计，评估企业技术储备
5. **项目与采购分析**: 查询招投标、拟建项目和采购统计，判断企业项目活跃度
6. **区域政策分析**: 查询某产业在国家部委和各省市的政策法规、申报指南、公示公告，对比支持方向和政策强度
7. **企业画像补全**: 查询工商、简介、标签、股东、投资、分支机构、主要人员和获批政策项目统计

## 使用注意事项

1. **企业全称要求**: 在调用需要企业全称的接口时，如果没有企业全称则先调用企业关键词模糊查询接口获取企业全称或企业ID
2. **分页限制**: 列表类接口通常一页最多获取50条数据；旧版扁平高级筛选一页最大10条且最多获取500条。完整 `filter` 条件组支持分页，`pageIndex` 从1开始，`pageSize` 最大50
3. **复杂参数格式**: 高筛 `filter` 可传 JSON object 或字符串；注册地址使用省/市/区路径，详细地址关键词使用 `addressValue in/nin`；格式错误会返回产品、字段和 JSON 路径
4. **Remote优先**: 推荐使用官方Remote服务，客户端只需要配置平台token
5. **凭证安全**: 本地启动时不要提交 `.env`、secret_id、secret_key 或签名
6. **接口权限**: 可用数据取决于账号已开通的数据产品权限
7. **费用提醒**: 真实查询可能产生接口调用费用，请按平台开通规则使用

## 使用提问示例

### enterprise_get_keyword_search (企业关键词模糊查询)
1. 帮我查找包含“eVTOL”的企业信息
2. 搜索与“人形机器人”相关的企业列表
3. 查询名称或产品中包含“减速器”的公司

### supply_get_down_stream_products (下游产品目录查询)
1. 查询“动力电池”的下游产品目录
2. 帮我看“碳纤维材料”可以关联哪些下游产品
3. 根据“激光雷达”查询下游行业和产品

### supply_get_down_stream_enterprises (下游企业清单查询)
1. 查询“动力电池”的下游企业清单
2. 帮我找广东省内“电机控制器”相关下游企业
3. 查询“工业机器人”相关的高新技术下游企业

### advanced_filter_get_enterprise_list (高级筛选获取企业清单)
1. 使用 `address eq [["广东"]]` 查询广东省营业中的无人机相关企业
2. 组合 `industriesV2`、`businessKeywords`、`business` 与 `desc` 筛选高端装备制造企业
3. 使用 `address eq [["广东","深圳市"]]` 和 `addressValue in ["南山区"]` 查询深圳南山区机器人企业

### patent_bigdata_patent_search (专利信息搜索)
1. 搜索关键词为“飞控系统”的专利信息
2. 查询某公司申请的所有发明专利
3. 查找申请号为某编号的专利详情

### patent_bigdata_patent_stats (企业专利统计分析)
1. 分析某公司的专利申请趋势
2. 查询某企业的专利类型分布统计
3. 查看某企业专利状态分布

### bid_bigdata_bidding_info (企业招投标信息查询)
1. 查询某企业最近参与的招投标信息
2. 查看某公司中标项目和招标项目记录
3. 查询某企业在低空经济相关项目中的招投标情况

### bid_bigdata_bid_search (招投标公告搜索)
1. 搜索标题包含“无人机”的中标公告
2. 查询广东省最近发布的低空经济招标公告
3. 查找项目金额大于1000万元的数据中心招标项目

### policy_bigdata_policy_search (政策搜索)
1. 查询国家部委和广东省最近发布的“智能网联汽车”相关政策
2. 对比北京、上海、江苏、广东在“自动驾驶”方向的政策重点
3. 搜索“低空经济”相关申报指南和公示公告

### policy_bigdata_approved_project_stats (企业获批政策项目统计)
1. 查询某企业近年获批政策项目数量和补贴金额趋势
2. 分析某企业政策项目主要来自哪些主管机构

## 开发与测试

不需要真实凭证即可运行单元测试：

```bash
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
python -m py_compile server/*.py
python -m build
```

真实接口联调前，请确认 `.env` 只保存在本地，并从最小 `pageSize` 开始测试。项目 CI 会在 Python 3.10 和 3.12 上执行测试。

贡献说明见 [CONTRIBUTING.md](CONTRIBUTING.md)，安全问题处理方式见 [SECURITY.md](SECURITY.md)。

## License

[MIT](LICENSE)
