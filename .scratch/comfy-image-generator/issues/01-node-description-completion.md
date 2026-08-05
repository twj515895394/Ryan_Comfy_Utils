Status: done

# 自定义节点功能介绍描述补全

## 父问题
`.scratch/comfy-image-generator/PRD.md`

## 要构建什么
由于原有的 12 个 ComfyUI 自定义节点缺乏功能介绍，用户在搜索节点列表时无法了解每个节点的作用。
需要为所有的自定义节点类添加 `DESCRIPTION` 常量属性。在 ComfyUI 后端反射解析时，会将此属性自动填充到节点的描述信息中（`info['description']`），并在前端搜索框与帮助浮窗中显示。

涉及的节点包括：
- `RyanImageAnalyzeAgent`
- `RyanImagePromptAgent`
- `RyanACPUniversalAgent`
- `RyanVideoPromptAgent`
- `RyanBatchVideoLoader`
- `RyanFileExporter`
- `RyanImageBatchSplitter`
- `RyanLLMChat`
- `RyanLLMVisionChat`
- `RyanPromptTemplate`
- `RyanVideoFrameSampler`
- `RyanVideoSceneSplitter`

## 验收标准
- [x] 所有 12 个类均含有 `DESCRIPTION` 属性，且描述准确。
- [x] 在 ComfyUI 加载或单元测试中无任何语法与解析报错。
