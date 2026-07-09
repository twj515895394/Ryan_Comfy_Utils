# ACP 固定 Prompt Agent 最小契约

面向 ComfyUI 节点作者与 runtime 维护者。与选型文档 `.scratch/acp-runtime-foundation/fixed-agent-node-selection.md` §2.1 / §2.2 对齐。

## 通用输出

固定 Prompt / Analyze 节点输出一致：

| 字段 | 类型 | 说明 |
|------|------|------|
| `response_text` | STRING | 模型产出的生成用 prompt |
| `session_dir` | STRING | 本次 ACP Session 目录 |
| `raw_result_json` | STRING | CLI 原始结果 JSON 文本 |

## Ryan Image Prompt Agent

**默认 Skill：** `image_prompt_generator`  
**Manifest：** `ryan_comfy_utils/acp/fixtures/manifests/image_prompt_agent.json`

| 输入 | 必填 | 说明 |
|------|------|------|
| `user_text` | 是 | 创作意图、题材描述 |
| `image_paths` | 否 | 多行本地参考图路径 |
| `style` | 否 | 风格约束 |
| `subject` | 否 | 主体 |
| `scene` | 否 | 场景 |
| `extra_prompt` | 否 | 附加约束 |
| `export_to_file` | 否 | 默认关；开则写入 `output/ryan_acp_exports/image_prompt/` |
| `export_filename` | 否 | 可选 |
| `profile_path` / `workspace_root` / `session_id` / `skill_root` | 运行参数 | `skill_root` 空则使用包内 fixtures skills |

v1 参考图：**ComfyUI `IMAGE` 槽位 `image_01`…`image_10`（默认 1 个，界面「+」最多 10）**，并可选多行 `image_paths`。详见 `docs/agents/comfy-multi-image-inputs.md`。

## Ryan Video Prompt Agent

**默认 Skill：** `video_prompt_generator`  
**Manifest：** `ryan_comfy_utils/acp/fixtures/manifests/video_prompt_agent.json`

| 输入 | 必填 | 说明 |
|------|------|------|
| `user_text` | 是 | 镜头/视频意图；可无参考图纯文本 |
| `image_paths` | 否 | 多行关键帧路径 |
| `task` | 否 | 任务说明（如时长、运镜偏好） |
| `extra_prompt` | 否 | 附加约束 |
| `export_to_file` | 否 | 默认关；开则写入 `output/ryan_acp_exports/video_prompt/` |
| `export_filename` | 否 | 可选 |
| 运行参数 | 同上 | 可与 Batch Video Loader / Frame Sampler 路径输出串联 |

## Ryan Image Analyze Agent（反推提示词）

**默认 Skill：** `image_prompt_reverse`  
**Manifest：** `ryan_comfy_utils/acp/fixtures/manifests/image_analyze_agent.json`

与 **Image Prompt** 分工：Analyze 从**已有参考图反推**绘图 prompt；Prompt 从**意图/字段创作** prompt。

| 输入 | 必填 | 说明 |
|------|------|------|
| 参考图 | **是** | 至少连接一路 `image_01`…`image_N` **或** 提供多行 `image_paths`（二者满足其一） |
| `user_text` | 否 | 补充要求 |
| `category` | 否 | `general` / `typography_logo` / `landscape` / `photography` / `illustration` / `render_3d` / `ip_character` |
| `output_language` | 否 | `bilingual`（默认）/ `zh` / `en` |
| `export_to_file` | 否 | 默认关；开则写入 `output/ryan_acp_exports/image_analyze/` |
| `export_filename` | 否 | 可选自定义文件名（不含路径） |

## 非目标

- 质检、分镜结构化交付
- 除 `export_to_file` 约定外的任意自定义落盘路径

## Runtime 失败语义

- CLI `returncode != 0`、超时、非法 `result.json`、`status` 为 `error`/`failed` 时抛出异常并中断 workflow。
- Profile `command` 支持占位符与 env 注入，见 `docs/agents/acp-runtime-cli-profile.md`。
