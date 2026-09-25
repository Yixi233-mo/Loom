"""LLM HTTP 客户端 — OpenAI 兼容：拉模型列表 / chat completions。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol


class HttpPostGet(Protocol):
    async def get_json(self, url: str, headers: Dict[str, str]) -> Dict[str, Any]: ...
    async def post_json(
        self, url: str, headers: Dict[str, str], body: Dict[str, Any]
    ) -> Dict[str, Any]: ...


class DefaultHttp:
    """httpx 实现（已有依赖）。4.4 超时：HTTP 30s / LLM 120s。"""

    def __init__(self, http_timeout: float = 30.0, llm_timeout: float = 120.0) -> None:
        self.http_timeout = http_timeout
        self.llm_timeout = llm_timeout

    async def get_json(self, url: str, headers: Dict[str, str]) -> Dict[str, Any]:
        import httpx

        async with httpx.AsyncClient(timeout=self.http_timeout) as client:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            return r.json()

    async def post_json(
        self, url: str, headers: Dict[str, str], body: Dict[str, Any]
    ) -> Dict[str, Any]:
        import httpx

        async with httpx.AsyncClient(timeout=self.llm_timeout) as client:
            r = await client.post(url, headers=headers, json=body)
            r.raise_for_status()
            return r.json()


class LLMClient:
    """OpenAI 兼容端点：GET /v1/models · POST /v1/chat/completions。"""

    def __init__(self, http: Optional[HttpPostGet] = None) -> None:
        self.http = http or DefaultHttp()

    def _headers(self, api_key: str) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if api_key:
            h["Authorization"] = f"Bearer {api_key}"
        return h

    async def fetch_models(self, base_url: str, api_key: str = "") -> List[str]:
        """拉取服务商模型列表：/v1beta/models → /v1/models → /models。"""
        base = base_url.rstrip("/")
        root = base
        for suf in ("/v1beta", "/v1"):
            if root.endswith(suf):
                root = root[: -len(suf)]
                break
        headers = self._headers(api_key)
        candidates = [
            root + "/v1beta/models",
            root + "/v1/models",
            root + "/models",
            base + "/v1beta/models",
            base + "/models",
        ]
        seen = set()
        urls = []
        for u in candidates:
            if u not in seen:
                seen.add(u)
                urls.append(u)
        last_err: Exception | None = None
        for url in urls:
            try:
                data = await self.http.get_json(url, headers)
                names = self._parse_models(data)
                if names:
                    return names
            except Exception as e:  # noqa: BLE001
                last_err = e
                continue
        raise RuntimeError(f"拉取模型列表失败: {last_err}（已尝试 {urls}）")

    @staticmethod
    def _parse_models(data: Dict[str, Any]) -> List[str]:
        items = data.get("data") or data.get("models") or []
        names: List[str] = []
        for it in items:
            if isinstance(it, str):
                names.append(it)
            elif isinstance(it, dict):
                mid = it.get("id") or it.get("name")
                if mid:
                    names.append(str(mid))
        return names

    async def chat(
        self,
        base_url: str,
        api_key: str,
        model: str,
        messages: List[Dict[str, str]],
        **params: Any,
    ) -> Dict[str, Any]:
        from observability.resilience import RETRY_MAX, retry_async

        if not api_key:
            # 2.4 缺密钥明确报错
            raise RuntimeError(
                "缺少 API Key：请在设置页配置，或设置环境变量 DEEPSEEK_API_KEY/OPERIT_API_KEY（见 .env.example）"
            )
        base = base_url.rstrip("/")
        body = {"model": model, "messages": messages, **params}
        headers = self._headers(api_key)

        async def _once() -> Dict[str, Any]:
            return await self.http.post_json(base + "/v1/chat/completions", headers, body)

        # 4.5 指数退避 ≤3 次
        return await retry_async(_once, retries=RETRY_MAX)

    async def complete_text(
        self,
        base_url: str,
        api_key: str,
        model: str,
        user_text: str,
        system: str = "",
    ) -> str:
        from observability.security import split_prompt_messages

        # 11.2 system / user 分离
        messages = split_prompt_messages(user_text, system=system)
        resp = await self.chat(base_url, api_key, model, messages)
        try:
            return str(resp["choices"][0]["message"]["content"])
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"响应解析失败: {e}: {resp}") from e


class LLMBackedGenerator:
    """把对话式 DSL 生成接到自定义 LLM（N9 Protocol 实现）。"""

    def __init__(
        self,
        client: LLMClient,
        base_url: str,
        api_key: str,
        model: str,
    ) -> None:
        self.client = client
        self.base_url = base_url
        self.api_key = api_key
        self.model = model

    def generate(self, user_text: str) -> str:
        """同步包装：调用 async complete_text。"""
        import asyncio

        system = (
            "你是 DSL 生成器。把用户需求输出为 Loom Workflow YAML，"
            "字段：name / trigger(可选) / device / steps(id+tool|agent)。"
            "只输出 YAML，不要解释。"
        )
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                raise RuntimeError("在事件循环内请改用 async generate_async")
            out = loop.run_until_complete(
                self.client.complete_text(
                    self.base_url, self.api_key, self.model, user_text, system=system
                )
            )
        except RuntimeError:
            out = asyncio.run(
                self.client.complete_text(
                    self.base_url, self.api_key, self.model, user_text, system=system
                )
            )
        return out.strip() + "\n"

    async def generate_async(self, user_text: str) -> str:
        system = (
            "你是 DSL 生成器。把用户需求输出为 Loom Workflow YAML，"
            "字段：name / trigger(可选) / device / steps(id+tool|agent)。"
            "只输出 YAML，不要解释。"
        )
        out = await self.client.complete_text(
            self.base_url, self.api_key, self.model, user_text, system=system
        )
        return out.strip() + "\n"
