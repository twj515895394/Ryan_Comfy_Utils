# ACP 固定 Prompt Agent 最小契约

面向 ComfyUI 节点作者与 runtime 维护者。与选型文档 `.scratch/acp-runtime-foundation/fixed-agent-node-selection.md` §2.1 / §2.2 对齐。

## 通用输出

两个固定节点输出一致：

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
| `profile_path` / `workspace_root` / `session_id` / `skill_root` | 运行参数 | `skill_root` 空则使用包内 fixtures skills |

v1 参考图仅支持路径字符串，不支持 ComfyUI `IMAGE` tensor 直连。

## Ryan Video Prompt Agent

**默认 Skill：** `video_prompt_generator`  
**Manifest：** `ryan_comfy_utils/acp/fixtures/manifests/video_prompt_agent.json`

| 输入 | 必填 | 说明 |
|------|------|------|
| `user_text` | 是 | 镜头/视频意图；可无参考图纯文本 |
| `image_paths` | 否 | 多行关键帧路径 |
| `task` | 否 | 任务说明（如时长、运镜偏好） |
| `extra_prompt` | 否 | 附加约束 |
| 运行参数 | 同上 | 可与 Batch Video Loader / Frame Sampler 路径输出串联 |

## 非目标

- 图像/视频分析、质检、分镜结构化交付
- 生成文件资产回传（仍属 Universal Agent / 后续扩展）