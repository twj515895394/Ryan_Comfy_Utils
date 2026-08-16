## 代理技能

### 问题追踪器

问题与 PRD 以 Markdown 存放在 `.scratch/<feature-slug>/`。参见 `docs/agents/issue-tracker.md`。

### 分类标签

分类状态使用默认五类标签（见各 issue 文件顶部 `Status:`）。参见 `docs/agents/triage-labels.md`。

### 领域文档

单一上下文：根目录 `CONTEXT.md` 与 `docs/adr/`。参见 `docs/agents/domain.md`。

### 浏览器操作边界

- 未经用户明确要求，不得连接、启动或操控浏览器；UI 验证优先使用静态检查、模块测试或 HTTP 层验证。
- 用户明确表示“不用连浏览器”后，必须停止所有浏览器工具调用；浏览器验收由用户手动完成。