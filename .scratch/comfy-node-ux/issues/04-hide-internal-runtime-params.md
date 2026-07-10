Status: ready-for-agent

# 隐藏 ACP 节点内部运行参数：workspace / profile / manifest / session / skill_root

## 父问题
`.scratch/comfy-node-ux/PRD.md`

## 要构建什么
从 `Ryan ACP Universal Agent`、`Ryan ACP Image Prompt Agent`、`Ryan ACP Video Prompt Agent`、`Ryan ACP Image Analyze Agent` 等节点的 INPUT_TYPES 中移除或隐藏以下参数的界面暴露：
- workspace_root
- profile_path
- manifest_path（固定节点可保留默认但不显示）
- session_id
- skill_root（Universal 可选保留但默认隐藏）

这些参数改为节点内部使用默认常量（包内 fixture 或约定路径）。用户界面上不再看到这些字段，也无法在节点上修改。

固定 Prompt 节点（Image/Video Prompt、Analyze）彻底不暴露这些；Universal Agent 保留 skill_id（下拉，由 issue 03 处理），其他运行参数隐藏。

端到端：用户拖出节点后只看到业务相关输入（user_text、style、category 等 + 图片槽位），内部参数由代码默认处理；老 workflow 若连了这些参数可能需清理。

## 验收标准
- [ ] 上述 4 个 ACP 节点界面上不再显示 workspace_root / profile_path / manifest_path / session_id / skill_root
- [ ] 节点执行仍使用正确的默认路径和 profile
- [ ] 固定节点 skill 绑定仍由 manifest 控制
- [ ] 单元测试通过，现有 fixture 仍可工作

## 被阻塞于
- 建议与 issue 03（skill_id 下拉）协调，避免重复暴露 skill_root

## 评论
- 风险：老 workflow 依赖这些参数暴露可能断连，需在发布说明中提示
