/**
 * DSL 编辑器组件（React.createElement，无 JSX，便于 Node 直测）。
 * `dsl-editor.tsx` 再导出本模块，供 Tauri/React 工具链使用。
 */

import * as React from "react";
import {
  type DslEditorState,
  type FileSystemPort,
  type ValidationIssue,
  type WorkflowForm,
  type WorkflowStepForm,
  saveYamlFile,
  switchMode,
  updateForm,
  updateYamlText,
  validateBeforeSave,
} from "./dsl-editor.impl.ts";

const e = React.createElement;

export function TextareaCodeEditor(props: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return e("textarea", {
    className: "loom-dsl-editor-code",
    "data-editor-backend": "textarea",
    value: props.value,
    placeholder: props.placeholder ?? "# 在此编辑 DSL YAML",
    spellCheck: false,
    rows: 16,
    onChange: (ev: { target: { value: string } }) => props.onChange(ev.target.value),
  });
}

export function ValidationBanner(props: { issues: ValidationIssue[] }) {
  if (props.issues.length === 0) return null;
  return e(
    "div",
    { className: "loom-dsl-validation", role: "alert", "data-valid": "false" },
    e("p", { className: "loom-dsl-validation-title" }, "Schema 校验未通过，已阻止保存"),
    e(
      "ul",
      { className: "loom-dsl-validation-list" },
      props.issues.map((iss, i) =>
        e(
          "li",
          { key: i, className: "loom-dsl-validation-item" },
          `${iss.path}: ${iss.message}`
        )
      )
    )
  );
}

export function FormModeEditor(props: {
  form: WorkflowForm;
  onChange: (form: WorkflowForm) => void;
}) {
  const { form, onChange } = props;
  const setStep = (i: number, patch: Partial<WorkflowStepForm>) => {
    const steps = form.steps.map((s, idx) => (idx === i ? { ...s, ...patch } : s));
    onChange({ ...form, steps });
  };
  return e(
    "div",
    { className: "loom-dsl-form", "data-mode": "form" },
    e(
      "label",
      { className: "loom-dsl-field" },
      e("span", null, "name"),
      e("input", {
        "data-field": "name",
        value: form.name,
        onChange: (ev: { target: { value: string } }) =>
          onChange({ ...form, name: ev.target.value }),
      })
    ),
    e(
      "label",
      { className: "loom-dsl-field" },
      e("span", null, "device"),
      e(
        "select",
        {
          "data-field": "device",
          value: form.device,
          onChange: (ev: { target: { value: string } }) =>
            onChange({ ...form, device: ev.target.value as WorkflowForm["device"] }),
        },
        ["pc", "tablet", "mobile", "any"].map((d) => e("option", { key: d, value: d }, d))
      )
    ),
    e(
      "label",
      { className: "loom-dsl-field" },
      e("span", null, "trigger.type"),
      e("input", {
        "data-field": "triggerType",
        value: form.triggerType ?? "",
        placeholder: "cron / webhook / ...",
        onChange: (ev: { target: { value: string } }) =>
          onChange({ ...form, triggerType: ev.target.value }),
      })
    ),
    e(
      "div",
      { className: "loom-dsl-steps" },
      e("h4", null, "steps"),
      form.steps.map((s, i) =>
        e(
          "div",
          { key: i, className: "loom-dsl-step" },
          e("input", {
            "data-field": `step-${i}-id`,
            placeholder: "id",
            value: s.id,
            onChange: (ev: { target: { value: string } }) => setStep(i, { id: ev.target.value }),
          }),
          e(
            "select",
            {
              "data-field": `step-${i}-kind`,
              value: s.kind,
              onChange: (ev: { target: { value: string } }) =>
                setStep(i, { kind: ev.target.value as "tool" | "agent" }),
            },
            e("option", { value: "tool" }, "tool"),
            e("option", { value: "agent" }, "agent")
          ),
          e("input", {
            "data-field": `step-${i}-target`,
            placeholder: "tool / agent name",
            value: s.target,
            onChange: (ev: { target: { value: string } }) =>
              setStep(i, { target: ev.target.value }),
          })
        )
      ),
      e(
        "button",
        {
          type: "button",
          "data-action": "add-step",
          onClick: () =>
            onChange({
              ...form,
              steps: [
                ...form.steps,
                { id: `step_${form.steps.length + 1}`, kind: "tool", target: "" },
              ],
            }),
        },
        "添加步骤"
      )
    )
  );
}

export interface DslEditorProps {
  fs: FileSystemPort;
  state: DslEditorState;
  onState: (s: DslEditorState) => void;
  onSaved?: (path: string) => void;
}

export function DslEditor(props: DslEditorProps) {
  const [issues, setIssues] = React.useState<ValidationIssue[]>([]);
  const [status, setStatus] = React.useState<string>("");

  const set = (s: DslEditorState) => props.onState(s);

  const doSave = async () => {
    const result = await saveYamlFile(props.fs, props.state);
    if (!result.ok) {
      setIssues(result.issues);
      setStatus("保存失败：Schema 校验未通过");
      return;
    }
    setIssues([]);
    setStatus(`已保存 ${result.path}`);
    props.onSaved?.(result.path);
    set({ ...props.state, dirty: false, filename: result.path });
  };

  const doValidate = () => {
    const r = validateBeforeSave(props.state.yamlText);
    setIssues(r.issues);
    setStatus(r.ok ? "校验通过" : `发现 ${r.issues.length} 处问题`);
  };

  return e(
    "div",
    { className: "loom-dsl-editor", "data-component": "dsl-editor" },
    e(
      "div",
      { className: "loom-dsl-toolbar" },
      e(
        "button",
        {
          type: "button",
          "data-action": "mode-file",
          "data-active": props.state.mode === "file",
          onClick: () => set(switchMode(props.state, "file")),
        },
        "文件模式"
      ),
      e(
        "button",
        {
          type: "button",
          "data-action": "mode-form",
          "data-active": props.state.mode === "form",
          onClick: () => set(switchMode(props.state, "form")),
        },
        "表单模式"
      ),
      e(
        "button",
        { type: "button", "data-action": "save", onClick: () => void doSave() },
        "保存"
      ),
      e(
        "button",
        { type: "button", "data-action": "validate", onClick: doValidate },
        "校验"
      )
    ),
    e(
      "p",
      { className: "loom-dsl-status", "data-status": "true" },
      props.state.filename,
      " — ",
      status
    ),
    e(ValidationBanner, { issues }),
    props.state.mode === "file"
      ? e(TextareaCodeEditor, {
          value: props.state.yamlText,
          onChange: (v: string) => set(updateYamlText(props.state, v)),
        })
      : e(FormModeEditor, {
          form: props.state.form,
          onChange: (f: WorkflowForm) => set(updateForm(props.state, f)),
        })
  );
}

export default DslEditor;
