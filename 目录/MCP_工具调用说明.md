# MCP 与工具调用说明

> 疑问：「工具调用这一块未知、未测试」——本文说清链路、已测范围、缺口与 Work Buddy 接入。

---

## 1. 全链路在系统中的位置

```text
用户对话
  → 意图识别（规则 / HybridIntentRouter，可插 LLM）
  → 判断运行端口 / 目标设备（Device Mesh 能力路由 + workflow.device）
  → 分支：
       A. 内置工具（notes、workflow tool steps）
       B. 连接外部 AI 助手：Claude Code · Work Buddy（MCP tools/call）
       C. Workflow 编排（DSL → TaskOrchestrator → 指定设备）
  → 聚合结果 → 回写任务 / 广播多端
```

| 环节 | 代码 | 状态 |
|------|------|------|
| 意图识别 | `agent_hub/graph.py` · `intent_router.py` | ✅ 有测试 |
| 选执行端 / 设备 | `device_mesh/` · `hub_bridge.py` | ✅ 有测试 |
| 内置工具 | `plugins/example/workflow_runner.py` + notes tools | ✅ 有测试 |
| MCP 协议 | `agent_hub/adapters/mcp_protocol.py` | ✅ MockTransport 单测 |
| REST 简化调用 | `adapters/claude_code.py` `/mcp/invoke` | ✅ 有测试 |
| **Work Buddy** | `adapters/work_buddy.py` + 内置目录 | ✅ 本轮补齐 |
| **HTTP 工具调用 API** | `POST /api/mcp/tools-call` | ✅ 本轮补齐 |
| **E2E：意图→MCP 工具** | `tests/test_tool_call_e2e.py` | ✅ 本轮补齐 |
| 真机 Claude Code / Work Buddy | 需本机安装对应 MCP | ⏳ 人工 |

---

## 2. MCP 是什么（一句话）

MCP = 让 Loom 用标准 JSON-RPC 调外部 AI 工具：

1. `initialize` 握手  
2. `tools/list` 看有哪些工具  
3. `tools/call` 真正干活  

演示服务：`python scripts/mock_mcp_server.py` → `http://127.0.0.1:3900/mcp`

---

## 3. HTTP 接口（工具调用）

| 方法 | 路径 | 作用 |
|------|------|------|
| GET | `/api/mcp/catalog` | 内置目录 + **Work Buddy 下载内链** |
| POST | `/api/mcp/probe` | 检测连接 + 工具列表 |
| POST | `/api/mcp/tools-call` | **真实 tools/call**（或 `protocol=rest`） |

`tools-call` 示例：

```json
{
  "url": "http://127.0.0.1:3900/mcp",
  "tool": "buddy_task",
  "arguments": { "prompt": "帮我总结日报" }
}
```

---

## 4. 内置 Work Buddy + 下载推荐

- 适配器：`agent_hub/adapters/work_buddy.py`  
- 目录卡片：`agent_hub/mcp_catalog.py` → `work_buddy`  
- 下载内链字段：`download_url`（可用环境变量覆盖）

| 环境变量 | 含义 | 默认 |
|----------|------|------|
| `LOOM_WORK_BUDDY_MCP` | Work Buddy MCP 地址 | `http://127.0.0.1:3910/mcp` |
| `LOOM_WORK_BUDDY_DOWNLOAD_URL` | 内链下载页 | `https://github.com/Yixi233-mo/WorkBuddy/releases/latest` |
| `LOOM_WORK_BUDDY_TOOL` | 默认工具名 | `buddy_task` |

前端「MCP 外接服务」面板会展示目录卡片与 **「下载 Work Buddy」** 按钮；点开推荐下载 → 安装启动 MCP → 填地址检测 → 工具调用。

演示 MCP 已含 `buddy_task`，未装 Work Buddy 也可联调全链路。

---

## 5. 已自动化测试（本轮）

- `tests/test_tool_call_e2e.py`  
  - 意图「审查代码」→ registry → MCP `tools/call`  
  - 意图 → **Work Buddy** `buddy_task`  
  - `/api/mcp/tools-call` 与 `/api/mcp/catalog`（含 download_url）  
  - 演示 MCP `buddy_task` 回声  
- 既有：`test_mcp_protocol.py` · `test_mcp_ui.py` · `test_integration.py`

```powershell
python -m pytest tests/test_tool_call_e2e.py tests/test_mcp_protocol.py tests/test_mcp_ui.py -q
npm run test
```

---

## 6. 建议人工真机步骤

1. `python scripts/mock_mcp_server.py`  
2. `npm run start` → 设置 · MCP → 检测 `http://127.0.0.1:3900/mcp`  
3. 对话输入「审查代码」→ 观察任务/结果是否来自 MCP  
4. （可选）安装 Work Buddy → 检测 `LOOM_WORK_BUDDY_MCP` → 调 `buddy_task`

---

## 7. 遗留

- 官方 MCP streamable HTTP/SSE 细节随 SDK 演进（`# 需确认当前版本API`）  
- Work Buddy 真机 endpoint / 下载页以你方发行地址为准，改 env 即可  
- stdio 传输未接（当前为 HTTP JSON-RPC）
