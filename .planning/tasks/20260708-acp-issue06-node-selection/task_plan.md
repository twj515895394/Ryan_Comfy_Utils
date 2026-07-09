# Task Plan: ACP Issue06 Fixed Node Selection

## Goal
完成 `.scratch/acp-runtime-foundation/issues/06-fixed-agent-node-selection.md` 的决策草案：形成首批固定绑定节点清单、保留在 Universal Agent 的能力边界、命名与数量控制策略，并提交给用户确认。

## Current Phase
Phase 2

## Phases

### Phase 1: Requirements & Discovery
- [x] 读取 issue06、PRD、README、handoff 与当前实现状态
- [x] 确认 issue06 是 HITL 决策切片，不是继续扩代码功能
- [x] 提炼当前仓库已经稳定的能力边界
- **Status:** complete

### Phase 2: Planning & Structure
- [x] 为 issue06 初始化独立 planning 会话
- [x] 确定“推荐固定节点”与“保留在 Universal Agent”两组清单
- [x] 确定节点数量控制与命名策略
- **Status:** complete

### Phase 3: Decision Draft
- [x] 写入固定节点选型结论草案
- [x] 更新 issue06 的状态与评论，标记等待人工确认
- [x] 保证结论与当前仓库能力现状一致
- **Status:** complete

### Phase 4: Review & Verification
- [x] 自审结论是否回答了 issue06 的全部验收标准
- [x] 校对节点名称、默认 skill、场景和最小 contract 是否清晰
- **Status:** complete

### Phase 5: Delivery
- [ ] 向用户展示建议与保留项
- [ ] 请求用户对选型草案做最终确认
- **Status:** in_progress

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 本轮以文档化决策作为“实现” | issue06 本质是产品切分与节点选型，不是继续堆 runtime 代码 |
| 需要显式请求用户拍板 | issue06 验收标准明确要求“该结论获得人工确认后再进入实现” |

## Errors Encountered
| Error | Resolution |
|-------|------------|
