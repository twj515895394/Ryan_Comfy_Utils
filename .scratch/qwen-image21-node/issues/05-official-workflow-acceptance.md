Status: ready-for-agent
Type: HITL

# 05 官方工作流替换与回归验收

## 父问题

- `.scratch/qwen-image21-node/PRD.md`

## 要构建什么

对完整节点进行官方 Qwen Image 2.1 工作流验收，确认 Ryan 节点可以替换官方文本编码、分辨率选择和空 latent 三个节点，同时不接管模型、采样器和采样参数。

验收覆盖纯文生图、多图参考、`@` 引用、画廊排序、外部 `IMAGE`、VAE reference latent、透明图片、batch size 和自定义尺寸。必要的自动化回归测试应在本票中补齐；最终 ComfyUI 节点界面和实际采样链路需要人工确认。

## 验收标准

- [ ] 使用 Ryan 节点后，可以移除官方文本编码节点、分辨率节点和空 latent 节点。
- [ ] 官方工作流的 CLIP、模型、采样器、VAE Decode 和保存节点仍由用户控制。
- [ ] 16:9、2.0 Megapixels、batch size 4 能生成正确尺寸和 batch 的 Qwen latent。
- [ ] 没有参考图时纯文生图可以完成完整采样链路。
- [ ] 两张内部参考图可以完成多图生成，图片顺序和节点槽位一致。
- [ ] Prompt 中的 `@图片1` 和 `@图片2` 能在实际生成链路中保持正确图片指代。
- [ ] 重新排序图片后，`@` 引用仍指向原图片。
- [ ] 外部 `IMAGE` 输入能替代一个画廊槽位，且优先级符合设计。
- [ ] 连接 VAE 后 reference latent 路径可以完成实际采样。
- [ ] 透明 PNG 参考图不会导致视觉编码或 VAE 路径异常。
- [ ] 自定义宽高、不同比例和 batch size 在实际采样中均可用。
- [ ] 失效图片和失效 mention 会在执行前给出明确错误。
- [x] 自动化测试通过，现有 Ryan 节点回归测试没有新增本功能相关失败；全量测试剩余的 2 项失败属于既有 skill contract 修改。
- [ ] 人工验收确认节点 UI 在 ComfyUI 中可操作、状态可保存、工作流可重新加载。

## 当前自动化验收证据

- [x] Qwen 后端专项测试：`18 passed`。
- [x] 前端契约测试：`4 passed`；前端脚本 `node --check` 通过。
- [x] 官方工作流静态连接检查：Ryan 节点提供 `CONDITIONING`、`CONDITIONING`、`LATENT`，模型、采样器、VAE Decode 和保存节点保持外部连接。
- [x] 全量回归：`398 passed, 2 failed`；两项失败均在已有的 `tests/workflow_agent/test_skill_contracts.py`，属于用户当前已有的 skill contract 修改，不是本功能新增失败。
- [ ] ComfyUI UI、状态持久化和真实采样链路人工验收待执行。

## 被阻塞于

- `.scratch/qwen-image21-node/issues/01-core-node-and-latent.md`
- `.scratch/qwen-image21-node/issues/02-multi-image-gallery.md`
- `.scratch/qwen-image21-node/issues/03-image-mentions.md`
- `.scratch/qwen-image21-node/issues/04-vae-reference-latents.md`
