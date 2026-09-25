# RUNBOOK — Loom 运维手册

> N16 · 部署 / 数据恢复 / 降级 / 停机。密钥见 [SECURITY.md](./SECURITY.md)。

---

## 1. 启动 / 停机

```powershell
# 开发
npm run start

# Hub 单独
python scripts/run_hub_server.py

# Docker
docker compose up -d hub
docker compose logs -f hub
docker compose stop hub   # SIGTERM → ≤30s 优雅停机
```

| 检查 | 命令 |
|------|------|
| 健康 | `curl http://127.0.0.1:8765/health` |
| 就绪 | `curl http://127.0.0.1:8765/ready` |

`/ready` 返回 503 时看 `checks` 字段定位 database / model / secrets。

---

## 2. 数据

镜像固定 tag：**loom/hub:0.1.0**（勿用 latest）。版本一致性：python scripts/check_versions.py。

- 默认库：`./data/loom.db`（`LOOM_DB_PATH` 可覆盖）
- 自动：建目录、建表、WAL、迁移（`migrations/README.md`）

### 备份

```powershell
python scripts/backup_db.py
python scripts/backup_db.py --db data/loom.db --out backups/loom-manual.db
```

### 损坏恢复（5.8）

1. 停 Hub
2. `python scripts/backup_db.py --restore backups/loom-YYYYmmdd-HHMMSS.db --db data/loom.db`
3. 若仍有 `-wal`/`-shm` 残留，恢复脚本会清理
4. 启动后 `curl /ready` 确认 database ok

### 索引

迁移 v1 含 `changelog(key/version/updated_at)` 索引；慢查询先 `EXPLAIN QUERY PLAN`。

---

## 3. 模型降级

链路：**DeepSeek → Ollama → 规则**（`degradation_level` 0/1/2）

| 触发 | 行为 |
|------|------|
| 单次 30s 超时 | 记失败，切下一档 |
| 连续 3 败 | 跳过该 Provider（WARNING） |
| Token 超限 | 熔断，返回规则档结果 |

环境变量：

| 变量 | 默认 | 说明 |
|------|------|------|
| `DEEPSEEK_API_KEY` | — | Cloud 档 |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | 本地档 |
| `LOOM_PROVIDER_TIMEOUT` | `30` | 单 Provider 超时 |
| `LOOM_PROVIDER_FAIL_LIMIT` | `3` | 连续失败阈值 |
| `LOOM_TOKEN_LIMIT` | `8000` | 单任务 Token 上限 |
| `LOOM_MODEL_DEEPSEEK` | `deepseek-chat` | 可热切换 `set_active_model` |

日志关键字：`[degrade]` · `cost.breaker_open` · `degrade.switch`。

---

## 4. 编排护栏

| 项 | 值 | 行为 |
|----|-----|------|
| 最大迭代 | 10 | 超限 `IterationLimitError` |
| 重复动作 | 同工具同参 3 次 | `DuplicateActionError` |
| 任务超时 | 120s | `TimeoutBudgetError` |
| 未注册工具 | — | `ToolNotFoundError` |
| 工具失败 | 不盲重试 | 记降级，继续下一步 |

多 Agent 分歧 → `MultiAgentAdjudicator` 返回 `needs_confirm=true`，需人工确认。

---

## 5. 回滚

| 目标 | 动作 |
|------|------|
| 应用 | `git checkout <last-good-tag>` → 重建镜像 / MSI |
| 数据 | 恢复备份（§2） |
| 配置 | 回滚 `.env` 并重启 |

---

## 6. 告警阈值

| 指标 | 阈值 |
|------|------|
| 任务成功率 | &lt; 90% |
| P95 延迟 | &gt; 30s |
| 降级到规则档占比 | &gt; 20% |
| 熔断次数 | &gt; 5 / 小时 |
