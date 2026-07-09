# Findings & Decisions

## Requirements
- runtime 需要将图片或文件输入保存到 session `input/` 目录。
- `ACP Context` 需要引用这些输入资源路径。
- result mapping 需要把结构化 payload 映射回节点输出字段。
- 至少一组单元测试要覆盖资源路径注入和结果字段映射。
- 文本-only 闭环不能被破坏。

## Research Findings
- 当前 `execute_text_session` 还没有任何资产落盘逻辑，`build_context_payload` 始终接收空的 `image_paths/file_paths`。
- 当前 node 直接从 `result["outputs"]["response_text"]` 和 `result["raw_result_json"]` 取值，没有使用 manifest 的 `result_mapping`。
- 现有 manifest fixture 已包含：
  - `response_text -> outputs.response_text`
  - `raw_result_json -> raw_result_json`
- 现有 runtime 测试已验证文本-only 闭环，可作为回归保护。

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 资产输入使用源文件路径列表而不是原始二进制 | 当前最小实现更容易测试，也满足 “runtime 可消费的文件资产” 要求 |
| materializer 输出使用 session 相对路径字符串 | 便于写入 context 并减少绝对路径耦合 |
| result mapping 缺失路径时返回空字符串 | 对齐当前节点 `STRING` 输出类型，避免抛异常破坏最小闭环 |
| 本轮静态校验继续使用 `py_compile` 替代类型检查 | 仓库内依然未发现 `pyproject.toml`、`mypy.ini`、`pyrightconfig.json` 等类型检查配置 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|

## Resources
- `.scratch/acp-runtime-foundation/issues/05-asset-input-and-result-mapping.md`
- `.scratch/acp-runtime-foundation/PRD.md`
- `docs/superpowers/plans/2026-07-08-acp-runtime-foundation.md`
- `ryan_comfy_utils/acp/runtime.py`
- `ryan_comfy_utils/nodes/acp_nodes.py`
