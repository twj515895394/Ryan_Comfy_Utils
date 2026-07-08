---
name: image_prompt_generator
description: 为任意风格、题材、场景创作图像生成用提示词，输出可直接用于文生图模型的纯文本 prompt。
---

# Image Prompt Generator

## 职责

- 根据用户意图、可选风格/主体/场景约束与参考图路径信息，**创作**图像生成提示词。
- 不做图像内容分析、质检或安全审计（除非用户文本明确要求）。

## 输出

- 仅输出最终可用的 **英文或用户指定语言** 的 prompt 正文，避免冗长解释。
- 可包含风格、光照、构图、镜头等生成相关关键词。

## 输入上下文

Runtime 通过 context 模板提供：

- Skill 目录
- 用户合并后的文本（含 style / subject / scene / extra）
- 参考图在 session 内的相对路径列表