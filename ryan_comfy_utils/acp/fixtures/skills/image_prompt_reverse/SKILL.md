---
name: image_prompt_reverse
description: 从参考图反推可用于 AI 绘图的提示词，支持通用与分类型反推模板。
---

# Image Prompt Reverse（反推提示词）

## 职责

根据 session 内参考图路径与用户指定的 **category**，按对应维度拆解画面并输出**可直接用于 AI 绘图**的 prompt（非质检报告）。

## category 与反推侧重

- **general**：主体、风格、色彩、光影、构图、质感、分辨率、细节（通用 8 维）
- **typography_logo**：字体风格、笔画、配色、排版、特效
- **landscape**：环境、天气、时段、氛围、镜头感、景深
- **photography**：光线、景深、焦段、色调、画质、情绪氛围
- **illustration**：画风、笔触、肌理、线条、技法
- **render_3d**：渲染风格、材质、灯光、PBR、渲染器特征
- **ip_character**：头身比、服饰、材质工艺、标志性特征

## output_language

- **bilingual**：中英双语，便于复制到国内外模型
- **zh** / **en**：单语输出

## 输出

仅输出 prompt 正文（或按语言要求的中英结构），避免冗长分析过程。