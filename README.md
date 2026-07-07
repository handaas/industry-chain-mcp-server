# 产业链分析服务

[该MCP服务提供产业链分析与企业挂链查询功能，包括产业链细分环节搜索条件生成、候选企业搜索、企业证据核验和挂链判断等，帮助用户进行产业研究、招商线索挖掘、企业归位和产业链图谱建设。](https://www.handaas.com/)


## 主要功能

- 🔍 产业链企业搜索条件生成
- 🏢 产业链候选企业搜索
- 📎 企业挂链证据查询
- 📊 候选企业挂链判断
- ⚙️ MCP服务配置检查

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

```bash
python -m venv mcp_env && source mcp_env/bin/activate
pip install -r requirements.txt
```

### 3. 环境配置

复制环境变量模板并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件。本地自托管模式需要配置以下环境变量：

```env
INTEGRATOR_ID=your_integrator_id
SECRET_ID=your_secret_id
SECRET_KEY=your_secret_key

HIGH_SCREEN_URL=https://example.com/enterprise-search-endpoint
HIGH_SCREEN_PRODUCT_ID=your_real_product_id_for_enterprise_search
HIGH_SCREEN_SECRET_ID=your_high_screen_secret_id
HIGH_SCREEN_SECRET_KEY=your_high_screen_secret_key
```

### 4. streamable-http启动服务

```bash
python server/mcp_server.py streamable-http
```

服务将在 `http://localhost:8000` 启动。

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

```json
{
  "mcpServers": {
    "industry-chain-mcp-server": {
      "command": "uv",
      "args": ["run", "mcp", "run", "{workdir}/server/mcp_server.py"],
      "env": {
        "PATH": "{workdir}/mcp_env/bin:$PATH",
        "PYTHONPATH": "{workdir}/mcp_env",
        "INTEGRATOR_ID": "your_integrator_id",
        "SECRET_ID": "your_secret_id",
        "SECRET_KEY": "your_secret_key",
        "HIGH_SCREEN_URL": "https://example.com/enterprise-search-endpoint",
        "HIGH_SCREEN_PRODUCT_ID": "your_real_product_id_for_enterprise_search",
        "HIGH_SCREEN_SECRET_ID": "your_high_screen_secret_id",
        "HIGH_SCREEN_SECRET_KEY": "your_high_screen_secret_key"
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

### 注意：integrator_id、secret_id、secret_key、high_screen配置及token需要登录 https://www.handaas.com/ 进行注册开通平台获取。使用官方Remote服务时，客户端只需要配置token，不需要在本地单独配置各数据接口凭证。


## 可用工具

### 1. industry_chain_health_check
**功能**: MCP服务配置检查

检查产业链MCP服务的本地自托管配置是否完整，并返回可用的证据产品、Remote MCP使用提示和缺失配置项。该工具不会返回明文密钥、签名或token。

**参数**:
- 无

**返回值**:
- `service`: 服务名称
- `version`: 服务版本
- `remote_token_mode`: 官方Remote MCP token使用说明
- `local_daas_configured`: 本地DAAS凭证是否已配置
- `local_high_screen_configured`: 本地企业搜索配置是否已配置
- `configured_evidence_products`: 已配置的证据产品名称
- `missing_for_local_search`: 本地企业搜索缺失配置项
- `missing_for_local_evidence`: 本地证据查询缺失配置项

### 2. industry_chain_build_search_condition
**功能**: 产业链企业搜索条件生成

根据产业链名称、细分环节、链路、关键词、行业边界和排除词，生成可用于企业搜索的结构化条件JSON。适用于把自然语言产业链节点转换为企业检索策略。

**参数**:
- `chain` (必需): 产业链或赛道名称，例如“低空经济”
- `node` (必需): 细分产品、技术、服务或能力，例如“eVTOL整机制造”
- `path` (可选): 完整链路，用 `>` 或 `/` 分隔，例如“低空经济产业链>航空器制造>eVTOL整机制造”
- `keywords` (可选): 补充业务关键词列表
- `industries` (可选): 行业边界路径列表
- `exclude` (可选): 排除噪声词列表

**返回值**:
- `chain`: 产业链名称
- `node`: 细分环节名称
- `path`: 标准化链路
- `keyword_profile`: 自动扩展的关键词画像
  - `core`: 核心业务词
  - `evidence`: 证据核验词
  - `recruiting`: 招聘岗位词
  - `noise`: 排除噪声词
- `condition`: 企业搜索条件JSON

### 3. industry_chain_search_enterprises
**功能**: 产业链候选企业搜索

根据产业链细分环节或已生成的搜索条件调用企业搜索接口，返回候选企业列表和分页信息。可用于招商线索挖掘、产业链企业召回和图谱挂链前置筛选。

**参数**:
- `chain` (必需): 产业链或赛道名称
- `node` (必需): 细分产品、技术、服务或能力
- `path` (可选): 完整链路
- `condition` (可选): 已生成的企业搜索条件JSON，不传则自动生成
- `keywords` (可选): 补充业务关键词列表
- `industries` (可选): 行业边界路径列表
- `exclude` (可选): 排除噪声词列表
- `pageIndex` (可选): 页码，从1开始
- `pageSize` (可选): 分页大小，一页最多获取50条数据
- `dryRun` (可选): 是否只返回脱敏请求而不调用网络

**返回值**:
- `total`: 候选企业总数
- `pageIndex`: 当前页码
- `pageSize`: 当前分页大小
- `totalPages`: 总页数
- `samples`: 候选企业列表
  - `id`: 企业ID
  - `name`: 企业名称
  - `socialCreditCode`: 统一社会信用代码
  - `regCapital`: 注册资本
- `condition`: 本次使用的企业搜索条件

### 4. industry_chain_evidence_call
**功能**: 企业挂链证据查询

调用配置的企业证据产品，查询企业工商、招聘、知识产权、招投标等证据，用于判断企业是否真实匹配某个产业链细分环节。

**参数**:
- `productName` (必需): 证据产品名，例如“工商照面”“招聘明细”“知识产权统计”“企业招投标信息”
- `matchKeyword` (必需): 企业名称、企业ID、注册号或统一社会信用代码
- `keywordType` (可选): 主体类型，可选值包括 `name`、`nameId`、`regNumber`、`socialCreditCode`
- `extraParams` (可选): 额外请求参数，例如 `{ "pageIndex": 1, "pageSize": 5 }`
- `dryRun` (可选): 是否只返回脱敏请求而不调用网络

**返回值**:
- `product`: 证据产品名
- `product_id`: 数据产品ID
- `params`: 实际查询参数
- `code`: 返回状态码
- `message`: 返回描述
- `data`: 证据产品返回数据
- `response`: 原始响应数据

### 5. industry_chain_link_enterprises
**功能**: 候选企业挂链判断

完成一个产业链细分环节的候选企业搜索、可选证据查询和挂链判断，输出企业是否适合挂到该细分环节的建议。适用于产业链图谱建设、招商筛选、企业归位和人工复核前的初筛。

**参数**:
- `chain` (必需): 产业链或赛道名称
- `node` (必需): 细分产品、技术、服务或能力
- `path` (可选): 完整链路
- `keywords` (可选): 补充业务关键词列表
- `industries` (可选): 行业边界路径列表
- `exclude` (可选): 排除噪声词列表
- `pageSize` (可选): 企业搜索返回数量，一页最多获取50条数据
- `withEvidence` (可选): 是否继续调用证据产品核验样本企业
- `evidenceProducts` (可选): 证据产品名列表
- `evidenceSampleSize` (可选): 最多核验的候选企业数量
- `dryRun` (可选): 是否只返回搜索条件和脱敏请求

**返回值**:
- `chain`: 产业链名称
- `node`: 细分环节名称
- `path`: 标准化链路
- `condition`: 企业搜索条件JSON
- `preview`: 候选企业预览
  - `total`: 候选企业总数
  - `samples`: 候选企业样本
- `decisions`: 挂链判断列表
  - `enterprise_name`: 企业名称
  - `enterprise_id`: 企业ID
  - `decision`: 判断结果，`confirmed`、`uncertain` 或 `rejected`
  - `evidence_strength`: 证据强度，`strong`、`medium` 或 `weak`
  - `matched_segment`: 匹配环节
  - `reason`: 判断原因
  - `next_action`: 建议动作
- `evidence`: 企业证据结果
- `next_actions`: 后续操作建议

## 使用场景

1. **产业研究**: 拆解行业主题，生成可用于企业搜索的细分环节和关键词策略
2. **招商线索挖掘**: 围绕重点产业链节点批量召回候选企业
3. **企业归位**: 判断企业适合挂到产业链的哪个细分环节
4. **证据核验**: 结合工商、招聘、知识产权、招投标等证据判断匹配强弱
5. **产业链图谱建设**: 为产业链可视化、企业库和运营后台提供挂链建议
6. **人工复核提效**: 将企业分为确认、待复核、剔除，减少人工筛选工作量

## 使用注意事项

1. **Remote优先**: 推荐使用官方Remote MCP服务，客户端只需要配置平台token
2. **本地配置要求**: 本地自托管模式需要配置DAAS凭证和HIGH_SCREEN企业搜索参数
3. **凭证安全**: 不要提交 `.env`、真实token、secret_id、secret_key或签名
4. **分页限制**: 企业搜索一页最多获取50条数据
5. **付费接口**: `withEvidence=true` 会继续调用多个证据产品，可能产生接口费用
6. **干跑验证**: 不确定配置或费用时，先使用 `dryRun=true` 查看脱敏请求
7. **企业全称要求**: 调用需要企业全称的证据产品时，如果只有简称，建议先进行候选企业搜索确认企业全称或企业ID

## 使用提问示例

### industry_chain_build_search_condition (产业链企业搜索条件生成)
1. 帮我生成低空经济产业链中eVTOL整机制造的企业搜索条件
2. 为人形机器人产业链的减速器环节构造候选企业检索策略
3. 生成半导体设备产业链中刻蚀设备企业的搜索JSON

### industry_chain_search_enterprises (产业链候选企业搜索)
1. 查询低空经济产业链中eVTOL整机制造相关企业
2. 帮我找一批机器人控制系统相关候选企业
3. 搜索广东省内适合挂到智能传感器环节的企业

### industry_chain_evidence_call (企业挂链证据查询)
1. 查询某企业的知识产权统计，用于判断是否匹配低空飞行器环节
2. 查看某企业招聘明细中是否有飞控、航电、适航相关岗位
3. 查询某企业招投标信息，核验是否参与数据中心建设项目

### industry_chain_link_enterprises (候选企业挂链判断)
1. 分析低空经济产业链eVTOL整机制造环节，并给出候选企业挂链建议
2. 判断一批企业是否适合挂到人形机器人产业链的运动控制环节
3. 围绕半导体设备产业链做招商线索挖掘，并区分确认、待复核和剔除企业
