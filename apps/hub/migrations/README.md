# migrations — 数据库 Schema 迁移

迁移定义在 `data/__init__.py` 的 `MIGRATIONS` 字典：

| 版本 | 内容 |
|------|------|
| 1 | `kv` / `changelog` / `meta` 表 + 查询索引 |

- 应用方式：`Database.migrate()` 启动时自动补齐
- 版本记录表：`schema_migrations(version, applied_at)`
- 新增迁移：在 `MIGRATIONS` 追加下一版本号，**禁止改写已发布 SQL**

备份/恢复：

```powershell
python scripts/backup_db.py
python scripts/backup_db.py --restore backups/loom-YYYYmmdd-HHMMSS.db
```

详见 [RUNBOOK.md](../RUNBOOK.md) §数据。
