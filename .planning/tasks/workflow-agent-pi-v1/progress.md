# Progress Log

## Session: 2026-08-10

### Phase 1: Requirements & Discovery
- **Status:** complete
- **Started:** 2026-08-10
- Actions taken:
  - 阅读最新 UI 交接、前置交接、总体设计、Context 合同和 Skill 迁移说明。
  - 检查当前代码注册、ACP Runtime、Profile、Session、Asset Materializer、测试和 Pi CLI。
  - 通过 grill-me 逐项确认 Pi Runner、Session、Workflow Scope、Context、Commit、Assets、UI 和兼容策略。
- Files created/modified:
  - `docs/adr/0001-workflow-agent-pi-runtime-v1.md`
  - `.scratch/workflow-agent-pi-v1/PRD.md`

### Phase 2: Planning & Structure
- **Status:** in_progress
- Actions taken:
  - 创建 7 个可独立验证的垂直切片草案。
  - 明确 Issue 01/02 可并行，Issue 05/06 可并行，其余按依赖执行。
  - 生成实施计划和 planning 文件。
- Files created/modified:
  - `docs/superpowers/plans/2026-08-10-workflow-agent-pi-v1.md`
  - `.planning/current`
  - `.planning/tasks/workflow-agent-pi-v1/task_plan.md`
  - `.planning/tasks/workflow-agent-pi-v1/findings.md`
  - `.planning/tasks/workflow-agent-pi-v1/progress.md`
- Pending:
  - 用户批准问题粒度、依赖和 AFK/HITL 标记后，发布 `.scratch/workflow-agent-pi-v1/issues/`。

## Test Results

| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| Pi availability | `rtk pi --version` | Installed CLI version | `0.84.1` | PASS |
| Current branch | `rtk git status --short --branch` | Clean and synced | `main...origin/main` | PASS |
| Implementation search | code/tree inspection | Workflow Agent paths registered | No Generic Workflow Agent implementation found | PASS |

## Error Log

| Timestamp | Error | Attempt | Resolution |
|-----------|-------|---------|------------|
| 2026-08-10 | `docs/adr/` not found | 1 | Created ADR directory and recorded decision |
| 2026-08-10 | ADR template path missing | 1 | Used documented ADR sections manually |

## 5-Question Reboot Check

| Question | Answer |
|----------|--------|
| Where am I? | Phase 2: Planning & Structure |
| Where am I going? | User approval → issue publication → parallel implementation |
| What's the goal? | Deliver Pi-backed Generic Workflow Agent V1 end to end |
| What have I learned? | See `findings.md`; current code has ACP primitives but no Workflow Agent |
| What have I done? | Recorded ADR/PRD and created plan with 7 slices |

### Phase 2 checkpoint: issue publication
- **Status:** complete
- **Completed:** 2026-08-10
- User approved the seven-slice decomposition, dependencies, and AFK/HITL labels.
- Published:
  - `.scratch/workflow-agent-pi-v1/issues/01-pi-runner-migration.md`
  - `.scratch/workflow-agent-pi-v1/issues/02-workflow-agent-scope.md`
  - `.scratch/workflow-agent-pi-v1/issues/03-ryan-context-generic-node.md`
  - `.scratch/workflow-agent-pi-v1/issues/04-workflow-agent-chat-commit.md`
  - `.scratch/workflow-agent-pi-v1/issues/05-workflow-agent-workspace.md`
  - `.scratch/workflow-agent-pi-v1/issues/06-workflow-agent-assets.md`
  - `.scratch/workflow-agent-pi-v1/issues/07-workflow-agent-integration.md`
- First implementation wave dispatched in parallel: Pi Runner and Workflow / Agent Scope.

### Phase 3: Implementation
- **Status:** complete
- **Completed:** Generic Context/Node, Chat/Commit/RPC, right-side Workspace, Asset Store/API and ComfyUI registration are implemented.
- **Next:** complete ComfyUI runtime/browser acceptance after the service is running, then finalize documentation and handoff.

### Phase 3 checkpoint: Issue 01 / 02 verification
- Pi Runner and Scope implementations were reviewed after agent completion.
- Added focused tests:
  - `tests/acp/test_pi_runner.py`
  - `tests/workflow_agent/test_identity.py`
  - `tests/workflow_agent/test_repository.py`
  - extended `tests/acp/test_contracts.py` for `local_pi.json`
- Passed:
  - `python -m unittest tests.acp.test_pi_runner tests.acp.test_contracts tests.workflow_agent.test_identity tests.workflow_agent.test_repository -v` — 12 tests.
  - `python -m unittest tests.acp.test_runtime -v` — 10 tests.
  - ACP export smoke check confirmed `create_session_record` and Pi exports.
- Fixed an export completeness issue by importing `create_session_record` in `ryan_comfy_utils/acp/__init__.py`.

### Phase 3 checkpoint: Issue 04 review
- Fixed Commit RPC iterator consumption, unique generated request IDs, per-request default Pi runner isolation, and context-summary route normalization.
- Added `tests/workflow_agent/test_chat_commit.py`; focused Chat/Commit tests passed: 2 tests.

### Phase 3 checkpoint: Workspace / Assets review
- Fixed upstream AssetRef resolution to use the source Agent scope during fan-in.
- Added multipart upload display-name and MIME propagation; UI deduplicates stable Asset IDs.
- Added stale-response guards so switching Agents cannot overwrite the active Draft or Commit state.
- Focused regression: `python -m unittest tests.workflow_agent.test_assets tests.workflow_agent.test_chat_commit tests.nodes.test_workflow_agent_node tests.workflow_agent.test_context tests.workflow_agent.test_repository tests.workflow_agent.test_identity -v` — 23 tests passed.
- Frontend syntax: all Workspace modules passed `node --check`.

### Phase 4 checkpoint: runtime / browser handoff
- Runtime smoke had already confirmed `/system_stats` returned 200, the Workspace DOM/style injection, Generic Agent registration, 8 Context inputs, 10 Image inputs, 5 Starter Skills, Workspace open/close/resize, and valid `workflow_id` / `agent_uid`.
- User requested to perform browser debugging manually; browser acceptance remains blocked by user-owned verification rather than code execution.
- Added the manual matrix at `docs/agents/workflow-agent-manual-acceptance-v1.md`.

### Phase 4 checkpoint: identity / dynamic inputs
- Frontend now initializes and persists `workflow_id` / `agent_uid`, maps Skill to a recommended Agent Name, preserves manual names, and emits complete `Open Chat` identity.
- Context and Image sockets remain fixed at 8 / 10; count controls hide only unconnected high slots and preserve connected sockets.
- Node state rendering covers not started, discussing, committed, generating, and upstream changed.
- Backend/node regression: 21 Workflow Agent tests plus 5 node tests passed.
- Frontend syntax: all changed Workspace modules passed `node --check`.


- Follow-up frontend fix preserves the selected Agent Name in the Workspace after the initial API state load.
- Clone hook regenerates `agent_uid` for duplicated nodes while retaining the Workflow scope and Skill choice.

### Phase 4 checkpoint: Pi RPC failure
- Reproduced the screenshot symptom with a minimal zero-exit subprocess: `NameError: name 'return_code' is not defined`.
- Fixed `PiRpcRunner.run()` to call `process.wait()` before checking the exit code and to close child process streams.
- Added `tests/workflow_agent/test_pi_rpc.py`; zero-exit and nonzero-exit cases pass.

### Phase 4 checkpoint: Pi RPC JSONL protocol
- Re-read the installed Pi RPC contract: commands arrive as JSONL on stdin, and `agent_settled` is the terminal lifecycle event.
- `PiRpcRunner.run()` now sends a JSON `prompt` command, consumes stdout and stderr concurrently, rejects RPC error responses, waits for `agent_settled`, and validates the process exit code.
- Process stream cleanup now joins reader threads and tolerates a closed pipe during shutdown.
- Added protocol regressions for prompt/settlement and zero-exit-without-settlement.
- Verification:
  - `python -m py_compile ryan_comfy_utils/workflow_agent/pi_rpc.py` passed.
  - 34 relevant Workflow Agent / ACP / node tests passed.
  - Real Pi RPC returned non-empty text with `status=completed` and `settled=True`.
  - Real `WorkflowAgentChatService` returned a non-empty response and returned the persisted state to `idle`.
- Normalized explicit and custom-resolver Skill directories to absolute paths before changing the Pi session working directory.
- Real ChatService regression with a relative custom resolver returned a non-empty response and `state=idle`.
- Commit 隔离修复：`WorkflowAgentCommitService` 改用 Agent scope 下的一次性临时 Pi 会话目录，不再复用私聊 `pi-session.jsonl`；避免私聊工具调用/历史污染 COMMIT Canon。
- 回归验证：`tests.workflow_agent.test_chat_commit` 3 tests passed；`commit_service.py` 编译通过。
- COMMIT Prompt 明确将 Draft 视为不可信素材，仅提取已确认事实，禁止回显聊天记录、工具调用、路径和内部推理。


### Remaining manual acceptance
- Real Pi Chat/Commit, serial/fan-out/fan-in DAGs, Save As / duplicate isolation, failure paths, and Canvas compatibility require the user's browser session.


### Phase 4 checkpoint: commit_revision Queue validation
- Reproduced from `user/comfyui.log`: ComfyUI rejected `commit_revision=""` before node execution because the input schema was `INT`.
- Root cause: hidden revision widget can be restored as an empty string in an existing Workflow; `run()` defaults cannot repair a value rejected during prompt validation.
- Changed the hidden schema to `STRING` with default `"0"` so legacy empty values pass validation; revision remains a cache-key/status value only.
- Frontend now normalizes blank/invalid revision widgets to `"0"` and writes the committed revision back to the hidden widget, so re-Queue invalidates the node cache.
- Added regression coverage in `tests/nodes/test_workflow_agent_node.py`.
- Verification: focused regression passed; `node --check ryan_comfy_utils/web/workflow_agent/node_extension.js` passed.
- Full `tests/workflow_agent` regression passed: 25 tests.

### Phase 4 checkpoint: Chat feedback UI
- Approved design implemented through subagent-driven slices:
  - `agent_panel.js`: accepted send clears composer; failed send preserves the user record and appends a system error record; status labels cover error/submitting/generating/stopped.
  - `message_list.js` / `styles.js`: accessible busy overlay covers only the message region.
  - `node_extension.js`: node status priority covers error, submitting, generating, and stopped with matching colors.
  - Stop path calls `/ryan/agent/stop` and preserves returned draft.
- Verification:
  - Frontend `node --check` passed for all four changed modules.
  - Workflow Agent tests: 25 passed.
  - Workflow Agent node tests: 7 passed.
  - Full repository test discovery is blocked by pre-existing missing optional dependencies (`aiohttp`, `openai`, `scenedetect`); 4 collection errors.
### Phase 4 checkpoint: structured artifacts and bounded model context
- User confirmed upgrading the existing creative Agents rather than adding a mandatory parsing Agent.
- User confirmed the four default mappings: character design, production / scene design, storyboard, and video prompts.
- Documented the `RYAN_CONTEXT` artifact bundle, deterministic Artifact Selector, summary / selected / full Context View modes, and conservative invalid-output fallback.
- Confirmed V1 character budgets: summary 12,000; selected output 4,000; source view 16,000; upstream view 24,000; draft 7,000; user message 5,000; Asset metadata 3,000 characters.
- Corrected the derived source and upstream budgets so a 12,000-character summary plus selected output can coexist.
- Design specification: `docs/agents/workflow-agent-artifact-context-v1.md`.

### Phase 4 checkpoint: structured Queue outputs
- `RyanWorkflowAgent` now exposes `artifact_text`, `image_prompt`, `storyboard_prompt`, and `video_prompt` as explicit outputs derived from the committed Artifact Bundle.
- Kept the legacy four outputs in the same order; added output-specific regression coverage and updated node tests for the expanded result tuple.
- Verification: `tests.nodes.test_workflow_agent_node` 8 tests passed.

### Phase 4 checkpoint: Artifact catalog UI
- `context_inspector.js` now renders valid Artifact Bundle outputs and shots from upstream entries.
- Each catalog item has a guarded copy action using Clipboard API with a textarea fallback; copy failure is visible and does not mutate source text.
- Added compact catalog and button styles in `styles.js`.
- Verification: changed frontend modules passed `node --check`; targeted node/context/chat regressions passed (22 tests).

### Phase 4 checkpoint: Queue revision validation and selector UX
- Reproduced ComfyUI prompt rejection for legacy `commit_revision=""`; changed the hidden input contract to `STRING` and normalized invalid widget values to `"0"` before Queue.
- Artifact Selector now keeps semantic selection within the latest active valid Entry, includes shots in `first_output`, rejects an unselected explicit shot, filters valid active Bundles, and exposes readable advanced combo labels backed by internal IDs.
- Added status rendering for missing Context, missing Bundles, upstream updates, and unmatched output.
- Verification: 15 Artifact Selector tests, 30 Workflow Agent/Context/Chat tests, 54 targeted node tests, and all changed frontend modules passed `node --check`.
- Full discovery remains blocked by four pre-existing optional dependency collection errors: `aiohttp`, `openai`, and `scenedetect`.