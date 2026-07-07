# 产业链分析 MCP 服务

参考 HandaaS [`patent-mcp-server`](https://github.com/handaas/patent-mcp-server) 的 Python FastMCP 结构重新开发，面向“旷湖产业链分析 / industry-chain-processing-skill”的 Remote MCP 服务。

## 目标

- 让用户在平台创建产业链 MCP 服务并拿到 `token` 后，`industry-chain-processing-skill` 可以直接走 Remote MCP；
- 用户不再需要分别配置 `integrator_id`、`secret_id`、`secret_key`、企业搜索 URL、各证据产品 ID；
- 本地开发/自托管仍兼容 `.env` 凭证模式。

## 工具

| Tool | 作用 |
| --- | --- |
| `industry_chain_health_check` | 检查本地自托管配置状态，不输出密钥。 |
| `industry_chain_build_search_condition` | 根据产业链、细分环节生成企业搜索条件 JSON。 |
| `industry_chain_search_enterprises` | 搜索候选企业；`dryRun=true` 时只返回脱敏请求。 |
| `industry_chain_evidence_call` | 查询工商、招聘、知识产权、招投标等证据产品。 |
| `industry_chain_link_enterprises` | 搜索候选企业并给出 `confirmed / uncertain / rejected` 挂链判断。 |

## 官方 Remote MCP 使用

平台创建服务后，客户端只需要一个 Remote MCP URL：

```json
{
  "mcpServers": {
    "industry-chain-mcp-server": {
      "type": "streamableHttp",
      "url": "https://mcp.handaas.com/industry-chain/industry_chain?token={token}"
    }
  }
}
```

> `{token}` 由平台生成。Remote MCP 由平台托管真实接口权限，用户侧不需要单独配置各数据产品凭证。

`industry-chain-processing-skill` 已支持读取同一个 token：

```bash
export INDUSTRY_CHAIN_MCP_TOKEN="你的平台 token"
# 如平台路径不同，也可直接指定完整 URL：
export INDUSTRY_CHAIN_MCP_URL="https://mcp.handaas.com/industry-chain/industry_chain?token=你的平台 token"
```

之后 skill 的 `link_enterprises.py`、`enterprise_search_preview.py`、`evidence_call.py` 会优先走 Remote MCP；只有未配置 token 时才回退到旧的本地 DAAS 配置。

## 本地快速启动

```bash
python -m venv mcp_env && source mcp_env/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，仅本地自托管需要填写真实凭证
python server/mcp_server.py streamable-http
```

服务默认启动在：

```text
http://127.0.0.1:8000/mcp
```

Cursor / Cherry Studio 本地配置示例：

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

## STDIO 模式

```json
{
  "mcpServers": {
    "industry-chain-mcp-server": {
      "command": "python",
      "args": ["/path/to/industry-chain-mcp-server/server/mcp_server.py"],
      "env": {
        "INTEGRATOR_ID": "your_integrator_id",
        "SECRET_ID": "your_secret_id",
        "SECRET_KEY": "your_secret_key"
      }
    }
  }
}
```

## 验证

```bash
python -m py_compile server/mcp_server.py
python -m unittest discover -s tests
```

不配置真实凭证也可以验证 dry-run：

```bash
python - <<'PY'
from server.mcp_server import industry_chain_link_enterprises
print(industry_chain_link_enterprises("低空经济", "eVTOL整机制造", dryRun=True))
PY
```

## 安全边界

- 不要提交 `.env` 或真实 token；
- 工具返回会脱敏 `token`、`secret_*`、`signature`；
- `industry_chain_link_enterprises(withEvidence=true)` 可能触发多个付费证据接口，默认最多核验 3 家样本企业；
- `dryRun=true` 不调用网络。
