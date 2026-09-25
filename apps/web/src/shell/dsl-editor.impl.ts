/**
 * DSL 编辑器核心 — 双模式（文件 / 表单）、打开保存、保存前 Schema 校验。
 *
 * YAML 使用最小子集编解码（聚焦 Workflow DSL），与 Python `dsl.compiler` 对齐。
 * Schema 校验规则对齐 `dsl/schema.py`（name/steps 必填等）。
 */

export type EditorMode = "file" | "form";

export type DeviceType = "pc" | "tablet" | "mobile" | "any";

export interface WorkflowStepForm {
  id: string;
  kind: "tool" | "agent";
  target: string;
  prompt?: string;
}

export interface WorkflowForm {
  name: string;
  device: DeviceType;
  triggerType?: string;
  triggerCron?: string;
  steps: WorkflowStepForm[];
}

export interface ValidationIssue {
  path: string;
  message: string;
}

export interface ValidationResult {
  ok: boolean;
  issues: ValidationIssue[];
}

export interface DslEditorState {
  mode: EditorMode;
  filename: string;
  yamlText: string;
  form: WorkflowForm;
  dirty: boolean;
}

/** 打开/保存抽象：生产可接 Tauri IPC；测试用内存实现 */
export interface FileSystemPort {
  read(path: string): Promise<string>;
  write(path: string, content: string): Promise<void>;
}

export function createMemoryFs(initial: Record<string, string> = {}): FileSystemPort & {
  files: Map<string, string>;
} {
  const files = new Map(Object.entries(initial));
  return {
    files,
    async read(path: string) {
      const t = files.get(path);
      if (t === undefined) throw new Error(`文件不存在: ${path}`);
      return t;
    },
    async write(path: string, content: string) {
      files.set(path, content);
    },
  };
}

export function emptyForm(): WorkflowForm {
  return {
    name: "",
    device: "any",
    steps: [],
  };
}

export function createEditorState(init?: Partial<DslEditorState>): DslEditorState {
  return {
    mode: "file",
    filename: "untitled.yaml",
    yamlText: "",
    form: emptyForm(),
    dirty: false,
    ...init,
  };
}

// ---------------------------------------------------------------------------
// 最小 YAML 编解码（Workflow DSL 子集）
// ---------------------------------------------------------------------------

export function formToYaml(form: WorkflowForm): string {
  const lines: string[] = [];
  lines.push(`name: ${form.name || "untitled"}`);
  if (form.triggerType) {
    lines.push("trigger:");
    lines.push(`  type: ${form.triggerType}`);
    if (form.triggerCron) lines.push(`  cron: "${form.triggerCron}"`);
  }
  lines.push(`device: ${form.device}`);
  lines.push("steps:");
  if (form.steps.length === 0) {
    lines.push("  []");
  } else {
    for (const s of form.steps) {
      lines.push(`  - id: ${s.id}`);
      if (s.kind === "tool") {
        lines.push(`    tool: ${s.target}`);
      } else {
        lines.push(`    agent: ${s.target}`);
        if (s.prompt) lines.push(`    prompt: "${s.prompt}"`);
      }
    }
  }
  return lines.join("\n") + "\n";
}

/** 解析本编辑器生成的 / 常规 Workflow YAML 子集。解析失败时 name 置空并保留原文。 */
export function yamlToForm(yamlText: string): WorkflowForm {
  const form = emptyForm();
  if (!yamlText || !yamlText.trim()) return form;

  const lines = yamlText.split(/\r?\n/);
  let inTrigger = false;
  let inSteps = false;
  let currentStep: WorkflowStepForm | null = null;

  const flush = () => {
    if (currentStep) {
      form.steps.push(currentStep);
      currentStep = null;
    }
  };

  for (const rawLine of lines) {
    const line = rawLine.replace(/\t/g, "  ");
    const t = line.trim();
    if (!t || t.startsWith("#")) continue;

    const isTop = /^\S/.test(line);
    if (isTop) {
      inTrigger = false;
      inSteps = false;
      flush();
    }

    if (isTop && t.startsWith("name:")) {
      form.name = unquote(t.slice(5).trim());
      continue;
    }
    if (isTop && t.startsWith("device:")) {
      const d = unquote(t.slice(7).trim()) as DeviceType;
      form.device = d || "any";
      continue;
    }
    if (isTop && t === "trigger:") {
      inTrigger = true;
      continue;
    }
    if (isTop && t === "steps:") {
      inSteps = true;
      const rest = t.slice(6).trim();
      if (rest === "[]" || rest === "") {
        // steps: [] 或空列表在下一行
      }
      continue;
    }

    if (inTrigger) {
      if (t.startsWith("type:")) form.triggerType = unquote(t.slice(5).trim());
      else if (t.startsWith("cron:")) form.triggerCron = unquote(t.slice(5).trim());
      continue;
    }

    if (inSteps) {
      if (t === "[]" || t === "- []") continue;
      if (t.startsWith("- ") || t.startsWith("-")) {
        flush();
        currentStep = { id: "", kind: "tool", target: "" };
        const rest = t.replace(/^-\s*/, "");
        if (rest.startsWith("id:")) currentStep.id = unquote(rest.slice(3).trim());
        continue;
      }
      if (currentStep) {
        if (t.startsWith("id:")) currentStep.id = unquote(t.slice(3).trim());
        else if (t.startsWith("tool:")) {
          currentStep.kind = "tool";
          currentStep.target = unquote(t.slice(5).trim());
        } else if (t.startsWith("agent:")) {
          currentStep.kind = "agent";
          currentStep.target = unquote(t.slice(6).trim());
        } else if (t.startsWith("prompt:")) {
          currentStep.prompt = unquote(t.slice(7).trim());
        }
      }
    }
  }
  flush();
  return form;
}

function unquote(s: string): string {
  if (
    (s.startsWith('"') && s.endsWith('"') && s.length >= 2) ||
    (s.startsWith("'") && s.endsWith("'") && s.length >= 2)
  ) {
    return s.slice(1, -1);
  }
  return s;
}

// ---------------------------------------------------------------------------
// Schema 校验（对齐 dsl/schema.py 的 workflow 必填规则）
// ---------------------------------------------------------------------------

const DEVICES: DeviceType[] = ["pc", "tablet", "mobile", "any"];

export function validateWorkflowYaml(yamlText: string): ValidationResult {
  const issues: ValidationIssue[] = [];
  const form = yamlToForm(yamlText);

  if (!form.name || form.name.trim() === "" || form.name === "untitled") {
    // 仅当原文也没有 name 时才报错（untitled 是 formToYaml 默认，原文含 name 则 OK）
    if (!/^\s*name:/m.test(yamlText)) {
      issues.push({ path: "/name", message: "缺少必填字段: name" });
    }
  }
  if (!yamlText.trim()) {
    issues.push({ path: "/", message: "内容为空" });
    return { ok: false, issues };
  }
  if (!/^\s*steps:/m.test(yamlText)) {
    issues.push({ path: "/steps", message: "缺少必填字段: steps" });
  } else if (form.steps.length === 0 && !/steps:\s*\[\s*\]/.test(yamlText)) {
    // steps: 存在但解析不到任何步骤（排除显式 []）
    if (!/^\s*- /m.test(yamlText) && !/^\s*-id/m.test(yamlText)) {
      const hasListItem = yamlText
        .split(/\r?\n/)
        .some((l) => /^\s+-\s+/.test(l) || /^\s+-\s*$/.test(l));
      if (!hasListItem) {
        issues.push({ path: "/steps", message: "steps 至少需要 1 项" });
      }
    }
  }

  if (form.device && !DEVICES.includes(form.device)) {
    issues.push({
      path: "/device",
      message: `非法 device: ${form.device}，应为 ${DEVICES.join(" / ")}`,
    });
  }

  form.steps.forEach((s, i) => {
    if (!s.id) issues.push({ path: `/steps/${i}/id`, message: `steps[${i}] 缺少必填字段: id` });
    if (s.kind === "tool" && !s.target) {
      issues.push({ path: `/steps/${i}/tool`, message: `steps[${i}] 缺少 tool/agent 目标` });
    }
    if (s.kind === "agent" && !s.target) {
      issues.push({ path: `/steps/${i}/agent`, message: `steps[${i}] 缺少 tool/agent 目标` });
    }
  });

  return { ok: issues.length === 0, issues };
}

export function validateBeforeSave(yamlText: string): ValidationResult {
  return validateWorkflowYaml(yamlText);
}

// ---------------------------------------------------------------------------
// 编辑器操作
// ---------------------------------------------------------------------------

export async function openYamlFile(
  fs: FileSystemPort,
  path: string
): Promise<DslEditorState> {
  const yamlText = await fs.read(path);
  return {
    mode: "file",
    filename: path,
    yamlText,
    form: yamlToForm(yamlText),
    dirty: false,
  };
}

export type SaveResult =
  | { ok: true; path: string }
  | { ok: false; issues: ValidationIssue[] };

/** 保存前做 Schema 校验；不通过则拒绝保存。 */
export async function saveYamlFile(
  fs: FileSystemPort,
  state: DslEditorState,
  path?: string
): Promise<SaveResult> {
  const target = path ?? state.filename;
  const check = validateBeforeSave(state.yamlText);
  if (!check.ok) {
    return { ok: false, issues: check.issues };
  }
  await fs.write(target, state.yamlText);
  return { ok: true, path: target };
}

export function switchMode(state: DslEditorState, mode: EditorMode): DslEditorState {
  if (mode === state.mode) return state;
  if (mode === "form") {
    return { ...state, mode, form: yamlToForm(state.yamlText) };
  }
  // form → file：把表单序列化进 yamlText
  return { ...state, mode, yamlText: formToYaml(state.form) };
}

export function updateForm(state: DslEditorState, form: WorkflowForm): DslEditorState {
  return { ...state, form, yamlText: formToYaml(form), dirty: true };
}

export function updateYamlText(state: DslEditorState, yamlText: string): DslEditorState {
  return { ...state, yamlText, form: yamlToForm(yamlText), dirty: true };
}
