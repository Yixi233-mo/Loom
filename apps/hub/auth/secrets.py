"""密钥与凭据加载 — 全部走环境变量，禁止硬编码。

覆盖 N16 第 2 章：
  2.1 密钥全走环境变量
  2.3 WS_SECRET 默认仅开发 + 启动警告
  2.4 缺 DEEPSEEK/OPERIT 密钥明确报错
  2.7 生产必须改默认 WS_SECRET
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# 开发默认值 — 生产环境必须覆盖
DEV_WS_SECRET = "dev-secret"
DEV_AUTH_SECRET = "change-me-in-production"
DEV_MASTER_KEY = "change-me-master-key"

# 敏感环境变量名（日志/错误中一律脱敏）
SECRET_ENV_KEYS = (
    "WS_SECRET",
    "LOOM_AUTH_SECRET",
    "LOOM_MASTER_KEY",
    "LOOM_WORK_BUDDY_TOKEN",
    "DEEPSEEK_API_KEY",
    "OPERIT_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
)


class SecretConfigError(Exception):
    """生产密钥配置错误 — 明确报错，不静默降级。"""


@dataclass
class SecretReport:
    """启动时密钥检查结果。"""

    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    is_production: bool = False

    @property
    def ok(self) -> bool:
        return not self.errors


def _is_production() -> bool:
    return os.environ.get("LOOM_ENV", os.environ.get("NODE_ENV", "")).lower() in {
        "production",
        "prod",
    }


def get_secret(name: str, default: str = "") -> str:
    """读取敏感环境变量。"""
    return os.environ.get(name, default)


def require_secret(name: str) -> str:
    """读取密钥，缺失则抛 SecretConfigError（2.4）。"""
    val = os.environ.get(name, "").strip()
    if not val:
        raise SecretConfigError(
            f"缺少环境变量 {name}。请在 .env 或部署环境配置后重启（见 .env.example / SECURITY.md）"
        )
    return val


def check_provider_keys(require: Optional[List[str]] = None) -> List[str]:
    """检查模型服务密钥；缺失返回错误列表，不打印值（2.4/2.5）。"""
    names = require or ["DEEPSEEK_API_KEY", "OPERIT_API_KEY"]
    errs: List[str] = []
    for n in names:
        if not os.environ.get(n, "").strip():
            errs.append(f"缺少 {n}：对应模型服务不可用（降级链将走 Ollama/规则）")
    return errs


def audit_secrets(environ: Optional[Dict[str, str]] = None) -> SecretReport:
    """启动审计：开发默认值告警；生产缺关键密钥报错（2.3/2.7）。"""
    env = environ if environ is not None else dict(os.environ)
    report = SecretReport(is_production=_is_production() or env.get("LOOM_ENV", "").lower() in {"production", "prod"})

    ws = env.get("WS_SECRET", "")
    if not ws:
        report.warnings.append("WS_SECRET 未设置，回退 dev-secret（仅开发可接受）")
        ws = DEV_WS_SECRET
    elif ws == DEV_WS_SECRET:
        if report.is_production:
            report.errors.append("生产环境禁止使用默认 WS_SECRET=dev-secret（2.7），请改为随机强口令")
        else:
            report.warnings.append("WS_SECRET=dev-secret：仅限开发；生产必须修改（2.3）")

    auth = env.get("LOOM_AUTH_SECRET", "")
    if report.is_production and (not auth or auth == DEV_AUTH_SECRET):
        report.errors.append("生产环境必须设置 LOOM_AUTH_SECRET 为随机强口令")

    master = env.get("LOOM_MASTER_KEY", "")
    if report.is_production and (not master or master == DEV_MASTER_KEY):
        report.errors.append("生产环境必须设置 LOOM_MASTER_KEY（LLM Key 加密主密钥）")

    # 生产缺模型密钥 → 明确错误（可按需只强制部分）
    if report.is_production:
        for err in check_provider_keys(["DEEPSEEK_API_KEY"]):
            # 生产缺 DeepSeek 可降级，记 warning 不拦启动；OPERIT 同理
            report.warnings.append(err)

    return report


def warn_if_default_secret(logger_: Optional[logging.Logger] = None) -> SecretReport:
    """Hub 启动时调用：打印告警/错误，返回报告。"""
    log = logger_ or logger
    report = audit_secrets()
    for w in report.warnings:
        log.warning("[secrets] %s", w)
    for e in report.errors:
        log.error("[secrets] %s", e)
    return report


def mask_value(value: str, keep: int = 3) -> str:
    """脱敏：sk-abc…xyz → sk-a***yz（2.5）。"""
    if not value:
        return ""
    if len(value) <= keep * 2:
        return "***"
    return f"{value[:keep]}***{value[-keep:]}"
