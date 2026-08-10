Status: ready-for-agent

## 父问题

`.scratch/minimax-h3-skill-v2/PRD.md`

## 要构建什么

将基础生成模式整理为 T2VA、I2VA、FL2VA 和 L2VA 模板，并保持当前中文用户可读的输出层。模板必须输出官方 H3 字段、关键帧对齐说明和可执行的连续动作路径。

## 验收标准

- [ ] T2VA 从文本构造完整视听时间线，不生成虚构参考标签。
- [ ] I2VA 将明确首帧对齐到 `0.00` 秒，并从首帧状态连续向后发展。
- [ ] FL2VA 描述从首帧到尾帧的连续变化，尾帧落在视频末端，默认不添加硬切。
- [ ] L2VA 从合理前置状态逐步收敛到明确尾帧，不把尾帧误放到开场。
- [ ] 基础模板严格使用 `integrated_multimodal_description`、`overall_soundscape`、`non_diegetic_music`。
- [ ] 第一镜、后续切镜、时间戳和一镜到底规则有可直接套用的示例。

## 被阻塞于

- `01-mode-contract.md`
- `02-reference-model.md`
