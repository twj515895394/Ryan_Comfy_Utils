# Task Plan: ACP Issue02 Session And CLI Smoke

## Goal
完成 `.scratch/acp-runtime-foundation/issues/02-acp-session-cli-smoke.md`：实现最小 session/workspace 生命周期，并打通可重复的 CLI smoke 链路。

## Current Phase
Phase 2

## Phases

### Phase 1: Requirements & Discovery
- [x] 读取 issue02、PRD 与 implementation plan
- [x] 确认上一轮 issue01 已提供协议与 fixture 基础
- [x] 明确本轮不进入 context builder、runtime facade 与节点层
- **Status:** complete

### Phase 2: Planning & Structure
- [x] 为 issue02 初始化独立 planning 会话
- [x] 确定最小模块边界：`workspace.py`、`session.py`、`cli_runner.py`
- [x] 确定 smoke 测试使用本地 `python3 -c` 命令，不依赖真实 CLI
- **Status:** complete

### Phase 3: Implementation
- [x] 先写失败测试
- [x] 实现 workspace/session/cli_runner 最小代码
- [x] 保持实现不越界到 runtime/node
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
| issue02 只实现 `workspace.py`、`session.py`、`cli_runner.py` | 严格贴合 issue 边界，避免越界到后续 `issue03` / `issue04` |
| CLI smoke 采用 `python3 -c` | 本地稳定、跨环境可重复，不依赖真实 Codex/Claude CLI |

## Errors Encountered
| Error | Resolution |
|-------|------------|
