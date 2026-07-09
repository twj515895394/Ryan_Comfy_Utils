# Findings & Decisions

## Requirements
- 用户希望继续推进 ACP 方向，暂时不做运行验证。
- 当前任务目标是制定实施计划，并结合 `to-prd` 与 `to-issues` 形成落地文档与拆票方案。
- 仓库已经运行过 `setup-matt-pocock-skills`，相关工程技能配置应以仓库内 `AGENTS.md` 与 `docs/agents/*.md` 为准。

## Research Findings
- 当前仓库已实现 5 个 v1 节点：LLM Chat、LLM Vision Chat、Prompt Template、Batch Video Loader、Video Frame Sampler。
- ACP 目前只有设计文档，没有 runtime 代码、session manager、skill registry、context builder 等实现目录。
- ACP handoff v2 明确的下一步是先定义 4 个协议：`Node Manifest Schema`、`ACP Context`、`Result Parser`、`ACP Profile Schema`。
- `docs/agents/issue-tracker.md` 指定本仓库问题追踪器为本地 Markdown：
  - PRD 路径：`.scratch/<feature-slug>/PRD.md`
  - issue 路径：`.scratch/<feature-slug>/issues/<NN>-<slug>.md`
- `docs/agents/triage-labels.md` 维持默认标签词汇，AFK 可用 `ready-for-agent`。
- `AGENTS.md` 与 `docs/agents/` 当前尚未提交，说明这是本轮新增的仓库配置。
- 仓库当前不存在 `.scratch/` 目录，需要在得到用户确认后初始化对应 feature 目录。

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| ACP feature slug 暂定为 `acp-runtime-foundation` | 既覆盖协议定义，也覆盖最小 runtime 骨架，便于后续在 `.scratch/` 下持续扩展 |
| PRD 聚焦“ACP Foundation”而不是一次性覆盖所有 Agent Nodes | 当前共识是先打通协议与 runtime，再扩展固定节点和可选 skill 节点 |
| issue 采用纵向切片而非按层拆分 | `to-issues` 要求每个 issue 都能形成可验证的端到端能力 |
| `issue01` 的协议实现先采用显式必填键校验 | 第一阶段优先稳定字段边界，避免 runtime 代码隐式依赖松散 JSON 结构 |
| fixtures 路径内置到 `ryan_comfy_utils/acp/fixtures/` | 便于后续 runtime 与测试共享同一套示例资产 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| `writing-plans` 初始路径读取失败 | 根据技能目录索引修正为 `custom/writing-plans` |

## Resources
- `README.md`
- `.handoff/20260708_092500_ACP_Design_Handoff_v2.md`
- `docs/20260708_ACP_Runtime_Architecture_Design_v1.md`
- `docs/20260708_ACP_Architecture_Decision_Record.md`
- `docs/agents/issue-tracker.md`
- `docs/agents/triage-labels.md`
- `docs/agents/domain.md`
