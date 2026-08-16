Status: ready-for-agent

# RYAN_CONTEXT 与 Generic Agent Queue

## 父问题

`.scratch/workflow-agent-pi-v1/PRD.md`

## 要构建什么

在 ComfyUI 中实现通用 `Ryan Workflow Agent` 节点和 `RYAN_CONTEXT` 数据合同。

节点固定保留：

- `context_01..context_08` 输入；
- `image_01..image_10` 输入；
- `workflow_id`；
- 隐藏的 `agent_uid`；
- `skill_id`、Agent 名称和 Commit revision；
- `RYAN_CONTEXT` 输出。

Queue 执行只合并当前有效上游 Context 和当前 Agent 最新 Commit，不启动 Pi，不自动执行下游 Workflow。

## 验收标准

- [ ] `RyanContext`、`RyanContextEntry`、`RyanAssetRef` 和 lineage 引用可 JSON 序列化、反序列化和校验。
- [ ] Context 禁止包含 Tensor、二进制、文件句柄和 base64 大对象。
- [ ] 固定 8 路 Context Socket 在节点刷新和 Workflow reload 后保持稳定。
- [ ] 节点注册在 `Ryan Utils / Agent` 分类下，名称为 `Ryan Workflow Agent`。
- [ ] 节点执行不调用 Pi 或其他外部 LLM。
- [ ] 串行图保留完整已提交 Canon 链路。
- [ ] fan-out 分支独立消费和提交 Context。
- [ ] fan-in 按 `entry_id` 和 `asset_id` 去重并保留 lineage。
- [ ] diamond 图不会重复传播同一个 Entry。
- [ ] 跨 Workflow Context 输入返回明确错误。
- [ ] 没有 Commit 时输出空或明确未提交状态，不把 Chat 历史传播给下游。

## 被阻塞于

- Issue 02：需要 Workflow / Agent Scope 和持久化边界。
