/**
 * UI Schema 渲染器入口（TSX）— 白名单组件映射，渲染插件 UI。
 *
 * 支持 form / list / chat / chart 4 类组件；
 * 未注册组件类型显示友好提示，不抛异常。
 *
 * 实现在 `schema-renderer.impl.ts`（React.createElement，无 JSX，便于单测）。
 */

export {
  FormView,
  ListView,
  ChatView,
  ChartView,
  UnknownTypeNotice,
  SchemaRenderer,
  UI_COMPONENTS,
  type FormField,
  type SchemaRendererProps,
} from "./schema-renderer.impl";

export {
  UI_WHITELIST,
  UI_TYPES,
  resolveUiSchema,
  unknownTypeMessage,
  isUiComponentType,
  type UiSchema,
  type UiComponentType,
} from "./ui-registry";

export { SchemaRenderer as default } from "./schema-renderer.impl";
