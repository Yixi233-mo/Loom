# SECURITY.md — Loom 密钥与泄露应急

> 对应 N16 第 2 章「密钥与凭据」。密钥只进环境变量 / 本机配置，**禁止入库**。

---

## 1. 密钥清单

| 环境变量 | 用途 | 必填 |
|----------|------|------|
| `WS_SECRET` | 设备注册 WebSocket HMAC-SHA256 | 生产必填 |
| `LOOM_AUTH_SECRET` | OAuth token（HS256）签名 | 生产必填 |
| `LOOM_MASTER_KEY` | 本地 LLM API Key 加密主密钥 | 生产必填 |
| `LOOM_WORK_BUDDY_TOKEN` | Work Buddy MCP Bearer | 可选 |
| `DEEPSEEK_API_KEY` | DeepSeek 模型服务 | 可选 |
| `OPERIT_API_KEY` | Operit 模型服务 | 可选 |

样例见 [`.env.example`](./.env.example)。`.env` 已在 `.gitignore`。

---

## 2. 生产必须修改默认值（2.7）

以下开发默认值 **禁止在生产使用**：

- `WS_SECRET=dev-secret`
- `LOOM_AUTH_SECRET=change-me-in-production`
- `LOOM_MASTER_KEY=change-me-master-key`

`LOOM_ENV=production` 启动时，Hub 会检测并 **报错拒绝** 默认 `WS_SECRET` / 未设置主密钥。

生成强口令示例：

```powershell
# PowerShell
-join ((1..32) | ForEach-Object { '{0:x}' -f (Get-Random -Max 16) })
# 或 openssl rand -hex 32
```

---

## 3. 密钥轮换（2.6）

1. 生成新口令（勿写进聊天记录 / 仓库）。
2. 更新部署环境变量或服务器 `.env`。
3. **重启 Hub**（`docker compose restart hub` 或重启进程）。
4. 已签发的 OAuth token 在 `LOOM_AUTH_SECRET` 轮换后立即失效 — 客户端需重新 `/api/auth/token`。
5. 已注册设备的 `WS_SECRET` 轮换后需重新注册（签名失效）。
6. 轮换 `LOOM_MASTER_KEY` 前需用旧主密钥解密再加密 LLM Key（`llm.crypto`），否则历史密文不可用。

---

## 4. 泄露应急流程（2.8）

**发现泄露（误提交 / 外泄 / 日志泄漏）时：**

| 步骤 | 动作 |
|------|------|
| **止血** | 立即在服务商控制台 **吊销/重置** 对应 API Key |
| **轮换** | 按 §3 轮换全部相关环境变量并重启 |
| **清理** | 从 git 历史中清除：`git filter-repo` 或 BFG；强制推送前先协调协作者 |
| **排查** | 检查审计日志 `observability.audit`：谁在何时调用了什么 |
| **影响面** | 确认是否已产生异常调用/费用（模型服务控制台） |
| **通知** | 内部同步影响范围；若涉及用户数据按合规要求上报 |
| **加固** | 找到泄漏路径（硬编码 / 日志 / 共享屏幕）；补测试或 hook 防再犯 |

**禁止：**

- 在 Issue / PR / 聊天中粘贴真实密钥
- 用 `git commit --amend` 掩盖已推送的密钥而不改密钥本身
- 假设「删掉文件就等于密钥未泄露」

---

## 5. 日志脱敏（2.5）

- 结构化日志与错误体经 `observability.security.redact_secrets` 脱敏
- 禁止 `logger.info(api_key)` 直接打印；需要时用 `auth.secrets.mask_value`
- traceback 同样过脱敏（见 `observability.logging` 与全局异常处理）

---

## 6. 检查命令

```powershell
# 确认 .env 未入库
git check-ignore .env

# 扫描疑似硬编码密钥
git grep -nE "sk-[A-Za-z0-9]{16,}|WS_SECRET\s*=\s*[\"']?(?!dev-secret)[^\"'\s]{8,}"
```

---

## 7. 联系

安全问题请开私密 Issue 或直接联系维护者，不要在公开渠道贴密钥。
