"""把 dist 构建产物打成单文件 HTML（JS/CSS 内联），便于预览/单文件分发。

用法：
  python scripts/build_single_html.py
输出：
  app.html
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
OUT = ROOT / "app.html"


def escape_for_inline_script(js: str) -> str:
    """防止内联 <script> 被 HTML 提前闭合。"""
    return js.replace("</script", "<\\/script").replace("<!--", "<\\!--")


def main() -> None:
    html_path = DIST / "index.html"
    if not html_path.exists():
        raise SystemExit("请先执行 npm run build")
    html = html_path.read_text(encoding="utf-8")

    css_files = sorted((DIST / "assets").glob("*.css"))
    js_files = sorted((DIST / "assets").glob("*.js"))

    css_blob = "\n".join(p.read_text(encoding="utf-8") for p in css_files)
    js_blob = escape_for_inline_script(
        "\n".join(p.read_text(encoding="utf-8") for p in js_files)
    )

    html = re.sub(
        r'<link[^>]+rel="stylesheet"[^>]*>',
        lambda _m: f"<style>\n{css_blob}\n</style>",
        html,
    )
    html = re.sub(
        r'<script[^>]+src="[^"]+\.js"[^>]*></script>',
        lambda _m: f'<script type="module">\n{js_blob}\n</script>',
        html,
    )
    html = re.sub(
        r"<title>.*</title>",
        lambda _m: "<title>Loom Shell · 织巢</title>",
        html,
        count=1,
    )

    OUT.write_text(html, encoding="utf-8")
    print(f"单文件已生成: {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
