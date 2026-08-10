Status: ready-for-human

## 父问题

`.scratch/minimax-h3-skill-v2/PRD.md`

## 要构建什么

为 MiniMax H3 skill 建立统一的输入模式和输出契约。将当前模式映射为 T2VA、I2VA、FL2VA、L2VA、Ref2VA，并增加视频编辑、视频续接、音频复用和音频参考关系。保留中文用户可读层，同时确定官方英文 prompt 字段作为最终结构。

## 验收标准

- [ ] 无素材、普通单图、明确首帧、明确首尾帧、明确尾帧、混合参考、原视频编辑和原视频续接分别有唯一模式判断。
- [ ] 普通单图不会默认被当作 I2VA，单张或两张图片不会在用户未指定时被当作关键帧。
- [ ] 基础模式字段顺序固定为 `integrated_multimodal_description`、`overall_soundscape`、`non_diegetic_music`，关键帧模式有明确对齐规则。
- [ ] 全参考模式字段顺序固定为 `subject_definitions`、`summary`、`retention_analysis`、`detailed_description`、`overall_soundscape`、`non_diegetic_music`。
- [ ] 中文解释层、英文 prompt 层和原文文案保留策略明确写入 skill。

## 被阻塞于

无 - 可以立即开始。
