"""Agent Registry — 管理本地 + 外部 Agent。

三个核心方法：register / match / invoke。
调用未知 Agent 抛 AgentNotFoundError。
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, List, Optional

# adapter 协议：async (prompt, **kwargs) -> Any
AgentAdapter = Callable[..., Awaitable[Any]]


class AgentNotFoundError(Exception):
    """调用未注册的 Agent 时抛出。"""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"未知 Agent: {name}")

    def __str__(self) -> str:
        return f"未知 Agent: {self.name}"


class AgentRegistry:
    """管理本地 + 外部 Agent。"""

    def __init__(self) -> None:
        self.agents: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, adapter: AgentAdapter, capabilities: List[str]) -> None:
        """注册一个 Agent（本地或外部）。同名覆盖。"""
        if not name:
            raise ValueError("Agent name 不能为空")
        if not callable(adapter):
            raise TypeError(f"adapter 必须可调用: {name!r}")
        self.agents[name] = {
            "adapter": adapter,
            "capabilities": list(capabilities or []),
        }

    def unregister(self, name: str) -> None:
        """注销 Agent；不存在时抛 AgentNotFoundError。"""
        if name not in self.agents:
            raise AgentNotFoundError(name)
        del self.agents[name]

    def list_agents(self) -> List[str]:
        return list(self.agents.keys())

    def match(self, capability: str) -> List[str]:
        """按能力匹配 Agent，返回具备该 capability 的 Agent 名列表。"""
        return [
            name
            for name, meta in self.agents.items()
            if capability in meta["capabilities"]
        ]

    def capabilities(self, name: str) -> List[str]:
        """返回指定 Agent 的能力列表；未知 Agent 抛 AgentNotFoundError。"""
        if name not in self.agents:
            raise AgentNotFoundError(name)
        return list(self.agents[name]["capabilities"])

    async def invoke(self, name: str, prompt: str, **kwargs: Any) -> Any:
        """调用指定 Agent；未知 Agent 抛 AgentNotFoundError。"""
        if name not in self.agents:
            raise AgentNotFoundError(name)
        adapter = self.agents[name]["adapter"]
        try:
            from observability.logging import get_logger, new_trace_id

            trace_id = str(kwargs.pop("trace_id", "")) or new_trace_id()
            with get_logger().span(
                "agent.invoke", trace_id=trace_id, agent_name=name
            ) as span:
                result = await adapter(prompt, **kwargs)
                span.set(task_status="done")
                return result
        except ImportError:
            return await adapter(prompt, **kwargs)
