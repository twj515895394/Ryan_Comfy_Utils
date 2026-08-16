# Findings

## 真实旧产物

`output/acp_workspace/.../production-designer/commits/latest.json` 中的 Entry content 含有 `ryan-artifact` 区块。Bundle 使用 `revision` 而非 `schema_version`；outputs 使用 `id + role + prompt` 或 `id + constraint`，没有规范的 `output_id + label + text`。Commit metadata 因 `output_id must be a non-empty path component` 被标为 invalid。

## 现有接缝

- `parse_artifact_markdown` 是 COMMIT 解析边界。
- `append_commit` 将仓库 Commit 转为 RYAN_CONTEXT Entry；这是让前端 context_json 携带规范 Bundle 的最小接缝。
- `artifact_outputs` 是 Workflow Agent 节点和 Selector 的公共读取入口。
- Selector 前端只读取 `entry.metadata.artifact_bundle`，因此 Context 追加时必须完成规范化，不能只在后端选择器内部懒解析。

## 风险

- 规范 Bundle 的非法字段不能被宽松转换，否则会把坏数据伪装成 valid。
- 旧正文中 artifact block 仍应从下游 Canonical Markdown 中移除；原始文本只在解析失败时保留。
- 工作区存在大量既有未提交改动，本次只能提交本次涉及文件和新规划/问题文件，不得覆盖或提交无关改动。
