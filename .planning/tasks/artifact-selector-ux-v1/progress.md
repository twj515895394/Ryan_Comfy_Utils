# Progress Log

## 2026-08-11

- 用户确认两层选择器 UX：普通语义选择 + 高级动态选择。
- 已完成设计规格并通过用户确认：`docs/superpowers/specs/2026-08-11-artifact-selector-ux-design.md`。
- 已读取现有 Artifact Selector、Artifact Bundle、Workflow Agent 前端扩展和 Context Inspector 实现。
- 当前阶段：编写实施计划，尚未修改代码。

## 2026-08-11 — Implementation plan complete

- 实施计划已保存：`docs/superpowers/plans/2026-08-11-artifact-selector-ux-v1.md`。
- 计划覆盖 Python 语义映射、旧 Workflow 输入顺序兼容、独立前端扩展、Context 来源节点匹配、动态下拉、空状态、回归测试和静态检查。
- 计划自审已完成：补充了 storyboard 多 kind 顺序选择，明确了高级模式只显示动态选项。
- 尚未修改实现代码；未执行 Git commit；ComfyUI UI 验收需要后续用户明确要求。

## 2026-08-11 — Implementation and verification

- Python 节点追加 `selection`、`source_agent`、`shot_scope`、`shot`，保留旧六字段顺序，并支持中英文语义值、来源/镜头显示值解析和 storyboard → shot prompt 回退。
- 新增 `artifact_selector_extension.js`：普通语义下拉、高级动态下拉、Context 来源节点匹配、空状态和旧字段兼容。
- Workflow Agent Context 事件新增 `nodeId`，Selector 只消费其 `context` 输入来源节点的事件。
- 通过：12 个 Artifact Selector 测试、Workflow Agent 节点及相关上下文/Chat Commit 共 29 个测试；受影响 JS `node --check` 全部通过。
- 完整测试套件执行到 115 个测试时因环境缺少既有依赖 `aiohttp`、`openai`、`scenedetect` 导入失败；未启动浏览器或 ComfyUI，人工 UI 验收保留给用户。


## 2026-08-12 — 用户现场反馈

- 用户反馈：Selector 参数不知道怎么填；连接前面的 Agent 后，Selector → 展示节点没有内容；认为当前流转对普通用户不够简单明了。
- 已确认截图对应当前实现：高级模式仍显示内部 ID 字段；默认自动选择依赖上游已 Queue 且 Commit 中存在合法结构化产物。
- 已运行 Selector 后端专项测试，15/15 通过；当前需要先确认新的用户级交互合同，再修改代码。

- 已生成本地交互讨论稿：`.planning/tasks/artifact-selector-ux-v1/selector-ux-options-20260812.html`，包含 A 自动选择、B 简单+高级、C Agent 直接输出三种方案；未启动浏览器或 ComfyUI。

## 2026-08-12 — A+B 实施完成

- 用户确认采用“默认自动选择 + 可选精确选择”方案。
- `artifact_selector_node.py`：`auto` 先读取最新结构化产物；无 Bundle 时回退到最新 active Entry 正文；显式图像/分镜/视频/镜头选择仍不回退正文。
- `artifact_selector_extension.js`：精确模式继续使用动态下拉，但内部字段始终以中文可读标签显示；产物类型、kind、版本改为可读名称；重复标签不再拼接内部 ID；Context 事件缺少可解析 origin link 时不再静默丢弃。
- `test_artifact_selector_node.py`：新增无 Bundle 时自动读取最新正文的回归测试。
- 验证通过：Selector 16 个测试；Selector + Workflow Agent + Context + Chat/Commit 共 35 个测试；新增 Queue → Context → Selector 默认正文流转测试；Python `py_compile`；受影响前端文件均通过 `node --check`。
- 未启动浏览器或 ComfyUI；保留用户侧重载工作流、Queue 和视觉验收。

## 2026-08-12 — Commit 故障诊断与修复

- 用户反馈 Agent Chat 点击 Commit 后显示 `pi command fail`。
- 已验证：Pi CLI 可执行；最小 RPC 调用成功；携带当前工作流 4 个上下游 Entry 和 2 个图片资产的完整 RPC 调用成功。
- 根因：`commit_service.py` 将 Pi 异常统一压缩为 `Pi COMMIT failed`，真实错误无法到达前端；同时 Commit 文本提取会拼接所有流式文本，可能混入重复过程内容。
- 修复：Commit 错误保留底层异常消息；优先使用 `agent_end.final_text`，仅在没有权威最终文本时回退到 delta/message_update。
- 新增 2 个 Commit 回归测试；Workflow Agent 模块 37 个测试、Pi RPC/路由 5 个测试均通过；修改文件 `py_compile` 通过。
- 未启动浏览器或 ComfyUI；用户侧需刷新后再次点击 Commit，若仍失败现在会显示具体原因。

## 2026-08-12 — Pi RPC 进程边界修复

- 用户现场仍出现 `pi command fail`；复核发现 Windows 下 `subprocess.Popen(..., shell=True)` 会把参数列表交给 `cmd`，导致 RPC Prompt 阶段只收到用户消息事件，无法稳定完成 Agent turn。
- `pi_rpc.py`：Windows 先用 `shutil.which()` 解析 `pi.cmd`/可执行文件，统一使用 `shell=False`；RPC 命令追加 `--no-session` 与 `--approve`，隔离全局会话和无 UI 授权等待。
- 新增命令构造回归断言；真实 Windows 进程 smoke 已收到 `get_state` 成功响应。
- 验证通过：Selector + Workflow Agent + Context + Chat/Commit + Pi RPC + 路由共 43 个测试；3 个受影响前端文件 `node --check`；4 个 Python 模块 `py_compile`；真实 Pi Prompt 仍受 Provider/模型响应限制，未声称 Agent Prompt 完成。
- 未启动浏览器或 ComfyUI；用户侧需重启/刷新 ComfyUI 后重试 Agent Chat → Commit → Queue → Selector。

## 2026-08-12 — Selector 现场问题修复

- 用户确认实施完整修复：普通模式零参数可用、旧字段隐藏、Commit 结构化合同补强、状态提示和回归覆盖。
- `artifact_selector_extension.js`：基础字段改为中文语义标签；默认显示“自动读取最新内容”；镜头相关字段按选择结果隐藏；旧字段同时设置 `hidden`、`options.hidden` 和零尺寸 `computeSize`，高级模式仍可恢复动态下拉。
- `artifact_selector_extension.js`：区分未 Queue、无结构化产物和 invalid Bundle；invalid Bundle 明确提示重新 Commit，自动模式仍提示可读取正文。
- `commit_service.py`：Commit Prompt 明确 `output_id`、`shot_id`、`kind`、`label`、`text`、`prompt`、`priority` 的 JSON 字段和 ID 合法字符，禁止用 `id`/`constraint` 替代正式字段。
- `test_artifact_selector_node.py`：新增完全默认参数和 invalid Bundle 回退正文测试；`test_chat_commit.py`：新增 Prompt 合同字段断言。
- 验证通过：Selector + Workflow Agent + Context + Chat/Commit 共 39 个测试；前端 `node --check`；相关 Python `py_compile`。
- 未启动浏览器或 ComfyUI；用户侧需重载扩展并重新 Commit/Queue 以重建现场 invalid Bundle。
- 补充 `RyanArtifactSelector.OUTPUT_NODE = True`，保证 Selector 作为工作流末端时也会被 Queue 执行；新增终端节点回归断言。
- 最终专项验证：40 个测试通过；Selector 前端 `node --check`；3 个相关 Python 模块 `py_compile`。

## 2026-08-12 — Selector 纯语义筛选改造

- 用户确认 Selector 应只负责从上游 Agent 产物中筛选提示词，不应暴露 UID、Bundle、kind、revision 等内部参数。
- 无需从零重建 Agent Workflow；保留 Agent → Context → Selector → STRING 下游连接。旧 Selector 节点建议删除后重新添加，以清除已序列化的旧 Widget。
- `artifact_selector_extension.js` 已收敛为仅显示“选择提示词”和条件显示的“选择镜头”；旧字段和来源/镜头范围辅助字段始终隐藏，后端仍保留兼容读取。
- 选择器选项：自动读取最新内容、图像提示词、分镜提示词、视频提示词、指定镜头提示词。输出仍为单一 STRING。
- 新增默认自动选择回归覆盖；前端扩展语法检查通过，Selector/Workflow Agent/Context/Commit 共 40 个测试通过。

## 2026-08-12 — Selector 下拉框现场修复

- 根因：Python `INPUT_TYPES` 将 `selection`、`shot` 声明为 `STRING`；前端运行时修改 `widget.type` 不会改变已创建的文本控件渲染。
- 修复：新增字段改为 ComfyUI 原生 `COMBO`；前端对旧 Workflow 中已创建的 STRING widget 做一次兼容替换，并继续动态刷新选项。
- 验证：Selector 21 个测试通过；前端 `node --check` 和 Python `py_compile` 通过。未启动浏览器或 ComfyUI。