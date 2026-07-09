# ACP 与文件导出约定

## 两类能力

### 1. ACP 节点内 `export_to_file`（BOOLEAN）

Image / Video Prompt、Image Analyze 等 Agent 可选开关，默认关。开启后写入：

```text
output/ryan_acp_exports/<node_slug>/
```

实现：`ryan_comfy_utils/acp/file_exporter.py` 中 `export_prompt_to_file`。

### 2. Ryan File Exporter（工具节点）

**不是 Agent**，分类 `Ryan Utils / File`，不走 ACP Runtime。

- 输入任意 `text`（如 Agent 的 `response_text`）
- 可配置 `output_subdir`（默认 `ryan_acp_exports/manual`）、`filename`、`extension`（txt/md/json）、`append_timestamp`、`overwrite`
- 输出：`file_path`、`file_text`

实现：`ryan_comfy_utils/nodes/file_nodes.py` + `write_text_export()`。

## Skill Resolver（ACP）

固定节点 Skill 来自 manifest，用户不可覆盖；Universal Agent 用户 `skill_id` 优先。模块：`ryan_comfy_utils/acp/skill_resolver.py`。

## 路径根目录

ComfyUI `output`（`folder_paths`），单测可用临时目录注入 `output_root`。