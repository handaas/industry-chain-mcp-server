# 产业链分析服务

[该MCP服务封装产业链分析常用的HandaaS已有数据接口，包括企业大数据、供应链潜客推荐、专利大数据和招投标大数据等，帮助用户进行产业研究、企业发现、供应链拓展、知识产权分析和招投标线索分析。](https://www.handaas.com/)


## 主要功能

- 🔍 企业关键词模糊搜索
- 🏢 企业基础信息与业务标签查询
- 🔗 供应链下游产品与企业查询
- 📄 专利信息搜索与企业专利统计
- 📊 招投标信息与采购统计分析
- 🧭 高级企业筛选

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

编辑 `.env` 文件，配置以下环境变量：

```env
INTEGRATOR_ID=your_integrator_id
SECRET_ID=your_secret_id
SECRET_KEY=your_secret_key
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

### 4. enterprise_get_enterprise_business_info
**功能**: 企业业务信息查询

查询企业业务相关信息，用于识别企业主营业务、产品服务和产业链相关能力。

**参数**:
- `matchKeyword` (必需): 企业名称/注册号/统一社会信用代码/企业id
- `keywordType` (可选): 主体类型 - name、nameId、regNumber、socialCreditCode

**返回值**:
- 企业业务、主营产品、能力标签等相关信息

### 5. enterprise_get_enterprise_tags
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

### 6. enterprise_get_enterprise_holder_info
**功能**: 企业控股股东信息查询

根据企业标识查询企业控股股东信息。

**参数**:
- `matchKeyword` (必需): 企业名称/注册号/统一社会信用代码/企业id
- `keywordType` (可选): 主体类型 - name、nameId、regNumber、socialCreditCode

**返回值**:
- `holderList`: 股东列表
- `stockHolderList`: 最新公示股东列表

### 7. enterprise_get_enterprise_invest_info
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

### 8. enterprise_get_enterprise_branch_info
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

### 9. enterprise_get_enterprise_main_person_info
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

### 10. supply_get_down_stream_products
**功能**: 下游产品目录查询

根据供应链产品关键词查询下游产品目录。

**参数**:
- `keywords` (必需): 供应链产品关键词，多个词中间用英文逗号分隔

**返回值**:
- `total`: 总数
- `resultList`: 下游产品目录
  - `industry`: 下游行业名称
  - `products`: 下游产品列表

### 11. supply_get_down_stream_enterprises
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

### 12. advanced_filter_get_enterprise_count
**功能**: 高级筛选获取企业数量

通过高级筛选条件查询全国符合要求的企业数量。该接口只返回数量，如需查询企业清单请使用 `advanced_filter_get_enterprise_list`。

**参数**:
- `operStatus` (可选): 营业状态，例如“营业,吊销”或“!吊销”
- `address` (可选): 地址筛选条件
- `industries` (可选): 行业筛选条件
- `enterpriseType` (可选): 企业类型筛选条件
- `name` (可选): 企业名称筛选条件
- `foundTimeGte` (可选): 成立时间起始，格式 yyyy-mm-dd
- `foundTimeLte` (可选): 成立时间截至，格式 yyyy-mm-dd
- `regCapitalRmbGte` (可选): 注册资本最小值，单位万元
- `regCapitalRmbLte` (可选): 注册资本最大值，单位万元
- `totalPayAmountGte` (可选): 实缴资本最小值，单位万元
- `totalPayAmountLte` (可选): 实缴资本最大值，单位万元

**返回值**:
- `total`: 符合条件的企业数量

### 13. advanced_filter_get_enterprise_list
**功能**: 高级筛选获取企业清单

通过高级筛选条件查询全国符合要求的企业清单列表，最多返回500条。

**参数**:
- 同 `advanced_filter_get_enterprise_count`
- `pageIndex` (可选): 页码，最大页码为50
- `pageSize` (可选): 分页大小，一页最大10条

**返回值**:
- `total`: 总数
- `resultList`: 企业清单列表

### 14. patent_bigdata_patent_search
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

### 15. patent_bigdata_patent_stats
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

### 16. bid_bigdata_bid_win_stats
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

### 17. bid_bigdata_bidding_info
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

### 18. bid_bigdata_tender_stats
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

### 19. bid_bigdata_procurement_stats
**功能**: 企业采购统计分析

根据企业名称或ID获取企业采购统计信息，包括采购产品分布、采购区域分布等。

**参数**:
- `matchKeyword` (必需): 企业名称/注册号/统一社会信用代码/企业id
- `keywordType` (可选): 主体类型 - name、nameId、regNumber、socialCreditCode

**返回值**:
- `purchasingProductStatList`: 采购产品分布
- `purchasingAreaStatList`: 采购区域分布

### 20. bid_bigdata_bid_search
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

### 21. bid_bigdata_planned_projects
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

## 使用场景

1. **产业研究**: 使用企业搜索、企业业务信息和企业标签识别产业链相关企业
2. **供应链拓展**: 根据上游产品查询下游产品和下游企业清单
3. **招商线索挖掘**: 结合高级筛选、企业标签、供应链企业清单发现潜在招商对象
4. **技术与创新分析**: 查询企业专利信息和专利统计，评估企业技术储备
5. **项目与采购分析**: 查询招投标、拟建项目和采购统计，判断企业项目活跃度
6. **企业画像补全**: 查询工商、简介、业务、股东、投资、分支机构和主要人员信息

## 使用注意事项

1. **企业全称要求**: 在调用需要企业全称的接口时，如果没有企业全称则先调用企业关键词模糊查询接口获取企业全称或企业ID
2. **分页限制**: 列表类接口通常一页最多获取50条数据，高级筛选企业清单一页最大10条、最多返回500条
3. **JSON参数格式**: `bid_bigdata_bid_search` 的 `biddingType`、`biddingRegion` 需要传入合法JSON字符串
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
1. 查询广东省营业状态且名称包含“无人机”的企业清单
2. 筛选高端装备制造相关企业并返回企业列表
3. 查询成立时间在2020年后的机器人相关企业

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
