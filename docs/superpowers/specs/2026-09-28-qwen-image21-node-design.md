# Ryan Qwen Image 2.1 节点设计规格

**日期：** 2026-09-28  
**状态：** 待实现  
**目标版本：** V1（基础文生图、参考图与图片引用）

## 1. 目标

为 Ryan Comfy Utils 增加一个面向 Qwen Image 2.1 的组合节点，解决官方 `Text Encode Qwen Image 2.1` 在多图工作流中的两个主要问题：

1. 每增加一张参考图都要手动新增一个 `Load Image` 节点并连接到下一个图片槽位。
2. 多张图片缺少直观的画廊管理和图片引用方式，Prompt 中很难明确说明“哪句话对应哪张图”。

新节点提供一个类似 `ComfyUI-FeiHou-Easy-H3` 的图片输入体验，但只负责以下边界内的工作：

- Prompt 和 Negative Prompt。
- CLIP 输入。
- 多张参考图片的画廊上传、拖拽管理和外部 `IMAGE` 输入。
- `@` 图片引用。
- Qwen Image 2.1 所需的参考图视觉编码和可选 VAE reference latent。
- 输出图片的宽度、高度、比例、Megapixels 和 batch size。
- 输出 Qwen Image 2.1 可直接使用的 Positive Conditioning、Negative Conditioning 和 Latent。

节点不接管模型加载、采样器、采样步数、CFG、调度器、LoRA、放大、VAE Decode 或保存图片。

## 2. 设计依据

本设计基于以下现有实现和工作流：

- 官方工作流：`X:/ComfyUI-aki-v2/ComfyUI/user/default/workflows/Qwen+image+2.1+文生图-V1.json`
- 官方 Qwen 节点：`X:/ComfyUI-aki-v2/ComfyUI/comfy_extras/nodes_qwen.py`
- 官方分辨率节点：`X:/ComfyUI-aki-v2/ComfyUI/comfy_extras/nodes_resolution.py`
- H3 参考实现：`X:/ComfyUI-aki-v2/ComfyUI/custom_nodes/ComfyUI-FeiHou-Easy-H3`
- Ryan 现有多图输入约定：`docs/agents/comfy-multi-image-inputs.md`

官方 Qwen Image 2.1 节点的执行逻辑有三个必须保留的行为：

1. 参考图片按照图片槽位顺序传入 Qwen tokenizer。
2. tokenizer 会自动插入 `<image1>`、`<image2>` 等视觉块，Prompt 本身不需要直接拼接这些特殊 token。
3. 连接 VAE 时，为每张参考图生成 `reference_latents`；未连接 VAE 时保留视觉 token 供 Qwen 视觉编码器使用。

因此，Ryan 节点应该包装官方 Qwen 的 conditioning 逻辑，而不是重新实现一套模型或采样逻辑。

## 3. 非目标

V1 明确不包含以下功能：

- 不加载 Qwen、CLIP、VAE、UNet 或其他模型。
- 不接管 KSampler、采样步数、CFG、seed、scheduler 或 denoise。
- 不实现 Prompt 优化、自动扩写、角色权重、图片权重或分区控制。
- 不实现图片局部编辑、蒙版、Inpaint、ControlNet、IP-Adapter 或 LoRA。
- 不支持视频、音频等 H3 资源类型；`@` V1 只引用图片。
- 不支持从网络 URL 直接加载图片。
- 不改变官方 Qwen tokenizer 的图片注入协议。
- 不把 `@` 解释为“只使用被引用的图片”。所有有效图片仍会传给 Qwen。
- 不输出最终 `IMAGE`。最终图片仍由下游采样和 VAE Decode 产生。

## 4. 用户体验

### 4.1 节点名称和分类

建议注册：

- 内部名称：`RyanQwenImage21`
- 显示名称：`Ryan Qwen Image 2.1`
- 分类：`Ryan/Conditioning`

节点应在 Ryan 节点集合中独立注册，不覆盖官方 `TextEncodeQwenImage21`。

### 4.2 推荐工作流

官方文生图工作流中的下列节点：

```text
Text Encode Qwen Image 2.1
Resolution Selector
Empty Latent Image
```

可以由一个 Ryan 节点替换为：

```text
Ryan Qwen Image 2.1
```

连接关系保持简单：

```text
CLIP Loader ────────────────> Ryan Qwen Image 2.1.clip
Load Image / 画廊 / IMAGE ─> Ryan Qwen Image 2.1.images
Ryan Qwen Image 2.1.positive ─> KSampler.positive
Ryan Qwen Image 2.1.negative ─> KSampler.negative
Ryan Qwen Image 2.1.latent ───> KSampler.latent_image
VAE Loader ────────────────> Ryan Qwen Image 2.1.vae（可选）
```

采样器、模型和 VAE Decode 仍由用户自由配置。

### 4.3 图片输入体验

节点默认显示一个内部图片画廊和两个可见图片槽位，最多支持 16 张图片。用户可以：

- 点击画廊单元格上传图片。
- 将本地图片拖入画廊。
- 在画廊内调整图片顺序。
- 删除单张图片。
- 通过 `image_slot_count` 增加或减少可见槽位。
- 直接从其他 ComfyUI 节点连接 `IMAGE` 到外部图片槽位。
- 将内部上传图片和外部 `IMAGE` 输入混合使用。

每个槽位同时最多有一个有效来源：

- 如果外部 `IMAGE` 已连接，执行时优先使用外部输入。
- 内部画廊中的图片保留在节点状态中，但该槽位暂时不参与编码。
- 前端将被外部输入占用的画廊单元格标记为已连接并禁止替换，行为参考 H3。
- 外部连接断开后，原内部图片恢复可用。

有效图片最终按槽位序号排序，而不是按上传时间排序。

## 5. 节点输入输出契约

### 5.1 可见输入

节点采用当前 Ryan 包更容易维护的传统 `INPUT_TYPES` / `FUNCTION` 注册方式，不直接继承官方的 `io.Autogrow` 节点。

建议输入如下：

| 输入 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `clip` | `CLIP` | 必填 | Qwen Image 2.1 对应 CLIP/Text Encoder |
| `vae` | `VAE` | 可选 | 连接后为参考图生成 `reference_latents` |
| `prompt` | `STRING` | 空 | 多行 Prompt，支持 `@` 图片引用 |
| `negative_prompt` | `STRING` | 空 | 多行 Negative Prompt，也支持 `@` 图片引用 |
| `resolution_mode` | `COMBO` | `aspect_ratio_megapixels` | 比例/Megapixels 或自定义宽高 |
| `aspect_ratio` | `COMBO` | `1:1 (Square)` | 官方分辨率节点的比例选项 |
| `megapixels` | `FLOAT` | `2.0` | 目标像素量，单位 MP |
| `width` | `INT` | `1024` | 自定义输出宽度 |
| `height` | `INT` | `1024` | 自定义输出高度 |
| `batch_size` | `INT` | `1` | 输出 latent batch 大小 |
| `reference_resolution` | `INT` | `1024` | 参考图视觉编码的目标面积；0 表示按原图尺寸 |
| `image_slot_count` | `INT` | `2` | 前端显示的图片槽位数量，范围 0–16 |
| `image_01` … `image_16` | `IMAGE` | 可选 | 外部图片输入 |

`width` 和 `height` 只在 `resolution_mode=custom` 时生效；`aspect_ratio` 和 `megapixels` 只在 `resolution_mode=aspect_ratio_megapixels` 时生效。

### 5.2 隐藏输入

前端画廊和 `@` 编辑器需要保存少量不可见状态：

| 输入 | 类型 | 作用 |
| --- | --- | --- |
| `gallery_01` … `gallery_16` | `STRING` | ComfyUI annotated filepath 或空字符串 |
| `gallery_manifest` | `STRING` | 画廊图片的稳定 ID、文件名和槽位信息 |
| `prompt_mentions` | `STRING` | Prompt/Negative Prompt 的 `@` 引用元数据 JSON |

隐藏字段只保存工作流状态，不参与模型配置，也不向用户暴露绝对路径。

### 5.3 输出

```text
positive: CONDITIONING
negative: CONDITIONING
latent: LATENT
```

`latent` 必须是 Qwen Image 2.1 格式，而不是普通 `EmptyLatentImage` 的 4 通道格式：

```text
samples shape = [batch_size, 64, height // 16, width // 16]
device = comfy.model_management.intermediate_device()
```

这样可以直接连接官方 Qwen Image 2.1 工作流中的 KSampler latent 输入。

## 6. 分辨率和 Latent 设计

### 6.1 比例与 Megapixels 模式

`aspect_ratio` 使用官方 `ResolutionSelector` 的八个选项：

- `1:1 (Square)` → `1:1`
- `2:3 (Portrait Photo)` → `2:3`
- `3:2 (Photo)` → `3:2`
- `3:4 (Portrait Standard)` → `3:4`
- `4:3 (Standard)` → `4:3`
- `9:16 (Portrait Widescreen)` → `9:16`
- `16:9 (Widescreen)` → `16:9`
- `21:9 (Ultrawide)` → `21:9`

计算方式与官方节点一致：

```text
total_pixels = megapixels * 1024 * 1024
scale = sqrt(total_pixels / (ratio_width * ratio_height))
width = round(ratio_width * scale / 16) * 16
height = round(ratio_height * scale / 16) * 16
```

这里使用 16 作为 Qwen latent 的安全对齐倍数。官方 `ResolutionSelector` 默认以 8 对齐，但 Qwen Image 2.1 官方文本编码节点会以 `width // 16` 和 `height // 16` 创建 latent，因此 Ryan 节点内部必须确保最终尺寸可以安全整除 16。

最终宽高限制为：

- 最小值：16
- 最大值：4096
- 必须为 16 的倍数

### 6.2 自定义宽高模式

当 `resolution_mode=custom` 时：

```text
width = round_to_multiple(width, 16)
height = round_to_multiple(height, 16)
```

建议使用四舍五入到最近倍数，并在范围外进行 clamp。节点执行时应使用归一化后的实际尺寸生成 latent，不能只在前端显示修正后的尺寸。

### 6.3 Batch Size

`batch_size` 范围建议为 1–64，默认 1。它只影响输出 latent 的 batch 维度，不重复读取或复制参考图 conditioning 的语义结构。

### 6.4 参考图预处理尺寸

输出尺寸和参考图预处理尺寸必须分离：

- 输出尺寸决定最终生成图片的 latent 大小。
- `reference_resolution` 决定送入 Qwen 视觉编码器以及可选 VAE 的参考图大小。

当 `reference_resolution > 0` 时，每张参考图按保持宽高比、目标面积约为 `reference_resolution²` 的方式缩放，并将宽高对齐到 32 的倍数，以保持官方 Qwen 节点的行为。

当 `reference_resolution == 0` 时，使用参考图原始尺寸，并将尺寸对齐到 32 的倍数。

参考图之间分别计算尺寸，不强制把所有参考图拉伸为同一比例。

## 7. `@` 图片引用设计

### 7.1 语义

`@` 是面向用户的图片指代语法，不是 Qwen tokenizer 的原生特殊 token。

例如：

```text
@图片1 是人物身份参考，@图片2 是服装参考，生成一张电影感肖像。
```

节点会在执行前将引用转换为模型更容易理解的文本：

```text
Picture 1 is the identity reference, Picture 2 is the clothing reference, 生成一张电影感肖像。
```

同时，Qwen tokenizer 仍会自动注入对应的 `<image1>`、`<image2>` 视觉块。

因此：

- `@` 不会原样传给模型。
- `@` 不会改变图片注入数量。
- 所有有效参考图仍然会传入 Qwen。
- `@` 只帮助 Prompt 表达图片之间的角色和关系。

### 7.2 用户界面

Prompt 和 Negative Prompt 各自使用一个轻量的富文本编辑层：

- 用户输入 `@` 时打开图片选择菜单。
- 菜单显示图片缩略图、用户可见编号、文件名和来源。
- 选择后插入一个带缩略图的引用 chip。
- chip 的可见文本为 `@图片1`、`@图片2` 等。
- 删除或替换 chip 会同步更新底层 Prompt 字符串和引用清单。
- 复制、粘贴、保存和重新加载工作流后，引用仍可恢复。
- 不支持视频、音频和任意外部 URL 的 mention。

菜单条目示例：

```text
┌──────────────┬─────────────────────────────┐
│ 缩略图       │ @图片1  character.png       │
│ 缩略图       │ @图片2  clothing.jpg        │
│ 缩略图       │ @图片3  外部输入 image_03   │
└──────────────┴─────────────────────────────┘
```

文件名只用于帮助用户识别，默认插入稳定的图片编号，不直接把文件名作为引用 key，避免重名文件产生歧义。

### 7.3 引用稳定性

引用不能只绑定当前图片序号，因为用户可能会拖动排序。因此画廊中每张内部图片都有稳定的 `asset_id`：

```json
{
  "asset_id": "gallery-uuid",
  "slot": 2,
  "filename": "character.png",
  "path": {
    "name": "character.png",
    "subfolder": "ryan_qwen_image21",
    "type": "input"
  }
}
```

外部 `IMAGE` 输入使用稳定的槽位 ID，例如 `external-slot-02`。这样外部输入更换内容时仍然保持“引用这个槽位”的语义。

`prompt_mentions` 保存 mention 与资源之间的绑定：

```json
[
  {
    "prompt": "positive",
    "display": "@图片1",
    "asset_id": "gallery-uuid",
    "fallback_ordinal": 1
  }
]
```

执行时按以下步骤解析：

1. 收集所有有效图片，并为每张图片建立 `asset_id → current_ordinal` 映射。
2. 优先使用 `asset_id` 找到当前图片。
3. 找到后将其转换为当前有效图片序号对应的 `Picture N`。
4. 如果工作流没有旧版 mention 元数据，则使用 `fallback_ordinal` 兼容手动输入。
5. 如果引用已经失效，直接报错并指出失效的 `@图片N`，不静默忽略。

拖动排序会改变 `Picture N` 的当前序号，但不会改变 mention 所绑定的实际图片。

### 7.4 手动输入兼容

除了 UI chip，用户也可以手动输入以下形式：

- `@图片1`
- `@图片2`
- `@image1`
- `@image2`

手动输入没有稳定 `asset_id` 时，执行时按当前有效图片顺序解析。文件名形式不作为 V1 的正式语法，以避免重名和特殊字符问题。

### 7.5 失效和错误

以下情况必须提供可读错误：

- Prompt 引用了不存在的图片，如 `@图片4`，但只有三张有效图片。
- mention 的 `asset_id` 已被删除，且没有有效 fallback 序号。
- 外部 `IMAGE` 槽位曾被引用，但执行时没有连接图片。
- 内部画廊路径不再存在。

错误中应包含节点名、引用文本和建议动作，例如：

```text
Ryan Qwen Image 2.1: @图片2 指向的参考图已不存在。
请重新上传图片，或删除 Prompt 中的该引用。
```

## 8. 图片收集和官方 Qwen 逻辑

### 8.1 收集顺序

后端执行开始时，按 `image_01` 到 `image_16` 顺序收集图片：

1. 如果外部 `IMAGE` 非空，使用外部 tensor。
2. 否则如果对应画廊槽位有 annotated filepath，加载画廊图片。
3. 否则跳过该槽位。

收集结果形成紧凑的有效图片列表，并重新编号为 `image1...imageN`。`@` 的 `fallback_ordinal` 使用这个紧凑编号，而不是原始槽位编号。

### 8.2 图片 tensor

与官方节点保持一致：

- 每个 `IMAGE` 槽位只取 batch 的第一张图片。
- 参考图转换为适合 Qwen vision encoder 的 RGB tensor。
- 有 alpha 通道时，vision 输入在白色背景上合成。
- 如果连接 VAE，VAE reference latent 使用保留原始 alpha 处理的图像 tensor。
- 参考图缩放后再进入 vision tokenizer 和 VAE 编码。

### 8.3 Positive/Negative Conditioning

执行逻辑应与官方 `TextEncodeQwenImage21` 保持一致：

1. 对 Prompt 做 mention 解析和文本替换。
2. 对 Negative Prompt 做同样的 mention 解析。
3. 将所有有效参考图作为 `images` 传给 `clip.tokenize`。
4. 没有 VAE reference latent 时使用 `keep_vision=True`。
5. 连接 VAE 并成功生成 reference latents 时，使用官方方式设置 `keep_vision`，并把 `reference_latents` 追加到 Positive 和 Negative conditioning。
6. 分别调用 `encode_from_tokens_scheduled` 得到 Positive 和 Negative conditioning。

不因为 Prompt 中没有 `@` 而移除参考图；`@` 只是语义提示。

### 8.4 无图片和纯文生图

没有任何有效图片时，节点仍然应支持纯文生图：

- `images=[]`
- 不生成 `reference_latents`
- 正常执行文本 tokenizer
- `prompt` 中不能出现有效 `@` 引用；若出现则返回明确错误
- 正常输出目标尺寸的 Qwen latent

## 9. 内部上传与文件安全

内部画廊上传沿用 H3 已验证的 ComfyUI 输入文件流程：

1. 前端使用 ComfyUI API 的 `/upload/image` 上传到 input 目录。
2. 请求使用 `type=input`，避免写入 arbitrary path。
3. 前端只保存 ComfyUI 返回的 `name/subfolder/type` 信息。
4. 后端通过 `folder_paths.exists_annotated_filepath` 验证文件存在。
5. 后端通过 `folder_paths.get_annotated_filepath` 获取受控路径。
6. 图片使用 ComfyUI 的安全 Pillow helper 加载并进行 EXIF 方向校正。

禁止从隐藏输入接收任意绝对路径并直接 `Image.open`。工作流保存后，画廊状态必须仍然可以在 ComfyUI input 目录范围内安全恢复。

## 10. 前端实现边界

建议新增独立文件：

```text
ryan_comfy_utils/web/ryan_qwen_image21.js
```

不直接扩展 H3 的前端文件，也不修改现有 `ryan_multi_image_slots.js` 的全局行为，以避免影响已有 Ryan 节点。

前端职责分为四部分：

### 10.1 动态图片槽位

- 预注册 16 个 `IMAGE` 输入。
- 根据 `image_slot_count` 隐藏或显示槽位。
- 保留 ComfyUI 连线所需的真实 widget/input。
- 节点载入时根据已有连线、画廊数据和 `image_slot_count` 恢复显示。
- 外部连接存在时禁用同槽位内部上传单元格。

### 10.2 图片画廊

- 支持点击上传、拖拽上传和删除。
- 支持画廊内排序。
- 为每张内部图片创建并持久化 `asset_id`。
- 显示来源标签：内部画廊或外部 `IMAGE` 槽位。
- 生成缩略图时使用 ComfyUI input URL，不把本地绝对路径暴露给浏览器。

### 10.3 Prompt mention 编辑器

- 保留底层 `prompt` 和 `negative_prompt` 为普通字符串，确保后端和工作流兼容。
- 在节点界面上增加 contenteditable 编辑层或等价轻量富文本层。
- chip 只负责视觉表现，序列化后仍然写入普通字符串。
- chip 的显示文本为 `@图片N`，元数据写入 `prompt_mentions`。
- 节点重新加载时使用普通字符串和 mention manifest 重建 chip。
- 如果浏览器或工作流缺少 manifest，退化为普通多行文本编辑。

### 10.4 尺寸控件

- `resolution_mode` 切换时显示对应控件。
- 显示计算后的实际宽高和总像素量，帮助用户确认设置。
- 前端可以进行即时提示，但后端必须再次归一化和验证。

## 11. 后端代码结构建议

建议新增：

```text
ryan_comfy_utils/nodes/qwen_image21_node.py
tests/nodes/test_qwen_image21_node.py
ryan_comfy_utils/web/ryan_qwen_image21.js
tests/frontend/test_qwen_image21_frontend_contract.py
```

后端文件内部建议拆分为纯函数，便于测试：

- `collect_image_sources(...)`
- `load_gallery_image(...)`
- `resolve_image_mentions(...)`
- `replace_prompt_mentions(...)`
- `calculate_qwen_resolution(...)`
- `normalize_custom_resolution(...)`
- `build_qwen_latent(...)`
- `encode_qwen_conditioning(...)`

节点主函数只负责按照官方执行顺序编排这些步骤，不把前端状态解析、路径安全和尺寸计算全部堆在一个 `execute` 函数中。

注册时增加：

- `NODE_CLASS_MAPPINGS["RyanQwenImage21"]`
- `NODE_DISPLAY_NAME_MAPPINGS["RyanQwenImage21"]`
- 将新前端文件纳入现有 `WEB_DIRECTORY` 加载方式。

## 12. 兼容性策略

### 12.1 官方节点兼容

- 不修改官方 `TextEncodeQwenImage21`。
- 不依赖官方节点的内部实例状态。
- 复用 ComfyUI 提供的 `clip.tokenize`、`conditioning_set_values`、`model_management.intermediate_device` 和 VAE API。
- 通过官方 conditioning 结构传递 `reference_latents` 和 `image_slots` 所需信息。

### 12.2 现有 Ryan 节点兼容

- 不修改现有通用多图槽位的上限和默认行为。
- 新节点使用自己的前端选择器和画廊状态。
- 新节点不会更改已有 Image Generator、Video Generator 或 ACP 节点的 Prompt 字段。

### 12.3 工作流兼容

- 没有 `gallery_manifest` 的节点状态可以正常加载为空画廊。
- 没有 `prompt_mentions` 的旧状态按普通字符串处理，并支持 `@图片N` 的 fallback 解析。
- 画廊图片丢失时工作流仍可打开，但执行时给出可读错误。
- 节点使用固定 16 个图片槽位，前端只改变可见性，不动态改写节点输入 schema。

## 13. 测试计划

所有 Python 测试从 Ryan 包根目录使用 ComfyUI Python 运行：

```powershell
X:/ComfyUI-aki-v2/python/python.exe -m pytest tests/ -q
```

### 13.1 纯函数测试

- 八种官方 aspect ratio 都能得到合法宽高。
- Megapixels 计算结果宽高均为 16 的倍数。
- 自定义宽高会正确四舍五入、clamp 和生成 latent shape。
- `batch_size` 正确反映在 latent 第一维。
- `@图片1`、`@image1` 能按当前有效图片序号解析。
- 资产排序后，带 `asset_id` 的 mention 仍指向同一图片。
- 重名文件不会错误合并 mention。
- 不存在的 mention 会返回清晰错误。
- 没有图片时普通文生图仍然可以执行。
- 没有图片但 Prompt 含 `@` 时会失败并说明原因。

### 13.2 Qwen 执行测试

使用 fake CLIP 和 fake VAE 验证调用协议，不加载完整大模型：

- 无图片、无 VAE。
- 多张图片、无 VAE，确认 `keep_vision` 行为。
- 多张图片、有 VAE，确认 Positive/Negative 都携带 `reference_latents`。
- 含 alpha 图片的 vision/VAE 输入处理。
- 单个 IMAGE 输入为 batch 时只取第一张，和官方节点一致。
- latent channel 数为 64，空间尺寸为目标宽高除以 16。
- Prompt 和 Negative Prompt 的 mention 替换互不污染。

### 13.3 前端契约测试

- 新节点只注册自己的动态图片槽位。
- `image_slot_count` 显示范围为 0–16。
- 画廊上传状态能保存和恢复。
- 外部连接存在时对应画廊格子进入禁用状态。
- `@` 菜单只显示当前有效图片。
- 重新排序后 mention manifest 的 `asset_id` 不变。
- 普通字符串 Prompt 在没有 manifest 时仍可编辑。

### 13.4 官方工作流验收

使用官方 Qwen 2.1 文生图工作流验证替换路径：

1. 用 Ryan 节点替换官方 `Text Encode Qwen Image 2.1`。
2. 删除官方 `ResolutionSelector` 和 `EmptyLatentImage`。
3. 使用 `16:9 (Widescreen)`、`2.0 MP` 和 `batch_size=4`。
4. 将 Positive、Negative 和 Latent 连接到原 KSampler。
5. 确认能正常生成，且输出尺寸和 latent batch 与设置一致。
6. 再添加两张参考图，分别用 `@图片1`、`@图片2` 指定人物和服装职责。

## 14. 验收标准

V1 完成必须满足：

1. 可以从一个 Ryan 节点管理至少两张、最多十六张图片。
2. 图片可以通过内部上传或外部 `IMAGE` 输入提供。
3. Prompt 中输入 `@` 可以选择图片并生成稳定 mention。
4. 图片排序后，已有 mention 仍指向原图片。
5. Qwen 收到的图片顺序和节点槽位顺序一致。
6. `@` 会转换为模型可理解的 `Picture N` 类文本，不把原始 `@` 直接传给 Qwen。
7. 没有 `@` 时，多图工作流仍然保持官方 Qwen 行为。
8. 节点可以独立输出 Positive、Negative 和 Qwen 64 通道 Latent。
9. 节点不包含模型、采样器或采样参数。
10. 官方文生图工作流可以通过删除三个官方节点并替换为一个 Ryan 节点完成迁移。
11. 现有 Ryan 节点的多图输入和前端行为不回归。
12. Python 测试通过，且对画廊文件不存在、mention 失效等错误有明确提示。

## 15. 实现顺序

建议按以下顺序实现：

### 阶段一：后端基础

1. 增加 Qwen Image 2.1 节点注册。
2. 实现输入槽位收集和安全画廊加载。
3. 实现分辨率计算与 Qwen latent 输出。
4. 复用官方 Qwen conditioning 逻辑。
5. 先用普通字符串 Prompt 验证节点能独立运行。

### 阶段二：`@` 引用解析

1. 增加 `asset_id`、`gallery_manifest` 和 `prompt_mentions` 数据结构。
2. 实现 mention 的稳定资源解析。
3. 实现 `@图片N` 和 `@imageN` fallback。
4. 增加失效引用错误和单元测试。

### 阶段三：前端画廊与编辑器

1. 增加 16 槽位动态显示。
2. 增加 H3 风格的图片画廊和上传。
3. 增加画廊排序、删除和外部输入禁用状态。
4. 增加 Prompt/Negative Prompt 的 `@` 自动完成和 chip。
5. 增加工作流保存和恢复。

### 阶段四：集成验收

1. 运行 Ryan 包测试。
2. 做官方 Qwen 工作流静态替换检查。
3. 使用小模型或现有模型进行一次最小文生图验证。
4. 检查无图、单图、多图、VAE、alpha、batch 和失效引用场景。

## 16. 已确认的设计决策

- 采用方案一：内部图片上传/拖拽画廊 + 外部 `IMAGE` 槽位。
- 采用方案 B：官方工作流风格的 aspect ratio + Megapixels + custom width/height + batch size。
- 节点输出 Qwen Image 2.1 专用 latent，替换官方 `EmptyLatentImage`。
- `@` 图片引用是 V1 核心功能。
- `@` 只做图片指代，不筛选或排除未引用图片。
- 通过稳定 `asset_id` 处理排序和工作流恢复。
- V1 不接管采样、模型配置和高级图像控制能力。
