Status: ready-for-agent

## 父问题

`.scratch/minimax-h3-skill-v2/PRD.md`

## 要构建什么

建立用户素材标签与 H3 官方引用标签之间的稳定映射。让人物、产品、场景、动作、运镜、关键帧和音频可以分别锁定、迁移或弱参考，并处理一份素材多角色和编号冲突。

## 验收标准

- [ ] 用户层继续支持 `@图片N`、`@视频N`、`@音频N`，并定义到 `<Subject N>`、`<Picture N>`、`<Video N>`、`<Audio N>` 的映射。
- [ ] 规则明确区分来源文件、可复用内容对象和目标视频中的引用角色。
- [ ] 视觉关系支持 `fully_preserved`、`partially_preserved`、`attribute_transfer`、`weak_reference`。
- [ ] 音频关系支持 `fully_copy`、`partially_copy`、`reference`、`weak_reference`。
- [ ] 同一素材承担多个角色时逐项说明锁定、仅参考和禁止参考的维度。
- [ ] 编号冲突遵循用户明确映射优先，不静默重排。

## 被阻塞于

- `01-mode-contract.md`
