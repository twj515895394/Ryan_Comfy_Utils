# Ryan Artifact Selector 用户体验设计规格

**日期：** 2026-08-11  
**状态：** 已确认并实施

## 1. 问题

当前 `Ryan Artifact Selector` 将 `source_agent_uid`、`artifact_type`、`output_id`、`shot_id`、`kind` 和 `revision` 直接显示为文本框。它暴露了内部数据模型，用户不知道可填写的值，也无法从已连接的 `RYAN_CONTEXT` 获得可发现的选择项。

## 2. 目标

1. 普通用户不需要了解 UID、Bundle schema 或内部 `kind`。
2. 选择器默认可直接工作，不依赖手工输入 ID。
3. 支持从上游 Context 中选择 Agent、产物和镜头。
4. 保留任意 Artifact Bundle 精确选择能力，但放入精确模式。
5. 旧 Workflow 的内部字段仍能被后端读取，避免已有图失效。
6. 显式选择图像、分镜、视频或镜头时不返回其它类型正文；默认自动模式在没有结构化产物时读取最新 Agent 正文，避免下游空白。

## 3. 非目标

- 不在本次改动中重新设计 Artifact Bundle 数据合同。
- 不自动创建 ComfyUI 节点或自动改写用户的 DAG 连接。
- 不允许普通模式通过文本框输入内部 ID。
- 不把所有上游正文自动拼接为输出。

## 4. 普通模式

节点保留 `context` 输入插槽，并将选择参数改成用户可理解的语义控件：

| 控件 | 默认值 | 行为 |
| --- | --- | --- |
| 来源 Agent | `自动（最新有效来源）` | 单一来源时自动锁定；多来源时显示 Agent 名称 |
| 产物类型 | `自动选择` | 提供图像提示词、分镜提示词、视频提示词、首个结构化产物、指定镜头提示词 |
| 镜头范围 | `全部镜头` | 仅在选择指定镜头提示词时启用 |
| 镜头 | `自动` | 从当前 Context 的 shots 动态生成，显示 label 和摘要，不显示 shot_id |

普通模式不显示 `source_agent_uid`、`artifact_type`、`output_id`、`shot_id`、`kind` 或 revision 文本输入。

### 4.1 普通模式语义映射

- `图像提示词`：优先选择 kind 为 `image_prompt` 的 output。
- `分镜提示词`：优先选择 kind 为 `storyboard_sheet_prompt` 的 output；没有时允许 `shot_prompt` 作为兼容候选。
- `视频提示词`：优先选择 kind 为 `video_prompt` 的 output。
- `首个结构化产物`：按 Artifact Bundle priority 选择第一个 output 或 shot。
- `指定镜头提示词`：从 shots 中按来源和镜头下拉值选择。
- `自动选择`：沿用后端现有优先级，取最新有效 Bundle 中的首个可用输出。

所有语义选择均只读取最新有效 Entry；不存在匹配时输出空字符串并显示“未找到匹配产物”。

## 5. 精确模式

节点提供一个“精确选择”折叠入口。展开后仍然只显示用户可读的动态下拉，不显示 UID、output_id、shot_id、kind 或 revision 等内部字段：

- 来源 Agent：Context 中的 Agent 名称，无名称时使用可读 UID 作为最后回退。
- 产物类型：当前来源下可用 Bundle 的人类可读类型。
- 输出：当前 Bundle 中 output 的 `label · 类型`。
- 镜头：当前 Bundle 中 shot 的 `label · 类型`。
- 产物类型过滤：显示“自动”或当前选择范围内的类型名称。
- 版本：显示“最新”或“第 N 版”，不显示裸 revision 数字。

精确模式只是给需要指定某个产物的用户使用；内部值由前端写入隐藏兼容字段，用户不需要填写或理解它们。

动态选项来自已经接收到的 Context。首次 Queue 前没有动态数据时，显示“先运行上游 Agent，完成后这里会出现可选产物”，但默认自动模式仍可保存和执行。

## 6. 节点状态与数据流

1. 用户在上游 Agent 中完成 Chat → Commit，生成正式 Canonical Entry 和可选结构化产物。
2. 用户 Queue Workflow；`Ryan Workflow Agent` 通过 `context` 输出包含已提交 Entry 的 `RYAN_CONTEXT`。
3. Artifact Selector 从执行结果更新来源、Bundle、output 和 shot 选项。
4. 默认模式自动选择最新有效 Bundle 的首个适用产物；用户只需在“我要输出什么”中选择语义类型。
5. 用户选择精确模式后，前端把可读选项映射为隐藏的规范化值；Python 节点继续使用确定性选择逻辑。
6. 选择器不启动 Pi、不调用 LLM、不修改 Context；节点输出仍为单个 `STRING`。

连线只建立数据关系，不代表上游已经产生 Context；如果上游未 Commit 或未 Queue，节点必须显示下一步提示，而不是让用户猜参数。

## 7. 兼容性

- 后端可继续接受旧 Workflow 序列化的内部字段。
- 旧字段在 UI 中始终作为隐藏兼容值，不作为可见高级字段。
- 旧节点没有 Context 时，保留现有空字符串行为。
- 普通和精确模式不改变已有精确选择器的后端匹配规则，只增加用户可读映射层。

## 8. 错误与空状态

- 无上游 Context：显示“请先连接并运行上游 Agent”。
- 已连接但尚未 Queue：显示“先运行上游 Agent，完成后这里会出现可选产物”。
- Context 中没有已提交 Entry：显示“上游还没有 Commit 内容，请先打开 Agent 完成 Commit”。
- Context 无 Artifact Bundle：显示“上游已提交，但没有可选择的结构化产物”。
- 当前选择无匹配：显示“没有找到符合条件的产物”，输出空字符串。
- Context 更新后当前精确选项失效：自动回到“自动选择”，显示“上游产物已更新，已恢复自动选择”。
- 动态选项刷新失败：保留上次有效选项，节点仍按已保存的规范化值执行。


## 9. 验收标准

1. 节点普通视图不再出现六个内部 ID 文本框。
2. 新用户只通过下拉选项即可完成图像、分镜、视频提示词选择。
3. 多 Agent Context 能显示可读 Agent 名称。
4. 指定镜头时能看到 label，不需要输入 `shot_id`。
5. 首次未 Queue 时有明确空状态，不阻塞普通模式。
6. 高级模式支持任意有效 output 和 shot 的动态选择。
7. 无匹配时输出空字符串并显示状态，不发生正文回退。
8. 旧 Workflow 的内部字段仍能正确执行。
9. Python 节点测试覆盖语义映射、动态值失效、空 Context、无 Bundle、无匹配和旧字段兼容。
10. 前端语法检查通过，且不改变 Workflow Agent、Artifact Bundle 和 Context Inspector 的既有行为。
