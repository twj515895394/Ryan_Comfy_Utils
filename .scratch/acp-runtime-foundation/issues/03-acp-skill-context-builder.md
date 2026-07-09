Status: ready-for-agent

# Skill 解析与 Context Builder 打通

## 父问题

`.scratch/acp-runtime-foundation/PRD.md`

## 要构建什么

构建 ACP 的 skill 解析、context payload 组装和 context template 渲染能力，让 runtime 在执行 CLI 前拿到稳定的上下文输入。

这个切片需要打通一条完整但窄的链路：

- 给定 `skill_id` 能定位 skill 目录
- 给定用户文本能构建结构化 `ACP Context`
- 给定模板能渲染出最终要交给 CLI 的上下文文本

第一阶段只要求文本输入可用，不在这一片内扩展图片/文件复杂逻辑。

## 验收标准

- [ ] 可以根据 `skill_id` 定位 skill 目录，找不到时返回明确错误
- [ ] `ACP Context` 至少包含 `skill`、`input`、`workspace` 三段
- [ ] 文本输入可以被写入 `input.text`
- [ ] context template 可以替换 `skill_directory` 和 `input.text` 等已定义占位符
- [ ] 单元测试验证 payload 结构和模板渲染结果

## 被阻塞于

- `.scratch/acp-runtime-foundation/issues/01-acp-protocol-assets.md`
- `.scratch/acp-runtime-foundation/issues/02-acp-session-cli-smoke.md`
