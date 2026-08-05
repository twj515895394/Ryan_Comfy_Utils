Status: done

# RyanVideoGenerator 节点类注册与插槽交互开发

## 父问题
`.scratch/comfy-video-generator/PRD.md`

## 要构建什么
1. 在 `__init__.py` 中引入并注册新节点 `RyanVideoGenerator`，显示名称为 `"Ryan Video Generator"`。
2. 在前端 `ryan_multi_image_slots.js` 中将新节点名称加入 `RYAN_MULTI_IMAGE_NODES` 匹配列表，以激活 1~5 张图片插槽的动态增减 UI。
3. 创建后端接口节点类 `RyanVideoGenerator`：
   - 定义 `INPUT_TYPES`：包括 `profile` (使用 `list_profile_names("image")` 过滤下拉框)、`model_override`、`prompt`、`aspect_ratio`、`resolution`、`duration` (整型，范围 1..15)、`polling_interval` (整型，默认5)、`extra_body_json` 和可选的 10 个图片输入插槽。
   - 定义 `RETURN_TYPES` 为 `("IMAGE", "STRING")`，对应 `images` 和 `video_path`，`FUNCTION = "generate"`。
4. 扁平化槽位张量，转为 PIL 并限制为最多 5 张参考图：
   - 如果槽位无输入（文生视频），不传入任何参考图。
   - 如果槽位只有 1 张输入（首帧生视频），保存为单图结构。
   - 如果槽位有 >1 张输入（多参考图生视频），保存为多参考图结构列表。

## 验收标准
- [x] 节点可在 ComfyUI 顺利搜索并拉出。
- [x] 动态图片槽前端“Update”交互与 `RyanImageGenerator` 保持高度一致，正常调整可见槽数。
- [x] 节点 INPUT_TYPES 中的 `profile` 仅展示 `"type": "image"` 的模型配置，实现精准过滤。
