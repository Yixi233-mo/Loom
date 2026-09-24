/**
 * UI Schema 白名单注册表 — 与 JSX 解耦，便于单测。
 *
 * Plugin DSL 的 ui 字段：
 *   { "type": "form"|"list"|"chat"|"chart", "props": { ... } }
 */

export type UiComponentType = "form" | "list" | "chat" | "chart";

export interface UiSchema {
  type: string;
  props?: Record<string, unknown>;
}

export interface UiComponentDescriptor {
  type: UiComponentType;
  /** 展示名，便于友好提示 */
  label: string;
}

/** 白名单：只允许这 4 类组件 */
export const UI_WHITELIST: Record<UiComponentType, UiComponentDescriptor> = {
  form: { type: "form", label: "表单" },
  list: { type: "list", label: "列表" },
  chat: { type: "chat", label: "对话" },
  chart: { type: "chart", label: "图表" },
};

export const UI_TYPES: UiComponentType[] = ["form", "list", "chat", "chart"];

export function isUiComponentType(value: string): value is UiComponentType {
  return Object.prototype.hasOwnProperty.call(UI_WHITELIST, value);
}

export type ResolveResult =
  | { ok: true; descriptor: UiComponentDescriptor; props: Record<string, unknown> }
  | { ok: false; reason: string; fallbackLabel: string };

/**
 * 解析 UI Schema → 白名单命中 / 友好失败。
 * 未注册类型不抛异常，返回 fallback 信息。
 */
export function resolveUiSchema(schema: UiSchema | null | undefined): ResolveResult {
  if (!schema || typeof schema !== "object") {
    return {
      ok: false,
      reason: "UI Schema 为空或格式错误",
      fallbackLabel: "无效的插件界面定义",
    };
  }
  const rawType = schema.type;
  if (typeof rawType !== "string" || rawType.trim() === "") {
    return {
      ok: false,
      reason: "缺少 type 字段",
      fallbackLabel: "未指定组件类型",
    };
  }
  if (!isUiComponentType(rawType)) {
    return {
      ok: false,
      reason: `未注册的组件类型: ${rawType}`,
      fallbackLabel: `暂不支持的组件类型「${rawType}」`,
    };
  }
  const props = (schema.props ?? {}) as Record<string, unknown>;
  return {
    ok: true,
    descriptor: UI_WHITELIST[rawType],
    props,
  };
}

/** 提示文案：未注册组件的友好展示 */
export function unknownTypeMessage(type: string): string {
  return `暂不支持的组件类型「${type}」，当前可用：${UI_TYPES.join(" / ")}`;
}
