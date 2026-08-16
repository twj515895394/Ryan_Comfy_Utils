# ADR-0001：Workflow Agent V1 使用 Pi Runtime

- **状态**：Accepted
- **日期**：2026-08-10
- **范围**：Ryan Workflow Agent V1、现有 ACP Agent Runner 迁移

## 背景

当前 ACP Runtime 通过 Profile 调用外部 CLI，内部结果契约已经统一为 `status + outputs`，但默认 Profile 仍然使用 Claude CLI。Workflow Agent V1 需要支持长期 Agent Session、DISCUSS / COMMIT、DAG Context、右侧 Workspace 和 Pi 流式运行时。

用户确认后续 Agent Runtime 使用 Pi，而不是把 Claude 作为默认运行时。现有工作流必须保持节点输入输出契约不变。

## 决策

### 1. Runner

- 现有 ACP 节点默认切换到 Pi `--mode text`。
- 新 Workflow Agent 使用 Pi `--mode rpc`，由后端通过 ComfyUI 原生 WebSocket 转发事件。
- 两种模式最终都归一化为现有 ACP 结果契约：

```json
{
  "status": "ok",
  "outputs": {
    "response_text": "..."
  }
}
```

- Pi 使用项目级 `local_pi.json`，但 Provider / Model 使用 Pi 全局默认配置。
- Pi 启动前检查 CLI、认证和所需参数能力，不满足时明确失败。
- Pi 失败时不自动回退 Claude；只有用户显式选择旧 Claude Profile 时才回滚。
- `local_claude_cli.json` 保留为显式回滚配置。

### 2. Prompt 与工具

- 使用 `--no-context-files`，不自动加载项目 `AGENTS.md` / `CLAUDE.md`。
- 使用 `--skill <skill_directory>` 显式加载 Skill。
- 使用 Ryan System Prompt，明确 DISCUSS、COMMIT、Context 来源和 Commit 边界。
- 使用完整 Pi 工具权限，但进程工作目录限定为当前 `workflow_id + agent_uid` 的独立 Session 目录。

### 3. Workflow / Agent 身份

- `workflow_id` 持久化于 `extra.ryan_agent.workflow_id`。
- Workflow 改名保留 `workflow_id`。
- Save As / Duplicate 创建新的 `workflow_id`，不继承原 Workflow 的 Chat、Draft、Commit 或 Pi Session。
- `agent_uid` 使用隐藏持久化 Widget。
- 复制 Agent 节点、切换 Skill 都生成新的 `agent_uid` 和独立 Pi Session。
- 删除节点时保留孤儿数据，不立即物理删除。

### 4. Session 与存储

- Session 作用域是 `workflow_id + agent_uid`。
- 使用文件系统，不引入数据库。
- 使用 Pi 原生 Session JSONL 保存连续多轮 Chat。
- 使用 Ryan `state.json` 保存 Draft、Commit 状态、revision 和索引。
- Reset 只清理私有 Chat / Draft，不删除已提交 Commit。
- Retry 使用同一 `message_id / request_id`，避免重复追加用户消息。

### 5. Context / Commit

- 固定 8 路 `RYAN_CONTEXT` 输入。
- `RYAN_CONTEXT.entries` 只包含当前有效 Entry；每个 `source_agent_uid + kind` 只保留最新正文。
- 每次 Commit 生成新的 `entry_id`，revision 单调递增，但磁盘只保留最新正文。
- 保留轻量 lineage 索引：`entry_id`、来源 Agent、kind、revision、时间。
- Commit 使用独立 `COMMIT` 调用；Skill 输出 Markdown，Ryan 包装 Entry 元数据。
- Chat / Commit 不自动触发 ComfyUI Queue。
- 上游更新保留当前 Session 和 Draft，只标记 `upstream_changed`；下一次调用使用最新上游 Context。
- Context 冲突保留所有来源并提示，不静默覆盖。

### 6. Assets

- Chat 上传和 ComfyUI 节点输入统一转换为 `RyanAssetRef`。
- 固定 `image_01..image_10` 图片输入。
- 视频和文档使用多行路径型 `STRING` 输入。
- 文档 V1 支持 `.txt`、`.md`、`.json`、`.csv`。
- 视频预处理为元数据、关键帧和场景首帧。
- 音频入口保留并置灰禁用，V1 不做音频转写和 Agent 消费。
- 文本单文件上限 20MB，注入 Context 上限 100,000 字符，超出时明确提示。

### 7. UI

- 先实现功能完整、视觉朴素的 Node 和右侧 Workspace，再做视觉 Polish。
- 单击保留 ComfyUI 原生选中；双击或节点按钮打开 Panel。
- Panel 关闭不终止后台 Pi；重新打开恢复 Session、Draft 和生成状态。
- Stop 保留已生成部分为 Draft，禁止自动 Commit。
- Audio 入口保留并禁用。
- Commit 历史只显示轻量索引，不显示旧正文、不提供回滚。

## 后果

正面：

- 现有 ACP 节点可以保留输入输出契约，只更换 Runner Profile。
- Pi 不会被仓库开发规则隐式污染。
- Workflow / Agent 隔离边界明确，Session 实现保持简单。
- 新 Workflow Agent 可获得 RPC 流式能力，同时兼容旧 ACP 文本节点。

代价：

- 不同机器的 Pi 全局 Provider / Model 可能不同，结果可复现性由部署环境负责。
- 只保留最新 Commit 正文，V1 不支持旧正文回滚。
- 音频入口存在但暂不具备实际处理能力。
- Pi Text / RPC 需要两套输出适配，但共享统一内部结果契约。

## 不采用的方案

- 不让 Chat 消息自动触发 ComfyUI Queue。
- 不自动回退 Claude。
- 不把 Pi Session 作为 DAG Commit 的唯一业务状态源。
- 不引入数据库。
- 不做动态 Context Socket。
- 不在 V1 实现 Supervisor、Router、Agent Team、全局 Workflow Memory 或 ComfyTV 深度集成。
