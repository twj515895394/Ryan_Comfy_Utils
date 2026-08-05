Status: ready-for-agent

# ComfyUI 图像生成与编辑节点开发及模型分类过滤

## 问题陈述
为了在 ComfyUI 中支持高效的图像生成和图生图/图像编辑工作流，用户提出以下需求：
1. 希望新增一个图片生成节点 `RyanImageGenerator`，它能够支持文本提示词生图，也支持接收图片输入以进行图生图/图像编辑。
2. 该节点需要支持多图输入，最多支持 5 张图片，前端 UI 需要与 `RyanACPUniversalAgent` 的图片输入槽交互保持一致。
3. 该节点能够通过配置文件 `llm_profiles.json` 配置并选择模型，且需要配置本地代理端口 `http://localhost:8317`（使用 API Key `twj123456`），测试并支持三种模型：`gemini-3.6-flash-high`/`gemini-3.1-flash-image`、`grok-imagine-image` 和 `grok-imagine-image-quality`。
4. 为了使界面的下拉选项更加精准，`llm_profiles.json` 中的文本对话模型和图像生成模型需要进行分类隔离，文本聊天节点（LLM Chat）和图像生成节点（Image Generator）各自只能筛选并展示符合其类别的 profile 选项。
5. 针对自制的 12 个 ComfyUI 节点，需要在后端添加功能描述，以便用户在搜索及悬停时能直观了解每个节点的功能。

---

## 用户故事
- 作为 ComfyUI 工作流设计者，我希望能在生图节点中自由切换 Grok 和 Gemini 模型，并在界面上直接拖入多张参考图进行图像编辑。
- 作为用户，我希望选择模型时下拉菜单只展示和当前节点匹配的模型 profile（如生图节点不展示对话模型），使配置更加精准。
- 作为初学者，我希望在搜索节点或悬停在节点上时，能看到清晰的功能介绍描述，了解该节点的作用。

---

## 范围
- 开发新节点 `RyanImageGenerator` 并将其注册进 ComfyUI。
- 修改 `llm_profiles.json` 引入 `"type": "chat"` 与 `"type": "image"` 分类，并更新 `config_loader.py` 对各节点的下拉菜单选项进行过滤。
- 修改代理端 `config.yaml` 授权配置，并在新节点中针对 Gemini 模型的 `/chat/completions` 多模态路由进行定制开发，支持解析返回的 Base64 图像列表。
- 给所有 12 个自定义节点类增加 `DESCRIPTION` 属性。

---

## 验收
- 新节点在 ComfyUI 前端正常加载，且其图片槽动态增减功能正常。
- 下拉框中，聊天/视觉节点只列出 chat 配置文件，生图节点只列出 image 配置文件。
- 文本与图生图实测（运行 `test_image_models.py`）对于 `gemini-3.1-flash-image`、`grok-imagine-image` 和 `grok-imagine-image-quality` 均能正常生成图片张量。
- 所有的 98 个单元测试全部通过。
