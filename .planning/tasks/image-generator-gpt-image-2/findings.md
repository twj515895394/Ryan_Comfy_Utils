# Findings

- Image Generator 节点通过 `list_profile_names("image")` 生成 profile 下拉项。
- 当前 `ryan_comfy_utils/config/llm_profiles.json` 没有 `gpt-image-2`，所以界面不会显示该 profile。
- 运行时配置优先级：`RYAN_COMFY_UTILS_PROFILE_PATH`、仓库内 `llm_profiles.json`、`llm_profiles.example.json`。
- 节点当前把 `size` 直接放入 `/images/generations` payload；`custom` 才拼接自定义宽高。
- 官方 GPT Image 2 尺寸契约：`1024x1024`、`1536x1024`、`1024x1536`、`2048x2048`、`2048x1152`、`3840x2160`、`2160x3840`、`auto`，并要求边长为 16 的倍数、最长边不超过 3840、总像素不超过 8,294,400。
- 本次用户补充要求 1K 横竖屏；采用 `1024x1536` 与 `1536x1024`。2K 采用 `2048x1152` 与 `1152x2048`；4K 采用 `3840x2160` 与 `2160x3840`。
