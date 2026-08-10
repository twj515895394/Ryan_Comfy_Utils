# Ryan Workflow Agent Workspace V1 详细设计

> 状态：V1 设计基线
> 日期：2026-08-10
> 目标仓库：`Ryan_Comfy_Utils`
> 核心原则：**Workflow = Project Scope；Agent = 独立会话；DAG = Context 传播路径；Chat != Commit。**

## 1. 背景与目标

当前 `Ryan_Comfy_Utils` 已具备 ACP Runtime、Selectable Skill、session/workspace、多图输入、固定 Prompt Agent 等基础能力。下一阶段不是再做一套自动 Multi-Agent 编排器，而是在 ComfyUI 原生 DAG 上增加一个可交互的 Agent 节点：用户逐个与 Agent 对话，确认后将结果 Commit 到节点输出，再沿工作流连线传给下游 Agent。

V1 只做显式 DAG，不做 Agent 自主互调、不做 Supervisor/Router、不做自动多 Agent 群聊。

目标体验：

```text
创意 Agent ──┐
             ├──> 剧本 Agent ──> 分镜 Agent ──> 视频提示词 Agent
资产 Agent ──┘
```

用户点击任一 Agent 节点，在右侧打开该节点自己的聊天面板。聊天可多轮、可上传图片/文档/视频/音频；只有用户执行「确认并提交」后，当前 Agent 的正式产物才进入 `RYAN_CONTEXT` 并对下游可见。

## 2. 最重要的架构决策

### 2.1 Workflow 就是 Project

V1 不新增独立 Project 实体。一个 ComfyUI Workflow 就是一个项目边界：

- Workflow 内所有 Agent Session、Commit Snapshot、上传素材都归属于同一个 `workflow_id`；
- 不同 Workflow 默认完全隔离；
- Workflow 重命名、另存为、文件名变化不能影响身份，因此不能以文件名作为主键；
- `workflow_id` 应持久化在 workflow extra metadata 中，首次使用 Ryan Workflow Agent 时自动生成。

推荐结构：

```json
{
  "extra": {
    "ryan_agent": {
      "schema_version": 1,
      "workflow_id": "wf_01J..."
    }
  }
}
```

### 2.2 一个通用 Agent 节点，不按角色硬编码节点类型

V1 的核心节点应是一个通用节点，例如：

```text
Ryan Workflow Agent
```

Agent 的角色由 `skill_id` 决定，不为创意、编剧、角色、场景、分镜、视频提示词分别实现 Python 节点类。

因此下面这些都只是同一种节点的不同 Skill 配置：

```text
Ryan Workflow Agent(skill=creative-story-planner)
Ryan Workflow Agent(skill=production-designer)
Ryan Workflow Agent(skill=script-director)
Ryan Workflow Agent(skill=storyboard-director)
Ryan Workflow Agent(skill=video-prompt-director)
Ryan Workflow Agent(skill=任意未来自定义 Skill)
```

这解决了“不同 Agent 输入输出不一样是否意味着固定几个 Agent”的问题：**ComfyUI Socket 类型固定，Skill 的语义合同可变。**

### 2.3 不把 `creative/script/characters/...` 设计成 RYAN_CONTEXT 的固定一级字段

V1 禁止把上下文设计成：

```text
RYAN_CONTEXT
├── creative
├── script
├── characters
├── locations
├── scenes
└── shots
```

这种结构适合某个影视产品，但会把 Ryan Agent Runtime 锁死在固定阶段和固定 Agent 上。

正确方式是通用 Envelope + 可扩展 Entry：

```text
RYAN_CONTEXT
├── workflow_id
├── entries[]
├── assets[]
├── lineage[]
└── metadata
```

每个 Entry 用 `kind` 表示语义，例如：

```text
creative.story
production.design
script.direction
storyboard.plan
video.prompts
character.design
location.design
research.note
custom.xxx
```

`kind` 是 Skill 语义，不是 Python 数据结构字段。未来任何 Skill 都能生产新的 kind，无需修改 RYAN_CONTEXT 类。

### 2.4 DAG 决定可见范围，Workflow 只决定生命周期边界

同一个 Workflow 中，不是所有 Agent 自动互相共享全部内容。

规则：

- Workflow 决定“这些 Agent 属于同一个项目”；
- 连线决定“这个 Agent 能看到哪些上游正式信息”；
- 未连接的 Agent 默认互不可见；
- Private Chat History 永远不会因为在同一个 Workflow 就自动注入其他 Agent。

一句话：

> **Workflow 管归属，DAG 管知识传播。**

### 2.5 Chat 与 Workflow Execution 分离

不能让“用户发一条聊天消息”触发整个 ComfyUI Queue。

V1 必须分成两个运行面：

#### Interactive Plane

右侧聊天面板直接调用 Ryan Agent HTTP/SSE API：

```text
User Message
  -> Agent Session
  -> ACP Runtime
  -> LLM/CLI
  -> Chat Response
```

它只更新该 Agent 的 Private Session，不执行下游节点。

#### DAG Plane

ComfyUI Queue 执行节点时，`Ryan Workflow Agent` 不再次与模型聊天，只做：

```text
读取上游 RYAN_CONTEXT
+ 读取该 Agent 最新 Commit Snapshot
-> merge
-> 输出新的 RYAN_CONTEXT
```

这样 Agent 节点既是交互会话锚点，也是 DAG 中确定性的 Context 节点。

## 3. Agent 节点合同

### 3.1 推荐节点外观

```text
┌──────────────────────────────┐
│ 🤖 剧本导演                  │
│ ● 已提交 v3                  │
│                              │
│ Skill: script-director       │
│ 💬 18 messages  📎 4 assets │
│                              │
│ [打开聊天] [重新开始]        │
└──────────────────────────────┘
   ▲  ▲  ▲              │
 ctx ctx ctx          RYAN_CONTEXT
```

### 3.2 输入 Socket

V1 推荐保留固定数量 Context Slot，前端只隐藏未使用项，不动态删除/重排 Socket，避免工作流刷新或参数变化时连线索引漂移。

推荐：

```text
context_01: RYAN_CONTEXT optional
context_02: RYAN_CONTEXT optional
context_03: RYAN_CONTEXT optional
context_04: RYAN_CONTEXT optional
context_05: RYAN_CONTEXT optional
context_06: RYAN_CONTEXT optional
context_07: RYAN_CONTEXT optional
context_08: RYAN_CONTEXT optional
```

V1 8 路足够覆盖多 Agent fan-in；后续如需扩容，增加新尾部 slot，不重排旧 slot。

直接素材输入继续支持已有图片槽位，并逐步扩展统一 Asset Bundle：

```text
image_01..image_10: IMAGE optional
asset_bundle: RYAN_ASSET_BUNDLE optional (后续)
```

节点属性/widget：

```text
skill_id
agent_name
agent_uid (hidden/persisted)
workflow_id (hidden/injected)
commit_revision (hidden, commit 后递增)
profile_path
skill_root
```

### 3.3 输出 Socket

核心输出：

```text
context: RYAN_CONTEXT
response_text: STRING        # 最新正式 Commit 的可读文本
session_dir: STRING          # 调试/兼容
```

可选调试输出：

```text
context_json: STRING
```

不要为每个 Skill 定义不同 ComfyUI RETURN_TYPES。角色差异由 context entry kind 表达。

## 4. Skill 语义合同

Skill 可以声明自己更适合消费/生产什么上下文，但这只是语义约束，不改变节点 Socket。

推荐每个可交互 Skill 增加 `agent-contract.json`：

```json
{
  "schema_version": 1,
  "display_name": "剧本导演",
  "recommended_agent_name": "剧本导演",
  "accepts_context_kinds": ["creative.story", "production.design"],
  "produces_context_kind": "script.direction",
  "discussion_mode": true,
  "commit_mode": true
}
```

V1 默认把 `accepts_context_kinds` 作为 UI 提示和质量检查，不做强制阻塞；用户可以从零与任何 Agent 开始。

## 5. 两种 Skill 执行模式

交互式 Agent Skill 必须理解两种运行模式。

### 5.1 DISCUSS

用户正常聊天时 Runtime 注入：

```text
RYAN_AGENT_MODE=DISCUSS
```

Skill 应：

- 围绕当前角色与用户讨论；
- 阅读当前 DAG 上游 Context；
- 可以提出方案、修改、比较；
- 不把每一句建议都视为项目 Canon；
- 不生成新的下游可见 Commit。

### 5.2 COMMIT

用户点击「确认并提交」时 Runtime 注入：

```text
RYAN_AGENT_MODE=COMMIT
```

Skill 应：

- 综合上游 Context；
- 综合本 Agent 当前 Chat History 中用户已经确认的要求；
- 排除已被用户否定/废弃的草案；
- 产出一个自洽、可供下游直接消费的 Canonical Artifact；
- 输出的 artifact kind 来自 `agent-contract.json`。

Commit 是“从私有讨论生成正式快照”的边界。

## 6. Fan-in：多个 Agent 合并输入

这是 V1 必须原生支持的场景。

示例：

```text
创意 Agent ────────┐
角色/美术 Agent ───┼──> 分镜 Agent
剧本 Agent ────────┘
```

分镜 Agent 的 `context_01..03` 都是同一种 `RYAN_CONTEXT`，但其中包含不同 Entry kind。

节点执行时：

```text
merge(context_01, context_02, context_03)
  -> deduplicate entries by entry_id
  -> deduplicate assets by asset_id
  -> validate same workflow_id
  -> keep lineage
  -> append current agent committed entry
  -> output new RYAN_CONTEXT
```

不需要为“角色输入”“剧本输入”“场景输入”分别建立不同 Python 类型。

### 6.1 为什么不直接把上游文本拼成一个 STRING

STRING 会丢失：

- 来源 Agent；
- Commit 版本；
- 资产引用；
- Entry kind；
- lineage；
- 去重能力；
- 冲突追踪；
- 后续按需裁剪上下文的能力。

所以 Agent 链路应传 `RYAN_CONTEXT`，最终真正调用模型时再由 Context Builder 编译成文本/多模态输入。

## 7. Context 传播不是覆盖，而是追加不可变 Entry

每次 Commit 产生一个新的不可变 Entry：

```text
upstream entries
+ current commit entry
= downstream context
```

如果 Agent 重新 Commit：

```text
script.direction v1
script.direction v2
```

V1 可以在 context 中同时保留 lineage，但 Context Builder 默认只选择同一 `source_agent_uid + kind` 的最新有效版本给模型，旧版本留作追溯。

不要原地改写旧 Entry。

## 8. 多模态资产

聊天上传与节点连线最终应统一成 AssetRef。

来源可以是：

```text
chat_upload
comfy_node
workflow_asset
external_path
```

AssetRef 最低字段：

```json
{
  "asset_id": "asset_01J...",
  "type": "image",
  "mime_type": "image/png",
  "source": "chat_upload",
  "uri": "...",
  "display_name": "女主参考图.png",
  "created_by_agent_uid": "agent_01J..."
}
```

`RYAN_CONTEXT.entries[].asset_refs` 只保存 `asset_id`，不在 Context JSON 内复制 base64 或大文件内容。

## 9. 会话与持久化

逻辑主键：

```text
workflow_id + agent_uid
```

建议 workspace：

```text
output/acp_workspace/
└── workflows/
    └── <workflow_id>/
        ├── workflow.json
        ├── assets/
        └── agents/
            └── <agent_uid>/
                ├── agent.json
                ├── chat/
                │   └── messages.jsonl
                ├── commits/
                │   ├── 000001.json
                │   └── 000002.json
                └── input/
```

`agent_uid` 不能只使用 ComfyUI node id。node id 用于图连接，`agent_uid` 用于 Session 稳定身份。

节点复制时建议默认生成新的 `agent_uid`，避免两个画布节点意外共享同一聊天历史；后续可以提供“复制并继承 Session”的显式操作。

## 10. Commit Snapshot

Commit 建议保存：

```json
{
  "commit_id": "commit_01J...",
  "workflow_id": "wf_01J...",
  "agent_uid": "agent_01J...",
  "skill_id": "script-director",
  "kind": "script.direction",
  "revision": 3,
  "content": "...canonical markdown...",
  "asset_refs": ["asset_x"],
  "upstream_entry_ids": ["ctx_a", "ctx_b"],
  "created_at": "..."
}
```

下游只消费 Commit，不消费上游 Agent 的 Private Chat History。

## 11. Context Builder

当前 ACP 已有 `context_builder.py`，V1 应在其上方增加 Workflow Context 编译层，而不是把所有逻辑塞进节点类。

推荐模块：

```text
ryan_comfy_utils/acp/workflow_agent/
├── models.py
├── context_merge.py
├── context_select.py
├── repository.py
├── workflow_identity.py
├── agent_session_service.py
├── commit_service.py
├── asset_service.py
└── context_prompt_builder.py
```

职责：

- `models.py`：RYAN_CONTEXT / Entry / AssetRef / CommitSnapshot；
- `context_merge.py`：fan-in 合并、去重、workflow_id 校验；
- `context_select.py`：选择每个 Agent/Kind 最新有效 Entry；
- `repository.py`：本地 workspace 读写；
- `agent_session_service.py`：聊天历史；
- `commit_service.py`：DISCUSS -> COMMIT；
- `context_prompt_builder.py`：把上游 Entry + AssetRef 编译成 ACP 调用输入。

现有 `execute_text_session()`、Skill Resolver、Profile、Asset Materializer 应继续复用，不重写 ACP Runner。

## 12. 后端 API（V1）

建议使用 ComfyUI PromptServer 增加 `/ryan/agent/*` 路由。

### 12.1 Skills

```text
GET /ryan/agent/skills
```

返回 Skill + agent-contract 元数据。

### 12.2 Agent Session

```text
GET /ryan/agent/workflows/{workflow_id}/agents/{agent_uid}
POST /ryan/agent/workflows/{workflow_id}/agents/{agent_uid}/reset
```

### 12.3 Chat

```text
POST /ryan/agent/chat
```

请求包含：

```text
workflow_id
agent_uid
skill_id
message
upstream_context
asset_refs
```

第一版可先 blocking；UI 体验稳定后切 SSE。若直接做流式，推荐：

```text
POST /ryan/agent/chat/stream
```

### 12.4 Upload

```text
POST /ryan/agent/assets
```

支持图片、文档、视频、音频，落盘后返回 AssetRef。

### 12.5 Commit

```text
POST /ryan/agent/commit
```

Commit 成功后返回：

```text
commit_id
revision
kind
content_preview
```

前端同时更新节点隐藏 widget `commit_revision`，让 ComfyUI 知道节点状态发生变化。

## 13. ComfyUI Queue 执行语义

`Ryan Workflow Agent.run()` 不应该默认调用 LLM。

伪代码：

```python
def run(context_01=None, ..., context_08=None, workflow_id="", agent_uid="", commit_revision=0):
    upstream = merge_contexts([...])
    commit = repository.get_latest_commit(workflow_id, agent_uid)
    output = append_commit(upstream, commit) if commit else upstream
    return output, commit.content if commit else "", session_dir
```

如果没有上游、也没有 Commit：

- 可以输出空 RYAN_CONTEXT；
- UI 显示“未提交”；
- 不自动调用模型。

建议实现 `IS_CHANGED` 或通过 `commit_revision` hidden widget 参与节点输入，使 Commit 更新后重新 Queue 能正确刷新下游。

## 14. 右侧 Chat Panel

V1 Panel 分四区：

```text
[Agent Header]
Agent 名称 / Skill / 状态 / Commit revision

[Upstream Context]
来源 Agent、kind、revision、文字/资产数量，可展开查看

[Chat History]
仅当前 Agent 私有对话

[Composer]
文件 / 图片 / 视频 / 音频上传 + 输入框 + 发送
[确认并提交]
```

### 14.1 打开/关闭

- 双击 Agent 或点击「打开聊天」打开右侧 Panel；
- 关闭 Panel 后画布仅保留 Agent 节点；
- 点击不同 Agent，Panel 切换到不同 `workflow_id + agent_uid` Session。

### 14.2 上下文可见性必须透明

Panel 应明确显示：

```text
当前 Agent 可见：
- 创意策划 / creative.story / v2
- 美术设计 / production.design / v1
- 6 张图片 / 1 个 PDF

不包含：
- 上游 Agent 未提交聊天记录
```

这是复杂 DAG 调试的关键功能。

## 15. 与当前 Ryan_Comfy_Utils 的兼容策略

V1 不替换现有：

- `RyanACPUniversalAgent`；
- Image Prompt / Video Prompt / Image Analyze / MiniMax H3 固定 Agent；
- 现有 Skill Resolver；
- 现有 ACP CLI Runtime；
- 现有多图 Slot；
- 现有 Prompt 导出能力。

新增 `Ryan Workflow Agent` 与当前 Universal Agent 并存。

当前 Universal Agent 属于“Queue 时执行 LLM”的执行节点；Workflow Agent 属于“交互 Session + Commit Snapshot”的新模型。待 V1 稳定后再评估是否统一底层调用入口。

## 16. Starter Skill Pack

从 `scene_forge/codex/v10-text-skill-pipeline` 迁移并适配以下 5 个 Skill 作为 V1 示例：

```text
creative-story-planner  -> creative.story
production-designer     -> production.design
script-director         -> script.direction
storyboard-director     -> storyboard.plan
video-prompt-director   -> video.prompts
```

这些不是固定 Agent 类型，而是验证同一 Generic Agent Node 可以完成不同语义阶段的 Starter Skills。

## 17. 推荐 V1 影视 DAG

串行最小链：

```text
Creative
  -> Production Design
  -> Script Direction
  -> Storyboard
  -> Video Prompts
```

允许 fan-out / fan-in：

```text
                    ┌-> Character Design Agent --┐
Creative Agent -----+                             +-> Storyboard Agent
                    └-> Script Agent ------------┘
```

只要所有节点输出 `RYAN_CONTEXT`，不需要新增任何专用 Merge 数据类型。

## 18. 冲突策略

V1 不做自动“事实数据库”。如果多个上游 Context 对同一事实冲突：

- Merge 层不静默覆盖；
- 保留两个来源 Entry；
- Context Builder 标记 conflict hint；
- 当前 Agent 在讨论中向用户指出冲突；
- 用户确认后由当前 Agent Commit 一个新的权威结果。

例如两个 Agent 对角色服装不一致，不应按连接顺序“最后一个覆盖前一个”。

## 19. Token 控制

随着链路增长，不能把所有历史 Commit 全量塞给 LLM。

V1 策略：

1. Context 保存完整 lineage；
2. 模型输入默认只选择每个 `source_agent_uid + kind` 最新有效 Commit；
3. 每个 Entry 提供短 summary（可在 Commit 时生成）；
4. 当前 Skill 根据 `accepts_context_kinds` 优先读取相关 kind；
5. Asset 只传引用与必要内容，不内联大文件；
6. 需要完整正文时再加载具体 Entry。

V1 可以先实现 1+2，后续增强 summary/按需加载。

## 20. 开发切片

### Phase A：Context Core

- 定义 RYAN_CONTEXT / Entry / AssetRef；
- 实现 merge/dedup/lineage；
- workflow_id / agent_uid；
- Commit repository；
- 单元测试 fan-in、重复链路、跨 workflow 错误。

### Phase B：Generic Workflow Agent Node

- 新节点；
- 固定 8 路 context input；
- latest commit -> RYAN_CONTEXT；
- hidden identity/revision；
- 不触发 LLM。

### Phase C：Interactive Backend

- Agent Session API；
- chat；
- commit；
- reset；
- asset upload；
- 复用 ACP runtime / skill resolver。

### Phase D：Right Panel

- 节点打开聊天；
- Agent 切换；
- 历史；
- 上游 Context Inspector；
- 多模态附件；
- Commit；
- Panel hide/show。

### Phase E：Starter Skills

- 验证 5 个迁移 Skill；
- 串行链；
- 3 路 fan-in；
- Commit 修改与下游刷新；
- 多模态引用。

## 21. V1 非目标

明确不做：

- Agent 自动调用其他 Agent；
- 自动 Supervisor；
- Agent 群聊；
- 全 Workflow 无差别共享聊天；
- 独立 Project Manager；
- 固定影视 schema 强绑定；
- 自动生成全流程；
- ComfyTV 深度集成。

ComfyTV 适配放到 Ryan Workflow Agent V1 稳定以后，只消费同一 Session/Context API。

## 22. 验收标准

V1 完成至少满足：

1. 同一通用 Agent Node 可选择不同 Skill；
2. 每个节点有独立可恢复的 Chat Session；
3. Chat 不触发 ComfyUI 全局 Queue；
4. Commit 前下游不可见当前讨论；
5. Commit 后节点输出新 `RYAN_CONTEXT`；
6. 两个以上上游 Context 可 fan-in 到同一 Agent；
7. Merge 不重复同一 lineage Entry；
8. 未连接 Agent 不自动共享内容；
9. Workflow 重开后 Session 可恢复；
10. 节点复制默认不会串 Session；
11. 图片/文档/视频/音频至少能以 AssetRef 进入会话；
12. Starter Skill 串行链可跑通 Creative -> Production -> Script -> Storyboard -> Video Prompt。

## 23. 最终一句话模型

```text
Workflow = Project Scope
Agent Node = Session Anchor + Commit Snapshot Node
Skill = Agent Role / Semantic Contract
DAG = Context Visibility & Propagation
RYAN_CONTEXT = Generic Immutable Context Envelope
Chat = Private Working Memory
Commit = Canonical Downstream Contract
```
