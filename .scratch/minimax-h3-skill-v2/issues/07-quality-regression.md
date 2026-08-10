Status: ready-for-agent

## 父问题

`.scratch/minimax-h3-skill-v2/PRD.md`

## 要构建什么

更新 H3 skill 质量检查和代表性回归场景，使模式、引用、时间、对白、音频、风格路由和超限处理都能被一致检查，并防止规则、模板和验收清单发生漂移。

## 验收标准

- [ ] 质量清单覆盖 T2VA、I2VA、FL2VA、L2VA、Ref2VA、视频编辑和视频续接。
- [ ] 质量清单覆盖完整音频复用、部分音频复用、音频参考和无音乐场景。
- [ ] 质量清单覆盖八种官方风格路由，以及普通请求不误触发风格的场景。
- [ ] 至少包含 10 个正常、边界或冲突回归场景。
- [ ] 回归场景检查官方字段顺序、标签闭环、关键帧时间、speaker ID、跨镜对白、Shot 起止状态和文字原文。
- [ ] 超限素材不会被静默丢弃，超长 prompt 只压缩低价值修饰。
- [ ] 最终一致性审查确认主 skill、规则、模板和质量清单没有互相矛盾的旧术语。

## 被阻塞于

- `01-mode-contract.md`
- `02-reference-model.md`
- `03-base-templates.md`
- `04-reference-audio.md`
- `05-timing-dialogue.md`
- `06-style-routing.md`
