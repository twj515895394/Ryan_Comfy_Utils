# Task Plan: ACP Issue05 Assets And Result Mapping

## Goal
完成 `.scratch/acp-runtime-foundation/issues/05-asset-input-and-result-mapping.md`：支持把图片/文件输入落盘到 session `input/`，在 `ACP Context` 中引用这些路径，并通过 result mapping 把结构化 payload 映射回节点输出字段。

## Current Phase
Phase 2

## Phases

### Phase 1: Requirements & Discovery
- [x] 读取 issue05、PRD、implementation plan 与当前 ACP runtime/node 代码
- [x] 确认 issue04 已提供最小文本闭环
- [x] 明确本轮目标是资产落盘与结果映射，不扩展固定节点矩阵
- **Status:** complete

### Phase 2: Planning & Structure
- [x] 为 issue05 初始化独立 planning 会话
- [x] 确定最小模块边界：`asset_materializer.py` + `runtime.py`/`acp_nodes.py` 增量改造
- [x] 确定文本链路保持兼容，不要求节点立刻暴露完整 ComfyUI 图片输入
- **Status:** complete

### Phase 3: Implementation
- [x] 先写失败测试
- [x] 实现资产落盘与结果映射最小代码
- [x] 保持实现不破坏 issue04 的文本-only 闭环
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
| 用独立 `asset_materializer.py` 承载资源落盘逻辑 | 给后续固定绑定节点复用留清晰接缝，避免 `runtime.py` 膨胀 |
| 资产输入先支持路径拷贝 | 满足 issue05 的文件资产需求，同时保持实现简单稳定 |
| 结果映射采用 manifest 中的点路径解析 | 对齐现有 `result_mapping` 设计，不引入额外 schema |

## Errors Encountered
| Error | Resolution |
|-------|------------|
