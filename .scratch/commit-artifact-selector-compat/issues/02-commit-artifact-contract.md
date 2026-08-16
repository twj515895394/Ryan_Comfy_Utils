Status: ready-for-agent

# 修正 Commit 结构化产物生成合同

## 父问题

`.scratch/commit-artifact-selector-compat/PRD.md`

## 要构建什么

让新的 Commit Prompt 和解析流程直接生成 Artifact Selector 可消费的规范 Bundle，避免 Agent 继续输出 `id`、`prompt`、`constraint` 等不兼容字段。Commit 仍可保留没有结构化产物的正文，但必须明确区分 valid、absent 和 invalid 状态。

## 验收标准

- [ ] Commit 指令明确要求输出字段：`output_id`、`kind`、`label`、`text`、`priority`。
- [ ] 镜头字段明确要求：`shot_id`、`kind`、`label`、`prompt`、`priority`。
- [ ] Prompt 明确禁止使用 `id` 替代 `output_id`，禁止使用 `constraint` 替代 `text`，并禁止使用 `prompt` 作为普通 output 的替代字段。
- [ ] 使用现有 Starter Skill 的 Commit 流程生成规范结构化产物后，Entry 的 `artifact_status` 为 `valid`，Selector 可读取至少一个对应类型的文本。
- [ ] 没有结构化产物时，Entry 正文仍然保存；状态为 `absent` 而不是伪造 Bundle；错误信息可被用户理解。
- [ ] Commit Prompt、解析和 HTTP/服务返回路径有回归测试覆盖，既验证成功字段也验证非法字段的错误边界。

## 被阻塞于

- Issue 01：`.scratch/commit-artifact-selector-compat/issues/01-legacy-artifact-normalization.md`
