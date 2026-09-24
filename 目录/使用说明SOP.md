# Loom 使用说明 SOP

> 应用内入口：左侧栏 **「使用说明」**  
> 版本：0.1.0（开发中）

---

## 0. 项目是什么

**Loom（织巢）** = 跨端 Agent 工作台：

- 把 **Windows / 平板 / 手机** 编织成一台电脑  
- 把 **Claude Code、Work Buddy** 等 AI 编织成一个团队  
- 用 **YAML DSL** 声明扩展，改声明即扩展

**链路**：用户对话 → 意图识别 → 判运行端 → 调用工具 / 连接外部 AI → 结果多端同步。

---

## 1. 快速启动

```powershell
npm install
npm run start:hub          # Hub :8765
npm run dev                # 前端 :5173
# 或一键
npm run start

# 可选演示 MCP
npm run mcp:demo           # :3900

# 离线 UI 预览
npm run build:single       # 打开 app.html
```

自检：`npm run test` · `npm run lint`

---

## 2. 界面导航

| 导航 | 功能 |
|------|------|
| **对话** | 与 AI 协作；默认铺满窗口，消息区滑动 |
| **任务** | 排队/执行中/完成；结果卡片（tokens / 延迟 / 降级） |
| **跨端** | 设备在线、同步摘要、手机能力说明、下发测试任务 |
| **设置** | 自定义 LLM（配置 / 拉模型 / 选用 / 测试） |
| **MCP** | 外接 Claude Code · Work Buddy |
| **使用说明** | 本 SOP |

手机端：底部 Tab，功能相同。右侧只显示当前页。

---

## 3. 对话工作台

1. 先在 **设置** 保存并选用 LLM 配置  
2. **对话** 输入需求，Enter 发送  
3. 「收起 / 放大」切换尺寸；消息多时框内滑动  
4. 示例：`帮我把这份 PDF 转成 Markdown 并总结`

---

## 4. 任务中心

- 筛选：全部 / 待处理 / 执行中 / 已完成 / 失败  
- 卡片字段：`tokens_used` · `latency_ms` · `degradation_level` · `trace_id`  
- 跨端下发的测试任务会出现在这里

---

## 5. 自定义 LLM（设置）

1. 名称 + Base URL（如 `https://api.deepseek.com/v1`）+ API Key → **保存配置**  
2. **拉取模型**（真实拉取 `/v1/models` 或 `/v1beta/models`）  
3. 下拉/点 chip **选择模型**  
4. 顶部 **「当前模型配置」** 切换要使用的配置  
5. **测试对话** 验证  

> Key 加密存储；缺 Key 时先重新保存再拉模型。

---

## 6. MCP 外接服务

> **MCP 只在 PC/Hub 配置一次**；手机看结果、分发任务即可。

1. 填协议地址 → **检测连接** → 看服务名与工具  
2. **试调用工具** 或点工具名验证 `tools/call`  
3. Work Buddy 默认：`http://127.0.0.1:54916/mcp`（token 见 `LOOM_WORK_BUDDY_TOKEN`）  
4. 无外部服务：`npm run mcp:demo` → `http://127.0.0.1:3900/mcp`  

详见：`目录/MCP_工具调用说明.md`

---

## 7. 跨端协同

| 端 | 职责 |
|----|------|
| PC / Hub | MCP、LLM Key、DSL、Shell |
| 手机 / 平板 | 任务列表与分发、对话下任务、文件上传、通知、技能树 |

**同步**：SyncEngine 版本号 + 增量广播，多端同一 `trace_id`；离线排队、上线分发。

---

## 8. DSL 扩展（进阶）

- 示例：`plugins/example/`  
- 改 YAML 保存 → 约 2s 热加载  
- Schema 校验不通过不落盘  
- 对话式生成 DSL：需求 → 生成 → diff 确认后写入

---

## 9. 日常 SOP 速查

```text
Day 0   npm install → npm run start
Step 1  设置 → LLM 保存 / 拉模型 / 选用 / 测试
Step 2  （可选）MCP 连接 Work Buddy 或演示服务
Step 3  对话下发任务 → 任务中心看结果
Step 4  手机连同一 Hub → 跨端查看 / 分发
扩展    改 plugins/*.yaml 热加载
```

排障：看 Hub 日志 `trace_id` → 任务错误卡片 → `目录/交接手册.md`

---

## 10. 文档索引

| 文件 | 内容 |
|------|------|
| `目录/使用说明SOP.md` | 本文 |
| `目录/项目介绍.md` | 定位与功能 |
| `目录/MCP_工具调用说明.md` | MCP 链路与接口 |
| `目录/FE7_交付清单.md` | 交付与启动命令 |
| `目录/FE5_三端验证步骤.md` | 三端人工验收 |
