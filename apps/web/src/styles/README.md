# Loom 设计系统 Token（FE.2）

> 阶段验收：**token 文件 + 本文档**  
> 主题气质：暖白毛玻璃 · 蜜桃/杏/陶土强调 · 鼠尾草状态 · 技能树节点  
> 文件：`tokens.css`（权威） · `tokens.ts`（类型/JS 侧） · `base.css` / `components.css`（用法层）

---

## 1. 分层

| 层 | 文件 | 谁可以依赖 |
|----|------|------------|
| **Primitive** `--p-*` | `tokens.css` | 只给 Token 作者改；组件禁止直接用 |
| **Semantic**（业务名） | `tokens.css` | 视图 / 组件 / 业务样式 |
| **Component**（少量） | `tokens.css` 末段 | 高频组件局部（按钮/输入/卡片/Toast） |
| **用法** | `base.css` `components.css` | 类名实现，不写死色值 |

JS 只在需要分支逻辑（如技能树状态类名）时读 `tokens.ts`，优先 CSS 变量。

---

## 2. 主题

- 默认 **暖光** `light`（`:root` / `[data-theme="light"]`）
- 可选 **暖夜** `dark`（`[data-theme="dark"]`）— 仍是暖调，不是冷灰死黑
- 切换：`document.documentElement.dataset.theme = "light" | "dark"`
- 或使用 `themeAttr("dark")`（`tokens.ts`）合并到元素属性

`prefers-reduced-motion` 下动效时长自动归零。

---

## 3. 色板语义（组件只记这些）

| Token | 用途 |
|-------|------|
| `--bg` `--bg-elevated` `--bg-glow` | 页面底 / 浮层底 / 暖光晕 |
| `--panel` `--panel-solid` `--panel-muted` | 毛玻璃面板 / 实底 / 次级底 |
| `--ink` `--ink-secondary` `--muted` `--ink-faint` | 主文 / 次文 / 弱文 / 极弱 |
| `--line` `--line-strong` | 描边 |
| `--accent` `--accent-strong` `--accent-soft` `--accent-ink` | 主按钮/选中（蜜桃杏） |
| `--apricot` `--terracotta` `--peach-glow` | 辅助暖强调 |
| `--success` `--success-soft` `--sage` | 已完成 / 已连接（鼠尾草） |
| `--champagne` `--champagne-soft` | 成就 Toast、开发中标记 |
| `--warn` `--danger` 及 `*-soft` | 警告 / 失败（仍偏暖） |
| `--node-on` `--node-off` `--node-half` `--node-glow` | 技能树点亮 / 灰 / 半亮 / 微光 |

**禁止**在业务 CSS 里写死 `#hex`（除历史 `styles.css` 待逐步替换）。

---

## 4. 尺度

**间距**（4px 基准）`--space-0` … `--space-10`（0 / 4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48 / 64）

**圆角** `--radius-xs|sm|md|lg|xl|pill`（6 → 8 → 12 → 16 → 22 → 999）

**阴影** `--shadow-sm|md|lg` + 统一 `--shadow`

**字体**  
- 族：`--font-body` / `--font-display` / `--font-mono`  
- 级：`--text-2xs` … `--text-display`（11 → 40）  
- 行高：`--leading-tight|normal|relaxed`  
- 字重：`--weight-normal|medium|semibold|bold`  
- 字距：`--tracking-tight|normal|wide|caps`

**动效** `--ease-out` `--ease-spring` · `--duration-fast|normal|slow|toast`

**层级** `--z-panel|drawer|modal|toast`

---

## 5. 组件 Token（局部）

| 组 | 变量 |
|----|------|
| 按钮 | `--button-primary-bg` / `-hover` / `-ink` · `--button-ghost-*` |
| 卡片 | `--card-radius` `--card-padding` `--card-bg` `--card-border` `--card-backdrop` `--card-shadow` |
| 输入 | `--input-bg` `--input-border` `--input-border-focus` `--input-radius` |
| Toast | `--toast-bg` `--toast-border` `--toast-radius` |
| 玻璃 | `--glass-bg` `--glass-border` `--glass-blur` |

类名契约见 `components/index.ts`：`.glass` `.ui-button` `.ui-input` `.ui-modal` `.ui-toast` `.ui-skill-node--on|half|off` 等，样式在 `components.css`。

---

## 6. 使用示例

```css
.panel {
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--card-radius);
  backdrop-filter: blur(var(--glass-blur));
  box-shadow: var(--card-shadow);
  padding: var(--space-6);
}
```

```ts
import { SKILL_NODE_VAR, isThemeName } from "../styles/tokens.ts";

const cls = state === "on" ? "ui-skill-node--on" : "ui-skill-node--off";
```

---

## 7. 验收对照

- [x] 色板 / 间距 / 圆角 / 阴影 / 字体层级均为 CSS 变量（`tokens.css`）
- [x] 暖光默认 + 暖夜可选（`data-theme`）
- [x] Token 文档（本文件）
- [x] 类型化导出 `tokens.ts` + 单测 `tests/js/test_design_tokens.mjs`
