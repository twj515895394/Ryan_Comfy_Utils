Status: ready-for-agent

# ACP Skill Resolver 独立模块

## 父问题

`.scratch/acp-runtime-foundation/PRD.md`

## 要构建什么

将「当前节点最终使用哪个 Skill、从哪棵目录解析」从节点散落逻辑中抽出，形成 ACP Runtime 的独立 **Skill Resolver** 模块，统一 **Fixed Skill Binding** 与 **User Selectable Skill** 两种模式。

端到端行为：任意 ACP Agent 节点在调用 `execute_text_session` 前，通过 resolver 得到标准 **SkillBinding**（含 `skill_id`、`skill_root`、`skill_dir`、`mode`、`source`），再传入 runtime；固定节点（Image/Video Prompt、Image Analyze）**不允许**用户输入覆盖 manifest 中的 `skill_id`；Universal Agent 允许用户 `skill_id` 优先，空则回退 manifest。

设计依据：`.handoff/handoff-20260709-104808-acp-resolver-file-output.md` §3。

## 验收标准

- [ ] 存在 `skill_resolver.py`，导出 `SkillBinding` 与 `resolve_skill_binding()`
- [ ] Fixed 模式：`allow_user_skill=false` 时忽略用户 skill_id，仅用 manifest
- [ ] Selectable 模式：用户 skill_id 非空优先，否则 manifest.skill_id
- [ ] `skill_root` 为空时行为与现 `resolve_skill_root` 回退一致
- [ ] `run_fixed_acp_agent` 与 `RyanACPUniversalAgent` 均经 resolver，无重复绑定逻辑
- [ ] 单元测试覆盖上述规则；全量 `unittest discover` 仍通过

## 被阻塞于

无 - 可以立即开始

## 评论

### 2026-07-09

- 优先级 P0（交接文档 §6）