# Findings & Decisions

## Requirements
- 根据 `skill_id` 定位 skill 目录，找不到时返回明确错误。
- 构建至少包含 `skill`、`input`、`workspace` 三段的 `ACP Context`。
- 文本输入必须写入 `input.text`。
- 模板渲染必须能替换 `skill_directory`、`input.text` 等已定义占位符。
- 交付物需要满足 issue03 的 5 条验收标准。

## Research Findings
- 当前 ACP 代码已有 `contracts.py`、`session.py`、`workspace.py`、`cli_runner.py`，但还没有 skill/context/template 三个模块。
- manifest fixture 中已经出现 `context_template`，并使用占位符：
  - `{skill_directory}`
  - `{input.text}`
- implementation plan 为 issue03 预留了：
  - `tests/acp/test_context_builder.py`
  - `ryan_comfy_utils/acp/skill_loader.py`
  - `ryan_comfy_utils/acp/context_builder.py`
  - `ryan_comfy_utils/acp/template_engine.py`
- 当前仓库没有真实 skill fixtures，因此可以在单测里用 `tempfile.TemporaryDirectory()` 动态创建 skill 目录来验证解析行为。

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| `resolve_skill_directory` 只负责 `skill_root / skill_id` 是否存在 | 保持接口简单，把更复杂的 skill 探测留给后续 |
| `build_context_payload` 输出统一 dict 结构，不提前引入 dataclass | 当前阶段以最少代码满足可测试契约 |
| `render_context_template` 先做显式替换，不引入模板引擎依赖 | issue03 只需要简单占位符渲染 |
| 本轮静态校验继续使用 `py_compile` 替代类型检查 | 仓库内依然未发现 `pyproject.toml`、`mypy.ini`、`pyrightconfig.json` 等类型检查配置 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|

## Resources
- `.scratch/acp-runtime-foundation/issues/03-acp-skill-context-builder.md`
- `.scratch/acp-runtime-foundation/PRD.md`
- `docs/superpowers/plans/2026-07-08-acp-runtime-foundation.md`
- `ryan_comfy_utils/acp/fixtures/manifests/universal_agent.json`
