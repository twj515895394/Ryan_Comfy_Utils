# Task Plan: ACP Issue04 Runtime And Universal Agent

## Goal
完成 `.scratch/acp-runtime-foundation/issues/04-universal-agent-minimum-loop.md`：打通 runtime facade 与 `Ryan ACP Universal Agent` 的最小文本闭环。

## Current Phase
Phase 2

## Phases

### Phase 1: Requirements & Discovery
- [x] 读取 issue04、PRD、implementation plan 与当前 ACP 模块状态
- [x] 确认 issue02 与 issue03 已提供 session/workspace、CLI、skill/context 基础
- [x] 明确本轮目标是最小 runtime facade 与最小 ComfyUI 节点
- **Status:** complete

### Phase 2: Planning & Structure
- [x] 为 issue04 初始化独立 planning 会话
- [x] 确定最小模块边界：`runtime.py`、`nodes/acp_nodes.py`、根 `__init__.py`
- [x] 确定测试避免依赖现有 ComfyUI 节点环境
- **Status:** complete

### Phase 3: Implementation
- [x] 先写失败测试
- [x] 实现 runtime facade 与 node 最小代码
- [x] 更新节点注册与 README
- **Status:** complete

### Phase 4: Testing & Verification
- [x] 运行单测确认红绿灯
- [x] 运行 `py_compile`
- [x] 跑一次当前测试全集
- **Status:** complete

### Phase 5: Delivery
- [x] 做 review 式自审
- [ ] 只提交本轮直接相关文件
- [ ] 向用户汇报结果与剩余风险
- **Status:** in_progress

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| `issue04` 只实现 `runtime.py` 与 `nodes/acp_nodes.py` 的最小文本链路 | 严格贴合 issue 边界，图片/文件输入与结果映射留给 `issue05` |
| runtime 使用现有 `prepare_workspace`、`create_session_record`、`build_context_payload`、`render_context_template`、`run_cli_command` 组合 | 尽量复用前 3 个 issue 的成果，避免重复逻辑 |
| node 测试只验证 contract 和 runtime 调用结果 | 避免测试依赖真实 ComfyUI 运行时 |

## Errors Encountered
| Error | Resolution |
|-------|------------|
