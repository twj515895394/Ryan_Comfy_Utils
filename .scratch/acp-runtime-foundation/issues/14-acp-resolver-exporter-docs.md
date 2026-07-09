Status: ready-for-agent

# Skill Resolver 与 File Exporter 文档校准

## 父问题

`.scratch/acp-runtime-foundation/PRD.md`

## 要构建什么

在 issue 12、13 实现合并后，统一更新文档与 issue 引用，消除「File Generator Agent」过时命名，并说明 Skill Resolver 在 ACP 流程中的位置。

范围包括：更新 `docs/agents/acp-file-export-convention.md`（File Exporter 工具节点 vs Agent 内开关）、README 节点列表、在 issue 11 追加 supersede 评论；若仓库内 ACP 架构 Markdown 仍写 File Generator Agent，改为 File Exporter / 工具节点表述。

## 验收标准

- [ ] 文档中不再将「写文件到 output」能力称为 Agent（除非明确指 ACP 节点类）
- [ ] README 列出 `Ryan File Exporter` 与 Skill Resolver 行为一句话说明
- [ ] issue 11 评论标明：开关已完成；独立节点由 issue 13 承接
- [ ] 交接 `handoff-20260708-233204.md` 中「File Generator Agent 未做」指向 issue 13（可选脚注，不改正文历史）

## 被阻塞于

- `.scratch/acp-runtime-foundation/issues/12-acp-skill-resolver.md`
- `.scratch/acp-runtime-foundation/issues/13-ryan-file-exporter-node.md`

## 评论

### 2026-07-09

- 优先级 P2（交接 §4）