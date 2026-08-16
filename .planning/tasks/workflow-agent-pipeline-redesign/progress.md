# Progress Log

## 2026-08-12

- 用户提供 `F:/trae_project/scene_forge/.agents/skills` 作为参考源。
- 已读取 SceneForge 总控、创意、美术、剧本、表演、分镜、音频、视频 Prompt 及其 output-contract/review/template 文件。
- 确认 SceneForge 的核心优势不是单纯 Prompt 文案，而是：阶段状态机、单一权威阶段文档、稳定实体 ID、对象级 Prompt 索引、Review/确认闸门、下游交接和音频到视频的显式执行链。
- 已将这些结论写入 `findings.md`，未修改业务代码。
- 下一步：把外部能力整合进 Ryan 设计规格；等待用户确认后再进入实现计划和编码。

## 2026-08-12 - SceneForge 能力整合

- 补充梳理 SceneForge 的可选入口阶段：`scene-video-intake`、`scene-topic-gate`、`scene-reference-decider`。
- 结论：入口路由、参考边界、风格确认应作为 Context metadata/Commit gate；不把所有前置 Skill 直接膨胀为常驻 Comfy 节点。
- 补充结论：`scene-performance-director` 的表演层不能丢失；当前建议先作为剧本阶段结构化子交付，后续按使用频率决定是否拆独立 Agent。

## 2026-08-12 - 范围校正

- 用户明确：SceneForge 仅作为专业内容规范、思考维度和质量标准参考，不迁移其流程逻辑。
- 已修正规划边界：保留 Ryan 的 ComfyUI Context/DAG/Chat/Commit/Queue；后续只深化六类 Agent 的内容输出合同与专业质量，不引入 PROJECT_BOARD、CLI 状态机或 SceneForge 11 阶段路由。

## 2026-08-12 - 最小中文产物设计确认

- 用户确认：沿用 Ryan 原有 Workflow Agent 设计，只借鉴外部 Skill 的内容丰富程度和专业思考维度。
- 已确定每个 Agent 只提交一份中文 Canonical 文档；不提交独立英文、Review、Handoff 或思考过程文件。
- 已确定 Prompt 映射：创意可选概念图，美术图像参考，剧本无 Prompt，分镜故事板/关键帧，音频按需音频 Prompt，视频按 `SEG_###` 输出视频 Prompt。
- 已生成正式规格：`docs/superpowers/specs/2026-08-12-workflow-agent-content-contract-design.md`。
- 已生成实施计划：`docs/superpowers/plans/2026-08-12-workflow-agent-content-contract.md`。
- 当前未修改业务代码，未启动浏览器；下一步需按计划进入实现。
 
## 2026-08-12 续做：输出合同与流程 Fixture

- 已新增 `tests/workflow_agent/test_pipeline_contract.py`：用创意、美术、剧本、分镜、音频、视频六阶段最小数据验证下游交接、锁定 ID、Prompt target 精确选择。
- 已补充五类（实际六类） Skill 的最小合格示例：正文 Canonical、按需 `ryan-artifact` Bundle、中文 `text`、`purpose`、`target_ids` 与阶段边界。
- `tests/workflow_agent/test_artifacts.py` 新增 V2 Prompt 单文本与 target 元数据校验用例，并修复测试文件缺失 `unittest` 导入。
- 定向回归：`python -m unittest tests.workflow_agent.test_skill_contracts tests.workflow_agent.test_artifacts tests.workflow_agent.test_pipeline_contract tests.nodes.test_artifact_selector_node tests.nodes.test_workflow_agent_node -q`，52 tests，OK。
- 全量回归：`python -m unittest discover -s tests -q`，128 tests 中 124 个实际通过，4 个导入错误；错误来自环境缺少既有依赖 `aiohttp`、`openai`、`scenedetect`，与本次改动无关。
- `agent-contract.json` 现统一声明 `artifact_output_kinds` 与 `artifact_output_purposes`；六阶段映射为：创意概念图、美术图像参考、剧本无 Prompt、分镜故事板/关键帧、音频按用途、视频按 `SEG_###`。
- `load_skill_contract()` 现在校验 kind/purpose 合同；Commit Prompt 动态注入用途白名单；Commit 解析按 V2 阶段白名单拒绝串类型/串用途产物。
- `RyanWorkflowAgent` 已保持正式 Canonical 正文与各类 Prompt 输出分离；`RyanArtifactSelector` 继续按 `kind/purpose/target_id` 精确取用，默认 Context 只传摘要、锁与交接。
- 定向回归：`python -m unittest tests.workflow_agent.test_skill_contracts tests.workflow_agent.test_artifacts tests.workflow_agent.test_pipeline_contract -q`，21 tests，OK。
- 节点/服务专项回归：`python -m unittest tests.workflow_agent.test_chat_commit tests.workflow_agent.test_routes tests.workflow_agent.test_repository tests.workflow_agent.test_context_view -q`，16 tests，OK。
- Commit Prompt 新增质量底线：要求完整 Canonical 文档、实体/动作/状态/因果绑定，禁止空泛摘要、重复上游、只输出 Prompt 或编造；测试已覆盖该提示注入。
- 完整测试集：`python -m unittest discover -s tests -q` 共发现 130 tests，126 个通过，4 个导入错误；错误均来自环境缺少既有依赖 `aiohttp`、`openai`、`scenedetect`，未触及本次流水线合同代码。
- 代码侧自审完成：六阶段 kind/purpose、V2 解析、Commit 质量规则、Selector 精确映射、默认 Context 摘要边界与 Node 输出索引一致；未启动浏览器，符合项目边界。
- 语法检查：`python -m py_compile ryan_comfy_utils/workflow_agent/artifacts.py ryan_comfy_utils/workflow_agent/skill_contract.py ryan_comfy_utils/workflow_agent/commit_service.py`，通过。

## 2026-08-12 音频导演职责校正

- 用户确认：音频导演的主职责是为视频提示词提供声音参考；独立 `audio_prompt` 仍保留，但仅在需要连接音频生成节点或用户明确要求时输出。
- 已更新 Audio Director Skill：Audio Design Canon 按 `SEG_###` 交接 BGM、Foley-SFX、Ambience、Silence、对白节拍和同步关系。
- 已更新 Video Prompt Director Skill：消费 `audio.design`，把相关声音翻译为绑定动作/反应/镜头节奏的 `audio_sync`，不机械复制完整音频文档。
- 已补充契约测试：视频合同必须消费 `audio.design`；Selector 回归确认视频 Prompt 中保留音频同步内容，同时独立音频 Prompt 仍可单独选择。
- 专项回归：`python -m unittest tests.workflow_agent.test_skill_contracts tests.workflow_agent.test_pipeline_contract tests.workflow_agent.test_artifacts tests.nodes.test_artifact_selector_node -q`，47 tests，OK。

## 2026-08-12 Selector 故障修复

- 复现确认：Selector 的“自动读取最新内容”先从所有 Bundle 中按 priority 取一条 Prompt，因此截图中随机显示了 `PROP_002` 绿光剑图像 Prompt，而不是最新 Agent 的 Canonical 正文。
- 根因确认：前端 `ensureComboWidget()` 插入新的 combo 后没有删除原始 `shot` widget，导致隐藏的新控件之外仍残留一个可见的 `shot` 输入框。
- 已修复：自动模式只返回最新 active Agent 的 Canonical 正文；显式选择 `图像/分镜/关键帧/音频/视频提示词` 时才返回结构化 Prompt。
- 已修复：删除重复 widget；对象控件按类型显示“选择对象 / 选择镜头 / 选择 Segment”，自动模式隐藏对象控件；状态栏明确提示自动模式与 Prompt 模式的区别。
- 回归：`python -m unittest tests.nodes.test_artifact_selector_node tests.workflow_agent.test_pipeline_contract -q`，28 tests，OK；Node 前端语法检查通过。


## 2026-08-12 Selector 画布与对象选项修复

- 复现确认：Selector 在无 Context 初始化时隐藏 `shot` 控件；其原始 `computeSize` 可能为未定义，恢复时未删除临时尺寸函数，后续切换选项会把节点压缩成极小窗口。
- 复现确认：真实美术 Commit 的 `production_design` Bundle V2 合法，包含 7 条 `image_prompt` 输出，目标为 `CHAR_001`、`CHAR_002`、`SCENE_001`、`PROP_001`、`PROP_002`、`PROP_003` 等。
- 修复：显式 Prompt 类型即使暂无上游对象也保留目标下拉控件，按类型显示“上游暂无可选对象 / 镜头 / Segment”占位和状态提示；仅自动模式隐藏目标控件。
- 修复：Selector 增加最小画布尺寸 280×120，并正确恢复被隐藏控件的原始 `computeSize`。
- 修复：Agent 执行结果缓存到页面级 Context 缓存；Selector 初始化时可从已执行的上游 Agent 恢复 Context，不再依赖 Selector 必须先于 Queue 建立监听。
- 前端烟测：无 Context 切换到图像提示词后目标控件保持可见并显示空状态；使用真实 Commit Context 后显示美术图像 Prompt 对象列表。
 
## 2026-08-13 ComfyUI 真实 Queue 断点诊断

- 重启后的 ComfyUI 已加载当前 `Ryan_Comfy_Utils`；HTTP `/history` 显示最新含 Agent → Selector → ShowText 的工作流执行状态为 `success`，无 `node_errors`。
- 最新实际工作流确认：Selector 的 `context` 输入连接 Agent `2`，ShowText 的 `text` 输入连接 Selector `3`；Selector 执行输出与 ShowText 输出均为同一份 `# Production Design Canon` 正文。
- 断点不是 Commit、Queue、RYAN_CONTEXT 连线或后端 Selector 空输出。实际 Selector 参数仍是 `selection: 自动读取最新内容`；该模式按合同返回 Canonical 正文，不会自动挑选第一条结构化 `image_prompt`。
- 使用同一真实 Context 通过 ComfyUI `/prompt` 重放 `selection: 图像提示词`、`target_id: SCENE_001`，得到非空场景图像 Prompt，`status_str=success`，证明显式 Prompt 选择链路后端可用。
- 回归：Selector/Agent/流水线合同共 40 tests，OK；两个前端扩展 `node --check` 通过。
- 当前无需继续修改业务代码；若用户界面仍显示空白，必须保留实际 Queue 后的 `/history/<prompt_id>` 和当前 Selector 的 `selection`/连线状态，不能再用默认模式是否符合“首个 Prompt”预期来代替现场证据。