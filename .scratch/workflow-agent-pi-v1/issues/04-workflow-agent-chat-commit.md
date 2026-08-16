Status: ready-for-agent

# Workflow Agent Chat / Commit / Pi RPC 闭环

## 父问题

`.scratch/workflow-agent-pi-v1/PRD.md`

## 要构建什么

打通一个 Agent 的私有 Pi Session、DISCUSS Chat、COMMIT、Stop、Retry、Reset、WebSocket 事件和 RYAN_CONTEXT 更新。

语义必须严格区分：

- DISCUSS 只更新 Agent Private Chat / Draft；
- COMMIT 才生成 Canonical Artifact 和新的 Context Entry；
- Chat 消息、试错过程和未提交 Draft 不传播给下游；
- Commit 不自动 Queue；
- upstream_changed 只提示，不自动重跑或覆盖。

## 验收标准

- [ ] Chat 请求使用 `workflow_id + agent_uid` 定位唯一 Agent Session。
- [ ] 多轮 DISCUSS 能继续使用同一 Pi Session。
- [ ] DISCUSS 注入当前有效上游 Context、当前 Agent Draft 和已关联 Assets。
- [ ] Pi RPC 增量事件通过 ComfyUI WebSocket 发送到 Panel。
- [ ] 请求具有稳定的 `request_id` / `message_id`，Retry 不重复写入用户消息。
- [ ] Stop 能终止当前生成，保留已生成内容为 Draft，不生成 Commit revision。
- [ ] COMMIT 通过独立 Pi COMMIT 调用生成 Canonical Artifact、Entry ID、revision 和 lineage。
- [ ] Commit 后只有最新有效 Entry 进入下游 Context。
- [ ] Reset 清理当前私有 Chat / Draft，但保留 Commit、Assets 和 DAG Context。
- [ ] 能检测当前 Commit 依据的上游 Entry 是否已变化，并显示 `upstream_changed`。
- [ ] API 错误不泄露 API Key、完整命令、绝对路径或 Python traceback。
- [ ] 测试覆盖 Chat、Commit 前隔离、Commit 后可见、Stop、Retry、Reset 和上游变更。

## 被阻塞于

- Issue 01：需要 Pi Runner 和 RPC 能力。
- Issue 02：需要 Session / state 持久化。
- Issue 03：需要 RYAN_CONTEXT 输入输出合同。
