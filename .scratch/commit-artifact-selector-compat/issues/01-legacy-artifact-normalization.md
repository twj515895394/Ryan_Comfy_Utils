Status: ready-for-agent

# 兼容旧版 Commit 产物并生成可选输出

## 父问题

`.scratch/commit-artifact-selector-compat/PRD.md`

## 要构建什么

让已有 Commit 正文中的旧结构化字段可以被规范化为 Artifact Selector 可消费的结构化产物，而不要求用户重新搭建 Workflow。兼容旧格式中的 `id`、`prompt`、`constraint`，转换为稳定的输出标识、可读标签和文本内容，并保留原有规范格式的行为。

规范化后的输出必须满足：

- 普通输出使用 `output_id`、`kind`、`label`、`text`、`priority`。
- 镜头输出使用 `shot_id`、`kind`、`label`、`prompt`、`priority`。
- 连续性约束也作为可复用文本输出，不得因为使用 `constraint` 字段导致整个 Bundle 失效。
- 无法安全转换的字段必须保留正文并给出明确 invalid 原因，不能静默伪造内容。

## 验收标准

- [ ] 旧格式 `id + prompt` 能转换为有效的结构化输出，`id` 映射为 `output_id`，`prompt` 映射为 `text`。
- [ ] 旧格式 `id + constraint` 能转换为有效的连续性约束输出，文本内容不丢失。
- [ ] 已有规范格式不发生回归，重复 ID、空 ID、空文本仍被明确拒绝。
- [ ] 当前工作区中已保存的旧 Production Design Commit 可解析为 `valid`，并能被 Selector 的自动模式和图像提示词模式读取。
- [ ] Parser、Commit 服务或等价的真实接缝有回归测试覆盖；测试验证字段映射和最终 Selector 输出，而非只验证没有抛异常。

## 被阻塞于

无 - 可以立即开始
