Status: ready-for-agent

# Ryan Image Prompt Agent 固定节点

## 父问题

`.scratch/acp-runtime-foundation/PRD.md`

## 要构建什么

新增 ComfyUI 固定节点 `Ryan Image Prompt Agent`，面向「任意风格、题材、场景的图像生成提示词创作」。节点绑定 manifest 中的 `image_prompt_generator`，接收用户意图文本与可选参考图路径，经 ACP runtime 返回生成用 prompt 文本。

端到端行为：用户在 ComfyUI 填写 `user_text` 与可选 `style` / `subject` / `scene` / `extra_prompt` / `image_paths` → 一次 ACP Session → 输出 `response_text`、`session_dir`、`raw_result_json`。不将能力定位为图像分析或质检。

## 验收标准

- [ ] `Ryan Image Prompt Agent` 已注册到 ComfyUI 节点映射，分类为 `Ryan Utils / ACP`
- [ ] 默认使用 `image_prompt_agent` manifest，用户无需填写 `skill_id`
- [ ] 支持纯文本输入；提供 `image_paths` 时，runtime 将图片落盘并写入 context
- [ ] 返回值包含 `response_text`、`session_dir`、`raw_result_json`
- [ ] 单元测试覆盖节点 contract 与（mock 下的）runtime 调用参数
- [ ] README 包含该节点的用途、主要输入与输出说明

## 被阻塞于

- `.scratch/acp-runtime-foundation/issues/07-prompt-agent-shared-assets.md`

## 评论

### 2026-07-08

- 产品优先级与最小 contract 来源：`.scratch/acp-runtime-foundation/fixed-agent-node-selection.md` §2.1