/** 示例 notes 插件（与 plugins/example/plugin.yaml 对齐）。 */

export const sampleNotesPlugin = {
  name: "notes",
  version: "1.0.0",
  description: "笔记插件 — 最小可跑示例",
  ui: {
    type: "list",
    props: {
      title: "笔记列表",
      source: "notes.list",
    },
  },
  tools: ["notes.list", "notes.create", "notes.daily_report"],
};

export const sampleNotesData = {
  items: [
    { id: "n1", title: "早会", content: "同步 Loom 进度" },
    { id: "n2", title: "想法", content: "把设备、Agent、任务编织成一体" },
    { id: "n3", title: "待办", content: "补前端 Shell 入口" },
  ],
};

export const sampleWorkflowYaml = `name: daily_report
trigger:
  type: cron
  cron: "0 9 * * *"
device: pc
steps:
  - id: fetch
    tool: notes.list
  - id: summarize
    agent: builtin_rag
    prompt: "总结今日笔记"
`;
