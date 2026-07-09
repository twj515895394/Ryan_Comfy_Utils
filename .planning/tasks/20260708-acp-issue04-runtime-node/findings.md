# Findings & Decisions

## Requirements
- 节点接收 `skill_id` 与 `user_text`。
- 节点加载 manifest/profile。
- 节点通过 runtime 发起一次 ACP Session。
- 节点返回 `response_text`、`session_dir`、`raw_result_json`。
- 单元测试覆盖 runtime 最小调用和 node contract。

## Research Findings
- 当前 ACP 层已经有：
  - `contracts.py`
  - `workspace.py`
  - `session.py`
  - `cli_runner.py`
  - `skill_loader.py`
  - `context_builder.py`
  - `template_engine.py`
- 根目录 `__init__.py` 当前直接导入现有 LLM/Prompt/Video 节点；如果在测试里直接导入根包，可能触发 ComfyUI 依赖。
- `ryan_comfy_utils/nodes/__init__.py` 目前几乎为空，适合作为测试中导入 `acp_nodes` 的稳定入口。
- 现有 manifest/profile fixtures 已足够支撑最小文本闭环。

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| `execute_text_session` 先只支持文本输入 | 与 issue04 的最小闭环目标一致 |
| runtime 优先读取 `output/result.json`，缺失时回退 `stdout` | 兼容当前最小执行链路，也为后续结构化结果预留接缝 |
| `RyanACPUniversalAgent` 默认读取 ACP fixtures | 让最小节点在本地单测中可直接跑通 |
| `raw_result_json` 返回字符串化结果 | 对齐 ComfyUI `STRING` 输出类型，避免本轮引入额外数据类型 |
| 本轮静态校验继续使用 `py_compile` 替代类型检查 | 仓库内依然未发现 `pyproject.toml`、`mypy.ini`、`pyrightconfig.json` 等类型检查配置 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|

## Resources
- `.scratch/acp-runtime-foundation/issues/04-universal-agent-minimum-loop.md`
- `.scratch/acp-runtime-foundation/PRD.md`
- `docs/superpowers/plans/2026-07-08-acp-runtime-foundation.md`
- `ryan_comfy_utils/acp/fixtures/manifests/universal_agent.json`
- `ryan_comfy_utils/acp/fixtures/profiles/local_codex.json`
