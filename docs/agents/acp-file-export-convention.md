# ACP File Generator 与节点「导出文件」约定（草案）

## File Generator 节点做什么

Agent 在 session 内生成**可复用的文本资产**（优秀 prompt、反推结果、分镜草稿等），并**可选**落盘到 ComfyUI 的 output 目录，供人工整理或下游节点读路径。

与「仅 `response_text`」的区别：开启导出时，除字符串输出外，在磁盘上留下**带命名规则的文件**。

## 界面：开关（ComfyUI）

每个支持导出的 ACP 节点（含未来的 **Ryan File Generator Agent**，以及可选挂在 **Image Analyze / Image Prompt** 上）在 `INPUT_TYPES` 中提供 **BOOLEAN**（或等效 UI）：

| 字段建议 | 默认 | 说明 |
|----------|------|------|
| `export_to_file` | `False` | 关：只走现有三字符串输出；开：额外写文件 |
| `export_filename` | 空或 `auto` | 可选；空则由 runtime 按 session + 时间戳生成 |

**要求：** 用户无需记路径，**路径不暴露在高级配置里**（写死约定，见下）。

## 输出路径（写死）

根目录：**ComfyUI `output` 目录**（实现时通过 ComfyUI `folder_paths` 或项目已用的 `output/` 约定解析，与现有 `output/acp_workspace` 并列、不混用 session 调试目录）。

子目录命名（便于识别节点）：

```text
output/ryan_acp_exports/<node_slug>/
```

`<node_slug>` 示例：

| 节点 | node_slug |
|------|-----------|
| Ryan Image Analyze Agent | `image_analyze` |
| Ryan Image Prompt Agent | `image_prompt` |
| Ryan Video Prompt Agent | `video_prompt` |
| Ryan File Generator Agent | `file_generator` |

文件名建议：

```text
{session_id}_{yyyyMMdd_HHmmss}.md
```

或用户指定 `export_filename` 时：

```text
{export_filename}.md
```

内容格式 v1：**Markdown 单文件**（含 prompt 正文 + 可选元数据 frontmatter：节点名、category、session_id）。

## 与第二批优先级

1. **先做** issue 10：`Ryan Image Analyze Agent`（反推），输出默认中英双语 prompt；可选 `export_to_file` 可放在 10 或 10.1 小切片。  
2. **再做** issue 11：`Ryan File Generator Agent` 或共享 `acp/file_exporter.py` + 各节点 BOOLEAN（你倾向「功能要有 + 界面开关」，适合 11 统一实现 exporter，10 只接开关）。

## 风险

- ComfyUI 无头/测试环境可能没有 `folder_paths`：单元测试用 `tempfile`，生产路径解析单独一层便于 mock。