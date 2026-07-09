# ACP Skill Resolver 与 Ryan File Exporter 实施计划

> 依据：`.handoff/handoff-20260709-104808-acp-resolver-file-output.md`  
> Issues：`12` → `13` → `14`（12 与 13 可并行）

**Goal:** 将 Skill 绑定逻辑收敛到 `skill_resolver.py`；新增非 ACP 工具节点 **Ryan File Exporter**（不叫 Agent）。

**Architecture:** `SkillBinding` + `resolve_skill_binding()`；Fixed 节点禁止用户覆盖 `skill_id`；Universal 用户优先。File Exporter 复用/扩展 `file_exporter.py`，分类 `Ryan Utils / File`。

---

## Issue 12 — Skill Resolver

- Create: `ryan_comfy_utils/acp/skill_resolver.py`
- Modify: `ryan_comfy_utils/nodes/acp_nodes.py`（`run_fixed_acp_agent`、Universal）
- Create: `tests/acp/test_skill_resolver.py`
- Verify: `python3 -m unittest tests.acp.test_skill_resolver -v`

## Issue 13 — File Exporter 节点

- Create: `ryan_comfy_utils/nodes/file_nodes.py`
- Modify: `ryan_comfy_utils/acp/file_exporter.py`（通用 text/json 写入，如需要）
- Modify: `__init__.py`、README
- Create: `tests/nodes/test_file_exporter_node.py`
- Verify: `python3 -m unittest tests.nodes.test_file_exporter_node -v`

## Issue 14 — 文档

- Modify: `docs/agents/acp-file-export-convention.md`、README、issue 11 评论
- 架构文档中移除 File Generator **Agent** 命名（若存在对应段落）

---

## 超出范围

- 真实 Claude/Codex CLI 联调（下一 feature）
- Storyboard / Character 固定节点