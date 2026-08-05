# MiniMax H3 视频提示词生成节点 (PRD)

## 概述

MiniMax H3 是 MiniMax 推出的原生音视频一体大模型（支持文字、多图像、多视频、多音频联合输入，原生同步生成 2K 24fps 视频与立体声双声道音效/配音）。
为了在 ComfyUI 工作流中高效配合 H3 的生成节点（如 `MiniMaxH3ImageToVideo` 与 `MiniMaxH3ReferenceToVideo`），需要打造专用的 Prompt ACP Agent 节点 `Ryan MiniMax H3 Video Prompt Agent`，绑定 `minimax-h3-video-prompt` 技能，实现多模态素材编排与 H3 结构化提示词的生成。

## 目标与功能点

1. **全新 ACP Agent 节点与 Manifest**：
   - 节点标识：`Ryan ACP MiniMax H3 Video Prompt Agent`
   - Manifest 文件：`minimax_h3_video_prompt_agent.json` 绑定 `minimax-h3-video-prompt` Skill。
   - 自动引导 LLM 在推理前学习 H3 结构规范、画面描述与音效文字编排规则。

2. **三类素材多模态 ComfyUI 插槽**：
   - **图片插槽**：`image_01` .. `image_09`（标准 `IMAGE` 类型，最多 9 张）。
   - **视频插槽**：`video_01` .. `video_03`（万能通配 `*` 类型，兼容 `LoadVideo` 的 `IMAGE` 帧批次、`VIDEO` 对象或 `STRING` 路径，最多 3 段）。
   - **音频插槽**：`audio_01` .. `audio_03`（万能通配 `*` 类型，兼容 `LoadAudio` 的 `AUDIO` 字典或 `STRING` 路径，最多 3 段）。

3. **动态数量调节与 Update 面板**：
   - `image_slot_count` (1~9)、`video_slot_count` (0~3)、`audio_slot_count` (0~3) 控制框。
   - 独立前端扩展 `ryan_minimax_h3_prompt.js` + `Update` 按钮，根据数值实时增减各类型槽位。

4. **模式联动与智能预设**：
   - `generation_mode`: 支持 `纯文生`（默认）、`普通图生`、`首尾帧`、`全能参考`、`视频编辑`。
   - 前端自动按选定模式显隐对应属性与拉伸槽位数。

5. **主视频指定起始帧抽帧分析**：
   - `video_start_frame`（起始帧索引）与 `video_frame_count`（截取帧数）只针对主视频源 `video_01` 生效。
   - 准确截取区间关键帧图像并自动提交给 VLM 视觉模型识别。

## 关联 Issue

- `.scratch/minimax-h3-video-prompt/issues/01-minimax-h3-video-prompt-agent.md`
