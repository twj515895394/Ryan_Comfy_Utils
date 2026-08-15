# Ryan Local Multimodal Chat

`Ryan Local Multimodal Chat` 是一个本地图片理解 / 多图对话节点，目标不是绑定某个 Qwen 版本，而是用一个节点承载两类本地模型运行方式：

1. Transformers 格式的本地多模态模型目录。
2. GGUF 主模型 + mmproj 视觉投影模型，由官方 `llama-server` 运行。

当前节点输入为文本与最多 10 路 ComfyUI `IMAGE`。音频和视频暂未直接暴露为节点输入；视频可以先通过现有抽帧节点转成多张图片。

## 1. 模型目录

默认扫描目录：

```text
ComfyUI/models/ryan_multimodal/
```

也可以通过 ComfyUI 的额外模型目录配置注册名为 `ryan_multimodal` 的目录，或者直接填写节点的 `model_path_override`。

### Transformers 模型

一个包含 `config.json` 的目录会出现在模型下拉框中，并显示为 `HF | ...`。

```text
ComfyUI/models/ryan_multimodal/
└── Qwen3-VL-4B-Instruct/
    ├── config.json
    ├── preprocessor_config.json
    ├── tokenizer.json
    ├── model-00001-of-00003.safetensors
    └── ...
```

### GGUF + mmproj

普通 `.gguf` 文件显示为 `GGUF | ...`。文件名中包含 `mmproj`、`projector`、`vision-proj` 或常见 CLIP projector 标记的文件会进入 `mmproj` 下拉框，而不会被当作主模型。

推荐把匹配的模型放在同一目录：

```text
ComfyUI/models/ryan_multimodal/
└── Qwen3-VL-4B-GGUF/
    ├── Qwen3-VL-4B-Instruct-Q4_K_M.gguf
    └── mmproj-Qwen3-VL-4B-Instruct-f16.gguf
```

当 `mmproj=auto` 时，节点会优先在主模型同目录寻找并匹配 projector。存在多个 projector 时，建议手动选择，避免加载错误组合。

## 2. 后端选择

### auto

- 选择模型目录：使用 Transformers。
- 选择 `.gguf`：使用官方 `llama-server`。

### transformers

使用：

- `AutoModelForImageTextToText`
- `AutoProcessor`
- `Processor.apply_chat_template`

这是一套通用入口，适合已经被当前 Transformers 版本原生支持的 Qwen-VL、Gemma、LLaVA、SmolVLM、部分 InternVL/OCR 等图文模型。

“通用”表示节点不写死模型类，不表示任意 Hugging Face 仓库都能无条件运行。以下模型仍可能需要：

- 更新 Transformers 版本；
- 打开 `trust_remote_code`；
- 特定模型自己的 prompt/chat template；
- 自定义 processor 参数；
- 模型仓库额外依赖。

安装可选依赖：

```bash
cd ComfyUI/custom_nodes/Ryan_Comfy_Utils
pip install -r requirements-local-multimodal.txt
```

使用 4bit/8bit 时还需按当前系统和 CUDA 环境安装 `bitsandbytes`。

### llama.cpp (GGUF + mmproj)

节点不会依赖 `llama-cpp-python` 的特定 Vision ChatHandler，而是临时启动官方 `llama-server`：

```bash
llama-server \
  -m /path/to/model.gguf \
  --mmproj /path/to/mmproj.gguf \
  --host 127.0.0.1 \
  --port <dynamic-port> \
  --no-webui
```

随后节点向本机 OpenAI-compatible `/v1/chat/completions` 发送图片 data URL 和文本，执行结束后关闭该进程。

这样设计的原因：

- 官方 llama.cpp 的 `libmtmd` 是 GGUF 多模态能力的主实现；
- 新模型支持通常先进入 llama.cpp；
- 结束独立进程后，主模型、mmproj、KV Cache 和 GPU 上下文能一起释放；
- 不需要在 ComfyUI Python 环境中编译并绑定 `llama-cpp-python`。

## 3. llama-server 查找顺序

节点按以下顺序查找：

1. 节点参数 `llama_server_path`；
2. 环境变量 `RYAN_LLAMA_SERVER_PATH`；
3. 系统 `PATH` 中的 `llama-server` / `llama-server.exe`；
4. ComfyUI 根目录下常见的 `llama.cpp/build/bin` 路径。

Windows 示例：

```text
D:\AI\llama.cpp\build\bin\Release\llama-server.exe
```

也可以设置：

```powershell
$env:RYAN_LLAMA_SERVER_PATH="D:\AI\llama.cpp\build\bin\Release\llama-server.exe"
```

必须使用支持目标模型和 mmproj 格式的较新 llama.cpp 构建。主模型和 mmproj 必须是匹配组合；仅文件格式都是 GGUF 并不代表可以任意搭配。

## 4. 加载与卸载

### keep_model_loaded = false（默认）

每次执行：

1. 解析模型和 mmproj；
2. 实时加载；
3. 完成推理；
4. 在 `finally` 中释放。

Transformers 后端会删除 Model/Processor 引用，执行 Python GC，并清理 CUDA/MPS cache。

GGUF 后端会终止临时 `llama-server` 进程。即使请求异常或启动失败，也会执行清理逻辑。

### keep_model_loaded = true

同一个节点实例会缓存当前模型：

- Transformers：保留 Model 和 Processor；
- GGUF：保留本地 `llama-server` 子进程。

模型路径、量化、dtype、attention 或 llama.cpp 启动配置变化时，会先卸载旧模型再加载新模型。推理发生异常时，常驻 GGUF 服务也会被关闭，避免保留损坏状态。

## 5. 关键参数

- `model`：从 `models/ryan_multimodal` 扫描出的模型。
- `mmproj`：GGUF projector，`auto` 时尝试同目录匹配。
- `model_path_override`：覆盖下拉框，可填写绝对路径。
- `mmproj_path_override`：覆盖 mmproj 下拉框。
- `image_slot_count` / `image_01...image_10`：复用 Ryan 多图输入规范。
- `image_max_side`：输入模型前等比缩小；`0` 表示不限制。
- `transformers_dtype`：`auto/bfloat16/float16/float32`。
- `transformers_quantization`：`none/4bit/8bit`。
- `context_size`：llama.cpp 上下文长度。
- `gpu_layers`：`auto`、`all` 或整数。
- `mmproj_offload`：是否把 projector 卸载到 GPU，默认开启。
- `startup_timeout_seconds`：等待本地 llama-server 加载模型。
- `request_timeout_seconds`：单次推理请求超时。

## 6. 输出

- `response_text`：模型回答。
- `backend_used`：实际使用的后端。
- `resolved_model_path`：解析后的模型绝对路径。
- `runtime_info_json`：模型路径、mmproj、图片数、加载耗时、总耗时和常驻状态等调试信息。

## 7. 已知边界

1. 当前节点聚焦图像 + 文本，不直接接收音频张量或视频文件。
2. 多图是否受支持取决于具体模型和其 chat template。
3. GGUF 多模态能力取决于当前 `llama-server` 构建；旧版本可能不识别新模型架构或新 mmproj。
4. Transformers 的“卸载”会释放 Python 引用和未使用的显存缓存，但进程级显存隔离不如独立子进程彻底。
5. `trust_remote_code=true` 会执行模型目录中的自定义 Python 代码，只应对可信模型开启。
6. 4bit/8bit 的可用性取决于 bitsandbytes、操作系统、CUDA 和显卡架构。

## 8. 后续建议

下一阶段可以在保持单一用户节点的前提下增加：

- 音频输入和视频文件输入；
- 模型能力探测与兼容性提示；
- Transformers 独立 Worker 进程，实现与 GGUF 一样彻底的进程级卸载；
- processor/chat-template 参数 JSON；
- llama.cpp 额外启动参数白名单；
- 手动 `Unload Local Model` 控制节点；
- 针对 Qwen3-VL、Gemma 3、InternVL、MiniCPM-V 的回归工作流。
