Status: ready-for-agent

# Ryan Workflow Agent V1：Pi Runtime 与工作台

## 目标

在原生 ComfyUI 中实现一个可复用的 Generic Ryan Workflow Agent：用户把多个 Agent 节点手工连成 DAG，在每个 Agent 的私有 Pi Session 中讨论，明确 Commit 后才把当前正式结果作为 `RYAN_CONTEXT` 传给下游。

## 用户故事

1. 用户可以在同一 Workflow 中放置多个 Generic Agent Node，选择不同 Skill，并通过固定 Context Socket 组成串行、fan-out、fan-in DAG。
2. 用户可以在同一 Agent 中进行连续多轮 Chat；不同 Workflow、不同 Agent 之间的私有 Chat 和 Pi Session 相互隔离。
3. 用户可以上传文本类文档、图片和视频，或通过 ComfyUI 节点输入素材；素材统一成为 `RyanAssetRef`。
4. 用户明确执行 Commit 后，当前 Agent 才产生正式 Canonical Entry；普通 Chat、Stop、失败和未提交 Draft 不会传播到下游。
5. 用户可以在右侧 Workspace 检查当前 Agent 看到的上游来源、有效 revision、资产和冲突提示。
6. 用户可以关闭 Panel、切换 Agent、重启 ComfyUI 后继续使用原有 Session 和 Draft。
7. 现有 ACP Agent 节点切换到 Pi 后，节点输入输出契约和已有工作流行为保持兼容。

## V1 范围

### Runtime

- 现有 ACP 节点默认使用 Pi `--mode text`。
- 新 Workflow Agent 使用 Pi `--mode rpc`，流式事件通过 ComfyUI WebSocket 推送。
- 使用项目 `local_pi.json`，Provider / Model 使用 Pi 全局默认。
- 禁用 Pi 自动加载项目上下文；显式加载 Skill 和 Ryan System Prompt。
- Pi 使用完整工具权限，工作目录限制在当前 Agent Session 目录。
- Pi 不可用时明确失败，不自动回退 Claude；保留旧 Claude Profile 作为显式回滚。

### Identity / Persistence

- `workflow_id` 位于 `extra.ryan_agent.workflow_id`。
- Workflow 改名保留 ID；Save As / Duplicate 创建新 ID。
- `agent_uid` 是隐藏持久化 Widget；复制节点或切换 Skill 时生成新 ID。
- Pi 原生 Session JSONL + Ryan `state.json`，文件系统存储，不引入数据库。

### Context / Commit

- 固定 8 路 Context 输入，固定 10 路图片输入。
- Context 只输出当前有效 Entry；每个 Agent / kind 只保留最新正文。
- Commit 生成新 Entry ID 和递增 revision，正文覆盖旧版本；保留轻量 lineage 索引。
- 冲突保留并提示；Commit 不自动 Queue；上游变化显示 `upstream_changed`。
- Stop 保留部分输出为 Draft；Retry 按 request ID 幂等。

### Assets

- Chat 上传与节点输入统一为 AssetRef。
- 文档支持 `.txt`、`.md`、`.json`、`.csv`。
- 视频生成元数据、关键帧和场景首帧供 Pi 消费。
- 音频入口保留并禁用，V1 不实现音频处理。
- 文本单文件 20MB、注入 Context 100,000 字符上限，超出明确提示。

### UI

- 先实现功能完整但视觉朴素的 Agent Node 与右侧 Panel，后做视觉优化。
- 单击保持原生选中；双击或“打开聊天”按钮打开 Panel。
- Panel 关闭不终止后台生成；切换 Agent 不丢 Session / Draft。
- Node 与 Panel 同步状态：idle、chatting、generating、stopped、committed、upstream_changed、error。
- Chat、Draft、Commit 明确分离；Commit 历史只显示轻量索引。

## V1 验收

- [ ] 现有 ACP Agent 默认使用 Pi text runner，原有节点输出契约不变。
- [ ] Pi CLI、Skill、工具、Session 和错误状态均可通过项目 Profile 配置或检查。
- [ ] Generic Agent Node 可放置、配置、保存、重载、复制并稳定连线。
- [ ] 串行、fan-out、fan-in 和 diamond DAG 的有效 Context 正确传播和去重。
- [ ] 不同 Workflow、不同 Agent 的 Session 完全隔离。
- [ ] DISCUSS 不影响下游；COMMIT 才产生当前有效 Entry。
- [ ] Commit、Stop、Retry、Reset、upstream_changed 行为符合合同。
- [ ] 图片、文本类文档、视频可以从 Chat 或节点输入进入 Agent；音频入口明确禁用。
- [ ] 右侧 Panel 支持历史、发送、RPC 流式、Stop、Draft、Commit、Context Inspector、附件和关闭恢复。
- [ ] 五个 Starter Skill 串行链和至少一个 fan-in Demo 可验证。
- [ ] 旧 ACP 节点、现有多图输入、Canvas 拖动/缩放/框选/连线不被破坏。

## 非目标

- Supervisor、Router、Agent Team、Agent 自动互调。
- 全 Workflow 自动共享 Chat。
- 自动 Queue 下游。
- 音频转写和音频 Agent 消费。
- PDF、DOCX、HTML 等非文本类文档解析。
- 旧 Commit 正文回滚。
- ComfyTV 深度集成和云端协作。
