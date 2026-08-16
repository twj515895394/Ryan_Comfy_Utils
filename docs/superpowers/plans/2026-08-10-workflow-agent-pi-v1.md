# Ryan Workflow Agent V1 Implementation Plan

> **For agentic workers:** 使用垂直切片逐项实施；每个切片完成后运行其模块测试，再进入下一个依赖阶段。

**Goal:** 在原生 ComfyUI 中交付一个以 Pi 为 Runtime 的 Generic Ryan Workflow Agent：Workflow / Agent Session 隔离，Chat 与 Commit 分离，RYAN_CONTEXT 沿 DAG 传播，右侧 Workspace 可用且不破坏现有节点。

**Architecture:** 现有 ACP 保持统一结果契约，并通过 Pi Profile 迁移到 Pi；新 Workflow Agent 复用 Skill Loader、Pi Runner 和文件 workspace。`workflow_id + agent_uid` 是 Session 主键，Pi 原生 Session JSONL 负责多轮缓存，Ryan state / Commit / Context 负责业务语义。Generic Agent Node 只在 Queue 中合并当前有效 Context 和最新 Commit，不调用 LLM；右侧 Panel 通过 HTTP API + ComfyUI WebSocket 调用 Pi RPC。

**Tech Stack:** Python 3、ComfyUI PromptServer、aiohttp、Pi CLI、JSON/JSONL、现有 unittest、原生 ComfyUI Web Extension。

---

## 决策基线

- 现有 ACP 节点默认使用 Pi `--mode text`；新 Workflow Agent 使用 Pi `--mode rpc`。
- `local_claude_cli.json` 仅作为显式回滚 Profile 保留，不自动 fallback。
- Pi 使用 `--no-context-files`、显式 `--skill`、Ryan System Prompt、完整工具权限；工作目录限定到当前 Agent Session 目录。
- Provider / Model 使用 Pi 全局默认，不在项目 Profile 固定。
- Workflow ID 存在 `extra.ryan_agent.workflow_id`；Save As / Duplicate 生成新 Workflow ID。
- Agent ID 是隐藏 Widget；复制节点或更换 Skill 生成新 Agent ID。
- 固定 8 个 Context 输入和 10 个图片输入；视频/文档使用多行路径。
- Context 只保存各 `source_agent_uid + kind` 的当前有效 Entry；Commit 正文只保留最新，轻量 lineage 索引保留来源。
- 图片、文本类文档、视频 V1 实际可消费；音频入口保留并禁用。
- Commit 不自动 Queue；Stop 保留 Draft；Panel 关闭不终止后台生成。

---

## Issue 01 — Pi Runner 兼容迁移

**类型：** AFK
**依赖：** 无
**目标：** 不改变现有 ACP 节点输入输出契约，将默认外部 Runner 从 Claude 切换到 Pi。

**Files:**
- Create: `ryan_comfy_utils/acp/pi_runner.py`
- Create: `ryan_comfy_utils/acp/fixtures/profiles/local_pi.json`
- Modify: `ryan_comfy_utils/acp/contracts.py`
- Modify: `ryan_comfy_utils/acp/runtime.py`
- Modify: `ryan_comfy_utils/nodes/acp_nodes.py`
- Modify: `__init__.py`（仅在需要保持注册兼容时）
- Create: `tests/acp/test_pi_runner.py`
- Modify: `tests/acp/test_contracts.py`
- Modify: `tests/acp/test_runtime.py`

**Implementation steps:**

1. 扩展 Profile 读取和校验，使 `runner=pi_cli` 可以声明 `mode=text`、`no_context_files`、`use_skill_flag`、`tool_policy=full`，同时兼容现有 Profile 字段。
2. 实现 Pi 命令构造：文本模式包含 `-p --mode text --no-context-files --skill <skill_directory> --system-prompt <ryan_prompt>`；不向命令行写入密钥；工作目录使用传入的 Session 目录。
3. 将 `DEFAULT_PROFILE_PATH` 切换到 `local_pi.json`，保留 `local_claude_cli.json` 不删除。
4. 保持 `_parse_and_validate_result()` 的 stdout fallback 和 `outputs.response_text` 映射不变。
5. 增加 Pi CLI 能力探测：命令存在、帮助文本包含 `--mode`、`--no-context-files`、`--skill`；失败抛出可读错误，不自动回退。
6. 为非零退出码、超时、纯文本输出、显式 `result.json`、Skill 路径和 Profile 加载增加测试。

**Verification:**

```bash
python -m unittest tests.acp.test_pi_runner tests.acp.test_contracts tests.acp.test_runtime -v
```

预期：现有 ACP 结果字段不变；Pi 配置可加载；Claude Profile 仍可显式加载。

---

## Issue 02 — Workflow / Agent Scope 与最小持久化

**类型：** AFK
**依赖：** 无
**目标：** 建立 `workflow_id + agent_uid` 作用域、Pi Session 目录和 Ryan state，不引入数据库。

**Files:**
- Create: `ryan_comfy_utils/workflow_agent/__init__.py`
- Create: `ryan_comfy_utils/workflow_agent/identity.py`
- Create: `ryan_comfy_utils/workflow_agent/repository.py`
- Create: `ryan_comfy_utils/workflow_agent/state.py`
- Create: `tests/workflow_agent/test_identity.py`
- Create: `tests/workflow_agent/test_repository.py`

**Implementation steps:**

1. 定义并校验目录布局：

```text
output/acp_workspace/workflows/<workflow_id>/agents/<agent_uid>/
├── pi-session.jsonl
├── state.json
├── commits/latest.json
├── lineage.jsonl
└── assets/
```

2. 提供安全的 ID 生成和路径组件校验，禁止 `..`、绝对路径和路径分隔符逃逸。
3. 提供 Workflow ID 读取/生成函数，约定来源是 `extra.ryan_agent.workflow_id`；不以文件名或 ComfyUI Node ID 推导。
4. 提供 Agent state 读写：`skill_id`、`agent_name`、`agent_uid`、`draft`、`status`、`commit_revision`、`latest_entry_id`。
5. 提供 Pi Session 路径、Commit latest、lineage index 和 assets 目录解析。
6. 实现 Save As / Duplicate 的新 Workflow ID 规则和节点复制新 Agent ID 的纯函数，供前端/后端调用。

**Verification:**

```bash
python -m unittest tests.workflow_agent.test_identity tests.workflow_agent.test_repository -v
```

预期：不同 Workflow / Agent 路径完全隔离；重启后 state 可恢复；非法 ID 被拒绝。

---

## Issue 03 — RYAN_CONTEXT 与 Generic Agent Queue Slice

**类型：** AFK
**依赖：** Issue 02
**目标：** 在 ComfyUI 中放置、连线、保存和执行一个 Generic Agent Node，并输出当前有效 Context；Queue 不调用 Pi。

**Files:**
- Create: `ryan_comfy_utils/workflow_agent/models.py`
- Create: `ryan_comfy_utils/workflow_agent/context_merge.py`
- Create: `ryan_comfy_utils/workflow_agent/context_select.py`
- Create: `ryan_comfy_utils/nodes/workflow_agent_node.py`
- Modify: `__init__.py`
- Create: `ryan_comfy_utils/web/workflow_agent/node_extension.js`
- Create: `tests/workflow_agent/test_context_models.py`
- Create: `tests/workflow_agent/test_context_merge.py`
- Create: `tests/nodes/test_workflow_agent_node.py`

**Implementation steps:**

1. 定义 `RyanContext`、`RyanContextEntry`、`RyanAssetRef` 和轻量 `RyanLineageRef` 的 JSON-safe 模型；禁止二进制、Tensor、文件句柄和 base64。
2. 实现固定 8 路 Context merge：同 Workflow 校验、Entry/Asset 去重、当前有效 revision、稳定排序、冲突保留和 lineage 索引。
3. 实现 Context Selector：每个 `source_agent_uid + kind` 只取最新有效正文，同时保留来源和 revision。
4. 实现 `RyanWorkflowAgent` 节点：固定 `context_01..context_08`、`image_01..image_10`、`workflow_id`、`agent_uid`、`commit_revision` 隐藏字段和 `context` 输出。
5. Queue 执行只读取上游 Context、读取 `latest.json`、追加当前 Commit，不启动 Pi，不触发 Chat。
6. 注册节点和最小 Node UI；节点先保持朴素，但可显示 Agent 名称、Skill、状态、revision 和打开聊天按钮。
7. 增加串行、fan-in、fan-out、diamond、跨 Workflow 和无 Commit 测试。

**Verification:**

```bash
python -m unittest tests.workflow_agent.test_context_models tests.workflow_agent.test_context_merge tests.nodes.test_workflow_agent_node -v
```

预期：A→B、A/B/C→D 和 diamond 图输出正确；跨 Workflow 抛明确错误；Queue 不执行外部 CLI。

---

## Issue 04 — Workflow Agent Chat / Commit / RPC Slice

**类型：** AFK
**依赖：** Issue 01、Issue 02、Issue 03
**目标：** 打通一个 Agent 的多轮 DISCUSS、RPC 流式、Stop、幂等 Retry 和 COMMIT 业务闭环。

**Files:**
- Create: `ryan_comfy_utils/workflow_agent/chat_service.py`
- Create: `ryan_comfy_utils/workflow_agent/commit_service.py`
- Create: `ryan_comfy_utils/workflow_agent/pi_rpc.py`
- Create: `ryan_comfy_utils/workflow_agent/routes.py`
- Modify: `ryan_comfy_utils/acp/__init__.py`（复用入口时）
- Create: `tests/workflow_agent/test_chat_service.py`
- Create: `tests/workflow_agent/test_commit_service.py`
- Create: `tests/workflow_agent/test_pi_rpc.py`
- Create: `tests/workflow_agent/test_routes.py`

**Implementation steps:**

1. 实现 `DISCUSS` 请求：读取 Pi Session、当前有效上游 Context、Assets 和用户消息，启动 Pi RPC，并把事件发布到 ComfyUI WebSocket。
2. 记录 request/message ID，保证 Retry 不重复写用户消息；Stop 终止当前 Pi 进程并保留已生成部分为 Draft。
3. 实现 `COMMIT` 请求：使用同一 Agent Session、最新上游 Context 和关联 Assets 调用 Pi COMMIT；读取 Markdown 结果；根据 `agent-contract.json` 生成当前最新 Entry、递增 revision 和 lineage index。
4. 实现 Reset：清理私有 Pi Chat 和 Draft，但保留 latest Commit、Asset 和 DAG Context。
5. 实现 `upstream_changed`：比较当前 Commit 依据的 lineage 与最新上游 Entry IDs，不自动重跑或覆盖。
6. 注册 PromptServer HTTP 路由和 WebSocket 事件；错误状态统一为 `error`，不泄露 API Key、完整命令或不必要的本机路径。
7. 为多轮 Chat、Commit 前不可见、Commit 后可见、Stop、Retry、Reset、上游更新和跨 Workflow 隔离写测试。

**Verification:**

```bash
python -m unittest tests.workflow_agent.test_chat_service tests.workflow_agent.test_commit_service tests.workflow_agent.test_pi_rpc tests.workflow_agent.test_routes -v
```

预期：同一 Agent 三轮 Chat 连贯；Stop 保留 Draft；Commit 才更新 latest Context；RPC 事件可被 WebSocket 消费。

---

## Issue 05 — 功能完整的右侧 Workspace Slice

**类型：** AFK
**依赖：** Issue 03、Issue 04
**目标：** 交付视觉朴素但功能完整的右侧 Agent Workspace，不等待最终视觉 Polish。

**Files:**
- Create: `ryan_comfy_utils/web/workflow_agent/index.js`
- Create: `ryan_comfy_utils/web/workflow_agent/panel_manager.js`
- Create: `ryan_comfy_utils/web/workflow_agent/agent_panel.js`
- Create: `ryan_comfy_utils/web/workflow_agent/state_store.js`
- Create: `ryan_comfy_utils/web/workflow_agent/api_client.js`
- Create: `ryan_comfy_utils/web/workflow_agent/context_inspector.js`
- Create: `ryan_comfy_utils/web/workflow_agent/message_list.js`
- Create: `ryan_comfy_utils/web/workflow_agent/composer.js`
- Create: `ryan_comfy_utils/web/workflow_agent/attachment_tray.js`
- Create: `ryan_comfy_utils/web/workflow_agent/commit_bar.js`
- Create: `ryan_comfy_utils/web/workflow_agent/styles.css`
- Modify: `ryan_comfy_utils/web/workflow_agent/node_extension.js`

**Implementation steps:**

1. 建立固定右侧 Panel 容器，默认宽度 480px，支持 resize、close、restore；单击保持 Canvas 原生选中，双击或节点按钮打开。
2. 实现按 `agent_uid` 保存的 active Agent、Draft、滚动位置、附件和生成状态。
3. 实现 Header、Chat Stream、Composer、Send/Stop、Context Inspector、Draft/Commit Bar、Attachment Tray 和 Footer Controls。
4. 通过 ComfyUI WebSocket 消费 RPC 增量事件；Node 与 Panel 同步 `generating`、`stopped`、`committed`、`upstream_changed`、`error`。
5. 关闭 Panel 不终止后台生成；切换 Agent 不丢 Draft；重新打开恢复状态。
6. Audio 入口保留并置灰；Commit 历史只显示轻量索引；错误提供重试但不把 Python stack trace直接放入主聊天区。
7. 通过 ComfyUI 浏览器手工验证 5 个 Agent 同屏、Panel 操作、长 Markdown、切换、关闭恢复和 Canvas 兼容性。

**Verification:**

```bash
python -m unittest tests.workflow_agent.test_routes -v
```

并在 ComfyUI 中完成 UI 验收：节点可放置和连线；Panel 可打开、resize、关闭、恢复；切换 Agent 不丢 Draft；流式、Stop、Commit 和上游状态可见。

---

## Issue 06 — 图片 / 文本文档 / 视频 Asset Slice

**类型：** AFK
**依赖：** Issue 02、Issue 04、Issue 05
**目标：** 让图片、文本类文档和视频从 Chat 或节点输入进入同一 Asset Store，并被 Agent 实际消费；Audio 仅保留禁用入口。

**Files:**
- Create: `ryan_comfy_utils/workflow_agent/asset_service.py`
- Create: `ryan_comfy_utils/workflow_agent/document_extract.py`
- Create: `ryan_comfy_utils/workflow_agent/video_preprocess.py`
- Modify: `ryan_comfy_utils/acp/asset_materializer.py`
- Modify: `ryan_comfy_utils/nodes/workflow_agent_node.py`
- Modify: `ryan_comfy_utils/web/workflow_agent/attachment_tray.js`
- Create: `tests/workflow_agent/test_asset_service.py`
- Create: `tests/workflow_agent/test_document_extract.py`
- Create: `tests/workflow_agent/test_video_preprocess.py`

**Implementation steps:**

1. 实现 Chat Upload 和节点输入的统一 `RyanAssetRef`：`asset_id`、`workflow_id`、type、mime、source、uri、display_name、size、created_by_agent_uid、metadata。
2. 复用现有安全路径和图片物化能力；路径型视频/文档先复制到 Agent Session 目录，Pi 不直接读取外部原路径。
3. 实现 `.txt`、`.md`、`.json`、`.csv` 文本抽取；单文件 20MB、Context 注入 100,000 字符，超出明确记录截断信息。
4. 复用现有视频元数据、场景检测和抽帧能力，生成限量关键帧、场景首帧和派生元数据 AssetRef。
5. Attachment Tray 显示来源、文件名、类型、缩略图或派生状态；Audio 入口 disabled 并显示未支持提示。
6. 将 AssetRef 和派生内容注入 DISCUSS / COMMIT，并在 Context Inspector 中显示来源和数量。
7. 测试重复 Asset、非法路径、文件不存在、大文件、文本截断、视频无帧和来源追踪。

**Verification:**

```bash
python -m unittest tests.workflow_agent.test_asset_service tests.workflow_agent.test_document_extract tests.workflow_agent.test_video_preprocess -v
```

预期：图片、文本文档、视频在 Chat 和节点输入两条路径下可被 Agent 消费；音频不会被误标记为已消费。

---

## Issue 07 — Identity / Fan-in / Compatibility / Demo 验收

**类型：** AFK
**依赖：** Issue 01、Issue 02、Issue 03、Issue 04、Issue 05、Issue 06
**目标：** 用真实 ComfyUI 场景验证完整 V1，补齐文档状态和回归测试。

**Files:**
- Create: `.scratch/workflow-agent-pi-v1/fixtures/serial-workflow.json`
- Create: `.scratch/workflow-agent-pi-v1/fixtures/fan-in-workflow.json`
- Modify: `docs/agents/workflow-agent-workspace-v1-design.md`
- Modify: `docs/agents/workflow-agent-ui-ux-v1.md`
- Modify: `README.md`（只增加已实现的 Pi / Workflow Agent 使用说明）
- Create: `tests/workflow_agent/test_compatibility.py`
- Create: `tests/workflow_agent/test_demo_contract.py`

**Implementation steps:**

1. 验证 Workflow 改名、Save As、节点复制、Skill 切换、节点删除孤儿数据和 ComfyUI reload。
2. 验证串行五阶段 Starter Skill 链：Creative → Production → Script → Storyboard → Video Prompt。
3. 验证三路 fan-in、diamond 去重、冲突提示和 `upstream_changed`。
4. 验证旧 ACP 节点、现有 Image / Video / H3 Agent、多图 Slot、Canvas 原生操作不回归。
5. 验证 Pi 缺失、能力不满足、认证失败、超时、RPC 中断、非法资产和跨 Workflow Context 时错误清晰且不自动回退 Claude。
6. 完成 D3 UI Polish：Node 紧凑视觉、深色主题、长 Markdown、resize、80%～125% 缩放、1366 / 1920 / 2K / 4K。
7. 更新设计文档的实现状态、PRD 闭环、测试结果和下一份交接文档。

**Verification:**

```bash
python -m unittest discover -s tests -v
```

并在 ComfyUI 中手工完成 UI / DAG 验收清单。只有模块测试和真实工作流验收都通过，才能标记 V1 完成。

---

## 依赖图

```text
Issue 01 Pi Runner ───────────────┐
                                 ├──> Issue 04 Chat / Commit / RPC ──┐
Issue 02 Scope / Storage ──> Issue 03 Generic Node ───────────────────┼──> Issue 05 Workspace
       │                         │                                     │       │
       └─────────────────────────┴─────────────────────────────────────┴──> Issue 06 Assets
                                                                            │
Issue 01..06 ──────────────────────────────────────────────────────────────> Issue 07
```

Issue 01 和 Issue 02 可并行。Issue 03 依赖 Issue 02；Issue 04 依赖 Issue 01～03。Issue 05、06 可在 Issue 04 完成后并行实施。Issue 07 最后执行。

## 明确不做

- Supervisor / Router / Agent Team / Agent 自动互调。
- 全 Workflow 自动共享 Chat。
- Commit 自动 Queue。
- 音频转写和 Agent 音频消费。
- PDF、DOCX、HTML 解析。
- 旧 Commit 正文回滚。
- ComfyTV 深度集成。
