# Loom · 织巢

> **状态：开发中（WIP）** · 尚未正式发布，请勿当生产依赖  
> 跨端协作 · Agent 联邦 · DSL 驱动的可生长工作台

把 Windows / 平板 / 手机编织成一台电脑，把手边的 AI Agent 编织成一个团队。

---

## 开发中说明

| 项 | 现状 |
|----|------|
| 版本 | `0.1.0` · 预览 / 内部迭代 |
| 稳定性 | **不稳定**，接口与目录可能随时调整 |
| 三端 | Web 与 Win 壳可跑；Android / 平板打包 **未完成** |
| 文档 | 以 `目录/` 交接文档为准，公开文档持续补全中 |
| 贡献 | 欢迎试用与提 Issue；**暂不接受大规模 PR**（架构仍在收敛） |

如果你只是想看看效果：本地 `npm run start` 或直接打开 `app.html`（Hub 能力除外）。

---

## 一分钟看懂

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

**核心主张**：功能用 YAML DSL 声明，改声明即扩展，尽量不改主程序。

---

## 能做什么

- **对话与任务** — 聊天、任务状态、结果卡片（tokens / latency / 降级档位）
- **自定义 LLM** — OpenAI 兼容 API，加密存 Key，拉模型列表，一键测试对话
- **MCP 外接** — 填地址 → 检测连接 → 看服务与工具（自带演示 MCP）
- **DSL 扩展** — Workflow / Plugin / Agent / Trigger 四类；校验后保存，约 2s 热生效
- **跨端协同** — 手机触发 → Hub 路由 → PC 执行 → 多端查看；离线排队、上线分发
- **可观测与安全** — trace_id 日志、降级链、Token 熔断、OAuth 风格鉴权

---

## 技术栈

| 层 | 技术 |
|----|------|
| Shell | Tauri 2.0 · React · TypeScript · Vite |
| Hub | Python 3.11+ · FastAPI · LangGraph · Pydantic |
| DSL | YAML · JSON Schema |
| Agent | MCP（JSON-RPC 兼容）· httpx |
| Device | WebSocket · HMAC-SHA256 |
| Store | SQLite |
| Deploy | Docker · GitHub Actions / Releases |

---

## 快速开始

```powershell
# 安装前端依赖
npm install

# 后端 Hub（REST + WebSocket）
npm run start:hub

# 另开终端：前端开发服务
npm run dev
# 浏览器打开 http://localhost:5173/

# 或一键同时启动
npm run start

# 无服务单文件预览（Hub 功能除外）
npm run build:single   # 然后打开 app.html
```

**自测 MCP**（无需 Claude Code）：

```powershell
npm run mcp:demo
# 面板地址填 http://127.0.0.1:3900/mcp → 检测连接
```

**测试 / 静态检查**：

```powershell
npm run test   # Python + JS + Rust
npm run lint
```

---

## 仓库地图

```text
loom/
├── dsl/  agent_hub/  device_mesh/  task_orchestrator/  sync/
├── api/  integration/  llm/  auth/  observability/
├── plugins/example/          # notes 插件 + 4 场景 workflow
├── src/                      # 前端（views / state / services / features…）
├── src-tauri/                # Tauri 壳
├── tests/                    # Python · JS · e2e
├── scripts/                  # 启动 / 构建 / 测试
└── 目录/                     # 设计与交接文档（中文）
```

深入阅读（建议顺序）：

1. [`目录/项目介绍.md`](./目录/项目介绍.md) — 定位与功能  
2. [`目录/交接手册.md`](./目录/交接手册.md) — 代码地图与决策  
3. [`目录/ROADMAP.md`](./目录/ROADMAP.md) — 阶段与计划  
4. [`目录/plan.md`](./目录/plan.md) — 进度日志  

---

## 当前进度（摘要）

| 阶段 | 状态 |
|------|------|
| DSL / Agent 联邦 / 跨端 / 编排 | ✅ 核心已落地 |
| Shell 前端骨架 · LLM / MCP / DSL 面板 | ✅ 可演示 |
| 可观测 · OAuth · CI · Docker | ✅ 初版 |
| **前端生产化（FE）** | 🚧 进行中（暖色毛玻璃 UI · 技能树交互） |
| 移动端打包 · 跨机真机 E2E | ⏳ 计划中 |

> 完整清单见 `目录/ROADMAP.md`。**开发中，一切以仓库内文档与代码为准。**

---

## 设计方向（前端 FE）

界面气质：暖白底 + 毛玻璃面板，蜜桃杏 / 陶土强调，鼠尾草绿表示「已连接 / 成功」。  
设备与 Agent 呈「技能树」节点，点亮即解锁；DSL 保存带「成就达成」式轻反馈。

---

## 许可与声明

- 本项目处于 **活跃开发中**，不提供任何明示或暗示的担保。  
- 示例配置中的第三方 API / 密钥 **请勿提交到仓库**。  
- License 待正式发布前确定（开发阶段仅作学习与内部协作用途）。

---

<div align="center">

**开发中 · Work in Progress**  
文档与行为以后续 Release 说明为准

</div>
