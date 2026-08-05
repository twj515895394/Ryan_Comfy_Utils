Status: done

# RyanImageGenerator 新节点开发与本地代理配置鉴权

## 父问题
`.scratch/comfy-image-generator/PRD.md`

## 要构建什么
1. 开发并注册全新的 `RyanImageGenerator` 节点，支持接收文本 Prompt 生图及图生图编辑。
2. 继承已有的多插槽图片输入机制，在前端 `ryan_multi_image_slots.js` 中将新节点名称加入匹配集合，使用户可以在界面上点击 "Update" 动态调节 1~5 个图片输入槽。输入的多张图片将在后端转化为 Base64 strings 作为列表传给 API payload。
3. 修改本地代理 `cli-proxy-api.exe` 配置文件 `config.yaml`，将用户指定的 API Key `twj123456` 和 `sk-twj123456` 加入 `api-keys` 列表，并重启代理服务，解决原本报 `401: Invalid API key` 导致无法调用的鉴权问题。
4. 在 `llm_profiles.json` 中增加对应三个测试模型的 Profile 配置：
   - `gemini-3.6-flash-high`
   - `grok-imagine-image`
   - `grok-imagine-image-quality`
5. 支持自适应解析 standard OpenAI 响应结构下的 `url` 和 `b64_json` 图像，转换为 ComfyUI `IMAGE` 张量批次输出。

## 验收标准
- [x] `RyanImageGenerator` 节点能在 ComfyUI 下拉及搜索中被成功实例化。
- [x] 前端 UI 图片插槽动态调整功能正常工作。
- [x] 调用代理接口鉴权成功，不再抛出 401 错误。
- [x] `grok-imagine-image` 和 `grok-imagine-image-quality` 的文本生图及图生图编辑在 `/v1/images/generations` 下测试成功。
