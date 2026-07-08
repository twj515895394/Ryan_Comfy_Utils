# Ryan Comfy Utils 交接文档

生成时间：2026-07-08 09:24:46 Asia/Tokyo

仓库：`twj515895394/Ryan_Comfy_Utils`

## 1. 背景与目标

本项目定位为作者自用的 ComfyUI 工具节点集合，目标是把常用节点统一沉淀到一个仓库中，方便在 ComfyUI 工作流里快速调用。

最初需求包括：

1. 整理常用 ComfyUI 节点到 `Ryan_Comfy_Utils`。
2. 后续希望支持连接本地 ACP，从而在 ComfyUI 中调用一些 Skill。
3. 需要通用 LLM 节点。
4. 需要增强视频加载节点，支持批量目录视频、按名称排序、按 index 切换视频，不再每次手动去系统目录选择下一个视频。
5. 旧项目 `ComfyUI_Qwen3-VL-Instruct-utils` 中已有部分节点能力，希望迁入新工具集合，但不是原封不动迁移。
6. 节点命名要便于在 ComfyUI 里搜索和区分，统一归到 Ryan 工具集合下。

## 2. 已达成的设计共识

### 2.1 仓库定位

`Ryan_Comfy_Utils` 作为总集合仓库，不再把每类能力分散维护在多个仓库中。

节点统一命名和分类：

- 节点显示名前缀统一使用 `Ryan`。
- 节点分类统一放在 `Ryan Utils / ...` 下。
- 搜索 `Ryan` 能快速找到本仓库所有节点。

### 2.2 旧 Qwen3-VL 仓库迁移方式

旧仓库 `ComfyUI_Qwen3-VL-Instruct-utils` 不做原封不动迁移，而是抽象化改造。

明确去掉第一版中的本地模型能力：

- 不保留本地 Qwen3-VL 模型加载。
- 不保留 transformers 模型管理。
- 不保留 bitsandbytes / triton / attention / quantization 等本地推理逻辑。
- 不建议第一版使用本地模型。

保留的是思路和部分通用能力：

- LLM / Vision 节点形态。
- Prompt 模板节点。
- 图片 / 视频 / 文本工具类节点思路。

第一版统一改成 OpenAI-Compatible API 调用。

### 2.3 LLM Profile 配置设计

第一版采用全局 Profile 配置：

- 示例配置入仓：`ryan_comfy_utils/config/llm_profiles.example.json`
- 真实配置不入仓：`ryan_comfy_utils/config/llm_profiles.json`
- `.gitignore` 忽略真实配置。
- 支持通过环境变量 `RYAN_COMFY_UTILS_PROFILE_PATH` 指定自定义配置路径。
- API Key 优先通过环境变量读取。

配置优先级：

1. `RYAN_COMFY_UTILS_PROFILE_PATH`
2. `ryan_comfy_utils/config/llm_profiles.json`
3. `ryan_comfy_utils/config/llm_profiles.example.json`

Profile 设计字段：

```json
{
  "default": "openai",
  "profiles": {
    "openai": {
      "base_url": "https://api.openai.com/v1",
      "api_key_env": "OPENAI_API_KEY",
      "default_model": "gpt-4.1"
    }
  }
}
```

节点中选择 `profile`，同时允许 `model_override` 覆盖默认模型。

### 2.4 第一版节点范围

第一版先做 5 个节点：

1. `Ryan LLM Chat`
2. `Ryan LLM Vision Chat`
3. `Ryan Prompt Template`
4. `Ryan Batch Video Loader`
5. `Ryan Video Frame Sampler`

ACP / Skill 节点放到第二批，不在第一版中开发。

### 2.5 模块化目录结构

第一版不沿用旧仓库里所有逻辑堆在 `nodes.py` 的模式，而是采用模块化结构：

```text
Ryan_Comfy_Utils/
  __init__.py
  README.md
  requirements.txt
  .gitignore
  .handoff/

  ryan_comfy_utils/
    __init__.py

    core/
      __init__.py
      config_loader.py
      llm_client.py
      image_utils.py
      video_utils.py

    nodes/
      __init__.py
      llm_nodes.py
      prompt_nodes.py
      video_nodes.py

    config/
      llm_profiles.example.json

    prompts/
      video_frame_analysis.md

    web/
      ryan_video_loader.js
```

原则：

- `core/` 放通用能力，不直接注册 ComfyUI 节点。
- `nodes/` 放 ComfyUI 节点定义。
- `config/` 放示例配置，不提交真实 key。
- `prompts/` 放提示词模板。
- 根目录 `__init__.py` 只做节点注册，不塞业务逻辑。

## 3. LLM 节点设计

### 3.1 Ryan LLM Chat

定位：纯文本 LLM 节点，走 OpenAI-Compatible 协议。

输入参数：

- `profile`
- `model_override`
- `system_prompt`
- `user_prompt`
- `temperature`
- `max_tokens`
- `top_p`
- `timeout_seconds`
- `retry_count`
- `extra_body_json`

输出：

- `response_text`
- `request_json`
- `raw_response_json`

### 3.2 Ryan LLM Vision Chat

定位：多图 Vision Chat 节点。

已确认设计：

- 默认多图一次性请求。
- 不做逐帧循环请求作为第一版重点。
- 最多 10 张图片。
- 输入 `images` 为 ComfyUI `IMAGE` batch。
- 将图片转为 OpenAI-Compatible 的 `image_url` base64 data URL。

图片处理策略：

- `image_max_side` 默认 1280。
- 节点界面可输入自定义最大边。
- 只等比缩小，不放大。
- 默认编码 `jpeg`。
- `jpeg_quality` 默认 85，可调 50-100。
- 可切换 `png`。

输出：

- `response_text`
- `request_json`
- `raw_response_json`

### 3.3 LLM 请求模式

已确认：

- ComfyUI 场景不做流式输出。
- 所有 LLM 请求使用 blocking 模式。
- `stream=false`。
- 请求完整返回后再输出节点结果。

超时和重试：

- `timeout_seconds` 默认 300。
- 最小 30。
- 最大 1200。
- `retry_count` 默认 0。
- 最大 3。

失败处理：

- 失败时直接抛异常。
- workflow 必须中断。
- 不把错误伪装成 `response_text` 正常输出。
- 这样更方便定位配置、网络、API、模型响应等问题。

## 4. Prompt 节点设计

### 4.1 Ryan Prompt Template

定位：Prompt 模板读取与变量替换节点。

已确认设计：

- 支持内置模板目录。
- 支持用户自定义模板目录。
- 支持文件类型：`.txt` / `.md` / `.json`。
- 支持简单变量替换：`{{key}}`。
- 第一版不引入 Jinja2，只做轻量替换。

输入参数：

- `template_source`: `built_in` / `custom_dir`
- `prompt_dir`
- `template_name`
- `variables_json`
- `user_prompt`
- `append_user_prompt`

输出：

- `final_prompt`
- `template_text`

变量替换示例：

```text
模板：
请分析任务：{{task}}
补充要求：{{extra_prompt}}

variables_json：
{
  "task": "分析视频首尾帧变化",
  "extra_prompt": "重点关注动作、镜头、画面质量"
}
```

## 5. 视频节点设计

### 5.1 Ryan Batch Video Loader

定位：批量目录视频选择 + 基础视频帧加载控制。

用户纠正后的最终设计：

- Loader 不只是视频路径选择器。
- Loader 要包含类似 VideoHelperSuite 的基础加载控制能力。
- Loader 第一版直接解码并输出 `images` 视频帧 batch。
- VideoHelperSuite 只作为参考，不作为依赖。

核心能力：

- 选择一个目录。
- 扫描目录下视频文件。
- 按视频名称默认升序排序。
- 默认加载排序后的第一个视频，即 `index=0`。
- 支持手动输入 index。
- 支持前端上一个 / 下一个按钮。
- 支持递归扫描。
- 支持扩展名过滤。
- 支持基础解码控制参数。

输入参数：

- `video_dir`
- `index`
- `recursive`
- `extensions`
- `sort_mode`
- `backend_mode`
- `force_rate`
- `custom_width`
- `custom_height`
- `frame_load_cap`
- `skip_first_frames`
- `select_every_nth`

排序模式：

- `filename_asc`
- `filename_desc`
- `mtime_asc`
- `mtime_desc`

解码后端：

- `auto`
- `opencv`
- `ffmpeg`

默认：`auto`。

VideoHelperSuite 相关参考点：

- 参考其 `force_rate`、`custom_width`、`custom_height`、`frame_load_cap`、`skip_first_frames`、`select_every_nth` 等设计。
- 参考其 OpenCV / FFmpeg 两类读取思路。
- 不依赖 `ComfyUI-VideoHelperSuite` 插件。

输出：

- `images`
- `frame_count`
- `video_path`
- `filename`
- `index`
- `total`
- `file_list_text`

### 5.2 Ryan Video Frame Sampler

定位：从视频帧 batch 中进一步抽取关键帧。

设计纠正：

- 输入不仅可以来自 video，也可以来自 images。
- 当前第一版已实现 `images` 输入。
- 很多视频节点输出的是 `images` 视频帧 batch，因此必须支持 `images`。

已确认功能：

- 默认输出首尾 2 帧。
- 最大输出 10 张。
- 支持修改输出帧数量。
- 支持按间隔抽帧。
- 支持保存到 ComfyUI 默认 output 目录的子目录中。
- 保存路径通过节点参数配置，不作为主要输出字段。

输入参数：

- `sample_mode`
- `frame_count`
- `frame_interval`
- `save_mode`
- `output_subdir`
- `filename_prefix`
- `images`

采样模式：

- `head_tail`
- `uniform`
- `interval`

输出：

- `images`
- `frame_indexes`
- `frame_count`

保存设计：

- `save_mode=preview_only`：只输出图片 batch。
- `save_mode=save_to_output`：保存到 ComfyUI 默认 output 目录下。
- `output_subdir` 基于默认 output 目录拼接。
- `filename_prefix` 控制保存文件名前缀。

## 6. 本次已经完成的内容

本次已直接提交到 `main` 分支。

### 6.1 文档与配置

已创建：

- `README.md`
- `.gitignore`
- `requirements.txt`
- `ryan_comfy_utils/config/llm_profiles.example.json`
- `ryan_comfy_utils/prompts/video_frame_analysis.md`

README 已记录：

- 项目定位。
- 第一版节点。
- 安装方式。
- LLM Profile 配置方式。
- 设计原则。

### 6.2 ComfyUI 注册入口

已创建根目录 `__init__.py`。

已注册节点：

- `Ryan LLM Chat`
- `Ryan LLM Vision Chat`
- `Ryan Prompt Template`
- `Ryan Batch Video Loader`
- `Ryan Video Frame Sampler`

已设置：

```python
WEB_DIRECTORY = "./ryan_comfy_utils/web"
```

### 6.3 Core 层

已创建：

- `ryan_comfy_utils/core/config_loader.py`
- `ryan_comfy_utils/core/llm_client.py`
- `ryan_comfy_utils/core/image_utils.py`
- `ryan_comfy_utils/core/video_utils.py`

能力摘要：

`config_loader.py`：

- 读取 Profile 配置。
- 支持环境变量配置路径。
- 支持私有配置文件。
- 支持示例配置 fallback。
- 解析 `base_url`、`api_key_env`、`api_key`、`default_model`、`model_override`。

`llm_client.py`：

- 基于 OpenAI Python SDK。
- 支持 OpenAI-Compatible base_url。
- blocking chat completions。
- 输出 `response_text`、`request_json`、`raw_response_json`。
- 失败后抛异常。

`image_utils.py`：

- ComfyUI IMAGE tensor 转 PIL。
- PIL list 转 IMAGE batch。
- 图片最长边等比缩小。
- JPEG / PNG data URL 编码。

`video_utils.py`：

- 扫描视频目录。
- 按名称 / 修改时间排序。
- index clamp。
- OpenCV 解码视频帧。
- FFmpeg fallback 的轻量占位实现。
- 视频帧采样。
- 图片 batch 保存。

### 6.4 Nodes 层

已创建：

- `ryan_comfy_utils/nodes/llm_nodes.py`
- `ryan_comfy_utils/nodes/prompt_nodes.py`
- `ryan_comfy_utils/nodes/video_nodes.py`

已实现：

`RyanLLMChat`：

- 文本 Chat。
- Profile 选择。
- model override。
- timeout / retry。
- extra_body_json。

`RyanLLMVisionChat`：

- IMAGE batch 输入。
- 最多 10 张图。
- 最大边等比缩小。
- JPEG 85 默认。
- PNG 可选。
- 多图一次请求。

`RyanPromptTemplate`：

- 内置模板目录。
- 自定义模板目录。
- 简单 `{{key}}` 替换。
- user_prompt 追加。

`RyanBatchVideoLoader`：

- 扫描目录视频。
- 排序。
- index 选择。
- OpenCV / FFmpeg / auto backend 参数。
- 基础帧控制参数。
- 输出 images、frame_count、video_path、filename、index、total、file_list_text。

`RyanVideoFrameSampler`：

- 从 images 中抽帧。
- head_tail / uniform / interval。
- 最大 10 张。
- 可保存到 output 子目录。

### 6.5 Web 前端扩展

已创建：

- `ryan_comfy_utils/web/ryan_video_loader.js`

当前能力：

- 给 `Ryan Batch Video Loader` 增加：
  - `Ryan Previous Video`
  - `Ryan Next Video`
- 按钮通过修改 `index` widget 实现上一个 / 下一个。

## 7. 已知限制与风险

### 7.1 尚未在本地 ComfyUI 实测

当前代码已提交，但未在用户本地 ComfyUI 环境中实际启动验证。

需要重点验证：

- ComfyUI 是否能正确加载节点。
- `WEB_DIRECTORY` 是否能加载前端 JS。
- 节点分类是否正常显示。
- Profile 下拉是否能动态读取配置。
- LLM 节点是否能正常请求用户配置的 OpenAI-Compatible 服务。
- 视频节点输出的 IMAGE batch 是否符合后续节点预期。

### 7.2 FFmpeg 后端第一版较轻量

当前 `ffmpeg` 后端实现是轻量 fallback：

- 先通过 ffmpeg 命令做校验。
- 实际解码仍复用 OpenCV。

后续如果需要更强兼容性，应改为真正的 FFmpeg raw pipe 解码，参考 VideoHelperSuite 的 FFmpeg generator 思路。

### 7.3 Ryan Video Frame Sampler 暂未实现 video 对象输入

讨论中确认 Sampler 输入可以是 `video` 或 `images`。

当前第一版已实现 `images` 输入，但还没有实现新版 ComfyUI `IO.VIDEO` 对象输入。

后续需要补：

- `video` optional input。
- video 对象解码为 IMAGE batch。
- 与 Batch Video Loader 输出 images 的链路保持兼容。

### 7.4 Prompt Template 的自定义目录模板列表可能不是动态刷新

ComfyUI 的下拉选项在节点注册 / 刷新时生成。

当前第一版 `template_name` 默认从 built-in 目录读取。若切换到 custom_dir，可能仍需要手动输入型方案或前端刷新增强，后续需实测。

### 7.5 前端按钮当前只增加 index，不知道 total

当前 `Ryan Next Video` 只会让 index +1，未读取 `total` 做上界 clamp。

后端会 clamp 到有效范围，因此不会越界崩掉，但 UI 上 index 可能大于实际 total。

后续可增强：

- JS 读取 `total` 输出或缓存扫描结果。
- 前端按钮 clamp 到 `0 ~ total - 1`。
- 显示当前文件名和 total。

### 7.6 图片保存命名可能覆盖

当前 `Ryan Video Frame Sampler` 保存图片时使用：

```text
{filename_prefix}_{i:03d}.png
```

如果重复执行，可能覆盖旧文件。

后续建议改为：

- 使用时间戳。
- 使用 ComfyUI 的 `folder_paths.get_save_image_path()`。
- 或引入递增 counter。

### 7.7 requirements 可能需要按 ComfyUI 环境调整

当前 `requirements.txt` 包含：

- `numpy`
- `pillow`
- `torch`
- `opencv-python`
- `openai>=1.0.0`

ComfyUI 环境通常已有 torch / pillow / numpy，重复安装可能不是问题，但后续可考虑精简或标注。

## 8. 后续待完成任务

### 8.1 第一优先级：本地启动与基础修复

1. 在本地 ComfyUI `custom_nodes` 下 clone 仓库。
2. 安装 requirements。
3. 重启 ComfyUI。
4. 检查是否能找到 5 个 Ryan 节点。
5. 检查控制台是否有 import error。
6. 检查前端按钮是否显示。
7. 用一个短视频测试 Batch Video Loader。
8. 用 Sampler 抽首尾帧。
9. 用 Vision Chat 调用配置的 OpenAI-Compatible 多模态模型。

### 8.2 视频 Loader 增强

待设计 / 开发：

- 真正 FFmpeg raw pipe 解码。
- 支持视频音频输出可选项。
- 支持读取 fps / duration / total_frames 等 video_info。
- 输出 `video_info_json`。
- 支持更丰富的编码格式。
- 前端显示当前文件名、总数、当前 index。
- 前端上一个 / 下一个按钮增加 total clamp。
- 目录扫描结果缓存，避免频繁扫描大目录。
- 支持按文件名关键字过滤。
- 支持指定文件名选择模式。

### 8.3 Frame Sampler 增强

待设计 / 开发：

- 支持 `video` 对象输入。
- 支持 custom indexes，例如 `0,10,20,-1`。
- 支持输出首帧、尾帧单独端口。
- 保存文件名加入时间戳或递增编号，避免覆盖。
- 支持输出保存目录文本，虽然不作为主要输出，也可作为辅助调试输出。
- 支持生成预览网格图。

### 8.4 LLM 节点增强

待设计 / 开发：

- Profile 下拉刷新机制。
- 支持自定义 headers。
- 支持 `seed`。
- 支持 `frequency_penalty` / `presence_penalty`。
- 支持 response_format / JSON mode。
- 支持兼容不同服务商的 message 格式差异。
- 增加模型列表手动刷新节点。
- 对 raw_response_json 做更稳定的序列化。
- 对 request_json 中的 base64 图片做脱敏或可选截断，避免调试文本过大。

### 8.5 Prompt 节点增强

待设计 / 开发：

- 自定义目录模板动态刷新。
- 支持手动输入 template_name。
- 支持列出模板内容预览。
- 支持模板变量检测，输出 missing variables。
- 支持多个 prompt 片段合并。
- 后续再考虑 Jinja2，但第一版暂不引入。

### 8.6 ACP / Skill 节点第二批

待设计：

- ACP 本地服务协议确认。
- Skill 列表读取方式。
- Skill 调用参数结构。
- Skill 输入输出类型映射到 ComfyUI。
- 是否复用 LLM Profile 配置体系。
- 是否新增 `Ryan ACP Skill Runner`。
- 是否支持把图片 / 文本 / 视频帧传入 Skill。

初步建议第二批节点：

- `Ryan ACP Skill List`
- `Ryan ACP Skill Runner`
- `Ryan ACP Skill Prompt`

## 9. 推荐下一步

建议下一步不是继续扩展功能，而是先做本地验证闭环：

1. 安装到本地 ComfyUI。
2. 跑通 `Ryan Batch Video Loader -> Ryan Video Frame Sampler -> Ryan LLM Vision Chat`。
3. 记录实际报错。
4. 优先修 import、节点显示、前端按钮、视频 tensor shape、OpenAI-Compatible 请求格式这几类问题。
5. 验证稳定后再进入 ACP / Skill 第二批设计。
