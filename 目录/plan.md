# plan.md — 进度日志

## [2026-09-24][FE.0] 需求确认与方案锁定

- 状态：✅ 完成
- 决策锁定（用户确认）：
  1. 功能：对话/任务/文件/LLM/MCP/DSL 全面打磨
  2. 三端：Win + Web 优先
  3. 风格：暖白毛玻璃 + 暖杏/蜜桃/陶土 + 鼠尾草绿 + 技能树/成就化
  4. 交互：WS + REST + Tauri IPC（EventBus）
  5. 性能：FE.6 延后
- 变更文件：`目录/前端优化规划.md`（锁定 5 项 + 设计主张 + 页面/选型）
- 验收：[x] 5 项均有用户明确选择 [x] 设计主张可指导 Token
- 下一 Task：FE.1 框架搭建

## [2026-09-24][FE.1] 前端框架搭建

- 状态：✅ 完成
- 变更文件：
  - `src/api/index.ts` — 统一通信门面（REST/上传/平台 refresh）
  - `src/hooks/use-router.ts` + `use-react-hooks.ts` + `index.ts` — 轻量 hash 路由与 React hooks
  - `src/stores/ui-store.ts` + `index.ts` — UI/路由状态，兼容既有 session/tasks/agents
  - `src/features/index.ts` — 业务域聚合 + FEATURES 元数据（技能树）
  - `src/components/index.ts` — UI 类名契约（FE.4 充实）
  - `src/styles/tokens.css` + `index.css` — 暖色毛玻璃 Token 雏形
  - `src/services/index.ts` — `createServiceLayer` 支持 `uploadFetch` 注入
  - `src/App.tsx` — 接线 McpPanel；修复 `llmDraft.providerId` 类型
  - `src/hub/ws-client.ts` — `intentionalClose` 暴露主动关闭语义
  - `src/main.tsx` / `tsconfig.json` / `package.json` — 样式入口、严格 TS、测试纳入
  - `tests/js/test_fe_framework.mjs` — 路由/门面/UI Store/契约单测
- 验收结果：
  - [x] 通信层单测 `test_fe_framework: ALL PASS`
  - [x] `npm run test:ui` 全绿；`npm run test:py` 296 OK
  - [x] `npx tsc --noEmit` 通过（strict + noUnusedLocals）
  - [x] `npm run build` 成功（Web 可构建启动）
- 遗留：
  - Android/平板仍按规划延后（Tauri 移动打包）
  - App 尚未按 hash 路由分页面（FE.3 页面化）；当前为单页聚合
  - 组件库仅类名契约（FE.4）；性能 FE.6 延后

## [2026-09-24][FIX] 示例 DeepSeek + 保存缺 API Key 明文

- 状态：✅ 完成
- 根因：`onSave` 未写入 `apiKeyPlain`，保存后「拉取模型」仍认为本页无 Key
- 变更：`App.tsx` 保存/合并保留明文 Key；面板与报错示例改为 `https://api.deepseek.com/v1`
- 验收：4/4 回归 + 283 Python OK


## [2026-09-24][N11] OAuth 鉴权

- 状态：✅ 完成
- 变更文件：
  - `auth/oauth.py` — OAuthService：issue_tokens / verify_access / refresh（轮换）/ revoke
  - `api/auth_routes.py` — `/api/auth/token` · `/refresh` · `/revoke` · `/whoami`
  - `tests/test_oauth.py` — 13 个单测
- 验收结果：
  - [x] 未授权设备无法注册（无 token / 伪造 / 过期 → AuthError）
  - [x] token 过期可续期（refresh 换新 access，旧 refresh 吊销轮换）
  - [x] 测试 13/13 OK；全量 296 OK
- 遗留问题：
  - **决策**：标准库 HS256 风格 JWT（非完整 OAuth2 IdP）；设备 `client_credentials` 语义
  - **决策**：WS 注册默认仍兼容 HMAC；`allow_register` 供强制 OAuth 模式接入
  - secret 来自 `LOOM_AUTH_SECRET`


## [2026-09-24][N12] 工程化（CI / lint / 一键全量测试）

- 状态：✅ 完成
- 变更文件：
  - `scripts/test_all.py` — 一键跑 Python unittest + 全部 JS + Rust cargo test
  - `scripts/lint_all.py` — py_compile +（可选 ruff）+ cargo fmt --check
  - `.github/workflows/ci.yml` — 矩阵 CI（python/js/rust + lint），红灯即失败
  - `ruff.toml` / `requirements.txt` / `package.json` scripts（test/lint/ci）
- 验收结果：
  - [x] 一条命令：`npm run test` / `python scripts/test_all.py`
  - [x] CI 工作流失败即红
  - [x] lint：Python 语法 + Rust fmt 通过
- 遗留：ruff 本机未装（lint 回退 py_compile）；CI 用 GitHub Actions


## [2026-09-24][STACK] 技术栈匹配与优化

- 状态：✅ 完成
- 目标栈对照：
  | 栈 | 状态 |
  |----|------|
  | Shell: Tauri 2.0 + React + TS + Vite | ✅ 已具备 |
  | Hub: Python 3.11+ + FastAPI + Uvicorn + LangGraph + Pydantic | ✅ 已具备 |
  | DSL: YAML + PyYAML + JSON Schema + jsonschema | ✅ schema 优先 jsonschema，回退内置 |
  | Agent: MCP SDK + httpx | ✅ httpx；mcp 入 requirements（当前为兼容 JSON-RPC 传输） |
  | Device: WebSocket + HMAC-SHA256 | ✅ 已具备 |
  | Store: SQLite | ✅ sync/engine |
  | Deploy: Docker + GitHub Releases | ✅ Dockerfile / compose / release.yml |
  | Tools: Ruff + pytest + pytest-asyncio | ✅ pyproject + lint/test 切换 pytest/ruff |
- 变更文件：
  - `requirements.txt` / `pyproject.toml`（pytest + ruff 配置）
  - `dsl/schema.py` — jsonschema Draft202012 优先，builtin 回退；`backend_name()`
  - `Dockerfile` / `docker-compose.yml`
  - `.github/workflows/release.yml`（tag 触发：测试→Docker→上传 app.html）
  - `scripts/lint_all.py` / `test_all.py` / `ci.yml` 对齐 ruff + pytest
- 验收：
  - [x] pytest 296 passed；test_all Py+JS+Rust ALL PASS
  - [x] schema backend=jsonschema（已安装）
  - [x] Docker / GitHub Releases 配置就绪


## [2026-09-24][STACK] 技术栈匹配与优化

- 状态：✅ 完成
- 目标栈对照：
  | 栈 | 状态 |
  |----|------|
  | Shell: Tauri 2.0 + React + TS + Vite | ✅ 已具备 |
  | Hub: Python 3.11+ + FastAPI + Uvicorn + LangGraph + Pydantic | ✅ 已具备 |
  | DSL: YAML + PyYAML + JSON Schema + jsonschema | ✅ schema 优先 jsonschema（4.26），builtin 回退 |
  | Agent: MCP SDK + httpx | ✅ httpx；mcp 入 requirements（当前为兼容 JSON-RPC 传输） |
  | Device: WebSocket + HMAC-SHA256 | ✅ 已具备 |
  | Store: SQLite | ✅ sync/engine |
  | Deploy: Docker + GitHub Releases | ✅ Dockerfile / compose / release.yml |
  | Tools: Ruff + pytest + pytest-asyncio | ✅ pyproject + lint/test 切换 pytest/ruff |
- 变更文件：
  - `requirements.txt` / `pyproject.toml`（pytest-asyncio auto + ruff 配置）
  - `dsl/schema.py` — jsonschema Draft202012 优先；错误文案映射中文；`backend_name()`
  - `Dockerfile` / `docker-compose.yml` / `.github/workflows/release.yml`
  - `scripts/lint_all.py` / `test_all.py` / `ci.yml` 对齐 ruff + pytest
- 验收：
  - [x] pytest 全绿（含 schema 中文文案断言）
  - [x] test_all Py+JS+Rust ALL PASS
  - [x] schema backend=jsonschema
  - [x] Docker / GitHub Releases 配置就绪
- 遗留：MCP SDK 已入依赖，传输层仍为兼容 JSON-RPC（可切换官方 mcp）；ruff 可 `pip install ruff`


## [2026-09-24][交接] 上下文压缩 + 前端优化规划

- 状态：✅ 文档完成（编码待确认）
- 变更文件（`目录/`）：
  - `交接手册.md` — 全量工作压缩、代码地图、决策、命令、遗留
  - `项目介绍.md` — 定位 / 功能 / 使用说明（重写）
  - `前端优化规划.md` — FE.0–FE.7 计划 + 5 项待确认
- ROADMAP：新增「P6 · 前端生产化（FE）」
- 待用户确认 5 项后启动 FE.1 框架搭建
