# Task Plan: ACP PRD And Issue Breakdown

## Goal
基于当前 ACP 设计文档，形成一套可执行的实施计划、PRD 草案与垂直切片 issue 草案，并在用户确认后写入本地 Markdown 追踪器。

## Current Phase
Phase 5

## Phases

### Phase 1: Requirements & Discovery
- [x] 理解用户目标：继续推进 ACP，不先做运行验证
- [x] 读取仓库现状、handoff、ADR、README 与现有节点实现
- [x] 确认 issue tracker 已配置为本地 Markdown
- [x] 将探索结论记录到 findings.md
- **Status:** complete

### Phase 2: Planning & Structure
- [x] 初始化 planning-with-files 会话
- [x] 提炼 ACP 的实现模块边界与依赖顺序
- [x] 形成测试策略与非目标范围
- [x] 输出计划/PRD/issues 的确认草案
- **Status:** complete

### Phase 3: PRD & Issue Authoring
- [x] 根据确认结果起草 `.scratch/acp-runtime-foundation/PRD.md`
- [x] 根据确认结果起草 `.scratch/acp-runtime-foundation/issues/*.md`
- [x] 为 PRD 和 AFK issues 标注 `Status: ready-for-agent`
- **Status:** complete

### Phase 4: Review & Verification
- [x] 自审 PRD 是否覆盖 ACP 文档中的关键决策
- [x] 自审 issue 是否为纵向切片而非水平分层任务
- [x] 校对计划中的文件路径、命名与依赖关系
- **Status:** complete

### Phase 5: Delivery
- [x] 向用户总结实施建议、PRD 模块和 issue 拆分
- [x] 标注剩余风险与后续建议
- **Status:** complete

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 使用本地 Markdown 作为问题追踪器 | `docs/agents/issue-tracker.md` 已将 `.scratch/<feature-slug>/` 设为仓库标准 |
| 先做计划、PRD 与 issue 草案，不直接进入代码实现 | 当前 ACP 仍处于协议待定阶段，交接文档明确建议先定协议再编码 |
| 本轮不做 ComfyUI 运行验证 | 用户已明确要求“验证放后面” |

## Errors Encountered
| Error | Resolution |
|-------|------------|
| 初次读取 `writing-plans` 使用了错误路径 | 根据技能索引切换到 `/Users/tangwujun/.agents/skills/custom/writing-plans/SKILL.md` |
