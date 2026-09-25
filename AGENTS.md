# AGENTS.md — Loom 工程入口

**产品名**：Loom · 你的 AI 总控台  
**定位**：不做能力，做连接；不做 Agent，做你所有 Agent 的总控台。

## 目录约定

根目录只放配置与入口；业务在 \pps/\。

| 路径 | 用途 | 入库 |
|------|------|------|
| `src/` `src-tauri/` `api/` … | 业务代码 | ✅ |
| `tests/` | 测试 | ✅ |
| `docs/` | 工程文档与 **showcase 预览** | ✅ |
| `docs/` | 文档 + showcase 预览 | ✅ |
| `deploy/` | Dockerfile / compose | ✅ |
| `apps/hub/plugins/` | 插件与知识数据 | ✅ |
| `scripts/` | 正式脚本（build/lint/test） | ✅ |
| `scripts/_archive/` | 历史一次性脚本 | 尽量不提交内容 |
| `目录/` | 产品/设计长文档 | ❌ **不进 git** |
| `dist/` `dist-bundle/` `app.html` | 构建与安装包 | 构建物 |
| `Loom-wt-*` | 隔离开发副本 | 不入主仓 |

## 开始干活前

1. 读 [`目录/01-执行规范/AGENTS.md`](目录/01-执行规范/AGENTS.md)（本地）  
2. 进度：`目录/04-进度与路线/plan.md`  
3. 产品：`目录/02-项目概览/产品定位.md`  

## 铁律（代码）

- 不编造 API；不写死业务；不引非必要依赖  
- 三端 UI：无横滚、无写死宽、无 PC 专属交互（`src/styles/responsive.css`）  
- 密钥只进环境变量 / `.env`（见 `SECURITY.md`）  

## 常用命令

```powershell
npm run test:ui
npm run build
python scripts/lint_all.py
python scripts/test_all.py
python scripts/build_android.py --release
python scripts/build_windows.py
```
