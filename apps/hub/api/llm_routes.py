"""REST /api/llm/* — 自定义 LLM 配置 / 模型列表。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from llm.client import LLMClient
from llm.config import LLMConfigStore
from pydantic import BaseModel, Field


class ProviderIn(BaseModel):
    name: str
    baseUrl: str = Field(alias="baseUrl")
    apiKey: Optional[str] = Field(default=None, alias="apiKey")
    defaultModel: Optional[str] = Field(default=None, alias="defaultModel")
    providerId: Optional[str] = Field(default=None, alias="providerId")
    enabled: bool = True

    model_config = {"populate_by_name": True}


def create_llm_router(
    store: LLMConfigStore,
    client: Optional[LLMClient] = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/llm")
    http_client = client or LLMClient()

    @router.get("/providers")
    def list_providers() -> List[Dict[str, Any]]:
        return store.list_public()

    @router.post("/providers")
    def upsert_provider(body: ProviderIn) -> Dict[str, Any]:
        prov = store.upsert(
            name=body.name,
            base_url=body.baseUrl,
            api_key=body.apiKey or "",
            default_model=body.defaultModel or "",
            provider_id=body.providerId,
            enabled=body.enabled,
        )
        return prov.to_public()

    @router.delete("/providers/{provider_id}")
    def delete_provider(provider_id: str) -> Dict[str, Any]:
        if provider_id not in store.providers:
            raise HTTPException(404, "provider not found")
        store.delete(provider_id)
        return {"ok": True}

    @router.post("/providers/{provider_id}/fetch-models")
    async def fetch_models(provider_id: str) -> Dict[str, Any]:
        prov = store.providers.get(provider_id)
        if not prov:
            raise HTTPException(404, "provider not found")
        api_key = store.api_key_plain(provider_id)
        try:
            models = await http_client.fetch_models(prov.base_url, api_key)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(
                502,
                {"message": f"拉取模型失败: {e}", "code": "UPSTREAM_ERROR"},
            ) from e
        store.set_models(provider_id, models)
        return {"providerId": provider_id, "models": models}

    @router.get("/providers/{provider_id}/models")
    def list_models(provider_id: str) -> Dict[str, Any]:
        prov = store.providers.get(provider_id)
        if not prov:
            raise HTTPException(404, "provider not found")
        return {
            "providerId": provider_id,
            "models": prov.models,
            "defaultModel": prov.default_model,
        }

    @router.post("/providers/{provider_id}/select")
    def select_model(provider_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        model = body.get("model") or ""
        prov = store.providers.get(provider_id)
        if not prov:
            raise HTTPException(404, "provider not found")
        store.upsert(
            name=prov.name,
            base_url=prov.base_url,
            api_key="",
            default_model=model,
            provider_id=provider_id,
            enabled=prov.enabled,
            models=prov.models,
        )
        return store.providers[provider_id].to_public()

    return router


def mount_llm_api(app: Any, store: LLMConfigStore) -> None:
    app.include_router(create_llm_router(store))
