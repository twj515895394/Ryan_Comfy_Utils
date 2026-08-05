Status: ready-for-agent

# ComfyUI 视频生成节点开发（RyanVideoGenerator）

## 问题陈述
为了在 ComfyUI 中支持视频生成和参考图生视频工作流，用户需要：
1. 新增一个视频生成节点 `RyanVideoGenerator`，使用 `grok-imagine-video` 模型。
2. 该节点需要支持多图参考输入（最多 5 张参考图），前端 UI 与 `RyanImageGenerator` 一致。当输入为 1 张图片时，自动采用 image-to-video 模式；当输入 >1 张时，自动采用 reference-to-video 模式。
3. 视频生成接口是异步执行的，节点提交任务后需要周期性轮询其状态，直到视频生成完毕。
4. 生成的视频需要下载并解码为 ComfyUI `IMAGE` 帧张量批次，供工作流后续节点处理，同时输出保存的 `.mp4` 视频文件路径 `STRING`。

---

## 解决方案
1. **接口请求与异步轮询**：
   - 使用 `POST {base_url}/videos/generations` 接口提交生视频任务，获取 `request_id`。
   - 使用 `GET {base_url}/videos/{request_id}` 接口进行轮询（每隔 5 秒），直到 `status` 为 `"done"` 或 `"failed"`/`"expired"`。
   - 生视频成功后，从返回的 `video.url` 链接下载 `.mp4` 视频文件，并保存至 ComfyUI 的临时或输出目录下。
2. **多参考图智能模式路由**：
   - 1 张图输入：在 payload 中构造 `"image": {"url": "data:image/..."}`。
   - >1 张图输入：在 payload 中构造 `"reference_image_urls": [{"url": "data:image/..."}, ...]`。
3. **视频解码与双重输出**：
   - 调用项目底层的 `load_video_frames` 对下载好的视频文件进行解码，还原成 PyTorch `IMAGE` 批次张量（范围 `0.0..1.0`，shape `[N, H, W, C]`）。
   - 节点同时输出 `IMAGE` 帧序列与视频文件路径 `STRING`。

---

## 用户故事
1. 作为 ComfyUI 工作流设计者，我想要使用文本提示词或者拖入单张/多张参考图生成视频，以便创建动态视觉效果。
2. 作为用户，我希望生视频节点能够直接输出解码后的图片张量批次，以便我不需要使用额外的视频加载器节点手动加载它。
3. 作为用户，我希望视频生成节点具有自适应过滤，下拉框中只显示支持的 image/video 类型配置，减少错误发生的概率。

---

## 实现决策
- **涉及接口与端点**：
  - `POST /v1/videos/generations` (接受 `model`、`prompt`、`image`、`reference_image_urls`、`aspect_ratio`、`resolution`、`duration` 等参数)。
  - `GET /v1/videos/{request_id}` (返回 `status`、`progress` 以及结果 `video: {url: "..."}`)。
- **本地存储决策**：
  - 将下载好的视频文件重命名为 `ryan_grok_video_{uuid}.mp4`，并保存到 ComfyUI 的 `output` 目录，使其能被系统统一管理。
- **界面参数设计**：
  - `profile` (过滤展示 `"image"` 类型的配置 profile)
  - `model_override`
  - `prompt`
  - `aspect_ratio` (`16:9`, `9:16`, `1:1`, `4:3`, `3:4`, `3:2`, `2:3`)
  - `resolution` (`480p`, `720p`)
  - `duration` (1-15秒，默认5)
  - `polling_interval` (默认5秒)
  - `extra_body_json`
  - 可选的多输入插槽（由前端 `ryan_multi_image_slots.js` 统一接管控制，最高 5 张参考图）。

---

## 测试决策
- 在 `tests/nodes/test_video_generator_node.py` 编写测试用例，模拟完整的异步 API 调用：
  - Mock 生视频请求响应返回 `request_id`。
  - Mock 状态轮询响应：首次返回 `status: pending`，第二次返回 `status: done` 与视频 url。
  - Mock 视频文件下载和本地 `load_video_frames` 解码动作，确保能顺利输出期望大小的虚拟张量批次。

---

## 超出范围
- 音频驱动生成视频（`grok-imagine-video` 目前只专注于画面的多图参考与生成）。
- 视频到视频（vid2vid）的重绘和插帧，本节点主要提供 text-to-video / image-to-video 功能。
