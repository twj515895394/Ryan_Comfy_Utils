Status: ready-for-agent

# Workflow / Agent Scope 与最小持久化

## 父问题

`.scratch/workflow-agent-pi-v1/PRD.md`

## 要构建什么

建立 Workflow Agent V1 的最小身份和文件持久化边界，不引入数据库。

`workflow_id + agent_uid` 是 Agent Session 的主键：

- Workflow ID 位于 `extra.ryan_agent.workflow_id`；
- Workflow 改名保持 ID；
- Save As / Duplicate 生成新 Workflow ID；
- 复制 Agent 或更换 Skill 生成新的 Agent ID；
- Pi Session、Ryan state、最新 Commit、lineage 和 assets 均按 Workflow / Agent 隔离。

## 验收标准

- [ ] 首次使用 Agent 时能够生成并持久化 Workflow ID。
- [ ] Workflow 改名不改变 Workflow ID。
- [ ] Save As / Duplicate 生成新的 Workflow ID，默认不继承原 Workflow 的 Chat、Draft、Commit 和 Pi Session。
- [ ] Agent 节点复制会生成新的 Agent ID，不共享原 Agent Session。
- [ ] 更换 Skill 会生成新的 Agent ID 和独立 Session。
- [ ] Agent Session 目录包含 Pi Session JSONL、Ryan state、latest Commit、lineage 索引和 assets 目录。
- [ ] state 可恢复 Draft、status、commit_revision、latest_entry_id 和 Skill 信息。
- [ ] 非法 ID、绝对路径和路径穿越均被拒绝。
- [ ] 删除节点不会立即物理删除该 Agent 的孤儿数据。
- [ ] 重启进程后同一 Workflow / Agent 能读取原有状态。

## 被阻塞于

无 - 可以立即开始
