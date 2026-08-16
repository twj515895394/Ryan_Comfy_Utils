# Findings & Decisions

## Existing Implementation

- `ryan_comfy_utils/nodes/artifact_selector_node.py` 当前 REQUIRED 输入是 `source_agent_uid`、`artifact_type`、`output_id`、`shot_id`、`kind`、`revision`，这些字段直接生成 ComfyUI 文本框/数值框。
- 该节点已经具备确定性选择逻辑：只读取 active Entry 的 Artifact Bundle；可按 output、shot、kind、revision 过滤；无匹配返回空字符串。
- `ryan_comfy_utils/workflow_agent/artifacts.py` 提供 `RyanArtifactBundle`、`RyanArtifactOutput`、`RyanArtifactShot` 解析，以及 `artifact_outputs` / `artifact_shots`。
- `ryan_comfy_utils/nodes/workflow_agent_node.py` 已通过 `context` 输出包含最新 Commit 的 `RYAN_CONTEXT`。
- `ryan_comfy_utils/web/workflow_agent/node_extension.js` 已有 ComfyUI 节点扩展、executed 事件桥接和动态 widget 控制模式，可沿用但应为 Artifact Selector 增加独立职责边界。
- `ryan_comfy_utils/web/workflow_agent/context_inspector.js` 已能从 Entry metadata 的 `artifact_bundle` 读取 outputs/shots，说明前端已有同一份数据的展示解析逻辑。

## UX Decisions

- 普通模式使用语义选择，不暴露内部 ID。
- 高级模式使用从当前 Context 动态生成的下拉选项。
- Agent、Bundle、Output、Shot 显示 label/name；内部 ID 只作为 widget value 保存。
- 语义选择映射：image_prompt -> 图像提示词；storyboard_sheet_prompt/shot_prompt -> 分镜提示词；video_prompt -> 视频提示词；首个按 priority；shot_prompt -> 指定镜头。
- `revision` 普通模式固定 latest；高级模式才允许 latest/现有 revision。
- 无 Context、无 Bundle、无匹配分别显示可理解的状态，并坚持返回空字符串。

## Compatibility

- 旧 Workflow 可能仍携带旧内部字段，后端 `run()` 需要继续接受并优先处理这些值，或由前端加载时转换成新语义值。
- 不改变 Artifact Bundle 合同，也不让 selector 启动 Pi/LLM。

## 2026-08-12 用户现场反馈与新调查

- 截图中的普通模式虽然已经显示中文下拉，但“高级选择”仍暴露 `source_agent_uid`、`artifact_type`、`output_id`、`shot_id`、`kind`、`revision`；这与“普通用户不需要理解内部 ID”的目标冲突。
- 现有默认 `selection=auto` 只读取 `metadata.artifact_bundle` 中的结构化 output/shot，不会读取 Entry 正文。上游 Agent 没有成功 Commit、Commit 没有合法 `ryan-artifact` block、或 Context 尚未 Queue 到 Selector 时，输出必然是空字符串。
- `Ryan Workflow Agent` 的 Queue 节点确实输出 `RYAN_CONTEXT`，但它只把当前 Agent 的 latest Commit 追加到 Context；Queue 不会替代 Chat/Commit。截图把“连接线”与“已有可选产物”混在了一起，当前 UI 没有把前置条件讲清楚。
- 当前前端的动态选项依赖 `ryan-workflow-agent-context` 执行事件，并按 `context` 输入 link 的 origin node ID 过滤；只有 Queue 后上游节点执行并发出事件，Selector 才能刷新候选项。
- 已运行 `python -m unittest tests.nodes.test_artifact_selector_node -v`：15 个现有后端选择测试通过，但这些测试没有覆盖“用户未 Commit/无 artifact bundle 时的可理解提示”和端到端 Queue → Selector 反馈。

## 当前根因假设（待与用户确认目标后验证）

1. **高概率：交互设计仍以内部数据模型为中心。** 高级模式把 UID/ID 重新展示给用户，用户自然无法判断如何填写；默认值也没有告诉用户“应先 Queue + Commit”。
2. **高概率：上游数据前置条件未被产品化。** Selector 设计成“结构化产物读取器”，但用户期待它直接拿到前一个 Agent 的最终文本；若上游只是连线或未 Commit，空字符串是当前合同的确定性结果。
3. **中概率：事件刷新边界导致已执行 Context 没被 Selector 看到。** Selector 只接受匹配 origin node ID 的事件；若 ComfyUI 重载图后 link/origin ID 不一致，候选项不会更新，即使 Queue 已执行。
