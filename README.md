# Loom · 织巢

![CI](https://github.com/Yixi233-mo/Loom/actions/workflows/ci.yml/badge.svg) ![status](https://img.shields.io/badge/status-开发中-orange)

> **状态：开发中（WIP）** · `0.1.0` · 请勿当生产依赖  
> 跨端协作 · Agent 联邦 · DSL 驱动的可生长工作台

把 Windows / 平板 / 手机编织成一台电脑，把手边的 AI Agent 编织成一个团队。

---

## 开发中说明

| 项 | 现状 |
|----|------|
| 版本 | `0.1.0` · 预览 / 内部迭代 |
| 稳定性 | **不稳定**，接口与目录可能随时调整 |
| 三端 | Web 与 Win 壳可跑；Android / 平板打包 **未完成** |
| 文档 | 交付清单见 [`目录/07-交付验收/FE7_交付清单.md`](./目录/07-交付验收/FE7_交付清单.md) |
| 贡献 | 欢迎试用与提 Issue；**暂不接受大规模 PR** |

---

## 架构

```text
  手机 / 平板 / PC          Agent（Claude Code · MCP · 内置）
        │                        │
        └──────────┬─────────────┘
                   ▼
            ┌─────────────┐
            │  Loom Hub   │  意图识别 · 任务路由 · 状态协调
            └─────────────┘
                   │
     ┌─────────────┼─────────────┐
     ▼             ▼             ▼
  Device Mesh   Task Orch     DSL Engine
  跨端消息/心跳   排队/超时     YAML 热加载
```

| 层 | 技术 | 目录 |
|----|------|------|
| Shell | Tauri 2 · React · TS · Vite | `src/` `src-tauri/` |
| Hub | Python · FastAPI · LangGraph | `api/` `integration/` `dsl/` … |
| 通信 | WebSocket · REST · Tauri IPC | `src/services/` `src/platform/` |
| 扩展 | YAML DSL（四类） | `dsl/` `plugins/` |
| 设计 | 暖白毛玻璃 Token | `src/styles/` |

前端分层：`contracts → api → state/stores → features/components → platform/perf`。

---

## 功能

- **对话工作台** — 消息流、模型对话、加载/空/错误态
- **任务中心** — 筛选、结果卡片（tokens / latency / 降级），长列表虚拟化
- **设置** — 自定义 LLM（加密 Key、拉模型、测试）· MCP 检测
- **DSL** — 校验后热加载；对话式生成（需确认落盘）
- **跨端** — 手机触发 → Hub → PC 执行 → 多端查看
- **安全观测** — trace_id、降级链、Token 熔断、OAuth 风格鉴权

---

## 开发

### 环境

Node 20+ · Python 3.11+ ·（桌面）Rust + WebView2 · Windows 优先

### 三端启动

```powershell
npm install

# Web / 开发
npm run start              # Hub :8765 + 前端 :5173
# 或：npm run start:hub  +  npm run dev

# 单文件预览（无 Hub）
npm run build:single       # 打开 app.html

# 桌面 Win
cd src-tauri && cargo run  # 另开终端保持 npm run dev

# Windows 安装包（.msi + NSIS setup）
npm run build:windows      # 产物在 dist-bundle/

# 移动预览：手机访问 http://<PC-IP>:5173/（正式 Tauri 打包待配置）

# 演示 MCP
npm run mcp:demo           # http://127.0.0.1:3900/mcp
```

### 常用脚本

| 命令 | 说明 |
|------|------|
| `npm run test` | Py + JS + Rust 全量 |
| `npm run test:ui` | 前端单测 |
| `npm run lint` / `npm run ci` | 静态检查 / 一键 CI |
| `npm run build` | 生产构建（react-vendor 拆包） |

---

## 构建与部署

```powershell
# 前端
npm run build              # dist/
npm run build:single       # app.html

# Hub（Docker）
docker compose up hub      # :8765

# Windows 安装包
npm run build:windows      # dist-bundle/*.msi + *-setup.exe
```

- CI：`.github/workflows/ci.yml`
- Release（含 app.html）：`.github/workflows/release.yml`
- 环境变量（**勿写进仓库**）：`WS_SECRET` · `LOOM_AUTH_SECRET` · `LOOM_MASTER_KEY`

完整清单与验证步骤：**[`目录/07-交付验收/FE7_交付清单.md`](./目录/07-交付验收/FE7_交付清单.md)**  
三端人工验证：[`目录/07-交付验收/FE5_三端验证步骤.md`](./目录/07-交付验收/FE5_三端验证步骤.md)

---

## 仓库地图

```text
loom/
├── dsl/ agent_hub/ device_mesh/ task_orchestrator/ sync/
├── api/ integration/ llm/ auth/ observability/
├── plugins/example/
├── src/                 # 前端
├── src-tauri/           # 桌面壳
├── tests/ scripts/
└── 目录/                # 设计与交付文档
```

深入：[`目录/02-项目概览/项目介绍.md`](./目录/02-项目概览/项目介绍.md) · [`目录/06-交接/交接手册.md`](./目录/06-交接/交接手册.md) · [`目录/04-进度与路线/ROADMAP.md`](./目录/04-进度与路线/ROADMAP.md)

---

## 设计方向

暖白底 + 毛玻璃，蜜桃杏/陶土强调，鼠尾草表示成功/已连接；设备与 Agent 呈技能树点亮。Token 见 `src/styles/README.md`。

---

## 许可与声明

- **开发中**，不提供明示或暗示担保  
- 禁止提交真实 API 密钥  
- License 待正式发布前确定  

---

<div align="center">

**开发中 · Work in Progress** · 交付基线见 `目录/07-交付验收/FE7_交付清单.md`

</div>
