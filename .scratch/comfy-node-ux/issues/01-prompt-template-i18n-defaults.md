Status: ready-for-agent

# Ryan Prompt Template：template_source 中文化 + 默认模板目录自动首选

## 父问题
`.scratch/comfy-node-ux/PRD.md`

## 要构建什么
将 `Ryan Prompt Template` 节点的 `template_source` 枚举从纯英文改为界面中文（“内置模板”“自定义目录”），逻辑值保持 `built_in` / `custom_dir`。

同时在节点包内提供默认 prompts 目录（`ryan_comfy_utils/prompts` 或用户确认的位置），启动时若未指定 custom_dir，则自动扫描该目录，按文件名排序后默认选中第一个文件作为 template_name。

端到端：用户在 ComfyUI 看到友好的中文选项；默认无需配置即可使用内置模板；切换到 custom_dir 时可指定目录并列出该目录下的模板文件。

## 验收标准
- [ ] `template_source` 在 ComfyUI 下拉显示中文标签，实际传入值仍为英文
- [ ] 节点包内存在默认 prompts 目录，至少包含当前 video_frame_analysis.md
- [ ] 未指定 prompt_dir 时，template_name 默认加载按名称排序的第一个文件
- [ ] 切换 source 或目录后，template_name 列表正确刷新
- [ ] 节点执行正常，返回正确 prompt 内容

## 被阻塞于
无 - 可以立即开始
