Status: ready-for-agent

# ComfyUI 节点界面反馈优化与视频预览

## 问题陈述
用户在将 Ryan_Comfy_Utils 节点安装到 ComfyUI 后进行界面测试时，提出了 5 点具体反馈：
1. Ryan Prompt Template 节点的 `template_source` 枚举值含义不清晰，需要界面显示中文（逻辑保持英文），且希望有默认模板目录，自动加载按名称排序的第一个文件。
2. 涉及图片输入的节点默认显示 10 张，与设计不符。应默认显示 2 张，支持指定张数（≥1），并通过“Update”按钮刷新可见输入数量。
3. 技能 ID（skill_id）应为下拉选择，自动从节点默认 skill 存放目录读取可用项。
4. 多个 ACP 节点暴露 workspace_root、profile_path、manifest_path、session_id、skill_root 等内部运行参数，这些不应显示给用户，且不可修改。
5. Ryan Batch Video Loader 节点无法预览视频。需要类似官方视频加载节点的预览功能：显示视频、隐藏/显示视频、播放/暂停。

这些是节点定义层（Python INPUT_TYPES + JS 扩展）的 UX 问题，不涉及 ACP runtime 核心逻辑。

## 用户故事
- 作为 ComfyUI 用户，我希望节点选项清晰易懂（中文标签、合理默认），以便快速上手。
- 作为用户，我希望图片输入数量可控且刷新受控，避免界面混乱。
- 作为用户，我希望 skill 选择是受限的下拉，而不是自由文本，减少错误。
- 作为用户，我不希望看到或修改内部实现细节参数。
- 作为视频工作流作者，我希望在节点上直接预览视频内容，而不仅是输出帧批次。

## 范围
- 仅修改节点界面与交互（`nodes/*.py` 的 INPUT_TYPES、默认值；`web/*.js` 的 widget 行为）。
- 不改动 runtime、路径安全、导出、ACP 契约。
- 保持向后兼容性尽可能（老 workflow 可能需调整隐藏参数连接）。
- 视频预览需研究 ComfyUI DOM widget 模式（参考其他 custom nodes 如 comfyui-easy-use）。

## 非目标
- 改变 ACP 固定节点 vs Universal 的 skill 绑定语义。
- 添加新的后端视频解码能力。
- 全局主题或 ComfyUI 核心修改。

## 验收
- 启动 ComfyUI 后界面反馈全部符合描述。
- 各节点可正常执行（使用现有 fixture）。
- 单元测试与集成冒烟通过。
