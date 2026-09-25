/**
 * DSL 编辑器入口（TSX）— 文件编辑 + 表单填写双模式。
 * 保存前做 Schema 校验。
 *
 * 逻辑在 `dsl-editor.impl.ts`，组件在 `dsl-editor.ui.ts`（createElement，可单测）。
 * monaco-editor 不在当前环境时退化为 textarea（预留 Monaco 接口）。
 */

export {
  DslEditor,
  FormModeEditor,
  TextareaCodeEditor,
  ValidationBanner,
  type DslEditorProps,
} from "./dsl-editor.ui.ts";

export {
  createEditorState,
  createMemoryFs,
  emptyForm,
  formToYaml,
  openYamlFile,
  saveYamlFile,
  switchMode,
  updateForm,
  updateYamlText,
  validateBeforeSave,
  validateWorkflowYaml,
  yamlToForm,
  type DslEditorState,
  type EditorMode,
  type FileSystemPort,
  type ValidationIssue,
  type ValidationResult,
  type WorkflowForm,
  type WorkflowStepForm,
} from "./dsl-editor.impl.ts";

export { DslEditor as default } from "./dsl-editor.ui.ts";
