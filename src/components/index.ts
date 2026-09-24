/**
 * FE.1 通用组件占位 — FE.4 充实 Button/Input/Modal/Toast/Layout。
 * 当前仅导出类名约定，避免破坏现有 views 测试。
 */

export const UI = {
  button: "ui-button",
  buttonPrimary: "ui-button--primary",
  input: "ui-input",
  modal: "ui-modal",
  toast: "ui-toast",
  panel: "ui-panel glass",
  card: "ui-card glass",
  skillNode: "ui-skill-node",
  skillNodeOn: "ui-skill-node--on",
  skillNodeOff: "ui-skill-node--off",
} as const;

export type UiClassKey = keyof typeof UI;
