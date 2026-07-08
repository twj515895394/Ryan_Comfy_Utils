# ACP Architecture Decision Record

## ADR-001 Skill 与 ComfyUI Node 解耦

状态：已确认

决定：

Skill 是独立 Agent 能力资产，不包含 ComfyUI 节点输入输出定义。

Skill 负责：

- 能力定义
- instructions
- 专业规则
- Agent 行为约束

ComfyUI Node 负责：

- 输入输出类型
- 数据转换
- Skill 调用适配

原因：

同一个 Skill 可以被多个入口复用。

---

## ADR-002 ACP 是 Runtime，不是 Skill

状态：已确认

决定：

ACP 只负责连接 Claude CLI / Codex CLI，并管理执行生命周期。

不包含业务能力。

---

## ADR-003 ComfyUI Node 固定存在，不动态生成

状态：已确认

决定：

不采用 Skill 自动生成 ComfyUI Node。

原因：

- ComfyUI workflow 需要稳定节点结构。
- 节点数量应该可控。
- Skill 数量增长不应该导致节点爆炸。

Node Manifest 用于描述绑定关系，不用于生成节点。

---

## ADR-004 Context Template 只负责上下文封装

状态：已确认

决定：

Context Template 负责：

- 输入数据组织
- 文件路径引用
- 参数注入

不负责：

- 系统 Prompt
- Agent 专业规则
- Skill 行为定义

---

## ADR-005 ACP 使用同步 Session 模式

状态：已确认

决定：

一次 ComfyUI Node 执行：

= 一次 ACP Session

= 一次 Claude/Codex CLI 调用

不使用：

- async
- callback
- websocket
- polling

---

## ADR-006 Session 默认永久保存

状态：已确认

决定：

Session 默认不自动清理。

原因：

- Agent 调试需要完整上下文。
- 需要复盘输入、日志、输出。

后续提供可选 cleanup 配置。
