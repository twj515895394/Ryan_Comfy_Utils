Status: ready-for-agent

# Prompt Agent 共享资产与固定节点基础

## 父问题

`.scratch/acp-runtime-foundation/PRD.md`

## 要构建什么

为首批固定 Prompt Agent 建立可复用的端到端基础，使后续两个 ComfyUI 节点只需声明各自输入字段并绑定 manifest，而不重复实现 runtime 调用与 skill 解析逻辑。

本切片贯穿：契约说明文档、仓库内最小 Skill 目录、两份固定 manifest、节点层公共运行入口，以及验证 manifest/skill 可被加载的测试。完成后，`image_prompt_generator` 与 `video_prompt_generator` 在默认配置下无需用户自备外部 skill 目录即可被单元测试解析。

实现决策已闭合（见 `docs/superpowers/plans/2026-07-08-acp-fixed-prompt-agents.md`）：两路独立 Skill；参考图 v1 用多行路径字符串；可选风格/题材/场景字段在节点层并入上下文。

## 验收标准

- [ ] 存在面向节点作者的固定 Prompt Agent 最小 I/O 说明文档
- [ ] 仓库内存在 `image_prompt_generator` 与 `video_prompt_generator` 的最小 Skill 资产（至少 `SKILL.md`）
- [ ] 存在 `image_prompt_agent` 与 `video_prompt_agent` 两份 manifest fixture，`mode` 为 fixed 且 `skill_id` 已绑定
- [ ] 节点模块提供固定 Agent 共用运行路径，支持从多行路径解析图片/文件并调用现有 `execute_text_session`
- [ ] 当用户未配置 `skill_root` 时，可回退到包内 fixtures skills 目录（行为有测试覆盖）
- [ ] 单元测试验证 manifest 字段与 skill 目录可解析

## 被阻塞于

- `.scratch/acp-runtime-foundation/issues/05-asset-input-and-result-mapping.md`
- `.scratch/acp-runtime-foundation/issues/06-fixed-agent-node-selection.md`

## 评论

### 2026-07-08 计划落库

- 实施计划：`docs/superpowers/plans/2026-07-08-acp-fixed-prompt-agents.md`
- 下游实现 issue：`08-image-prompt-agent.md`、`09-video-prompt-agent.md`