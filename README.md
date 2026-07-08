# Ryan Comfy Utils

Ryan Comfy Utils 是一个自用型 ComfyUI 工具节点集合，重点面向：

- OpenAI-Compatible LLM / Vision 调用
- Prompt 模板管理
- 批量目录视频加载与基础抽帧控制
- 视频帧首尾帧 / 均匀采样
- 后续扩展 ACP / Skill / Agent 工具节点

## 第一版节点

### Ryan LLM Chat

分类：`Ryan Utils / LLM`

纯文本 LLM 节点，走 OpenAI-Compatible 协议。

输出：

- `response_text`
- `request_json`
- `raw_response_json`

### Ryan LLM Vision Chat

分类：`Ryan Utils / LLM`

多图 Vision Chat 节点，默认把最多 10 张图片作为一次多图请求发给 OpenAI-Compatible Vision 模型。

图片默认处理：

- `image_max_side = 1280`
- 只等比缩小，不放大
- 默认 `jpeg`，`jpeg_quality = 85`
- 可切换 `png`

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

输出：

- `images`
- `frame_count`
- `video_path`
- `filename`
- `index`
- `total`
- `file_list_text`

### Ryan Video Frame Sampler

分类：`Ryan Utils / Video`

从 `images` 视频帧批次中抽取首尾帧、均匀采样帧或间隔帧，默认输出首尾 2 帧，最大 10 张。

支持预览输出，也可保存到 ComfyUI 默认 output 目录下的子目录。

## 安装

将本仓库 clone 到 ComfyUI 的 `custom_nodes` 目录：

```bash
cd ComfyUI/custom_nodes
git clone git@github.com:twj515895394/Ryan_Comfy_Utils.git
cd Ryan_Comfy_Utils
pip install -r requirements.txt
```

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

- 不内置本地 Qwen / transformers 模型加载逻辑
- 第一版统一走 OpenAI-Compatible 协议
- LLM 请求不做流式输出，适配 ComfyUI blocking 执行模式
- LLM 请求失败直接抛异常，中断 workflow，方便定位问题
- 视频能力参考 VideoHelperSuite，但不强依赖它
