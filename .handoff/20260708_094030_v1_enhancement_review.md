# Ryan Comfy Utils v1 增强后 Review

生成时间：2026-07-08 09:40:30 Asia/Tokyo

## 1. 本轮增强范围

本轮基于第一版已完成节点，补齐优先级最高的一批可用性增强。

已完成：

1. `Ryan LLM Chat` / `Ryan LLM Vision Chat` 的 `request_json` 调试输出中，自动截断 base64 图片内容。
2. `Ryan Batch Video Loader` 增加 `video_info_json` 输出。
3. `Ryan Batch Video Loader` 增加自然排序：`natural_asc` / `natural_desc`。
4. `Ryan Video Frame Sampler` 增加 `custom_indexes` 采样模式。
5. `Ryan Video Frame Sampler` 保存图片自动加入时间戳，避免覆盖。
6. `Ryan Video Frame Sampler` 增加 `saved_paths_text` 输出。
7. README 已同步更新。

## 2. 代码变更摘要

### 2.1 `ryan_comfy_utils/core/llm_client.py`

新增：

- `_truncate_data_url`
- `_sanitize_for_debug`

效果：

- 真实请求仍发送完整 base64 图片。
- 仅 `request_json` 调试输出会截断 `data:image/...;base64,...`。
- 避免 Vision 多图请求导致 ComfyUI 输出和 workflow JSON 过大。

### 2.2 `ryan_comfy_utils/core/video_utils.py`

新增：

- `natural_sort_key`
- `get_video_info`
- `video_info_to_json`
- `parse_custom_indexes`

增强：

- `sort_video_files` 支持自然排序。
- `sample_image_batch` 支持 `custom_indexes`。
- `save_image_batch` 改为返回保存路径列表，并在文件名中加入时间戳。

### 2.3 `ryan_comfy_utils/nodes/video_nodes.py`

增强：

- `Ryan Batch Video Loader` 输出增加 `video_info_json`。
- `Ryan Batch Video Loader` 的 `sort_mode` 增加：
  - `natural_asc`
  - `natural_desc`
- `Ryan Video Frame Sampler` 的 `sample_mode` 增加：
  - `custom_indexes`
- `Ryan Video Frame Sampler` 增加输入：
  - `custom_indexes`
- `Ryan Video Frame Sampler` 输出增加：
  - `saved_paths_text`

## 3. Review 结果

### 3.1 设计一致性 Review

结论：通过。

原因：

- 仍保持第一版的 5 个节点范围，没有提前引入 ACP / Skill。
- 仍保持 OpenAI-Compatible 方向。
- LLM 仍为 blocking 请求，不做流式输出。
- LLM 失败仍直接抛异常。
- Vision 图片真实请求未被截断，只是 debug 输出被截断，符合调试需求。
- Video Loader 仍参考 VideoHelperSuite 的基础参数，但没有引入强依赖。
- Frame Sampler 仍以 `images` 输入为主，符合当前链路。

### 3.2 ComfyUI 节点接口 Review

结论：基本通过，但需要本地运行验证。

检查点：

- `Ryan Batch Video Loader` 输出数量从 7 个增加为 8 个。
- `Ryan Video Frame Sampler` 输出数量从 3 个增加为 4 个。
- 这对新 workflow 没问题，但如果已有旧 workflow，连线可能需要重新调整。
- 当前项目还没有发布稳定版，因此可以接受。

需要本地验证：

- 新增输出是否在 ComfyUI UI 中正常显示。
- `custom_indexes` 输入是否正常显示为字符串输入框。
- `natural_asc` / `natural_desc` 下拉是否正常。
- `saved_paths_text` 是否可作为 STRING 输出被后续节点接收。

### 3.3 LLM Debug JSON Review

结论：通过。

当前实现：

- 发送前构造完整 `request_payload`。
- 用 deep copy 生成 debug 版本。
- 递归扫描 dict / list / str。
- 只截断以 `data:image/` 开头的字符串。
- 返回给节点的 `request_json` 使用 debug 版本。
- 实际 API 请求仍使用完整 request payload。

风险：

- 如果某些服务商的图片字段不是 data URL，而是其他大字符串，该逻辑不会截断。
- 当前只处理 `data:image/`，这符合本项目 Vision Chat 的生成方式。

### 3.4 Video Info Review

结论：基本通过。

当前 `video_info_json` 内容包括：

- `video_path`
- `filename`
- `extension`
- `width`
- `height`
- `fps`
- `total_frames`
- `duration_seconds`
- `size_bytes`
- `modified_time`
- `selected_index`
- `total_files`
- `decoded_frame_count`
- 当前加载参数

风险：

- `total_frames` / `fps` 依赖 OpenCV 返回，部分编码格式可能不准。
- 对可变帧率视频，`duration_seconds = total_frames / fps` 只是估算。
- 需要真实视频验证。

### 3.5 Frame Sampler Review

结论：通过。

新增 `custom_indexes` 支持：

```text
0,10,20,-1
```

规则：

- 支持英文逗号、中文逗号和空白分隔。
- 支持负数索引。
- `-1` 表示最后一帧。
- 自动 clamp 到合法范围。
- 自动去重。
- 最多保留 10 个索引。

保存文件增强：

- 文件名加入时间戳：`{prefix}_{timestamp}_{i:03d}.png`
- 解决重复执行覆盖旧文件的问题。
- 输出 `saved_paths_text`，方便调试或后续节点使用。

### 3.6 依赖与兼容性 Review

结论：需要本地验证。

当前依赖：

- `numpy`
- `pillow`
- `torch`
- `opencv-python`
- `openai>=1.0.0`

风险：

- ComfyUI 通常已有 `torch` / `pillow` / `numpy`，重复安装一般没问题，但可能会影响某些已有环境。
- `opencv-python` 在部分无桌面 Linux 环境可能更适合使用 `opencv-python-headless`。
- 当前代码使用 `dict | None` 类型写法，要求 Python 3.10+。现代 ComfyUI 通常满足，但如果用户环境仍是 Python 3.9 会失败。

建议后续：

- 如果用户本地是 Linux server，可以考虑把 `opencv-python` 改成可选说明，或者换成 `opencv-python-headless`。
- 如果需要兼容 Python 3.9，把 `dict | None` 改成 `Optional[dict]`。

## 4. 当前仍未完成的事项

### 4.1 必须本地验证

1. ComfyUI 能否正常启动。
2. 5 个 Ryan 节点是否能正常显示。
3. 前端 JS 是否能正常加载。
4. Batch Video Loader 是否能加载常见 mp4。
5. Video Frame Sampler 是否能接收 Loader 输出的 `images`。
6. Vision Chat 是否能接收 Sampler 输出的 `images`。
7. LLM Profile 是否能正确读取本地 `llm_profiles.json` 或环境变量。
8. OpenAI-Compatible 请求是否能跑通。

### 4.2 仍建议后续补的增强

1. 前端按钮读取 total，做 UI 层 clamp。
2. 前端显示当前文件名、index、total。
3. 真正 FFmpeg raw pipe 解码。
4. `Prompt Template` 支持手动输入 template_name，避免自定义目录下拉不刷新的问题。
5. `Prompt Template` 输出 missing variables。
6. LLM 节点支持 custom headers。
7. LLM 节点支持 response_format / JSON mode。
8. `request_json` 可选是否截断 base64，目前默认总是截断。
9. `Frame Sampler` 支持输出首帧 / 尾帧独立端口。
10. `Frame Sampler` 支持生成预览网格图。

## 5. 推荐下一步

下一步建议先不继续加功能，先做本地验证：

```text
Ryan Batch Video Loader
  -> Ryan Video Frame Sampler
  -> Ryan LLM Vision Chat
```

验证通过后，再进入下一轮增强：

1. 前端显示当前视频状态。
2. Prompt Template 变量检测。
3. LLM custom headers / JSON mode。
4. ACP / Skill 第二批设计。
