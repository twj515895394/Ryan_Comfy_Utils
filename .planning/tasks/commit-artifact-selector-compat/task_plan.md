# Task Plan: Commit 产物兼容与 Selector 展示

## Goal

将旧版 `id/prompt/constraint` 产物规范化为 Artifact Bundle，并让 Agent → Selector → STRING 链路可读取真实提示词。

## Phases

### Phase 1: 调查
- [x] 读取问题、解析器、服务与现有回归测试
- [x] 确认真实旧 Production Design 使用 `revision`、`id`、`role`、`prompt`、`constraint`
- **Status:** complete

### Phase 2: 实现
- [x] 规范化旧字段并保留明确错误状态
- [x] 修正 Commit Prompt 合同
- [x] 让 Context 合并与 Selector 读取规范化 Bundle
- [x] 补充行为回归测试
- **Status:** complete

### Phase 3: 验证
- [x] 运行专项测试与语法检查
- [x] 运行完整测试套件并记录环境阻塞
- [x] 完成代码审查并修复发现
- [ ] 提交当前分支改动
- **Status:** in_progress

## Decisions

- 规范化在 `workflow_agent.artifacts` 集中完成，避免 Commit、Context、Selector 各自维护别名映射。
- 旧产物只有在能确定 ID、kind、label 和文本来源时才转换；无法安全转换仍返回 `invalid`，不伪造内容。
- Context 追加时将旧正文中的合法 artifact block 转换进 Entry metadata，使前端动态选项与后端节点共享同一份合同。
- 不修改 Agent Chat、Session 或外部存储协议。

## Verification

- `python -m unittest tests.workflow_agent.test_artifacts tests.workflow_agent.test_context tests.workflow_agent.test_chat_commit tests.nodes.test_artifact_selector_node -v`
- `python -m py_compile ...`
- `python -m unittest discover -s tests -p "test_*.py" -q`

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|
| 完整测试套件有 4 个导入错误 | `python -m unittest discover -s tests -p "test_*.py" -q` | 缺少既有环境依赖 `aiohttp`、`openai`、`scenedetect`；专项测试仍通过。 |

- `python -m unittest tests.workflow_agent.test_artifacts tests.workflow_agent.test_context tests.workflow_agent.test_chat_commit tests.nodes.test_artifact_selector_node -v`
- `python -m py_compile ...`
- `python -m unittest discover -s tests -p "test_*.py" -q`
