# Loom FE.7 交付清单

> 阶段：FE（前端生产化）交付  
> 状态：**开发中 · 0.1.0** · 本清单为本轮 FE 交付基线

---

## 1. 交付物一览

| # | 交付物 | 位置 | 状态 |
|---|--------|------|------|
| 1 | 设计系统 Token | `src/styles/tokens.css` + `src/styles/README.md` | ✅ |
| 2 | 通用组件 | `src/components/index.ts` + `components.css` | ✅ |
| 3 | 核心页面 | `src/features/`（对话 / 任务 / 设置 + 四态） | ✅ |
| 4 | 三端适配 | `src/platform/adapters.ts` + `adapters.css` | ✅ |
| 5 | 性能原语 | `src/perf/`（虚拟列表 / memo / debounce） | ✅ |
| 6 | 架构说明 | 本节 + `README.md` | ✅ |
| 7 | 开发指南 | 本文件 §3 + `README.md` | ✅ |
| 8 | 构建与部署 | 本文件 §4 + Docker / CI | ✅ |
| 9 | 三端启动命令 | 本文件 §2 | ✅ |
| 10 | 验证步骤 | `目录/FE5_三端验证步骤.md` + §5 | ✅ |

---

## 2. 三端启动命令

### Web 浏览器

```powershell
npm install
npm run start          # 一键：Hub :8765 + Vite :5173
# 或分终端：
npm run start:hub
npm run dev
```

打开 `http://localhost:5173/`  
无服务预览：`npm run build:single` → 打开 `app.html`

### 桌面 Win（Tauri 2）

```powershell
# 前置：已装 Rust + WebView2
npm run dev            # 终端 1（或先 build）
cd src-tauri
cargo run              # 终端 2；或 npx tauri dev
```

### 移动（Android / 平板）

```powershell
# 预览：窄窗或手机浏览器访问开发机局域网
# http://<PC-IP>:5173/
# 正式打包：Tauri 移动目标（待配置，见 ROADMAP）
```

### 演示 MCP

```powershell
npm run mcp:demo       # http://127.0.0.1:3900/mcp
```

---

## 3. 开发指南

### 环境

| 依赖 | 版本建议 |
|------|----------|
| Node | 20+（`--experimental-strip-types` 可用） |
| Python | 3.11+ |
| Rust | stable（桌面壳） |
| 系统 | Windows 优先；Web 任意 |

### 脚本

```powershell
npm run dev        # 前端开发
npm run build      # 生产构建（含 react-vendor 拆包）
npm run preview    # 预览构建产物
npm run test       # Py + JS + Rust 全量
npm run test:py    # Python unittest
npm run test:ui    # 前端单测链
npm run test:rust  # Tauri 命令层
npm run lint       # 语法 / fmt
npm run ci         # lint + test
```

### 前端架构

```
src/
├── contracts/     # DTO / 事件 / REST 契约
├── api/           # 统一通信门面（REST / 上传 / 平台）
├── state/ stores/ # 业务 Store + UI Store
├── services/      # REST / WS / LLM / 文件
├── platform/      # 设备探测 / Tauri / 三端 adapters
├── features/      # 页面（chat / tasks / settings）+ 四态
├── components/    # Button Input Modal Toast Layout
├── perf/          # 虚拟列表 / memo / debounce
├── hooks/         # hash 路由 / React hooks
└── styles/        # Token → base → components → pages → adapters
```

### 约定

- 业务颜色一律 Token，不写死 `#hex`
- 逻辑可被 YAML DSL 覆盖（Hub 侧）
- 类型尽量不写 `any`；Node 可测文件避免 TS 参数属性

---

## 4. 构建与部署

### 前端

```powershell
npm run build          # dist/
npm run build:single   # 单文件 app.html（Hub 能力除外）
```

构建产物拆分：`index`（业务）+ `react-vendor`（React）+ CSS。

### Hub（Docker）

```powershell
docker compose up hub
# :8765  WS/REST · 环境变量见 docker-compose.yml
```

本地：`npm run start:hub`  
健康：`GET http://127.0.0.1:8765/health`

### CI / Release

- `.github/workflows/ci.yml` — lint + Py/JS/Rust 测试
- `.github/workflows/release.yml` — tag 触发，上传 `app.html`

### 配置密钥（勿入库）

| 变量 | 用途 |
|------|------|
| `WS_SECRET` | 设备 HMAC |
| `LOOM_AUTH_SECRET` | OAuth token |
| `LOOM_MASTER_KEY` | LLM Key 加密 |

---

## 5. 验证清单（交付勾选）

### 自动化

- [x] `npm run test:ui` 全绿（含 FE framework / tokens / pages / components / adapters / perf）
- [x] `npm run test:py` 296 OK
- [x] `npx tsc --noEmit` 通过
- [x] `npm run build` 成功（vendor 拆包）
- [x] `npm run lint` 通过

### 人工（对齐 `目录/FE5_三端验证步骤.md`）

- [ ] Web：断点 lg/md/sm、hash 分享、对话/任务/设置四态
- [ ] Win：窗口弹出、标题/托盘/快捷键/拖拽/通知
- [ ] 移动：安全区、软键盘、滑动、返回键

### 交付文档

- [x] 架构：`README.md` + 本文件 §3
- [x] 开发：本文件 §3
- [x] 构建部署：本文件 §4
- [x] 三端启动命令：本文件 §2
- [x] 验证步骤：本文件 §5 + `目录/FE5_三端验证步骤.md`

---

## 6. 范围与免责

- **开发中**，不提供生产担保；API 可能变更
- 移动端正式打包未完成（Tauri 多端目标待配置）
- License / 安全披露待正式发布前确定
- 真实 API 密钥请写入环境变量或本机配置，禁止提交仓库
