# HandaaS Industry Chain MCP — Codex Project Memory

This file is the repository-level operating contract for future Codex sessions. Read it before changing code or documentation.

## Mission

Maintain an open-source MCP server that exposes existing HandaaS data products for industry-chain research. The server is a data-access layer; analysis workflows belong in the companion Skill.

- Repository: `https://github.com/handaas/industry-chain-mcp-server`
- Companion Skill: `https://github.com/handaas/industry-chain-processing-skill`
- Runtime: Python 3.10+, FastMCP, `stdio` / `sse` / `streamable-http`
- Main implementation: `server/mcp_server.py`
- Public MCP endpoint when self-hosted: `/mcp`
- Health endpoints: `/health`, `/api/health`

## Non-negotiable boundaries

1. Every MCP tool must wrap an existing HandaaS product. Do not add tools that build industry chains, generate ES plans, score candidates, link enterprises, or render reports.
2. Preserve public tool names and upstream parameter names unless an intentional breaking release is approved.
3. Product IDs are stable public platform identifiers. Credentials, tokens, signatures, signed requests, customer data, and account-specific integrator URLs are private.
4. Never log or return `INTEGRATOR_ID`, `SECRET_ID`, `SECRET_KEY`, token values, signatures, or raw signed requests.
5. Keep errors structured and actionable. Distinguish missing configuration, invalid parameters, missing products, empty data, HTTP failures, timeouts, and network failures.
6. A `产品不存在` response must identify `product_key`, `product_name`, and `product_id` so operators know which product permission/configuration is missing.
7. `.env` is local-only. `.env.example` contains placeholders and public defaults only.

## Tool and product registry

`PRODUCT_IDS` and `PRODUCT_NAMES` in `server/mcp_server.py` are the source of truth. The current service exposes 23 MCP tools backed by 24 HandaaS products in these groups:

- Enterprise discovery and profile
- Supply-chain downstream products and enterprises
- Advanced enterprise filters
- Patent search and statistics
- Bidding, procurement, and planned projects
- Policy search, policy detail, and approved-project statistics

When adding or replacing a product:

1. Confirm it is an existing HandaaS product.
2. Add the stable public product ID and Chinese display name.
3. Define a narrowly typed wrapper with the upstream parameter contract.
4. Add regression tests for parameter normalization and error identity.
5. Update the README tool inventory in the same change.

Do not expose arbitrary `product_id` execution as a generic MCP tool.

## Parameter compatibility rules

- Pagination starts at `pageIndex=1`.
- General list products cap `pageSize` at 50.
- Legacy flat advanced-filter list/count calls cap `pageSize` at 10.
- `advanced_filter_get_enterprise_list` and `advanced_filter_get_enterprise_count` also accept a full high-screen `filter` condition object and route it to product `690dcb1b9c9dc8d0ff3c40eb`.
- Full high-screen `params.filter` must be a compact JSON string at the HandaaS boundary. MCP clients may pass an object or JSON string; normalize exactly once before `call_api`.
- High-screen validation is configuration-driven. `server/config/high_screen_fields.json` contains 369 field definitions and operator/normalization rules; `server/config/high_screen_options.json` contains 97 enum/tree sources. Both are public platform configuration version `0.14.3` and must ship as package data.
- Expose high-screen discovery as read-only MCP Resources, not custom tools: `handaas://high-screen/guide`, `handaas://high-screen/fields`, `handaas://high-screen/fields/{field}`, and `handaas://high-screen/options/{source}`. Resource discovery must not change the 24-tool product surface or assemble ES conditions inside the server.
- `server/high_screen.py` is the only condition normalization implementation. Do not reintroduce hard-coded field sets in `mcp_server.py`.
- Reject unknown fields with suggestions. Enforce configured action/input types, option paths, keyword counts, numeric bounds, dates and preset actions. Apply only configured safe operator corrections; never guess an unknown field or invalid tree path.
- High-screen top-level groups are `must` / `should` only. Reject `must_not` because the upstream product silently ignores it; exclusions use field-level `nin` / `neq` inside `must`.
- Tree-enum fields such as `address`, `industriesV2`, `operStatus_v2`, and `enterpriseType` use list-of-paths values for `eq` / `neq`. Address province names normalize to platform province abbreviations, e.g. `广东省` -> `广东`.
- Accept multiple fields in one `must` / `should` condition object and normalize them, in insertion order, into separate single-field conditions before validation; this is a safe compatibility correction for common LLM output.
- Full high-screen condition mode returns the total and the fixed first 50 rows. Accept `pageIndex=1` with either the tool default `pageSize=10` or the explicit fixed-result sentinel `pageSize=50`, never forward those paging fields, and reject all other paging values. Legacy flat list mode remains paginated up to 500 rows.
- Legacy flat `advanced_filter_get_enterprise_list` / `advanced_filter_get_enterprise_count` addresses use compact list-of-paths JSON at the HandaaS boundary, e.g. `[["广东省"]]`. MCP clients may pass a simple region string, province/city path string, JSON string, or array; validate against bundled address options and normalize once before `call_api`.
- Both legacy flat advanced-filter tools normalize every parameter before `call_api`: multi-value fields accept comma-delimited strings, JSON string arrays, or string arrays; dates must be valid `YYYY-MM-DD`; non-negative numeric fields accept JSON numbers or numeric strings; lower bounds must not exceed upper bounds.
- Invalid negative/zero pagination returns a structured `参数错误` without calling upstream.
- `bid_bigdata_bid_search.biddingType` and `biddingRegion` accept JSON arrays or legal JSON strings and are normalized before upstream calls.
- `policy_bigdata_policy_search.address` accepts list/list JSON or simple region strings and is normalized to HandaaS list-of-list JSON.
- Preserve empty upstream data such as `[]`; do not turn it into a generic request error.

## HTTP and signing contract

- DAAS endpoint: `${DAAS_BASE_URL}/api/v1/integrator/call_api/${INTEGRATOR_ID}`.
- Signature material is the sorted call-parameter values plus `SECRET_KEY`, then MD5 as required by the upstream interface.
- Request body is form encoded and contains `product_id`, `secret_id`, serialized `params`, and `signature`.
- Do not replace the upstream-required signing algorithm without an upstream contract change.
- Network exceptions must return exception class/category only, never request bodies or credentials.

## Runtime configuration

Local self-hosting uses:

- `INTEGRATOR_ID`
- `SECRET_ID`
- `SECRET_KEY`
- `DAAS_BASE_URL` (default `https://console.handaas.com`)
- `HANDAAS_TIMEOUT`
- `MCP_HOST` / `HANDAAS_MCP_HOST`
- `MCP_PORT` / `HANDAAS_MCP_PORT`

`./start_mcp_server.sh` defaults to `streamable-http`. The installed console command is `handaas-industry-chain-mcp`.

Health semantics:

- `ok`: process endpoint is reachable.
- `ready` / `credentials_configured`: all three local credential variables are present.
- Health responses must remain credential-free.

## Companion Skill integration

The Skill may connect with either:

- Platform Remote MCP token/URL; or
- Local `http://127.0.0.1:<port>/mcp`.

The MCP provides data wrappers only. The Skill owns ontology reuse, ES condition generation, relevance tuning, enterprise evidence scoring, linking, policy synthesis, and reports.

For integration smoke tests, start a non-conflicting local port and verify tool discovery from the Skill:

```bash
MCP_PORT=8023 ./start_mcp_server.sh
INDUSTRY_CHAIN_MCP_URL=http://127.0.0.1:8023/mcp \
  python ../industry-chain-processing-skill/industry-chain-processing/scripts/mcp_client.py ping
```

Expected tool count is currently 23. No tool name should start with a custom workflow prefix such as `industry_chain_`.

## Repository layout

- `server/mcp_server.py`: server, product registry, normalization, upstream client, tools, CLI.
- `server/high_screen.py`: configuration loader and high-screen condition validation/correction.
- `server/config/high_screen_fields.json`: field descriptions, control metadata and operator rules.
- `server/config/high_screen_options.json`: enum and tree-path values referenced by fields.
- `tests/test_condition.py`: tool boundary, normalization, signing, health, and error regression tests.
- `README.md`: user installation, Remote/local setup, complete tool documentation, Skill link.
- `pyproject.toml`: package metadata, dependencies, console entrypoint.
- `.github/workflows/ci.yml`: Python 3.10/3.12 test, compile, and build checks.
- `CONTRIBUTING.md`: contributor workflow.
- `SECURITY.md`: credential and vulnerability policy.

## Required verification

Run before claiming completion:

```bash
python -m unittest discover -s tests -v
ruff check server tests
python -m compileall -q server tests
python -m build
git diff --check
```

For transport or tool-contract changes, also run a local Streamable HTTP smoke test and enumerate all tools from the companion Skill.

## Documentation and release rules

- Keep the README section order compatible with other HandaaS MCP repositories: capabilities, requirements, local setup, stdio, Remote service, Skill integration, tool inventory, use cases, notes, examples, development, license.
- User setup documentation must provide separate macOS/Linux and Windows PowerShell commands for virtual environments, file copying/editing, environment variables, service startup, health checks, and CLI discovery. Do not publish a single Unix-only configuration path as universal guidance.
- Keep detailed contribution and security procedures in `CONTRIBUTING.md` and `SECURITY.md`.
- Tests remain committed to GitHub; they are required by CI. The wheel must not include `.env` or credentials.
- Commit messages use the repository's Lore decision-record format when the active Codex environment requires it.
- Push target: `origin/main` for `handaas/industry-chain-mcp-server`.

## Known limitations

- Product availability depends on the account's opened HandaaS products.
- Unit tests mock upstream calls; a local MCP tool-list smoke test does not prove every paid product permission.
- Do not claim exhaustive live integration coverage unless chargeable real queries were run and inspected.
