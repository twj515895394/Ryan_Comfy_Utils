# Ryan Comfy Utils

Ryan Comfy Utils 是一个自用型 ComfyUI 工具节点集合，重点面向：

- **ACP Runtime**：通过固定 Agent 节点调用本地 Claude/Codex CLI（Skill 与 Node 解耦）
- OpenAI-Compatible LLM / Vision 调用
- 本地多模态模型调用（Transformers 或 GGUF + mmproj）
- Prompt 模板管理与文件导出
- 批量目录视频加载与基础抽帧控制
- 视频帧首尾帧 / 均匀采样

多图输入（默认 1 路 `image_01`，节点上 **Ryan + 图片** 最多 10 路）见 `docs/agents/comfy-multi-image-inputs.md`。

ACP Profile / CLI 占位符与失败语义见 `docs/agents/acp-runtime-cli-profile.md`。CLI 非 0 退出码、超时或非法结果会抛异常并中断 workflow。

## 节点一览

### Ryan ACP Universal Agent

分类：`Ryan Utils / ACP`

通用 ACP Agent 节点（Selectable Skill）。支持文本、多图槽位与 `image_paths`，打通：

- manifest/profile 加载
- session/workspace 创建
- skill/context 组装
- CLI 执行
- 文本结果回传

输入重点：

- `skill_id`
- `user_text`
- `profile_path`
- `manifest_path`
- `workspace_root`
- `session_id`
- `skill_root`

输出：

- `response_text`
- `session_dir`
- `raw_result_json`

### Ryan Image Prompt Agent

分类：`Ryan Utils / ACP`

固定绑定 `image_prompt_generator`，用于创作任意风格/题材/场景的**图像生成提示词**（非图像分析）。

输入：`user_text`；可选 `image_paths`（多行参考图路径）、`style` / `subject` / `scene` / `extra_prompt`；`skill_root` 留空时使用包内默认 Skill。

输出：`response_text`、`session_dir`、`raw_result_json`。契约详见 `docs/agents/acp-fixed-prompt-agent-contracts.md`。可选 `export_to_file` 写入 `output/ryan_acp_exports/image_prompt/`。

### Ryan Video Prompt Agent

分类：`Ryan Utils / ACP`

固定绑定 `video_prompt_generator`，用于创作**视频生成提示词**；`image_paths` 可选，支持纯文本驱动。可与 `Ryan Batch Video Loader`、`Ryan Video Frame Sampler` 输出的帧路径串联。

输出与 Universal Agent 相同的三项文本字段。可选 `export_to_file` 写入 `output/ryan_acp_exports/video_prompt/`。

### Ryan Image Analyze Agent

分类：`Ryan Utils / ACP`

固定绑定 `image_prompt_reverse`，从参考图**反推**可用于 AI 绘图的提示词（默认中英双语）。`category` 选择反推模板类型；**必须**提供参考图：连接 `image_01`… 或填写 `image_paths`（满足其一即可）。

`export_to_file` 开关（默认关）：开启后将 prompt 写入 `output/ryan_acp_exports/image_analyze/`。与 Image Prompt 节点分工见 `docs/agents/acp-fixed-prompt-agent-contracts.md`。

### Ryan File Exporter

分类：`Ryan Utils / File`

将任意文本写入 ComfyUI `output` 下子目录（默认 `ryan_acp_exports/manual`），输出 `file_path` 与 `file_text`。可接在任意 Agent 的 `response_text` 之后整理 prompt。详见 `docs/agents/acp-file-export-convention.md`。

### Ryan LLM Chat

分类：`Ryan Utils / LLM`

纯文本 LLM 节点，走 OpenAI-Compatible 协议。

输出：

- `response_text`
- `request_json`
- `raw_response_json`

说明：

- 不做流式输出，使用 blocking 请求。
- 请求失败直接抛异常并中断 workflow。
- `request_json` 用于调试；如果包含 Vision 图片，base64 data URL 会被截断，避免 ComfyUI 输出过大。

### Ryan LLM Vision Chat

分类：`Ryan Utils / LLM`

多图 Vision Chat 节点，默认把最多 10 张图片作为一次多图请求发给 OpenAI-Compatible Vision 模型。

图片默认处理：

- `image_max_side = 1280`
- 只等比缩小，不放大
- 默认 `jpeg`，`jpeg_quality = 85`
- 可切换 `png`
- `request_json` 中的 base64 图片会被截断展示，真实请求仍发送完整图片

### Ryan Local Multimodal Chat

分类：`Ryan Utils / LLM`

通用本地图片理解/多图对话节点，支持两种后端：

- Transformers 本地模型目录：通过 `AutoModelForImageTextToText + AutoProcessor` 动态加载。
- GGUF 主模型 + mmproj：临时启动官方 `llama-server`，通过本机 OpenAI-compatible 接口推理。

模型默认放在 `ComfyUI/models/ryan_multimodal/`。节点会把包含 `config.json` 的目录列为 `HF | ...`，把普通 `.gguf` 列为 `GGUF | ...`，并自动识别常见 mmproj/projector 文件。

`keep_model_loaded=false`（默认）时，每次执行结束或异常都会清理模型；GGUF 后端会直接终止临时 `llama-server` 子进程。详细安装、目录布局、参数和限制见 `docs/llm/local-multimodal-node.md`。

### Ryan Prompt Template

分类：`Ryan Utils / Prompt`

支持内置模板目录和自定义模板目录，支持 `.txt` / `.md` / `.json`，并支持简单 `{{key}}` 变量替换。

### Ryan Batch Video Loader

分类：`Ryan Utils / Video`

选择目录后扫描视频文件，按文件名排序，默认加载第一个视频。支持 index 输入和前端上一个 / 下一个按钮。

参考 VideoHelperSuite 的基础参数设计，但不依赖 VideoHelperSuite：

- `force_rate`
- `custom_width`
- `custom_height`
- `frame_load_cap`
- `skip_first_frames`
- `select_every_nth`
- `backend_mode = auto / opencv / ffmpeg`

排序模式：

- `filename_asc`
- `filename_desc`
- `natural_asc`
- `natural_desc`
- `mtime_asc`
- `mtime_desc`

输出：

- `images`
- `frame_count`
- `video_path`
- `filename`
- `index`
- `total`
- `file_list_text`
- `video_info_json`

`video_info_json` 包含：

- `width`
- `height`
- `fps`
- `total_frames`
- `duration_seconds`
- `size_bytes`
- `decoded_frame_count`
- 当前加载参数

### Ryan Video Frame Sampler

分类：`Ryan Utils / Video`

从 `images` 视频帧批次中抽取首尾帧、均匀采样帧、间隔帧或自定义索引帧，默认输出首尾 2 帧，最大 10 张。

采样模式：

- `head_tail`
- `uniform`
- `interval`
- `custom_indexes`
- `scene_first_frames` (分镜首帧模式，配合 `Ryan Video Scene Splitter` 的 `manifest_json` 输入使用)

`custom_indexes` 示例：

```text
0,10,20,-1
```

其中 `-1` 表示最后一帧。

支持预览输出，也可保存到 ComfyUI 默认 output 目录下的子目录。保存文件会自动加时间戳，避免重复执行时覆盖旧文件。

输入新增：
- `manifest_json` (分镜元数据，在 `sample_mode` 选择 `scene_first_frames` 时必填)

输出：

- `images`
- `frame_indexes`
- `frame_count`
- `saved_paths_text`

### Ryan Video Scene Splitter

分类：`Ryan Utils / Video`

使用 PySceneDetect (包含自适应检测、内容突变检测、亮度阈值检测) 对视频进行物理/物理重编码切割，并导出结构化的分镜数据。

输入：
- `video_path`：视频文件绝对路径（提供选择文件对话框按钮及 HTML5 视频播放预览）
- `output_dir`：切割后分镜的导出子目录（在 ComfyUI `output` 下）
- `filename_prefix`：导出分镜视频的命名前缀
- `detector`：检测器类型（"自适应检测"、"内容突变检测"、"亮度阈值检测"）
- `threshold`：检测灵敏度阈值（0 表示采用检测器内置默认值）
- `min_scene_len`：最小镜头时长限制（秒）
- `merge_min_duration`：短片段镜头合并阈值（秒，避免零碎噪音片段）
- `fast_copy`：快速导出开关（True 时直接进行流复制 `-c copy`，修改宽高/帧率时会自动降级为重编码）
- **控制参数 (加载时自动读取视频信息)**：
  - `force_rate`：强制输出分镜帧率（0 表示保持原样，非 0 自动降级为精确重编码）
  - `custom_width` / `custom_height`：输出分镜视频画面大小（0 表示保持原样）
  - `frame_load_cap`：最大检测/切割帧数（0 表示全视频分析）
  - `skip_first_frames`：跳过视频前 X 帧开始分析
  - `select_every_nth`：采样检测/输出间隔（1 表示全帧，>1 时抽帧切割）

输出：
- `scene_count`：检测到的分镜总数
- `manifest_json`：分镜元数据清单（包含每个分镜的开始时间、结束时间、物理路径等，可对接给 `Ryan Video Frame Sampler` 提取各分镜首帧图片）
- `output_dir`：分镜文件所在的物理文件夹绝对路径

### Ryan Image Batch Splitter

分类：`Ryan Utils / Image`

将输入的批量 Image 批次拆分成最多 12 路独立的单张图片输出，并伴随生成前端临时预览图。

输入：
- `images`：ComfyUI 批次图像（IMAGE）
- `output_count`：拆分输出的图像总数（最大支持 12）

输出：
- `image_01` 到 `image_12`：各个独立的单张图像（若批次尺寸小于请求拆分数量，多余输出为 `None`）

## 安装

将本仓库 clone 到 ComfyUI 的 `custom_nodes` 目录：

```bash
cd ComfyUI/custom_nodes
git clone git@github.com:twj515895394/Ryan_Comfy_Utils.git
cd Ryan_Comfy_Utils
pip install -r requirements.txt
```

本地 Transformers 多模态后端使用额外依赖：

```bash
pip install -r requirements-local-multimodal.txt
```

GGUF + mmproj 后端需要单独安装较新的官方 `llama-server`，不需要安装 `llama-cpp-python`。

## LLM Profile 配置

复制示例配置：

```bash
cp ryan_comfy_utils/config/llm_profiles.example.json ryan_comfy_utils/config/llm_profiles.json
```

推荐使用环境变量保存 API Key，例如：

```bash
export OPENAI_API_KEY="sk-xxx"
export SILICONFLOW_API_KEY="sk-xxx"
```

也可以使用自定义配置路径：

```bash
export RYAN_COMFY_UTILS_PROFILE_PATH="/your/path/llm_profiles.json"
```

配置优先级：

1. `RYAN_COMFY_UTILS_PROFILE_PATH`
2. `ryan_comfy_utils/config/llm_profiles.json`
3. `ryan_comfy_utils/config/llm_profiles.example.json`

## 设计原则

- 远程模型统一走 OpenAI-Compatible 协议。
- 本地多模态模型使用可选后端，不把 Qwen 或某个具体模型类写死在节点协议中。
- GGUF 多模态优先调用官方 `llama-server + mmproj`，避免依赖特定 `llama-cpp-python` Vision Handler。
- 默认按次加载并在执行结束后卸载；需要连续推理时可显式开启常驻。
- LLM 请求不做流式输出，适配 ComfyUI blocking 执行模式。
- LLM 请求失败直接抛异常，中断 workflow，方便定位问题。
- 视频能力参考 VideoHelperSuite，但不强依赖它。
