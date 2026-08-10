# RYAN_CONTEXT V1 数据合同与合并规则

> 本文是 `Ryan Workflow Agent Workspace V1` 的数据层详细合同。

## 1. 设计目的

`RYAN_CONTEXT` 是所有 Workflow Agent 之间唯一的主上下文 Socket 类型。它必须同时支持：

- 串行 Agent；
- fan-out；
- 多路 fan-in；
- 任意 Skill；
- 文本与多模态资产引用；
- Commit 版本追溯；
- 去重；
- Workflow 隔离。

它不能假设系统永远只有 `creative/script/characters/scenes/shots` 这些固定阶段。

## 2. Python 类型

ComfyUI 节点层建议声明：

```python
RYAN_CONTEXT = "RYAN_CONTEXT"
```

运行时对象建议使用 dataclass/Pydantic-like plain Python model，但避免强依赖额外框架。

推荐对象：

```text
RyanContext
RyanContextEntry
RyanAssetRef
RyanContextLineage
```

## 3. RyanContext

```json
{
  "schema_version": 1,
  "workflow_id": "wf_01J...",
  "entries": [],
  "assets": [],
  "lineage": [],
  "metadata": {}
}
```

字段：

### `schema_version`

整数，V1 为 `1`。

### `workflow_id`

必填。Context 只能在同一个 Workflow 内自然合并。

### `entries`

已提交的 Canonical Context Entry 列表。

### `assets`

当前 Context 可引用的 AssetRef 集合。Entry 内只持有 asset id。

### `lineage`

记录 Context 由哪些 Commit/Entry 派生，便于去重与调试。

### `metadata`

扩展字段，不允许业务逻辑依赖未知 metadata。

## 4. RyanContextEntry

推荐结构：

```json
{
  "entry_id": "ctx_01J...",
  "workflow_id": "wf_01J...",
  "source_agent_uid": "agent_01J...",
  "source_agent_name": "剧本导演",
  "skill_id": "script-director",
  "kind": "script.direction",
  "revision": 3,
  "title": "正式剧本与表演导演稿",
  "summary": "三分钟短剧正式剧本，6 场，主冲突为……",
  "content_format": "markdown",
  "content": "# 03 SCRIPT DIRECTION ...",
  "asset_refs": ["asset_01J..."],
  "upstream_entry_ids": ["ctx_a", "ctx_b"],
  "created_at": "2026-08-10T16:00:00+08:00",
  "status": "active",
  "metadata": {}
}
```

### 4.1 `kind` 不是固定枚举

推荐内置命名：

```text
creative.story
production.design
script.direction
storyboard.plan
video.prompts
character.design
location.design
prop.design
audio.direction
review.report
research.note
```

但 Runtime 不应写死枚举。第三方 Skill 可以使用：

```text
custom.my-domain
marketing.campaign
software.requirements
```

### 4.2 Revision 语义

`revision` 针对同一个 `source_agent_uid + kind` 单调递增。

例如：

```text
agent_A creative.story v1
agent_A creative.story v2
agent_A creative.story v3
```

旧 Entry 不删除，默认选择器只把最新 active revision 注入模型。

### 4.3 status

V1 支持：

```text
active
superseded
withdrawn
```

最小实现可只写 `active`，在选择器中按 revision 取最新；后续再持久化 superseded。

## 5. RyanAssetRef

```json
{
  "asset_id": "asset_01J...",
  "workflow_id": "wf_01J...",
  "type": "image",
  "mime_type": "image/png",
  "display_name": "女主参考.png",
  "source": "chat_upload",
  "uri": "output/acp_workspace/workflows/.../assets/...",
  "size_bytes": 123456,
  "created_by_agent_uid": "agent_01J...",
  "created_at": "...",
  "metadata": {}
}
```

`type` 推荐：

```text
image
document
video
audio
text
other
```

`uri` 保存可解析的位置，不保存 base64。

## 6. Merge 算法

输入：

```python
merge_contexts(contexts: list[RyanContext]) -> RyanContext
```

### 6.1 空输入

如果所有 context 都为空，由当前节点的 `workflow_id` 创建空 Context。

### 6.2 Workflow 校验

所有非空 Context 的 `workflow_id` 必须一致。

不一致时：

```text
raise WorkflowContextMismatch
```

V1 不允许通过普通连线隐式跨项目导入 Context。以后如需要，单独设计 Explicit Context Import Node。

### 6.3 Entry 去重

按 `entry_id` 去重，而不是按文本内容去重。

原因：同一 Entry 可能沿两条上游支路重新汇聚。

示例：

```text
       -> Agent B ->
Agent A            -> Agent D
       -> Agent C ->
```

Agent A 的 Commit 会同时存在于 B 与 C 的 Context 中；D fan-in 时必须只保留一次 A Entry。

### 6.4 Asset 去重

按 `asset_id` 去重。

### 6.5 顺序

Context 存储层不要求严格依赖数组顺序表达优先级。

推荐稳定排序：

```text
created_at
then entry_id
```

模型注入顺序由 Context Selector 决定。

### 6.6 Lineage

lineage 以唯一 commit/entry id 合并。

## 7. Append Current Commit

Agent DAG 执行：

```python
upstream = merge_contexts(context_slots)
commit = get_latest_commit(workflow_id, agent_uid)
output = append_commit(upstream, commit)
```

`append_commit`：

1. 校验 workflow_id；
2. 将 commit 转换为 RyanContextEntry；
3. 如果 entry_id 已存在则不重复追加；
4. 合并 commit asset refs 对应 AssetRef；
5. 更新 lineage；
6. 返回新对象，不修改输入 Context。

## 8. Fan-in 示例

### 8.1 不同专业 Agent 合并

```text
Creative Agent ---- context_01 ---┐
Production Agent -- context_02 ---+--> Storyboard Agent
Script Agent ------ context_03 ---┘
```

Storyboard 输入 Context 可能包含：

```text
creative.story
production.design
script.direction
```

Storyboard Skill 根据自己的 `accepts_context_kinds` 优先读取这三类。

### 8.2 同一类型多个来源

例如两个 Reviewer 都产出：

```text
review.report
```

Merge 不覆盖任何一个，因为 `source_agent_uid` 不同。

当前 Agent 应看到两个来源并自行综合，必要时提示冲突。

## 9. Context Selector

完整 Context 用于追溯；实际模型调用不应无脑全塞。

V1 选择规则：

1. 丢弃 `withdrawn`；
2. 对同一个 `source_agent_uid + kind` 只保留最高 revision；
3. 优先选择当前 Skill `accepts_context_kinds` 中声明的 kind；
4. 其余 kind 可用摘要形式附加；
5. 永远保留来源 Agent、Skill、revision 标识。

推荐编译格式：

```text
# Upstream Context

## [creative.story] 创意策划 / v2
Source Agent: agent_x
Summary: ...
Content:
...

## [production.design] 美术设计 / v1
...
```

## 10. 冲突检测 V1

Merge 层只检测结构冲突，不做语义自动覆盖。

结构冲突包括：

- workflow_id 不一致；
- 相同 entry_id 内容不一致；
- 相同 asset_id 指向不同 uri。

语义冲突例如：

```text
Agent A：女主短发
Agent B：女主长发
```

V1 保留两条 Entry，由下游 Agent 在 DISCUSS 阶段指出。

## 11. Chat History 不属于 RYAN_CONTEXT

不要把整个聊天消息数组放进 Context。

```text
Private Chat History
  belongs to workflow_id + agent_uid session

RYAN_CONTEXT
  contains only committed canonical artifacts
```

这样能避免：

- 大量 token 污染；
- 用户已否定草案向下游泄漏；
- Agent 私有推敲过程传播；
- 多支路 context 爆炸。

## 12. Commit 模式上下文

Commit 请求应携带：

```text
upstream_context
current_private_chat
current_agent_assets
skill_id
agent_contract
```

最终 Commit Entry 的 `upstream_entry_ids` 必须记录本次正式产物所依据的上游最新 Entry。

这样后续能够回答：

> 这个分镜版本是基于哪个剧本版本生成的？

## 13. Skill Contract 与 Context

推荐 `agent-contract.json`：

```json
{
  "schema_version": 1,
  "display_name": "分镜导演",
  "recommended_agent_name": "分镜导演",
  "accepts_context_kinds": [
    "creative.story",
    "production.design",
    "script.direction"
  ],
  "produces_context_kind": "storyboard.plan",
  "discussion_mode": true,
  "commit_mode": true
}
```

注意：这不是节点输入类型定义。

无论 Skill contract 写什么，节点 Socket 都还是：

```text
RYAN_CONTEXT -> Ryan Workflow Agent -> RYAN_CONTEXT
```

## 14. 影视业务只是 Starter Domain

影视链可以自然表示：

```text
creative.story
production.design
script.direction
storyboard.plan
video.prompts
```

但底层不依赖这些 key，因此同一架构也可以表达：

```text
product.requirements
architecture.design
api.contract
implementation.plan
```

不需要修改 Context model。

## 15. JSON 序列化要求

Context 必须可 JSON 序列化，禁止在结构中直接放：

- torch.Tensor；
- PIL Image；
- file handle；
- subprocess object；
- 大型二进制；
- base64 媒体。

ComfyUI IMAGE 等直接输入在 Agent API/Commit 前先 materialize 成 AssetRef。

## 16. 建议测试用例

必须至少覆盖：

1. empty context；
2. A -> B 串行；
3. A fan-out 到 B/C，再 fan-in 到 D，A Entry 只出现一次；
4. B/C 产生不同 kind，D 同时可见；
5. 同 Agent v1/v2，Selector 只注入 v2；
6. 两个 Workflow context 合并时报错；
7. 相同 asset id 重复路径去重；
8. entry_id 相同但内容不同时报结构错误；
9. Chat History 不出现在 serialized context；
10. Commit upstream_entry_ids 可追溯。

## 17. V1 类型关系总结

```text
ComfyUI Workflow
  └── workflow_id

Ryan Workflow Agent
  ├── agent_uid
  ├── skill_id
  ├── private chat session
  └── latest commit

RYAN_CONTEXT
  ├── committed entries[]
  ├── assets[]
  └── lineage[]

DAG Connection
  └── controls which RYAN_CONTEXT reaches which Agent
```
