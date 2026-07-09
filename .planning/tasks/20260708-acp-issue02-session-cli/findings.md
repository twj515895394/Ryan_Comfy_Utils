# Findings & Decisions

## Requirements
- 实现最小 session/workspace 生命周期。
- 为一次 CLI 执行提供 smoke 级可验证链路。
- 单测必须不依赖真实 Codex/Claude CLI。
- 交付物需要满足 issue02 中列出的 5 条验收标准。

## Research Findings
- `issue01` 已提供 `ryan_comfy_utils/acp/contracts.py` 和 fixtures，可作为后续 runtime 的协议基线。
- 当前仓库还没有 `session.py`、`workspace.py`、`cli_runner.py`。
- implementation plan 已为 issue02 预留：
  - `tests/acp/test_session_workspace.py`
  - `ryan_comfy_utils/acp/session.py`
  - `ryan_comfy_utils/acp/workspace.py`
- `cli_runner.py` 在总 plan 中原本放到 task4，但 issue02 的验收标准已经要求 CLI smoke 返回 stdout/stderr/returncode，因此本轮需要提前实现最小 runner。

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| session 目录结构固定为 `workspace_root / "sessions" / session_id` | 对齐 PRD 与 ACP 文档中 `sessions/session_xxx/` 结构 |
| workspace 目录本轮至少创建 `input/`、`output/`、`logs/` | 直接对应 issue02 验收标准 |
| session metadata 与 context 使用 UTF-8 JSON 落盘 | 简单、稳定、便于后续调试与 runtime 复用 |
| `cli_runner` 只返回 `returncode`、`stdout`、`stderr` | 满足 issue02，不提前设计更复杂执行模型 |
| 本轮静态校验使用 `py_compile` 替代类型检查 | 仓库内未发现 `pyproject.toml`、`mypy.ini`、`pyrightconfig.json` 等类型检查配置 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|

## Resources
- `.scratch/acp-runtime-foundation/issues/02-acp-session-cli-smoke.md`
- `.scratch/acp-runtime-foundation/PRD.md`
- `docs/superpowers/plans/2026-07-08-acp-runtime-foundation.md`
