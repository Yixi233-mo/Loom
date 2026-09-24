/**
 * FE.4 通用组件 — Button / Input / Modal / Toast / Layout
 * React.createElement，无 JSX；状态齐全（disabled / invalid / open / tone）。
 */

import * as React from "react";

const e = React.createElement;

export const UI = {
  button: "ui-button",
  buttonPrimary: "ui-button--primary",
  buttonGhost: "ui-button--ghost",
  buttonDanger: "ui-button--danger",
  input: "ui-input",
  inputInvalid: "ui-input--invalid",
  modal: "ui-modal",
  modalBackdrop: "ui-modal-backdrop",
  toast: "ui-toast",
  toastSuccess: "ui-toast--success",
  toastError: "ui-toast--error",
  panel: "ui-panel glass",
  card: "ui-card glass",
  layout: "ui-layout",
  skillNode: "ui-skill-node",
  skillNodeOn: "ui-skill-node--on",
  skillNodeOff: "ui-skill-node--off",
  skillNodeHalf: "ui-skill-node--half",
} as const;

export type UiClassKey = keyof typeof UI;
export type ButtonVariant = "primary" | "ghost" | "danger";
export type ToastTone = "info" | "success" | "error";

export function Button(props: {
  children?: unknown;
  variant?: ButtonVariant;
  type?: "button" | "submit" | "reset";
  disabled?: boolean;
  loading?: boolean;
  className?: string;
  onClick?: () => void;
  "data-action"?: string;
}) {
  const variant = props.variant ?? "primary";
  const variantCls =
    variant === "primary"
      ? UI.buttonPrimary
      : variant === "ghost"
        ? UI.buttonGhost
        : UI.buttonDanger;
  const disabled = !!props.disabled || !!props.loading;
  return e(
    "button",
    {
      type: props.type ?? "button",
      className: `${UI.button} ${variantCls}${props.className ? " " + props.className : ""}`,
      disabled,
      "aria-busy": props.loading ? "true" : undefined,
      "data-loading": props.loading ? "true" : "false",
      "data-variant": variant,
      "data-action": props["data-action"],
      onClick: () => {
        if (!disabled && props.onClick) props.onClick();
      },
    },
    props.loading ? "处理中…" : (props.children as any)
  );
}

export function Input(props: {
  value: string;
  onChange?: (v: string) => void;
  placeholder?: string;
  disabled?: boolean;
  invalid?: boolean;
  error?: string;
  type?: string;
  name?: string;
  "data-field"?: string;
}) {
  const invalid = !!props.invalid || !!props.error;
  return e(
    "div",
    { className: "ui-field", "data-invalid": invalid ? "true" : "false" },
    e("input", {
      className: `${UI.input}${invalid ? " " + UI.inputInvalid : ""}`,
      type: props.type ?? "text",
      name: props.name,
      value: props.value,
      placeholder: props.placeholder,
      disabled: !!props.disabled,
      "aria-invalid": invalid ? "true" : "false",
      "data-field": props["data-field"],
      onChange: (ev: { target: { value: string } }) =>
        props.onChange?.(ev.target.value),
    }),
    props.error
      ? e(
          "p",
          { className: "ui-field-error", role: "alert", "data-error": "true" },
          props.error
        )
      : null
  );
}

export function Modal(props: {
  open: boolean;
  title: string;
  children?: unknown;
  onClose?: () => void;
  footer?: unknown;
}) {
  if (!props.open) {
    return e("div", {
      className: "ui-modal-root",
      "data-open": "false",
      "data-view": "modal",
    });
  }
  return e(
    "div",
    {
      className: "ui-modal-root",
      "data-open": "true",
      "data-view": "modal",
      role: "dialog",
      "aria-modal": "true",
      "aria-label": props.title,
    },
    e("div", {
      className: UI.modalBackdrop,
      "data-action": "modal-backdrop",
      onClick: () => props.onClose?.(),
    }),
    e(
      "div",
      { className: UI.modal + " glass" },
      e(
        "header",
        { className: "ui-modal-header" },
        e("h3", null, props.title),
        e(
          "button",
          {
            type: "button",
            className: UI.button + " " + UI.buttonGhost,
            "data-action": "modal-close",
            "aria-label": "关闭",
            onClick: () => props.onClose?.(),
          },
          "×"
        )
      ),
      e("div", { className: "ui-modal-body" }, props.children as any),
      props.footer
        ? e("footer", { className: "ui-modal-footer" }, props.footer as any)
        : null
    )
  );
}

export function Toast(props: {
  message: string;
  tone?: ToastTone;
  visible?: boolean;
  onDismiss?: () => void;
}) {
  if (props.visible === false) {
    return e("div", {
      className: "ui-toast-root",
      "data-visible": "false",
      "data-view": "toast",
    });
  }
  const tone = props.tone ?? "info";
  const toneCls =
    tone === "success"
      ? UI.toastSuccess
      : tone === "error"
        ? UI.toastError
        : "";
  return e(
    "div",
    {
      className: "ui-toast-root",
      "data-visible": "true",
      "data-tone": tone,
      "data-view": "toast",
      role: "status",
    },
    e(
      "div",
      { className: `${UI.toast}${toneCls ? " " + toneCls : ""}` },
      e("span", { className: "ui-toast-msg" }, props.message),
      e(
        "button",
        {
          type: "button",
          className: "ui-toast-close",
          "data-action": "toast-dismiss",
          "aria-label": "关闭通知",
          onClick: () => props.onDismiss?.(),
        },
        "×"
      )
    )
  );
}

export function Layout(props: {
  nav?: unknown;
  aside?: unknown;
  children?: unknown;
  footer?: unknown;
  density?: "compact" | "cozy";
}) {
  const density = props.density ?? "cozy";
  return e(
    "div",
    {
      className: `${UI.layout} ui-layout--${density}`,
      "data-view": "layout",
      "data-density": density,
    },
    props.nav
      ? e("header", { className: "ui-layout-nav" }, props.nav as any)
      : null,
    e(
      "div",
      { className: "ui-layout-main" },
      props.aside
        ? e("aside", { className: "ui-layout-aside" }, props.aside as any)
        : null,
      e("main", { className: "ui-layout-content" }, props.children as any)
    ),
    props.footer
      ? e("footer", { className: "ui-layout-footer" }, props.footer as any)
      : null
  );
}

export function Card(props: {
  title?: string;
  children?: unknown;
  footer?: unknown;
  className?: string;
}) {
  return e(
    "article",
    {
      className: `${UI.card}${props.className ? " " + props.className : ""}`,
      "data-view": "card",
    },
    props.title ? e("h3", { className: "ui-card-title" }, props.title) : null,
    e("div", { className: "ui-card-body" }, props.children as any),
    props.footer
      ? e("footer", { className: "ui-card-footer" }, props.footer as any)
      : null
  );
}

/** FE.4 示例画布 — 本地预览组件状态 */
export function ComponentGallery() {
  const [open, setOpen] = React.useState(false);
  const [toast, setToast] = React.useState<{
    message: string;
    tone: ToastTone;
    visible: boolean;
  }>({ message: "", tone: "info", visible: false });
  const [text, setText] = React.useState("");

  return e(
    "section",
    { className: "ui-gallery glass", "data-view": "component-gallery" },
    e("h2", null, "通用组件示例"),
    e(
      "div",
      { className: "ui-gallery-row" },
      e(Button, {
        "data-action": "demo-primary",
        onClick: () =>
          setToast({ message: "主按钮已点击", tone: "success", visible: true }),
      }, "主要按钮"),
      e(Button, { variant: "ghost" }, "幽灵按钮"),
      e(Button, { variant: "danger", disabled: true }, "危险 · disabled"),
      e(Button, { loading: true }, "加载中")
    ),
    e(Input, {
      value: text,
      onChange: setText,
      placeholder: "受控输入框",
      "data-field": "demo-input",
    }),
    e(Input, {
      value: "",
      invalid: true,
      error: "示例：字段不合法",
      placeholder: "错误态",
      "data-field": "demo-input-invalid",
    }),
    e(
      "div",
      { className: "ui-gallery-row" },
      e(Button, {
        variant: "ghost",
        "data-action": "open-modal",
        onClick: () => setOpen(true),
      }, "打开 Modal"),
      e(Button, {
        variant: "ghost",
        "data-action": "show-toast",
        onClick: () =>
          setToast({ message: "暖色成就反馈", tone: "success", visible: true }),
      }, "显示 Toast")
    ),
    e(Modal, {
      open,
      title: "示例弹窗",
      onClose: () => setOpen(false),
      footer: e(Button, {
        "data-action": "modal-ok",
        onClick: () => setOpen(false),
      }, "知道了"),
    }, e("p", null, "Modal 正文：可放置表单或说明。")),
    e(Toast, {
      message: toast.message || "通知",
      tone: toast.tone,
      visible: toast.visible,
      onDismiss: () => setToast((t) => ({ ...t, visible: false })),
    })
  );
}
