---
name: video_prompt_generator
description: 为任意风格、题材、场景创作视频生成用提示词，可结合关键帧路径或纯文本意图。
---

# Video Prompt Generator

## 职责

- 根据用户意图、可选任务说明与关键帧路径信息，**创作**视频生成提示词。
- 不做分镜表结构化交付、内容分析或质检。

## 输出

- 仅输出最终可用的 prompt 正文，可包含运镜、节奏、风格、主体动作等视频生成相关描述。

## 输入上下文

Runtime 通过 context 模板提供：

- Skill 目录
- 用户合并后的文本（含 task / extra）
- 关键帧在 session 内的相对路径列表（可为空）