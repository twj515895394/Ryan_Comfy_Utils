# Findings & Decisions

## Requirements

- 现有 ACP Agent 默认改用 Pi；Claude Profile 仅保留为显式回滚。
- 现有 ACP 节点保持输入输出契约；新增 Workflow Agent 支持 Pi RPC。
- Workflow = Project Scope；Session 主键是 `workflow_id + agent_uid`。
- Chat / Draft 不自动进入 DAG；独立 COMMIT 才产生当前有效 Entry。
- 固定 8 路 Context、10 路图片；视频/文档多行路径输入。
- 图片、文本类文档、视频实际可消费；Audio UI 保留但 disabled。
- 先做简单但功能完整 UI，后做视觉 Polish。
- Save As 新 Workflow 全新 Session；节点复制和 Skill 切换生成新 Agent ID。
- Commit 只保留最新正文，保留轻量 lineage。

## Research Findings

- 最新交接 `.handoff/20260810_1724_workflow_agent_ui_ux_addendum.md`：UI 必须是右侧 Workspace，不是节点内 textarea；Phase D 拆为 D1/D2/D3；固定 Slot 不能破坏 ComfyUI 连线。
- 前置交接 `.handoff/20260810_1717_workflow_agent_workspace_v1_handoff.md`：当前 baseline 只有设计和五个 Starter Skill，`RYAN_CONTEXT`、Generic Node、Session API、Panel、Asset Runtime、Demo、自动化测试均未实现。
- 当前根目录 `__init__.py` 仅注册现有 ACP、LLM、图片、视频和过滤器节点，没有 Generic Workflow Agent。
- 当前 `ryan_comfy_utils/acp/runtime.py` 通过 Profile 的 `command` 调用外部 CLI；读取 `result.json`，缺失时把 stdout 包装成 `outputs.response_text`。
- 当前默认 ACP Profile 是 `local_claude_cli.json`；已有 `local_codex.json`，说明 Runner 已通过 Profile 抽象。
- 当前 `session.py` 只写一次性的 metadata/context JSON，不是长期多轮 Chat Session。
- 当前 `asset_materializer.py` 支持图片和文件复制到 Session input；项目已有视频元数据、场景检测和抽帧基础，没有音频转写依赖。
- 当前依赖包括 numpy、pillow、torch、opencv-python、openai、scenedetect；没有 Whisper/PDF 解析依赖。
- 本机 `pi --version` 为 `0.84.1`；Pi CLI 支持 `--mode text/json/rpc`、`--skill`、`--no-context-files`、`--session`、`--session-dir` 和工具权限参数。
- ComfyUI 代码已有 PromptServer HTTP 路由注册模式，适合复用；现有视频前端使用 ComfyUI API。

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Pi text for legacy ACP, Pi rpc for Workflow Agent | Legacy contract stability plus new streaming UI |
| Ryan System Prompt + explicit Skill | Avoid Pi coding prompt and repository context pollution |
| Pi full tools in Agent Session directory | Keep existing capability while limiting cross-workflow access |
| Filesystem JSON/JSONL | Simple and consistent with current ACP workspace |
| Latest active Entry only | User chose fast/simple and bounded Context |
| Lightweight lineage only | Retain source trace without old Commit body storage |
| No automatic Queue or Claude fallback | Explicit user control and explainable runtime behavior |

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Original handoff required full Commit history, user selected latest only | Recorded deliberate V1 scope reduction in ADR and PRD |
| Original audio requirement was broad, user deferred audio | Keep disabled Audio UI and data type; no STT implementation |
| document-helper advertised missing reference template | Wrote ADR using project conventions; no blocker |

## Resources

- `docs/adr/0001-workflow-agent-pi-runtime-v1.md`
- `.scratch/workflow-agent-pi-v1/PRD.md`
- `docs/superpowers/plans/2026-08-10-workflow-agent-pi-v1.md`
- `docs/agents/workflow-agent-workspace-v1-design.md`
- `docs/agents/workflow-agent-context-contract-v1.md`
- `docs/agents/workflow-agent-ui-ux-v1.md`
- `.handoff/20260810_1717_workflow_agent_workspace_v1_handoff.md`
- `.handoff/20260810_1724_workflow_agent_ui_ux_addendum.md`
 
## Additional Implementation Findings

- `__init__.py` currently exposes `WEB_DIRECTORY = "./ryan_comfy_utils/web"` and registers all nodes through `NODE_CLASS_MAPPINGS`; the Generic Agent registration must preserve this convention.
- Existing Web extensions import `app` from `../../../scripts/app.js` and use `beforeRegisterNodeDef`, `onNodeCreated`, `configure`, and `loadedGraphNode`; fixed Socket arrays are an established compatibility rule.
- Existing HTTP routes are registered at import time behind `hasattr(PromptServer, "instance")`; new Workflow Agent routes should use the same guarded import pattern and return `aiohttp.web.json_response`.
- `acp/runtime.py` currently expands `{context_file}`, `{session_dir}`, and `{skill_directory}` and injects rendered context through stdin; Pi migration must preserve these secure replacement and result-normalization paths.

- `contracts.py` currently validates only five Profile keys (`runner`, `command`, `workspace_root`, `timeout_seconds`, `environment`); optional Pi behavior should remain backward-compatible.
- `local_claude_cli.json` currently contains the Claude permission flag in its command; `local_codex.json` is a second simple Profile fixture.
- Existing Runtime tests use `unittest`, `tempfile.TemporaryDirectory`, `unittest.mock.patch`, and fake Python subprocesses; new tests should follow this style.

- Workflow Agent design defines outputs `context: RYAN_CONTEXT`, `response_text: STRING`, `session_dir: STRING`, and optional `context_json`; `skill_id`, `agent_name`, `agent_uid`, `workflow_id`, `commit_revision`, `profile_path`, and `skill_root` are node properties.
- DISCUSS and COMMIT are separate modes (`RYAN_AGENT_MODE=DISCUSS|COMMIT`); only COMMIT appends an immutable canonical Entry to downstream Context.
- Context propagation is immutable append, not text overwrite; model injection selects latest revision per `source_agent_uid + kind` while retaining lineage for inspection.

- UI source of truth requires a compact Context Bar that expands to real source Agent names, a document-like long Markdown stream, a persistent Draft/Commit distinction, and streaming Stop behavior without locking other Agent panels.

- Issue 03 implementation verified: Context dataclasses reject chat history/non-JSON values, merge detects workflow/ID conflicts, selector keeps latest active revision, and Generic Node uses fixed 8 Context + 10 Image sockets without invoking Pi.
- Generic Node currently falls back to `workflow_default` only when no workflow ID and no upstream Context are supplied; later node UI/state integration must inject/persist real Workflow ID.

- Starter Skill contracts expose `display_name`, `recommended_agent_name`, `accepts_context_kinds`, `produces_context_kind`, `discussion_mode`, `commit_mode`, and optional `commit_title`; Commit service should use these fields instead of hard-coded role names.
- Existing ACP `session.py` only writes one-shot `metadata.json` / `context.json`; Workflow Agent must use the new scoped repository for long-lived private Chat and Commit state.

- Chat/Commit review found three contract hazards and fixed them before slice verification: Commit must consume the Pi RPC iterator (not only list/tuple), requests without caller IDs must receive unique IDs (otherwise every message dedupes), and default Pi RPC runners must be cloned per request so Agent panels can generate concurrently without sharing a stop handle.
