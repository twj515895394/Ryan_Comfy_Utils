Status: ready-for-agent

# 让 Selector 展示真实提示词产物

## 父问题

`.scratch/commit-artifact-selector-compat/PRD.md`

## 要构建什么

把规范化后的历史产物和新 Commit 产物接入 Selector 的语义筛选链路。普通用户只看到提示词类型和需要时的镜头选择；Selector 输出单一 STRING，供显示文本、图像节点、视频节点或其他下游节点继续使用。

## 验收标准

- [ ] Selector 能从有效产物动态提供图像提示词、分镜提示词和视频提示词。
- [ ] Selector 选择“指定镜头提示词”时，能动态列出镜头并输出所选镜头的 `prompt`。
- [ ] Selector 选择不存在的类型或镜头时返回空字符串，并显示可理解的状态，不回退到错误类型的正文。
- [ ] 没有结构化产物时，“自动读取最新内容”仍输出最新正文，并明确提示没有可精确选择的结构化产物。
- [ ] invalid 和 absent 状态分别显示重新 Commit 或只能读取正文等下一步提示。
- [ ] 用户无需填写 UID、Bundle、内部 ID、kind 或 revision；历史 Workflow 的旧字段仍可由后端兼容读取。
- [ ] 覆盖 Agent → Selector → STRING 的回归测试，并验证旧 Selector 节点迁移或重新添加后的行为。

## 被阻塞于

- Issue 01：`.scratch/commit-artifact-selector-compat/issues/01-legacy-artifact-normalization.md`
