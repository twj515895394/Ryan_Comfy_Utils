Status: ready-for-agent

# Pi Runner 兼容迁移

## 父问题

`.scratch/workflow-agent-pi-v1/PRD.md`

## 要构建什么

将现有 ACP Agent 的默认外部 Runner 从 Claude CLI 切换为 Pi，同时保持现有 ComfyUI 节点输入、输出和结果映射契约不变。

现有 ACP 节点使用 Pi `--mode text`。Pi Profile 必须支持：

- `--no-context-files`；
- 显式 Skill 加载；
- Ryan System Prompt；
- 当前 Agent Session 工作目录；
- 完整工具权限；
- Pi CLI 能力探测。

`local_claude_cli.json` 保留为显式回滚配置，但 Pi 失败时不得自动回退 Claude。

## 验收标准

- [ ] 现有 ACP Agent 默认使用项目 Pi Profile。
- [ ] 现有节点继续返回 `response_text`、`session_dir`、`raw_result_json`，不改变 ComfyUI 节点契约。
- [ ] Pi 纯文本 stdout 和 `result.json` 均可归一化到现有 ACP 结果结构。
- [ ] Pi 命令不会自动加载 `AGENTS.md` / `CLAUDE.md`，并显式加载当前 Skill 和 Ryan System Prompt。
- [ ] Pi 工作目录是当前 Agent Session 目录，不跨 Workflow 访问其他 Session。
- [ ] Pi CLI 缺失、认证失败、缺少必要参数或超时会返回明确错误。
- [ ] Pi 失败不会自动切换 Claude；用户显式指定 Claude Profile 时仍可回滚。
- [ ] 测试覆盖非零退出码、超时、纯文本输出、结构化结果、Skill 注入和能力探测。

## 被阻塞于

无 - 可以立即开始
