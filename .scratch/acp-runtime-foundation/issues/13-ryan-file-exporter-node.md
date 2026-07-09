Status: ready-for-agent

# Ryan File Exporter 工具节点

## 父问题

`.scratch/acp-runtime-foundation/PRD.md`

## 要构建什么

新增 ComfyUI **工具节点** `Ryan File Exporter`（**不是** Agent，不走 ACP Runtime / CLI / Skill Resolver）。接收工作流中的文本（如 Agent 的 `response_text`），写入 ComfyUI `output` 下可配置子目录，并**输出文件路径**供下游使用。

与现有各 Agent 上 `export_to_file` 开关的关系：开关仍为「节点内一键落盘」；File Exporter 为**通用串联节点**，可接任意 STRING 文本。

建议输入：`text`（必填）、`output_subdir`（默认 `ryan_acp_exports/manual`）、`filename`（可空）、扩展名选项（txt / md / json）、`append_timestamp`、`overwrite`。  
建议输出：`file_path`、`file_text`（回传原文便于校对）。

分类：**`Ryan Utils / File`**（不要放在 ACP 分类）。

设计依据：`.handoff/handoff-20260709-104808-acp-resolver-file-output.md` §2。

## 验收标准

- [ ] 节点已注册，分类 `Ryan Utils / File`
- [ ] 写入路径基于 ComfyUI output 根 + `output_subdir`，单测用临时目录 mock
- [ ] 支持 txt / md / json 至少三种扩展；timestamp 与 overwrite 行为有测试
- [ ] 复用或扩展 `ryan_comfy_utils/acp/file_exporter.py`，避免重复路径规则
- [ ] README 含简短用法（接在 Prompt/Analyze 输出之后）

## 被阻塞于

无 - 可与 issue 12 并行

## 评论

### 2026-07-09

- 替代 issue 11 中「Ryan File Generator **Agent**」命名；issue 11 的 export 开关部分视为已完成