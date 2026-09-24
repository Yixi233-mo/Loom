"""内置 MCP / 外部 AI 助手目录 — 含 Work Buddy 下载推荐。

给 `/api/mcp/catalog` 与前端「外接服务」面板用：
  - 内置演示 MCP（一键自测）
  - Claude Code（MCP）
  - Work Buddy（内置推荐，带下载内链）
"""

from __future__ import annotations

from typing import Any, Dict, List

from agent_hub.adapters.work_buddy import work_buddy_catalog_entry


def builtin_mcp_catalog() -> List[Dict[str, Any]]:
    """返回可展示的 MCP / 助手卡片列表（含下载链接字段）。"""
    demo = {
        "id": "loom_demo",
        "name": "Loom 演示 MCP",
        "kind": "builtin-demo",
        "description": "仓库自带演示服务，无需外部安装，用来验证「检测连接 / 工具调用」全链路。",
        "endpoint": "http://127.0.0.1:3900/mcp",
        "default_tool": "code_task",
        "capabilities": ["code.gen", "echo"],
        "download_url": None,
        "download_label": None,
        "install_hint": "在项目根目录执行：python scripts/mock_mcp_server.py",
        "docs": "目录/MCP_工具调用说明.md",
    }
    claude = {
        "id": "claude_code",
        "name": "Claude Code",
        "kind": "external-assistant",
        "description": "外部编码助手。Loom 通过 MCP JSON-RPC 调用 code_task 等工具；也可走简化 REST。",
        "endpoint": "http://127.0.0.1:3001/mcp",
        "default_tool": "code_task",
        "capabilities": ["code.gen", "file.edit", "shell.exec"],
        "download_url": None,
        "download_label": None,
        "install_hint": "自行安装 Claude Code 并开启 MCP 端点后填入上方地址",
        "docs": "目录/MCP_工具调用说明.md",
    }
    buddy = work_buddy_catalog_entry()
    return [demo, claude, buddy]


def catalog_download_links() -> List[Dict[str, str]]:
    """仅推荐可下载的助手（用于「内部链接推荐下载」）。"""
    out: List[Dict[str, str]] = []
    for item in builtin_mcp_catalog():
        url = item.get("download_url")
        if url:
            out.append(
                {
                    "id": str(item["id"]),
                    "name": str(item["name"]),
                    "download_url": str(url),
                    "download_label": str(item.get("download_label") or "下载"),
                    "install_hint": str(item.get("install_hint") or ""),
                }
            )
    return out
