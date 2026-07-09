# Task Plan: ACP Issue03 Skill Context Builder

## Goal
完成 `.scratch/acp-runtime-foundation/issues/03-acp-skill-context-builder.md`：打通 skill 目录解析、结构化 ACP Context 构建和 context template 渲染能力。

## Current Phase
Phase 2

## Phases

### Phase 1: Requirements & Discovery
- [x] 读取 issue03、PRD、implementation plan 与当前 ACP 代码
- [x] 确认 issue03 依赖 issue01 与 issue02 已完成
- [x] 明确本轮不进入 runtime facade 与节点层
- **Status:** complete

### Phase 2: Planning & Structure
- [x] 为 issue03 初始化独立 planning 会话
- [x] 确定最小模块边界：`skill_loader.py`、`context_builder.py`、`template_engine.py`
- [x] 确定模板占位符只支持 issue03 当前需要的字段
- **Status:** complete

### Phase 3: Implementation
- [x] 先写失败测试
- [x] 实现 skill 目录解析、context payload 构建、模板渲染最小代码
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
| issue03 只实现 `skill_loader.py`、`context_builder.py`、`template_engine.py` | 严格贴合 issue 边界，避免越界到 runtime facade 和 node |
| 模板渲染优先支持 `{skill_directory}`、`{input.text}`、`{input.images}`、`{input.files}` | 对齐现有 manifest fixture 和 issue03 验收标准 |

## Errors Encountered
| Error | Resolution |
|-------|------------|
