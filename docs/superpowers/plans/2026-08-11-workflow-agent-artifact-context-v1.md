# Workflow Agent Artifact Context V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 Workflow Agent 的 Commit/DAG 基础上增加结构化产物、确定性产物选择和有预算的模型 Context View，避免下游 Agent 因完整 Context 膨胀而漂移。

**Architecture:** 完整 `RYAN_CONTEXT` 继续保存 Canonical Entry、Artifact Bundle、AssetRef 和 lineage；模型调用前由 `context_select.py` 按 Skill 合同、最新 revision、读取模式和字符预算生成 Context View。现有四类创作 Agent 通过 COMMIT Prompt 输出 Markdown 与可选 `ryan-artifact` JSON fenced block；解析失败时保留原正文，不自动猜测。ComfyUI 增加纯确定性的 `Ryan Artifact Selector`，Workflow Agent 保留原有四个输出并追加常用提示词输出。

**Tech Stack:** Python 标准库 dataclasses/json/unittest、现有 ComfyUI 节点注册、Vanilla ES Modules、Node `--check`。

---

### Task 1: Add the artifact contract and parser

**Files:**
- Create: `ryan_comfy_utils/workflow_agent/artifacts.py`
- Modify: `ryan_comfy_utils/workflow_agent/models.py:361-370`
- Create: `tests/workflow_agent/test_artifacts.py`
- Modify: `ryan_comfy_utils/acp/fixtures/skills/production-designer/agent-contract.json`
- Modify: `ryan_comfy_utils/acp/fixtures/skills/storyboard-director/agent-contract.json`
- Modify: `ryan_comfy_utils/acp/fixtures/skills/video-prompt-director/agent-contract.json`
- Modify: `ryan_comfy_utils/acp/fixtures/skills/creative-story-planner/agent-contract.json`

- [ ] **Step 1: Define validated artifact dataclasses**

  Add `RyanArtifactOutput`, `RyanArtifactBundle`, and `ArtifactParseResult` in `artifacts.py`. Required output fields are `output_id`, `kind`, `label`, and `text`; `priority` defaults to `50`. Bundle fields are `artifact_type`, `schema_version=1`, `content`, `outputs`, and optional `shots`. Validate IDs and strings with the existing identity/model helpers, reject non-JSON values, reject duplicate `output_id` / `shot_id`, and preserve unknown content keys as JSON-safe values.

- [ ] **Step 2: Define the machine-readable Commit block**

  Parse exactly one optional fenced block with this shape:

  ````markdown
  ```ryan-artifact
  {"artifact_type":"character_design","schema_version":1,"content":{},"outputs":[]}
  ```
  ````

  `parse_artifact_markdown(text, expected_artifact_type="")` must return the original text unchanged when the block is absent or invalid. For a valid block it returns the Markdown with that block removed, the validated bundle, and `status="valid"`. Invalid JSON, wrong schema, wrong expected type, duplicate IDs, or multiple blocks return `status="invalid"`, an error string, no bundle, and the original Markdown unchanged.

- [ ] **Step 3: Add entry metadata helpers**

  Add `artifact_bundle_from_entry(entry)` and `artifact_outputs(entry)` helpers. They read only `entry.metadata["artifact_bundle"]`, return no outputs for invalid/missing metadata, and expose the bundle summary and selected outputs without changing `RyanContextEntry`’s top-level JSON contract.

- [ ] **Step 4: Add contract metadata for the four creative Skills**

  Add `artifact_type` and `artifact_output_kinds` to the four fixture contracts:

  - `creative-story-planner`: `creative_story`, `story_summary`, `image_prompt`;
  - `production-designer`: `production_design`, `image_prompt`, `continuity_constraint`;
  - `storyboard-director`: `storyboard_plan`, `storyboard_sheet_prompt`, `shot_prompt`;
  - `video-prompt-director`: `video_prompts`, `video_prompt`, `shot_video_prompt`.

  Keep existing `produces_context_kind`, `accepts_context_kinds`, and mode flags unchanged.

- [ ] **Step 5: Write failing parser tests**

  Cover valid JSON extraction and Markdown cleanup, absent block compatibility, malformed JSON fallback, wrong artifact type fallback, duplicate output rejection, and `artifact_outputs()` returning only validated outputs.

- [ ] **Step 6: Run the focused tests**

  Run: `rtk python -m unittest tests.workflow_agent.test_artifacts -v`

  Expected: all new parser tests pass.

---

### Task 2: Build bounded Context Views and shared Skill contract loading

**Files:**
- Create: `ryan_comfy_utils/workflow_agent/skill_contract.py`
- Modify: `ryan_comfy_utils/workflow_agent/commit_service.py:53-90`
- Modify: `ryan_comfy_utils/workflow_agent/context_select.py:1-78`
- Modify: `ryan_comfy_utils/workflow_agent/chat_service.py:108-132`
- Create: `tests/workflow_agent/test_context_view.py`
- Modify: `tests/workflow_agent/test_context.py:85-107`

- [ ] **Step 1: Extract shared Skill contract loading**

  Implement `load_skill_contract(skill_id, payload, resolver)` in `skill_contract.py`. It resolves explicit `skill_directory`, custom resolver, or the existing Skill loader; reads `agent-contract.json`; requires a non-empty `produces_context_kind`; returns the directory and JSON mapping; and raises the existing service-specific error at each caller. Refactor Commit to use it without changing its public errors.

- [ ] **Step 2: Define the Context View policy**

  Add `ContextViewPolicy` with these defaults: `summary_limit=12000`, `output_limit=4000`, `source_limit=16000`, `total_limit=24000`, `draft_limit=7000`, `message_limit=5000`, and `asset_limit=3000`. Use explicit character counts, never UTF-8 byte counts.

- [ ] **Step 3: Implement latest-entry and artifact selection**

  Keep `select_context_entries()` behavior unchanged: latest active revision per `source_agent_uid + kind`. Add `render_context_view(context, accepts_context_kinds, mode="summary", selected_output_ids=(), selected_shot_ids=(), policy=None)`. `summary` renders source metadata, artifact summary when available, and entry summary/content fallback capped at `summary_limit`; `selected` renders only named artifact outputs/shots; `full` renders entry content but still applies source and total budgets. Do not render Chat history or binary data.

- [ ] **Step 4: Implement deterministic budget trimming**

  Sort candidates by: explicitly selected output, accepted kind, latest revision, continuity constraints, Asset metadata, then non-target summaries. Omit lower-priority sections until the total budget fits. Append a `[Context truncated]` marker containing source, omitted count, reason, and selector guidance. Never mutate the original `RyanContext` or cut the stored Commit body.

- [ ] **Step 5: Route Chat Prompt through the Context View**

  Update `WorkflowAgentChatService._prompt()` to receive the Skill contract, call `render_context_view(..., mode="summary")`, cap Draft to `draft_limit`, cap user message to `message_limit`, and serialize only bounded Asset metadata. The existing `[UPSTREAM_CONTEXT]`, `[ASSETS]`, `[CURRENT_DRAFT]`, and `[USER_MESSAGE]` section names remain stable.

- [ ] **Step 6: Add Context View tests**

  Cover latest revision selection, accepted-kind ordering, summary mode excluding full content, selected output and shot extraction, source/total budget markers, old unstructured entry fallback, and preservation of the original Context.

- [ ] **Step 7: Run focused Context tests**

  Run: `rtk python -m unittest tests.workflow_agent.test_context tests.workflow_agent.test_context_view -v`

  Expected: existing selector tests and new budget tests pass.

---

### Task 3: Upgrade Commit output without breaking old Markdown

**Files:**
- Modify: `ryan_comfy_utils/workflow_agent/commit_service.py:91-120,123-203`
- Modify: `tests/workflow_agent/test_chat_commit.py:31-59`
- Modify: `tests/workflow_agent/test_chat_commit.py` (append structured Commit cases)

- [ ] **Step 1: Extend the COMMIT Prompt contract**

  Keep the existing Markdown Canonical Artifact requirement, then add a deterministic instruction using the Skill contract’s `artifact_type` and `artifact_output_kinds`: write user-facing Markdown first and append one optional `ryan-artifact` JSON block. The JSON block must contain only confirmed facts, semantic/model-independent prompts, continuity constraints, and selected outputs; it must not contain chat history, tool calls, file paths, or internal reasoning.

- [ ] **Step 2: Parse and persist structured output**

  After `_commit_text()`, call `parse_artifact_markdown()` with the expected contract artifact type. Store cleaned Markdown in `entry.content`; store a valid bundle in `entry.metadata["artifact_bundle"]`; store `artifact_status="valid"` for valid output, `"absent"` for legacy Markdown, and `"invalid"` plus `artifact_error` for invalid output. Invalid optional metadata must never reject an otherwise non-empty Commit.

- [ ] **Step 3: Preserve API compatibility**

  Continue returning `entry`, `kind`, `lineage`, `commit_revision`, and existing state fields. Add `artifact_status`, `artifact_bundle`, and `artifact_error` only when applicable. Keep old fake RPC responses and old Markdown content behavior unchanged.

- [ ] **Step 4: Add Commit regression tests**

  Add a fake RPC response containing valid `ryan-artifact` JSON and assert cleaned content, metadata bundle, output IDs, and returned status. Add malformed-block coverage asserting the Commit succeeds with original Markdown and `artifact_status="invalid"`. Keep the current iterator, temporary-session, and persisted-latest assertions.

- [ ] **Step 5: Run Chat/Commit tests**

  Run: `rtk python -m unittest tests.workflow_agent.test_chat_commit -v`

  Expected: all existing and new tests pass.

---

### Task 4: Add the deterministic Artifact Selector node

**Files:**
- Create: `ryan_comfy_utils/nodes/artifact_selector_node.py`
- Modify: `__init__.py:1-74`
- Create: `tests/nodes/test_artifact_selector_node.py`

- [ ] **Step 1: Define node inputs and output**

  Add `RyanArtifactSelector` with optional `context: RYAN_CONTEXT`, required `source_agent_uid`, `artifact_type`, `output_id`, `shot_id`, `kind`, and `revision` filters. Return one `STRING` named `text`, use `CATEGORY="Ryan Utils / Agent"`, and never start Pi, access the repository, or mutate Context.

- [ ] **Step 2: Implement deterministic selection**

  Merge the supplied Context values with the existing `merge_contexts()` rules. Search latest active entries, filter by supplied fields, then return the selected output text or shot prompt. If no selector matches, return an empty string; never fall back to arbitrary entry content or an error string that could be sent to a downstream generation node.

- [ ] **Step 3: Register the node**

  Add `Ryan Artifact Selector` to `NODE_CLASS_MAPPINGS`, `NODE_DISPLAY_NAME_MAPPINGS`, and the package import list without changing existing mapping keys.

- [ ] **Step 4: Test normal, boundary, and failure cases**

  Cover selecting an output, selecting a shot, filtering by revision/source, duplicate fan-in context, absent bundle, and no-match empty output. Assert no external runner is invoked.

- [ ] **Step 5: Run node tests**

  Run: `rtk python -m unittest tests.nodes.test_artifact_selector_node tests.nodes.test_workflow_agent_node -v`

  Expected: all selector and existing Workflow Agent node tests pass.

---

### Task 5: Expose common prompt outputs from Workflow Agent

**Files:**
- Modify: `ryan_comfy_utils/nodes/workflow_agent_node.py:103-250`
- Modify: `tests/nodes/test_workflow_agent_node.py:18-42,53-75`

- [ ] **Step 1: Add stable appended outputs**

  Preserve the first four output positions exactly. Append `artifact_text`, `image_prompt`, `storyboard_prompt`, and `video_prompt` as `STRING` outputs. The generic text is the latest selected artifact’s first valid output; typed outputs choose the first matching `kind` (`image_prompt`, `storyboard_sheet_prompt` or `shot_prompt`, `video_prompt` or `shot_video_prompt`). Missing outputs return empty strings.

- [ ] **Step 2: Read outputs from the existing latest Commit**

  Use the validated `artifact_outputs()` helper on the committed Entry already appended by `append_commit()`. Do not parse arbitrary Markdown in the Queue node and do not invoke Pi or the repository beyond the existing latest Commit read.

- [ ] **Step 3: Update tests**

  Assert old output names and positions remain unchanged; add a structured Entry fixture and assert all four new strings; assert an old unstructured Entry returns empty prompt outputs while preserving `response_text`.

- [ ] **Step 4: Run node regression**

  Run: `rtk python -m unittest tests.nodes.test_workflow_agent_node -v`

  Expected: all Workflow Agent node tests pass.

---

### Task 6: Show Artifact outputs in the Workspace UI

**Files:**
- Modify: `ryan_comfy_utils/web/workflow_agent/context_inspector.js:1-76`
- Modify: `ryan_comfy_utils/web/workflow_agent/agent_panel.js:100-143,280-307`
- Modify: `ryan_comfy_utils/web/workflow_agent/styles.js`
- Modify: `ryan_comfy_utils/web/workflow_agent/node_extension.js` only if output labels need semantic display

- [ ] **Step 1: Render artifact metadata without rendering hidden raw payloads**

  In `ContextInspector`, show each valid bundle’s artifact type, output label, kind, revision, and a Copy button. Copy only the selected output text with `navigator.clipboard.writeText`; show a short success/failure message. Do not render full `metadata.artifact_bundle` JSON by default.

- [ ] **Step 2: Preserve existing Context Inspector behavior**

  Keep source Agent, revision, summary, entry content, asset count, empty state, and received-state text. Invalid or absent bundles show a compact status, not an exception.

- [ ] **Step 3: Merge Commit response metadata into panel state**

  On successful Commit, retain `result.entry.metadata`, `artifact_status`, and `artifact_error` in the store/context state so the inspector updates immediately without reopening the panel. Existing Draft clearing and revision state remain unchanged.

- [ ] **Step 4: Add bounded UI styles**

  Add styles for artifact rows, kind/revision metadata, copy buttons, and invalid status using existing Ryan variables. Avoid rendering large payloads or adding a second nested card hierarchy.

- [ ] **Step 5: Run frontend syntax checks**

  Run: `rtk node --check ryan_comfy_utils/web/workflow_agent/context_inspector.js && rtk node --check ryan_comfy_utils/web/workflow_agent/agent_panel.js && rtk node --check ryan_comfy_utils/web/workflow_agent/styles.js && rtk node --check ryan_comfy_utils/web/workflow_agent/node_extension.js`

  Expected: all commands exit successfully.

---

### Task 7: Full regression and contract review

**Files:**
- Modify: `docs/agents/workflow-agent-context-contract-v1.md` only if implementation adds a field not already covered by `workflow-agent-artifact-context-v1.md`.
- Modify: `.planning/tasks/workflow-agent-pi-v1/progress.md`

- [ ] **Step 1: Run the complete relevant Python suite**

  Run: `rtk python -m unittest tests.workflow_agent tests.nodes.test_workflow_agent_node tests.nodes.test_artifact_selector_node -v`

  Expected: all collected relevant tests pass; any pre-existing optional-dependency collection failures remain explicitly reported rather than hidden.

- [ ] **Step 2: Run all changed JavaScript syntax checks**

  Run: `rtk node --check ryan_comfy_utils/web/workflow_agent/context_inspector.js && rtk node --check ryan_comfy_utils/web/workflow_agent/agent_panel.js && rtk node --check ryan_comfy_utils/web/workflow_agent/styles.js && rtk node --check ryan_comfy_utils/web/workflow_agent/node_extension.js`

  Expected: all commands pass.

- [ ] **Step 3: Verify observable contracts**

  Exercise with tests and direct calls: legacy Markdown Commit, valid structured Commit, malformed structured Commit, summary budget overflow, selected output extraction, selector no-match, old Workflow Agent output positions, and new prompt outputs.

- [ ] **Step 4: Review the diff scope**

  Confirm no Pi Runner changes, no ComfyUI core changes, no Chat history in Context, no binary payload in model Context, no mandatory parsing Agent, and no temporary debug logs.

- [ ] **Step 5: Record the checkpoint**

  Append exact test commands/results and any pre-existing blockers to `.planning/tasks/workflow-agent-pi-v1/progress.md`; update the design document only for implementation deviations.
