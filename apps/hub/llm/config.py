"""LLM 服务商配置 — 加密存储 API Key，支持多提供商。"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from llm.crypto import decrypt, encrypt, mask_secret

DEFAULT_MASTER_ENV = "LOOM_MASTER_KEY"


@dataclass
class LLMProvider:
    provider_id: str
    name: str
    base_url: str
    api_key_enc: str = ""
    default_model: str = ""
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    # 拉取过的模型缓存
    models: List[str] = field(default_factory=list)

    def to_public(self) -> Dict[str, Any]:
        """对外输出：密钥脱敏。"""
        return {
            "providerId": self.provider_id,
            "name": self.name,
            "baseUrl": self.base_url,
            "apiKeyMasked": mask_secret(self._api_key_plain_cached or ""),
            "hasApiKey": bool(self.api_key_enc),
            "defaultModel": self.default_model,
            "enabled": self.enabled,
            "createdAt": self.created_at,
            "models": list(self.models),
        }

    # 内存缓存明文（避免反复解密）；不落盘
    _api_key_plain_cached: str = field(default="", repr=False)


class LLMConfigStore:
    """JSON 文件存储 + 主密钥加密 API Key。"""

    def __init__(
        self,
        path: str | Path,
        master_key: Optional[str] = None,
    ) -> None:
        self.path = Path(path)
        self._master = master_key or os.environ.get(DEFAULT_MASTER_ENV) or "loom-dev-master"
        self.providers: Dict[str, LLMProvider] = {}
        self._load()

    # ---- 持久化 ----

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return
        for item in data.get("providers", []):
            p = LLMProvider(
                provider_id=item["provider_id"],
                name=item.get("name", ""),
                base_url=item.get("base_url", ""),
                api_key_enc=item.get("api_key_enc", ""),
                default_model=item.get("default_model", ""),
                enabled=bool(item.get("enabled", True)),
                created_at=float(item.get("created_at") or time.time()),
                models=list(item.get("models") or []),
            )
            self.providers[p.provider_id] = p

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "providers": [
                {
                    "provider_id": p.provider_id,
                    "name": p.name,
                    "base_url": p.base_url,
                    "api_key_enc": p.api_key_enc,
                    "default_model": p.default_model,
                    "enabled": p.enabled,
                    "created_at": p.created_at,
                    "models": p.models,
                }
                for p in self.providers.values()
            ]
        }
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ---- CRUD ----

    def upsert(
        self,
        name: str,
        base_url: str,
        api_key: str = "",
        default_model: str = "",
        provider_id: Optional[str] = None,
        enabled: bool = True,
        models: Optional[List[str]] = None,
    ) -> LLMProvider:
        pid = provider_id or f"llm-{uuid.uuid4().hex[:8]}"
        existing = self.providers.get(pid)
        api_key_enc = existing.api_key_enc if (existing and not api_key) else (
            encrypt(api_key, self._master) if api_key else existing.api_key_enc if existing else ""
        )
        prov = LLMProvider(
            provider_id=pid,
            name=name,
            base_url=base_url.rstrip("/"),
            api_key_enc=api_key_enc,
            default_model=default_model or (existing.default_model if existing else ""),
            enabled=enabled,
            created_at=existing.created_at if existing else time.time(),
            models=models if models is not None else (existing.models if existing else []),
        )
        if api_key:
            prov._api_key_plain_cached = api_key
        self.providers[pid] = prov
        self._save()
        return prov

    def delete(self, provider_id: str) -> None:
        self.providers.pop(provider_id, None)
        self._save()

    def list_public(self) -> List[Dict[str, Any]]:
        out = []
        for p in self.providers.values():
            if not p._api_key_plain_cached and p.api_key_enc:
                try:
                    p._api_key_plain_cached = decrypt(p.api_key_enc, self._master)
                except Exception:  # noqa: BLE001
                    p._api_key_plain_cached = ""
            out.append(p.to_public())
        return out

    def api_key_plain(self, provider_id: str) -> str:
        p = self.providers.get(provider_id)
        if not p:
            raise KeyError(provider_id)
        if p._api_key_plain_cached:
            return p._api_key_plain_cached
        if not p.api_key_enc:
            return ""
        return decrypt(p.api_key_enc, self._master)

    def set_models(self, provider_id: str, models: List[str]) -> None:
        p = self.providers.get(provider_id)
        if not p:
            raise KeyError(provider_id)
        p.models = list(models)
        self._save()
