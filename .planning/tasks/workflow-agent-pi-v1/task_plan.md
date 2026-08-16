# Task Plan: Workflow Agent V1 Pi Runtime

## Goal
将已确认的 Ryan Workflow Agent V1 设计记录为可执行计划，并在问题切片批准后按依赖交付 Pi Runtime、Context、Generic Node、Chat/Commit、Workspace、Assets 和 Demo 验收。

## Current Phase
Phase 4

## Phases

### Phase 1: Requirements & Discovery
- [x] 阅读最新交接、总体设计、Context 合同和 UI 基线
- [x] 核对当前代码：现有 ACP 默认 Claude、无 Workflow Agent 实现
- [x] 通过 grill-me 确认 Pi、Session、资产、Commit、UI 和兼容性决策
- [x] 记录架构决策和 V1 PRD
- **Status:** complete

### Phase 2: Planning & Structure
- [x] 生成 writing-plans 实施计划
- [x] 设计可独立演示的垂直切片和依赖图
- [x] 获得用户对问题拆分、依赖和 AFK/HITL 标记的批准
- [x] 将批准的切片发布到 `.scratch/workflow-agent-pi-v1/issues/`
- **Status:** complete
 
### Phase 3: Implementation
- [x] 按依赖执行 Issue 01 Pi Runner 与 Issue 02 Scope/Storage
- [x] 执行 Issue 03 Generic Node 与 Issue 04 Chat/Commit/RPC
- [x] 执行 Issue 05 Workspace 与 Issue 06 Assets
- [x] 执行 Issue 07 Integration / Compatibility / Demo（代码注册与模块级验证完成）
- **Status:** complete

### Phase 4: Testing & Verification
- [x] 运行各切片模块测试
- [x] 运行完整 Python 测试集（119 tests discovered；4 个既有可选依赖导入错误）
- [ ] 启动 ComfyUI 并完成人工 UI / DAG 验收
- [ ] 验证 Pi 缺失、认证失败、跨 Workflow、Stop、Retry 和旧节点兼容
- [x] 修复 Pi RPC JSONL prompt / agent_settled 协议和进程清理
- [x] 运行真实 Pi RPC 与 WorkflowAgentChatService 回归
- **Status:** in_progress（ComfyUI / 浏览器人工验收仍按用户边界保留）

### Phase 5: Delivery
- [ ] 更新设计文档实现状态
- [ ] 更新 README 使用说明和测试结果
- [ ] 生成新的交接文档
- [ ] 向用户汇报改动、验证和剩余风险
- **Status:** pending

## Key Questions
1. Pi 是否是所有现有 ACP Agent 的默认 Runner？已确认：是，旧 Claude 仅显式回滚。
2. Pi 如何与现有 ACP 结果契约兼容？已确认：现有节点 text，Workflow Agent rpc，统一归一化。
3. Session 作用域是什么？已确认：`workflow_id + agent_uid`。
4. V1 是否实现音频实际消费？已确认：否，入口保留并禁用。
5. Commit 是否保留正文历史？已确认：只保留最新正文，保留轻量 lineage。
6. 是否允许自动回退 Claude？已确认：不允许。

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 现有 ACP 使用 Pi text，新 Workflow Agent 使用 Pi rpc | 保持旧节点兼容，同时支持新 Workspace 流式体验 |
| Pi Profile 使用全局 Provider/Model | 快速接入，避免项目绑定具体模型；代价由部署环境承担 |
| 禁用 Pi 自动上下文，显式 Skill + Ryan System Prompt | 防止仓库 Agent 规则污染业务 Agent |
| Pi 原生 Session JSONL + Ryan state.json | 保持同 Agent 连续会话，避免重复维护完整消息副本 |
| 文件系统而非数据库 | 简单、可调试、复用现有 ACP workspace |
| 当前有效 Entry only + 轻量 lineage | 控制 Context 体积，保留来源索引 |
| Audio 入口保留并禁用 | 保持 UI 布局稳定，但不拖慢主链 |
| Commit 不自动 Queue | 保持用户对 DAG 执行的控制 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| `docs/adr/` 原不存在 | 1 | 按项目 domain 规则创建并记录 ADR |
| document-helper 引用的 ADR 模板路径不存在 | 1 | 使用同一文档技能的 ADR 结构自行编写，未阻塞计划 |

## Notes
- `.handoff/20260810_1724_workflow_agent_ui_ux_addendum.md` 和 `.handoff/20260810_1717_workflow_agent_workspace_v1_handoff.md` 是设计输入，不直接修改历史交接。
- Issue 发布前必须让用户确认垂直切片粒度、依赖关系和 AFK/HITL 标记。
- Issue 01 与 Issue 02 可并行；Issue 05 与 Issue 06 可并行；其余按依赖推进。
