Status: ready-for-agent

# Ryan Video Prompt Agent 固定节点

## 父问题

`.scratch/acp-runtime-foundation/PRD.md`

## 要构建什么

新增 ComfyUI 固定节点 `Ryan Video Prompt Agent`，面向「任意风格、题材、场景的视频生成提示词创作」。节点绑定 manifest 中的 `video_prompt_generator`，可基于关键帧路径（多行 `image_paths`）和/或纯文本意图生成视频 prompt。

端到端行为：与 Image Prompt 节点相同的 ACP 输出 contract；`image_paths` 为可选，允许全文本驱动。输出目标是创作 prompt，而非分镜结构化交付或内容分析。

## 验收标准

- [ ] `Ryan Video Prompt Agent` 已注册到 ComfyUI 节点映射，分类为 `Ryan Utils / ACP`
- [ ] 默认使用 `video_prompt_agent` manifest，用户无需填写 `skill_id`
- [ ] 支持无参考图的纯 `user_text` 运行；提供 `image_paths` 时注入 context
- [ ] 返回值包含 `response_text`、`session_dir`、`raw_result_json`
- [ ] 单元测试覆盖节点 contract 与（mock 下的）runtime 调用参数
- [ ] README 简要说明可与现有视频加载/抽帧节点组合使用

## 被阻塞于

- `.scratch/acp-runtime-foundation/issues/07-prompt-agent-shared-assets.md`

## 评论

### 2026-07-08

- 与 issue 08 可并行，均仅依赖 07 共享基础。
- 产品说明来源：`.scratch/acp-runtime-foundation/fixed-agent-node-selection.md` §2.2