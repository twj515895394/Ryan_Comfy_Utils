# Image Generator GPT Image 2 Implementation Plan

**目标：** 让 Ryan Image Generator 的 image profile 显示 `gpt-image-2`，并在 size 下拉框提供 1K/2K/4K 横屏与竖屏尺寸。

**架构：** 沿用现有 `llm_profiles.json` 的 `type: "image"` 分类与 `list_profile_names("image")` 过滤机制；节点将尺寸标签映射为 API 需要的纯 `宽x高` 字符串，不引入新抽象或新依赖。

**技术栈：** Python、ComfyUI 自定义节点、JSON 配置、unittest/mock。

---

### Phase 1：配置与节点输入
**Status:** complete

- [x] 在私有 profile 配置中加入 `gpt-image-2` image profile
- [x] 在示例 profile 配置中同步加入 `gpt-image-2` image profile
- [x] 在 Image Generator size 下拉框加入 1K/2K/4K 横竖屏选项

### Phase 2：测试与验证
**Status:** complete

- [x] 增加输入选项和请求 payload 的行为测试
- [x] 运行图片节点测试及代表性配置验证
- [x] 完成代码自审并记录剩余风险

## Errors Encountered
| Error | Attempt | Resolution |
|---|---:|---|
| `pytest tests/nodes/test_image_generator_node.py -q` failed during collection because `openai` is not installed in the active Python 3.11 environment | 1 | Use syntax/config checks and a controlled test import without changing project dependencies |
