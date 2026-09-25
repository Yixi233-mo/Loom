"""DSL 热加载 — 监听 plugins/ 目录，2s 内生效，Hub 不重启。

策略：轮询 mtime/size（标准库），默认 interval=0.5s。
变更后刷新编译缓存，并回调 on_reload（更新工具列表 / cron 任务）。
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

Snapshot = Dict[str, Tuple[int, int]]  # path -> (mtime_ns, size)


class DslCache:
    """YAML → 编译结果缓存（含工具列表提取）。"""

    def __init__(self) -> None:
        self.by_path: Dict[str, Dict[str, Any]] = {}
        self.tools: Set[str] = set()
        self.workflows: Dict[str, Dict[str, Any]] = {}
        self.plugins: Dict[str, Dict[str, Any]] = {}

    def tool_names(self) -> List[str]:
        return sorted(self.tools)

    def apply(self, path: str, spec: Optional[Dict[str, Any]]) -> None:
        self.by_path[path] = spec or {}
        self._rebuild()

    def remove(self, path: str) -> None:
        self.by_path.pop(path, None)
        self._rebuild()

    def _rebuild(self) -> None:
        self.tools = set()
        self.workflows = {}
        self.plugins = {}
        for p, spec in self.by_path.items():
            if not spec:
                continue
            if "steps" in spec:
                name = spec.get("name") or Path(p).stem
                self.workflows[name] = {"path": p, **spec}
            elif "tools" in spec or "ui" in spec:
                name = spec.get("name") or Path(p).stem
                self.plugins[name] = {"path": p, **spec}
                for t in spec.get("tools") or []:
                    if isinstance(t, dict) and t.get("name"):
                        self.tools.add(str(t["name"]))
                    elif isinstance(t, str):
                        self.tools.add(t)
            for step in spec.get("steps") or []:
                if isinstance(step, dict) and step.get("tool"):
                    self.tools.add(str(step["tool"]))


class DslHotReloader:
    """轮询目录，检测 YAML 增删改，编译并回调。"""

    def __init__(
        self,
        root: str | Path,
        cache: Optional[DslCache] = None,
        on_reload: Optional[Callable[[DslCache], None]] = None,
        interval: float = 0.5,
    ) -> None:
        self.root = Path(root)
        self.cache = cache or DslCache()
        self.on_reload = on_reload
        self.interval = interval
        self._snapshot: Snapshot = {}
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self.reload_count = 0
        self.enabled = True

    # ---- 快照 ----

    def _scan(self) -> Snapshot:
        snap: Snapshot = {}
        if not self.root.exists():
            return snap
        for p in self.root.rglob("*.yaml"):
            try:
                st = p.stat()
                snap[str(p)] = (st.st_mtime_ns, st.st_size)
            except OSError:
                continue
        for p in self.root.rglob("*.yml"):
            try:
                st = p.stat()
                snap[str(p)] = (st.st_mtime_ns, st.st_size)
            except OSError:
                continue
        return snap

    def _load_yaml(self, path: str) -> Optional[Dict[str, Any]]:
        try:
            import yaml

            data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        except Exception as e:  # noqa: BLE001
            logger.warning("DSL 热加载解析失败 %s: %s", path, e)
            return None

    def _diff(self, new: Snapshot) -> Tuple[Set[str], Set[str], Set[str]]:
        old_keys = set(self._snapshot)
        new_keys = set(new)
        added = new_keys - old_keys
        removed = old_keys - new_keys
        changed = {
            k
            for k in old_keys & new_keys
            if self._snapshot[k] != new[k]
        }
        return added, removed, changed

    def scan_once(self) -> bool:
        """扫描一次；有变更则刷新缓存并回调。返回是否发生变更。"""
        if not self.enabled:
            return False
        new = self._scan()
        added, removed, changed = self._diff(new)
        if not (added or removed or changed):
            self._snapshot = new
            return False

        for path in added | changed:
            self.cache.apply(path, self._load_yaml(path))
        for path in removed:
            self.cache.remove(path)
        self._snapshot = new
        self.reload_count += 1
        logger.info(
            "DSL 热加载: +%d ~%d -%d tools=%s",
            len(added),
            len(changed),
            len(removed),
            self.cache.tool_names(),
        )
        if self.on_reload:
            try:
                self.on_reload(self.cache)
            except Exception as e:  # noqa: BLE001
                logger.error("on_reload 回调失败: %s", e, exc_info=True)
        return True

    def bootstrap(self) -> None:
        """启动时全量加载（不触发回调以外的副作用）。"""
        self.scan_once()
        if self.reload_count == 0:
            # 首次即使无 diff 也要把已有文件灌进缓存
            new = self._scan()
            for path, _ in new.items():
                self.cache.apply(path, self._load_yaml(path))
            self._snapshot = new

    def _loop(self) -> None:
        while not self._stop.is_set():
            self.scan_once()
            self._stop.wait(self.interval)

    def start(self) -> None:
        self.bootstrap()
        if self._thread is None or not self._thread.is_alive():
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._loop, name="dsl-hot-reload", daemon=True
            )
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None


def apply_tools_to_stack(cache: DslCache, stack: Any) -> None:
    """把 DSL 中的 tool 名同步进 HubStack.tools（占位可调用）。"""
    for name in cache.tool_names():
        if name not in stack.tools:
            stack.tools[name] = (lambda n: (lambda **kw: {"tool": n, "ok": True}))(name)


def apply_cron_to_scheduler(cache: DslCache, scheduler: Any) -> None:
    """把 Workflow cron trigger 同步进 TriggerScheduler。"""
    for name, spec in cache.workflows.items():
        trig = (spec or {}).get("trigger") or {}
        if trig.get("type") == "cron" and trig.get("cron"):
            scheduler.add_or_update(
                name,
                str(trig["cron"]),
                {"name": name, "device": (spec or {}).get("device", "any")},
            )
