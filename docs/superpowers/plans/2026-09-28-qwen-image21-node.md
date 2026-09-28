# Ryan Qwen Image 2.1 Node Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Ryan Comfy Utils 中实现一个只负责 Prompt、参考图片、Qwen conditioning 和输出尺寸的 Qwen Image 2.1 组合节点，并提供 H3 风格多图画廊与稳定 `@` 图片引用。

**Architecture:** 以传统 ComfyUI 节点接口包装官方 Qwen Image 2.1 的 tokenizer、conditioning 和 reference latent 行为。后端将图片来源收集、mention 解析、分辨率计算和 latent 构造拆成纯函数；前端使用独立扩展管理 16 个槽位、内部画廊和 Prompt mention 编辑，不修改现有 Ryan 多图扩展的全局行为。

**Tech Stack:** Python 3.12 / ComfyUI bundled runtime / PyTorch / Pillow / ComfyUI `folder_paths` and `node_helpers` / LiteGraph frontend JavaScript / pytest.

---

## 文件结构

### 新增

- `ryan_comfy_utils/nodes/qwen_image21_node.py`：节点注册、图片来源收集、Qwen conditioning、尺寸与 latent 构造。
- `ryan_comfy_utils/web/ryan_qwen_image21.js`：Qwen 节点专用槽位、画廊、上传、排序和 `@` 编辑交互。
- `tests/nodes/test_qwen_image21_node.py`：后端纯函数、节点契约、Qwen fake dependency 测试。
- `tests/frontend/test_qwen_image21_contract.mjs`：可独立导入的前端状态/序列化契约测试；若现有 Node 测试环境不支持浏览器 DOM，只测试无 DOM 的纯函数导出。

### 修改

- `__init__.py`：导入新节点并加入 `NODE_CLASS_MAPPINGS` 与显示名映射。

### 不修改

- 官方 Qwen 节点、官方 Resolution Selector、现有 `ryan_multi_image_slots.js`、已有 Ryan 节点的输入协议。

## Task 1: 基础节点、分辨率与 Qwen Latent

**Files:**

- Create: `ryan_comfy_utils/nodes/qwen_image21_node.py`
- Modify: `__init__.py`
- Test: `tests/nodes/test_qwen_image21_node.py`

- [x] **Step 1: 写尺寸和 latent 的失败测试**

测试 `calculate_qwen_resolution` 覆盖八种比例、Megapixels、16 倍数对齐、边界 clamp；测试 `normalize_custom_resolution` 覆盖非法尺寸；测试 `build_qwen_latent` 覆盖 `[batch, 64, h//16, w//16]` 和 intermediate device。

- [x] **Step 2: 运行第 01 票的失败测试**

运行：

```powershell
X:/ComfyUI-aki-v2/python/python.exe -m pytest tests/nodes/test_qwen_image21_node.py -q
```

预期：因为新模块和函数尚未存在而失败。

- [x] **Step 3: 实现纯函数和节点输入契约**

在新模块中定义官方八种比例映射、`calculate_qwen_resolution(aspect_ratio, megapixels)`、`normalize_custom_resolution(width, height)` 和 `build_qwen_latent(batch_size, width, height)`。所有最终宽高限制为 16–4096，并归一化为 16 的倍数。

节点先注册以下输入：CLIP、VAE 可选、Prompt、Negative Prompt、resolution mode、aspect ratio、megapixels、width、height、batch size、reference resolution、16 个预留 IMAGE 槽位和画廊隐藏字符串状态。V1 纯文本执行时忽略空图片槽位。

- [x] **Step 4: 接入官方 Qwen conditioning 行为**

按官方 Qwen Image 2.1 执行顺序调用 `clip.tokenize(prompt, images=[], keep_vision=True, prevent_empty_text=True)`、`clip.encode_from_tokens_scheduled`，分别产生 Positive 和 Negative Conditioning；没有图片时不生成 reference latents。返回传统节点格式 `(positive, negative, {"samples": latent})`。

- [x] **Step 5: 注册节点并运行测试**

把新节点加入根入口的 class import、node mapping 和 display mapping。运行：

```powershell
X:/ComfyUI-aki-v2/python/python.exe -m pytest tests/nodes/test_qwen_image21_node.py -q
```

预期：新测试全部通过，并确认现有节点导入不受影响。

- [x] **Step 6: 提交第 01 票**

```powershell
rtk git add __init__.py ryan_comfy_utils/nodes/qwen_image21_node.py tests/nodes/test_qwen_image21_node.py
rtk git commit -m "feat: add Qwen Image 2.1 conditioning node"
```

## Task 2: 多图来源与图片画廊

**Files:**

- Modify: `ryan_comfy_utils/nodes/qwen_image21_node.py`
- Create: `ryan_comfy_utils/web/ryan_qwen_image21.js`
- Test: `tests/nodes/test_qwen_image21_node.py`
- Test: `tests/frontend/test_qwen_image21_contract.mjs`

- [x] **Step 1: 写多图收集和文件错误测试**

测试外部 `IMAGE` 优先于同槽位画廊图片、空槽位压缩、按槽位排序、batch 取第一张、文件不存在错误和 16 槽位输入契约。

- [x] **Step 2: 实现安全画廊加载和图片收集**

实现 `collect_image_sources` 和 `load_gallery_image`：外部 tensor 优先；否则验证 annotated filepath，再通过 `folder_paths.get_annotated_filepath` 和 ComfyUI Pillow helper 加载；对图片做 EXIF transpose、参考尺寸缩放和 tensor 转换。保留稳定资源 ID 与当前槽位信息。

- [x] **Step 3: 把收集结果接入官方 Qwen 图像编码**

参考图按槽位顺序生成 `images_vl`。vision 输入对 alpha 做白底合成；没有 VAE 时 `keep_vision=True`。将 `images_vl` 传入 Positive/Negative 的官方 tokenizer 调用，确保没有 `@` 也会传入所有有效图片。

- [x] **Step 4: 实现独立前端槽位与画廊状态**

新前端只匹配 `Ryan Qwen Image 2.1`。预注册 16 个槽位，根据 `image_slot_count` 控制可见性；支持上传、拖拽、删除、排序、稳定资源 ID 和外部连接占用状态。上传只使用 ComfyUI `/upload/image`，保存返回的 annotated filepath 元数据，不保存绝对路径。

- [x] **Step 5: 运行后端和前端契约测试**

运行：

```powershell
X:/ComfyUI-aki-v2/python/python.exe -m pytest tests/nodes/test_qwen_image21_node.py -q
node --test tests/frontend/test_qwen_image21_contract.mjs
```

预期：内部/外部图片来源行为通过，现有前端测试不受影响。

- [x] **Step 6: 提交第 02 票**

```powershell
rtk git add ryan_comfy_utils/nodes/qwen_image21_node.py ryan_comfy_utils/web/ryan_qwen_image21.js tests/nodes/test_qwen_image21_node.py tests/frontend/test_qwen_image21_contract.mjs
rtk git commit -m "feat: add Qwen reference image gallery"
```

## Task 3: `@` 图片引用与稳定绑定

**Files:**

- Modify: `ryan_comfy_utils/nodes/qwen_image21_node.py`
- Modify: `ryan_comfy_utils/web/ryan_qwen_image21.js`
- Modify: `tests/nodes/test_qwen_image21_node.py`
- Modify: `tests/frontend/test_qwen_image21_contract.mjs`

- [x] **Step 1: 写 mention 解析失败测试**

测试 `@图片1`、`@image1`、stable `asset_id`、画廊排序、外部槽位、失效资源、越界序号、Prompt/Negative Prompt 独立解析和无图引用错误。

- [x] **Step 2: 实现后端 mention 解析**

定义 `resolve_image_mentions(prompt, active_assets, manifest)` 和 `replace_prompt_mentions(prompt, resolved_assets)`。优先按稳定 `asset_id` 解析，旧工作流或手写文本按当前紧凑序号 fallback；解析结果替换为 `Picture N`，未知引用抛出包含原始引用和修复建议的 `ValueError`。

- [x] **Step 3: 接入两个 Qwen Prompt**

执行前分别解析 Prompt 和 Negative Prompt，再将替换后的文本传给官方 tokenizer。图片列表保持原有效图片顺序，不因为 mention 数量变化而删图。

- [x] **Step 4: 实现前端 `@` 菜单和 chip 序列化**

Prompt 和 Negative Prompt 各自监听 `@` 输入，显示当前有效图片菜单；选择后插入 `@图片N` chip，并同步普通字符串和 `prompt_mentions` manifest。复制、删除、重新排序和工作流加载必须保留或正确移除稳定 `asset_id`。

- [x] **Step 5: 运行 mention 测试**

运行：

```powershell
X:/ComfyUI-aki-v2/python/python.exe -m pytest tests/nodes/test_qwen_image21_node.py -q
node --test tests/frontend/test_qwen_image21_contract.mjs
```

预期：mention 的稳定绑定、fallback、错误和前端序列化全部通过。

- [x] **Step 6: 提交第 03 票**

```powershell
rtk git add ryan_comfy_utils/nodes/qwen_image21_node.py ryan_comfy_utils/web/ryan_qwen_image21.js tests/nodes/test_qwen_image21_node.py tests/frontend/test_qwen_image21_contract.mjs
rtk git commit -m "feat: add stable Qwen image mentions"
```

## Task 4: VAE Reference Latent 与透明图

**Files:**

- Modify: `ryan_comfy_utils/nodes/qwen_image21_node.py`
- Modify: `tests/nodes/test_qwen_image21_node.py`

- [ ] **Step 1: 写 fake VAE 测试**

使用 fake CLIP 和 fake VAE 验证无 VAE、多图有 VAE、alpha 图片、空槽位和 reference latent 数量；断言 Positive/Negative 都收到 `reference_latents`。

- [ ] **Step 2: 实现参考图预处理**

按 `reference_resolution` 保持比例缩放到约定面积并按 32 对齐；vision tensor 将 alpha 合成白底；VAE 输入保留适合官方编码的图像 tensor。

- [ ] **Step 3: 接入 reference latents**

VAE 存在时对每张有效参考图调用 `vae.encode`，设置官方 `keep_vision` 行为，并使用 `node_helpers.conditioning_set_values(..., append=True)` 同时追加到 Positive 和 Negative。VAE 不存在时保持视觉 token 路径。

- [ ] **Step 4: 运行测试并提交第 04 票**

运行：

```powershell
X:/ComfyUI-aki-v2/python/python.exe -m pytest tests/nodes/test_qwen_image21_node.py -q
```

```powershell
rtk git add ryan_comfy_utils/nodes/qwen_image21_node.py tests/nodes/test_qwen_image21_node.py
rtk git commit -m "feat: add Qwen reference VAE latents"
```

## Task 5: 官方工作流集成与回归验收

**Files:**

- Modify: `tests/nodes/test_qwen_image21_node.py` if integration contracts need expansion
- Modify: `tests/frontend/test_qwen_image21_contract.mjs` if persistence contracts need expansion
- Modify: `.scratch/qwen-image21-node/issues/05-official-workflow-acceptance.md` to record completion evidence

- [ ] **Step 1: 运行全量相关测试**

运行：

```powershell
X:/ComfyUI-aki-v2/python/python.exe -m pytest tests/nodes/test_qwen_image21_node.py tests/nodes/test_image_generator_node.py -q
node --test tests/frontend/test_qwen_image21_contract.mjs
```

- [ ] **Step 2: 做官方工作流静态替换检查**

确认 Ryan 节点可以提供官方工作流 KSampler 所需的 Positive、Negative 和 latent；确认模型、采样器、VAE Decode 和保存节点仍为外部连接。

- [ ] **Step 3: 做 ComfyUI 人工验收**

使用官方 Qwen Image 2.1 工作流验证无图、两张内部图、`@` 引用、重排、外部 `IMAGE`、VAE、透明 PNG、16:9 2 MP 和 batch size 4。

- [ ] **Step 4: 记录验收并提交回归票**

在第 05 票中记录自动化测试和人工验收结果；确认现有 Ryan 多图节点没有前端回归后提交：

```powershell
rtk git add tests/nodes/test_qwen_image21_node.py tests/frontend/test_qwen_image21_contract.mjs .scratch/qwen-image21-node/issues/05-official-workflow-acceptance.md
rtk git commit -m "test: verify Qwen Image 2.1 workflow integration"
```

## 验证命令总表

```powershell
X:/ComfyUI-aki-v2/python/python.exe -m pytest tests/nodes/test_qwen_image21_node.py -q
node --test tests/frontend/test_qwen_image21_contract.mjs
X:/ComfyUI-aki-v2/python/python.exe -m pytest tests/ -q
```

## 自审结果

- 设计规格中的基础节点、尺寸、latent、多图来源、`@`、VAE、前端持久化、错误处理和官方工作流验收均有对应任务。
- 任务顺序与已确认的 1→2→3/4→5 依赖一致。
- 未把采样、模型配置、LoRA 或高级编辑功能放入实施范围。
- 后续任务使用的名称与前置任务保持一致：`collect_image_sources`、`resolve_image_mentions`、`replace_prompt_mentions`、`calculate_qwen_resolution`、`normalize_custom_resolution`、`build_qwen_latent`。
- 当前计划采用 inline execution，因为用户已明确要求开始开发。
