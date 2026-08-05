Status: done

# Gemini 图像接口路由与文本/图像模型类别隔离过滤

## 父问题
`.scratch/comfy-image-generator/PRD.md`

## 要构建什么
1. **Gemini 路由兼容**：本地代理并不支持 Gemini 模型调用标准 `/v1/images/generations`，需通过 `/v1/chat/completions` 多模态方式发起。新节点在检测到模型名含 `gemini` 时自动切入 chat 路由，支持将图片输入拼入 messages `content` 的多模态列表，并兼容解析返回报文 `"choices"[0]["message"]["images"]` 数组下的 Base64 data URL 图像。
2. **文本/图像模型隔离**：在 `llm_profiles.json` 中定义 `"type": "chat"` (如 `grok`, `openai`, `gemini-3.6-flash-high`) 和 `"type": "image"` (如 `gemini-3.1-flash-image`, `grok-imagine-image`, `grok-imagine-image-quality`) 属性。
3. **接口过滤**：修改 `config_loader.py` 中的 `list_profile_names()` 以支持根据 type 属性筛选。更新 `llm_nodes.py` (对话节点类) 过滤展示 `"chat"` 类型 profile，更新 `image_generator_node.py` (生图节点类) 过滤展示 `"image"` 类型 profile，避免模型选择混乱。
4. **运行与测试**：测试 `gemini-3.1-flash-image` 的 txt2img 与 img2img 双向生成，验证 `gemini-3.6-flash-high` 返回纯文本时能够被抛出合理异常捕获。

## 验收标准
- [x] `gemini-3.1-flash-image` 的 txt2img 与 img2img 正常通过，返回对应大小的图像张量批次。
- [x] 对话节点和生图节点展示的 Profile 相互隔离，精准区分。
- [x] 所有单元测试均成功跑通。
