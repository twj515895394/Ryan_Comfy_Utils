# Ryan Workflow Agent Workspace V1 — 开发交接文档

> 交接时间：2026-08-10 17:17 +08:00
> 仓库：`twj515895394/Ryan_Comfy_Utils`
> 分支：`main`
> 设计基线 Commit：`de846210b04d2d68271ecc280cea65d2ad9e36fc`
> 当前阶段：**设计已完成 + 第一批 SceneForge Starter Skills 已迁移；核心 Runtime / Node / Chat UI 尚未实现**
> 面向对象：后续接手开发的 Codex / Claude / 其他 Agent

---

## 0. 先读这里：本交接的优先级

本项目下一阶段不要重新从“要做什么 Agent”开始发散，也不要先做自动 Multi-Agent、Supervisor、Router 或 Agent 自主互调。

V1 已经确定的产品目标非常克制：

```text
用户在 ComfyUI DAG 中手工摆放多个 Agent
→ 用户逐个打开 Agent 聊天
→ 每个 Agent 有自己的 Private Chat Session
→ 用户确认后 Commit
→ Commit 生成正式 RYAN_CONTEXT
→ RYAN_CONTEXT 沿 ComfyUI DAG 连线传播
→ 下游 Agent 可以消费一条或多条上游 Context
→ fan-in 时自动 Merge + 去重
```

**请严格优先完成这个闭环。**

设计的核心不是“五个固定影视 Agent”，而是：

```text
Generic Ryan Workflow Agent
+ 任意 Skill
+ 通用 RYAN_CONTEXT
+ Workflow Scope
+ Private Chat / Commit 分离
```

SceneForge 迁移过来的五个 Skill 只是 Starter Skill Pack，用来验证这套通用架构，不是底层固定角色模型。

---

# 1. Source of Truth：必须先读的设计文件

后续实现前，按以下顺序阅读：

1. `docs/agents/workflow-agent-workspace-v1-design.md`
   - V1 总体架构
   - Workflow = Project Scope
   - Generic Agent Node
   - Chat / Commit 生命周期
   - 多模态、右侧 Chat Panel、持久化、API、Phase 规划

2. `docs/agents/workflow-agent-context-contract-v1.md`
   - `RYAN_CONTEXT` 的正式数据合同
   - Entry / AssetRef / Lineage
   - 多路 fan-in Merge
   - 去重、版本、冲突、跨 Workflow 隔离

3. `docs/agents/scene-forge-skill-migration-v1.md`
   - SceneForge 哪些 Skill 已迁移
   - 为什么只迁五个 consolidated Skill
   - DISCUSS / COMMIT 适配原则
   - `agent-contract.json` 的用途

4. 现有 ACP 相关文档：
   - `docs/20260708_ACP_Runtime_Architecture_Design_v1.md`
   - `docs/20260708_ACP_Architecture_Decision_Record.md`
   - `docs/agents/acp-runtime-cli-profile.md`
   - `docs/agents/acp-fixed-prompt-agent-contracts.md`
   - `docs/agents/comfy-multi-image-inputs.md`

**若代码实现与上述 V1 设计冲突，应先更新设计文档并明确记录 ADR，再修改代码。不要在实现中静默改变架构。**

---

# 2. 核心设计决策（不可轻易改变）

## 2.1 Workflow = Project Scope

V1 不额外发明独立 Project 实体。

一个 ComfyUI Workflow 就是一个项目边界：

```text
Workflow
├── workflow_id
├── Agent A Session / Commits
├── Agent B Session / Commits
├── Agent C Session / Commits
├── uploaded assets
└── DAG Context lineage
```

必须有稳定 `workflow_id`，不能依赖 workflow 文件名。

推荐持久化到 workflow metadata：

```json
{
  "extra": {
    "ryan_agent": {
      "schema_version": 1,
      "workflow_id": "wf_xxx"
    }
  }
}
```

目标：Workflow 改名后 identity 不变；打开其他 Workflow 时 Session 完全隔离。

---

## 2.2 Generic Agent，而不是固定 Agent 类

不要实现：

```text
RyanCreativeAgent
RyanScriptAgent
RyanCharacterAgent
RyanStoryboardAgent
...
```

应该实现一个核心节点：

```text
Ryan Workflow Agent
```

角色由 `skill_id` 决定。

同一种 Python/ComfyUI 节点，通过不同 Skill 可以变成：

```text
创意策划
资产设计
编剧导演
角色设计
场景设计
分镜导演
视频 Prompt 导演
音乐导演
Review Agent
任意用户自定义 Agent
```

因此 Node Contract 必须保持通用，不能把影视字段硬编码进底层节点接口。

---

## 2.3 不要把 RYAN_CONTEXT 写成固定影视对象

禁止把底层 Context 定义成：

```text
RYAN_CONTEXT
├── creative
├── script
├── characters
├── locations
├── scenes
├── shots
└── assets
```

这个模型会把系统锁死成固定阶段，也会让多个同类 Agent、分支、合并、Review、未来非影视 Agent 很难扩展。

V1 已确定使用通用 Entry 模型：

```text
RyanContext
├── schema_version
├── workflow_id
├── entries[]
├── assets[]
├── lineage[]
└── metadata
```

每次 Commit 添加一个 `RyanContextEntry`。

Entry 至少需要：

```text
entry_id
source_agent_uid
source_agent_name
skill_id
kind
revision
content
asset_refs[]
upstream_entry_ids[]
created_at
metadata
```

`kind` 是开放字符串，例如：

```text
creative.story
production.design
script.direction
storyboard.plan
video.prompts
character.design
location.design
audio.direction
review.report
custom.xxx
```

**Socket 类型统一为 `RYAN_CONTEXT`，语义由 Entry 的 kind / skill / source 表达。**

---

## 2.4 DAG 决定“谁能看到什么”

Workflow 只负责项目隔离，不代表 Workflow 内所有 Agent 自动共享全部内容。

正确模型：

```text
Agent A ───────────┐
                   │
Agent B ───────────┼──> Agent D
                   │
Agent C ───────────┘
```

Agent D 只消费实际连到它的 Context。

不要实现一个全局“所有 Agent 自动读取整个 Workflow Memory”的黑盒机制。

理由：

- 避免无关信息污染；
- DAG 本身就是可视化上下文权限模型；
- 用户可以一眼看出信息来源；
- 分支/合并天然成立；
- 调试方便。

---

## 2.5 Chat != Commit

这是 V1 最关键的交互语义之一。

### DISCUSS / Chat

用户可以：

- 多轮提问；
- 修改需求；
- 推翻方案；
- 上传图片/文档/视频/音频；
- 与当前 Skill 反复讨论。

这些内容属于：

```text
Agent Private Chat Session
```

默认**不传播给下游 Agent**。

### COMMIT

只有用户明确点击类似：

```text
确认并提交
Commit
```

之后：

```text
Private Chat + Upstream Context + 当前素材
          ↓
Skill 执行 COMMIT
          ↓
Canonical Artifact / Commit Snapshot
          ↓
RyanContextEntry
          ↓
RYAN_CONTEXT output
```

下游看到的是已确认 Canon，而不是当前 Agent 的所有试错聊天记录。

不要把“发送一条聊天消息”实现成“运行整个 ComfyUI Workflow”。

---

# 3. 预期 DAG 形态

V1 首先必须验证下面三类图。

## 3.1 串行

```text
创意 Agent
    │ RYAN_CONTEXT
    ▼
剧本 Agent
    │
    ▼
分镜 Agent
    │
    ▼
视频 Prompt Agent
```

下游 Context 应包含整条已提交 Canon 链路。

## 3.2 Fan-out

```text
              ┌──> 角色设计 Agent
创意 Agent ───┼──> 剧本 Agent
              └──> 场景设计 Agent
```

三个分支独立讨论、独立 Commit。

## 3.3 Fan-in

```text
角色设计 Agent ───────┐
                      │
剧本 Agent ───────────┼──> 分镜 Agent
                      │
场景设计 Agent ───────┘
```

分镜 Agent 支持多路 `RYAN_CONTEXT` 输入，并在运行/显示时得到统一 merged context。

fan-in 不能简单字符串拼接；必须按 Entry ID 去重，并保留 lineage。

---

# 4. Generic Agent Node 建议合同

V1 建议节点名：

```text
Ryan Workflow Agent
```

建议 Category：

```text
Ryan Utils / Agent
```

## 4.1 Context 输入

建议首版固定预留多个 Context Socket（例如 8 路），不要动态修改 ComfyUI slot 数组。

原因：当前项目已经遇到过动态调整 slot 可能造成刷新后连线丢失的问题；H3 Smart Filter 的修复也是通过固定保留 slots 来稳定 workflow compatibility。

例如：

```text
context_01: RYAN_CONTEXT
context_02: RYAN_CONTEXT
...
context_08: RYAN_CONTEXT
```

未连接输入为 null。

## 4.2 其他输入

Node UI/配置层建议至少包括：

```text
skill_id
agent_name
agent_uid（隐藏/自动）
workflow_id（隐藏/自动）
profile / provider 配置
```

多模态物理连线可以逐步增加：

```text
IMAGE
VIDEO / video path
AUDIO / audio path
FILE / file path
STRING
```

但 V1 核心优先级仍然是 Context + Chat + Commit。

## 4.3 输出

核心输出：

```text
context: RYAN_CONTEXT
```

可选调试/兼容输出：

```text
committed_text: STRING
session_dir: STRING
raw_result_json: STRING
```

是否保留这三个兼容输出可以实现期结合当前 ACP 节点习惯决定，但不能替代 `RYAN_CONTEXT`。

---

# 5. Workflow Queue 中 Agent 节点应该做什么

需要避免一个常见错误：把聊天 Runtime 和 ComfyUI Queue Runtime 混在一起。

建议职责拆分如下。

## 5.1 Chat Runtime

右侧聊天面板调用独立 API：

```text
sendMessage
attachAsset
getHistory
commit
stop
```

这里可以调用 Claude/Codex/OpenAI-compatible Provider，并维护 session。

## 5.2 ComfyUI Node Runtime

ComfyUI Queue 执行 Agent Node 时，V1 核心职责更接近：

```text
读取 context_01..context_08
→ merge_contexts()
→ 读取当前 Agent latest committed snapshot
→ append/overlay 当前 commit entry
→ 返回新的 RYAN_CONTEXT
```

换句话说：

**Workflow Queue 不应该因为用户只是聊天就反复执行 Agent LLM。**

LLM Chat 是交互 Runtime；DAG Queue 是 Canon Context 的数据流 Runtime。

---

# 6. Context Merge 必须满足的规则

实现 `merge_contexts()` 时至少保证：

1. 同一个 `workflow_id` 才能自然合并；
2. 不同 workflow_id 默认抛明确错误，不静默混入；
3. `entries` 按 `entry_id` 去重；
4. `assets` 按 `asset_id` 去重；
5. lineage 合并后仍可追溯来源；
6. 同一个 Agent 多 revision 默认允许同时存在历史 Entry，但“当前可消费版本”需要清晰规则；
7. 合并顺序必须 deterministic；
8. 不依赖 Context Socket 的语义命名来判断内容类别；
9. 不把 Context 转成一坨不可追踪的文本再传下去。

建议同时提供：

```text
merge_contexts(contexts)
select_entries(...)
get_latest_entries_by_agent(...)
get_latest_entries_by_kind(...)
validate_workflow_scope(...)
```

完整合同见 `workflow-agent-context-contract-v1.md`。

---

# 7. Session / Identity

必须区分两个 ID。

## workflow_id

项目级身份。

```text
Workflow A -> wf_xxx
Workflow B -> wf_yyy
```

## agent_uid

节点实例的长期身份。

不要只依赖 ComfyUI node id。

推荐：

```text
workflow_id + agent_uid
```

作为 Agent Session / Commit Store 的逻辑主键。

节点复制行为需要显式测试：

- 普通保存/加载：agent_uid 应保持；
- 用户复制一个 Agent Node：新节点应生成新的 agent_uid，不能与原节点共用私有聊天 Session；
- 仅 node_id 变化不应导致已有 Session 丢失。

---

# 8. 持久化建议

设计目标是：关闭浏览器、重启 ComfyUI、重新打开 Workflow 后还能恢复对应 Agent 会话与 Commit。

推荐结构（具体根目录实现时可调整，但语义不要变）：

```text
output/ryan_agent_workspace/
└── <workflow_id>/
    ├── workflow.json / metadata.json
    ├── agents/
    │   └── <agent_uid>/
    │       ├── session.json
    │       ├── messages.jsonl
    │       ├── commits/
    │       │   ├── rev_001.json
    │       │   ├── rev_002.json
    │       │   └── ...
    │       └── assets/
    └── shared_assets/
```

不要把所有 workflow 的聊天历史塞进一个无 scope 的全局文件。

---

# 9. 多模态 Asset 模型

聊天上传素材与 ComfyUI 节点连线素材，最终要统一成 AssetRef，而不是各建一套私有协议。

建议核心结构：

```text
RyanAssetRef
├── asset_id
├── type        image | video | audio | document | text | other
├── mime_type
├── source      chat_upload | node_input | upstream_context | external
├── path / uri
├── filename
├── size / metadata
├── source_agent_uid
└── created_at
```

Context Entry 只通过 `asset_refs[]` 引用资产 ID。

右侧 UI 应能告诉用户：当前 Agent 看到了哪些素材、素材来自哪个节点/哪个 Agent/聊天上传。

V1 可以先支持图片和文件，再扩展视频/音频，但数据合同应从开始就允许这些类型。

---

# 10. 右侧 Chat Panel — V1 UX

目标体验参考 UpDream，但要更符合 ComfyUI DAG。

点击/双击 Agent 节点后打开右侧面板；关闭后画布只剩 Agent Node。

推荐布局：

```text
┌──────────────────────────────┐
│ Agent 名称 / Skill       ×   │
├──────────────────────────────┤
│ 上游上下文摘要                │
│ - 来自 Agent A rev 3          │
│ - 来自 Agent B rev 1          │
│ - 7 assets                    │
│ [查看完整上下文]              │
├──────────────────────────────┤
│                              │
│        Private Chat          │
│                              │
├──────────────────────────────┤
│ attachments                  │
│ [图][文件][视频][音频]        │
│                              │
│ 输入消息...                   │
│                    [Send]    │
├──────────────────────────────┤
│ Draft / Commit 状态           │
│ rev N           [确认并提交]  │
└──────────────────────────────┘
```

必须让用户明确区分：

```text
聊天中的 Draft
vs
下游已经可见的 Commit
```

节点本体最好显示：

```text
Agent Name
Skill
状态：未开始 / 讨论中 / 已提交 / 上游已变更
消息数量
附件数量
当前 commit revision
打开聊天
```

---

# 11. API 建议

实际路径可按 ComfyUI 扩展规范调整，语义建议至少包含：

```text
GET    workflow agent state
GET    session history
POST   send message
POST   attach asset
DELETE detach asset
POST   commit
POST   reset/restart session
POST   stop generation
GET    skills
GET    context summary
```

推荐后端服务层不要把 HTTP handler 直接写成业务逻辑，建议拆成：

```text
workflow_scope_service
agent_session_service
context_service
asset_service
agent_chat_service
skill_registry
```

这样未来 ComfyTV 要接入同一个 Agent Runtime 时，可以复用服务层，而不是复制一套逻辑。

---

# 12. 现有 ACP Runtime：应复用什么

当前已有能力包括：

```text
ryan_comfy_utils/acp/
```

重点已有：

```text
runtime.py
session.py
workspace.py
skill_loader.py
skill_resolver.py
context_builder.py
asset_materializer.py
contracts.py
cli_runner.py
```

以及现有：

```text
RyanACPUniversalAgent
固定 Image / Video / H3 Prompt Agents
```

不要推翻 ACP Runtime。

建议新 Workflow Agent 在服务层复用：

- Skill resolve / load；
- Provider / CLI runner；
- workspace 基础逻辑；
- 现有图片/文件 materialize 能力；
- Runtime 错误语义和日志。

但需要把“一次执行式 session”扩展成真正的长期 Chat Session。

**不要为了实现 Workflow Agent 又单独写第二套 Skill Loader / Claude CLI Runner。**

---

# 13. 当前已迁移的 Starter Skills

来自：

```text
twj515895394/scene_forge
branch: codex/v10-text-skill-pipeline
```

已迁入 `Ryan_Comfy_Utils`：

```text
creative-story-planner
production-designer
script-director
storyboard-director
video-prompt-director
```

推荐 Demo 主链：

```text
Creative Story Planner
        ↓
Production Designer
        ↓
Script Director
        ↓
Storyboard Director
        ↓
Video Prompt Director
```

但这只是 demo/starter chain。

未来完全允许：

```text
Creative
   ├──> Character Design ─┐
   ├──> Location Design ──┼──> Script / Storyboard
   └──> Props Design ─────┘
```

每个迁移 Skill 目录中已增加 `agent-contract.json`，用于描述：

```text
display_name
accepts_context_kinds
produces_context_kind
supports_discuss
supports_commit
```

这个 contract 是**语义元数据**，不是新的 ComfyUI 数据类型。

---

# 14. Skill 执行语义

迁移 Skill 已按两种模式设计：

## DISCUSS

- 可以分析上游 Context；
- 可以提建议；
- 可以和用户迭代；
- 可以给候选方案；
- 不把当前回答自动视为正式 Canon；
- 不要求每条消息都生成阶段文件。

## COMMIT

- 根据当前上游 Context；
- 当前 Agent 完整私有讨论；
- 用户最后确认；
- 当前关联资产；
- 生成唯一权威 Artifact；
- 写入 RyanContextEntry；
- revision +1。

这层能力需要 Runtime 在调用 Skill 时明确注入 mode，而不是让 Skill 靠猜。

---

# 15. 推荐代码目录（实现时可微调）

不要把所有东西继续塞进 `acp_nodes.py`。

建议逐步形成：

```text
ryan_comfy_utils/
├── acp/                         # 现有 Runtime，继续复用
│
├── workflow_agent/
│   ├── __init__.py
│   ├── models.py                # RyanContext / Entry / AssetRef
│   ├── context_merge.py
│   ├── workflow_scope.py        # workflow_id
│   ├── agent_identity.py        # agent_uid
│   ├── session_store.py
│   ├── commit_store.py
│   ├── asset_store.py
│   ├── skill_registry.py
│   ├── chat_service.py
│   └── api.py / routes.py
│
├── nodes/
│   └── workflow_agent_nodes.py
│
└── web/
    ├── ryan_workflow_agent.js
    └── workflow_agent_chat/...  # 如需要拆模块
```

如果 ComfyUI 的后端路由注册需要放在其他现有模块，请遵从项目现有入口，但保持上述职责边界。

---

# 16. Phase 开发顺序

## Phase A — RYAN_CONTEXT Core

第一优先级。

实现并测试：

```text
RyanContext
RyanContextEntry
RyanAssetRef
merge_contexts
context selection
workflow scope validation
serialization/deserialization
```

### Phase A DoD

- 串行 Context 正确累积；
- fan-out 不互相污染；
- fan-in 能 Merge；
- diamond graph 不产生重复 Entry；
- 跨 workflow Context 不能静默合并；
- JSON round-trip 不丢数据；
- revision / lineage 可追踪。

---

## Phase B — Generic Ryan Workflow Agent Node

实现：

- 一个 Generic Agent Node；
- 固定多路 RYAN_CONTEXT inputs；
- `skill_id` 选择；
- stable `agent_uid`；
- workflow_id 获取；
- Queue 时输出 merged + own latest commit Context。

### Phase B DoD

至少能在 ComfyUI 上搭：

```text
A -> B -> C
```

和：

```text
A -> D
B -> D
C -> D
```

并从调试输出验证 Context 正确。

此 Phase 还不要求完整 Chat UI。

---

## Phase C — Agent Session / Chat API

实现：

- Session Store；
- 多轮消息；
- DISCUSS 调用 Skill；
- COMMIT；
- Stop；
- Session restore；
- Commit revisions；
- 上游 Context 注入。

### Phase C DoD

后端 API 可以做到：

```text
create/open session
send 3+ rounds
restart process
reload history
commit rev1
continue discuss
commit rev2
```

下游 Context 只看到 Commit，不看到未提交 Chat。

---

## Phase D — Right-side Chat Panel

实现 UI：

- 点击 Agent 打开面板；
- Agent 切换；
- history；
- loading / streaming 或状态更新；
- attach；
- commit；
- close panel；
- context inspector。

首版不必追求和 UpDream 1:1 视觉复刻，先保证状态逻辑稳定。

---

## Phase E — Multimodal Assets

按顺序建议：

```text
IMAGE
→ document/file
→ video
→ audio
```

统一 AssetRef，不为 chat upload 和 node input 重复实现数据协议。

---

## Phase F — Starter Film Pipeline Demo

用已迁移 Skill 建一张演示 Workflow：

```text
creative-story-planner
→ production-designer
→ script-director
→ storyboard-director
→ video-prompt-director
```

然后再验证一个 fan-in 版本，例如把 Production 拆出角色/场景分支后再汇总。

---

# 17. 测试要求

不要只测试 Happy Path。

至少覆盖：

## Context

- empty input；
- single context；
- multi context；
- duplicate entry；
- duplicate asset；
- same Agent multi revision；
- diamond DAG；
- different workflow_id；
- old schema version；
- malformed context。

## Identity

- save/reload；
- node copy；
- workflow rename；
- workflow duplicate / Save As；
- deleting node 后 session 残留策略。

## Chat / Commit

- DISCUSS 不改变 downstream Context；
- COMMIT rev1；
- 再 DISCUSS 不改变 rev1；
- COMMIT rev2；
- downstream 获取 latest revision；
- upstream Commit 更新后当前 Agent 提示“上游已变化”；
- 不自动覆盖用户已确认当前 Commit。

## Assets

- chat upload；
- node input；
- upstream asset；
- 同一 asset 多路径汇入去重；
- 文件不存在；
- 非法路径；
- 大文件处理边界。

## Compatibility

- 旧 Ryan ACP 节点不受影响；
- 现有 Image/Video/H3 agents 不受影响；
- workflow reload 不丢 Ryan Agent Socket 连线。

---

# 18. 特别注意：ComfyUI 动态 Slot 风险

当前项目最近已经修复过动态 slot 变化导致 workflow reload / 连线稳定性风险。

因此 Generic Workflow Agent 的 V1 `context_01..context_N` 建议固定存在，不要为了 UI 漂亮动态 add/remove socket 数组。

可以：

- 用前端隐藏未使用 slot；
- 用“有效输入数”配置控制显示；

但底层 slot identity 应保持稳定。

这一点属于兼容性优先，不要轻易改回完全动态 slots。

---

# 19. 不在 V1 做的事情

以下均不是当前第一阶段目标：

```text
Agent 自动调用另一个 Agent
Supervisor Agent
Router Agent
Agent Team
自主任务规划
全局 Workflow Memory 自动注入
自动把所有 Agent Chat 共享给所有节点
复杂权限系统
云端多人协作
ComfyTV 深度集成
完整影视领域数据库 Schema
```

尤其不要先做 ComfyTV Adapter。

Ryan Workflow Agent 必须先在**原生 ComfyUI + Ryan_Comfy_Utils** 独立成立。

以后 ComfyTV 只消费同一个 Runtime / Session / Context Service，提供高级 Workspace UI，而不是重新实现 Agent Core。

---

# 20. 后续与 ComfyTV 的边界

未来架构目标：

```text
                  Ryan Agent Core
                 /               \
        Native ComfyUI UI       ComfyTV UI
              │                    │
       simple chat panel     advanced workspace
```

因此 Chat / Session / Asset / Context 逻辑尽量写成可复用 Python 服务，不要强耦合到某个 JS 面板。

ComfyTV 未来可以增加：

- 项目 Asset Library 拖入 Chat；
- 多 Agent Workspace；
- richer history；
- Storyboard / Timeline 联动；

但 Agent Core 仍然在 Ryan。

---

# 21. 当前代码状态

交接发生时：

```text
main HEAD baseline:
de846210b04d2d68271ecc280cea65d2ad9e36fc
```

该 Commit 已完成：

- V1 总体设计；
- RYAN_CONTEXT 合同；
- SceneForge Skill 迁移设计；
- 5 个 Starter Skill 的 Ryan 适配版迁入；
- 每个 Skill 的 agent-contract metadata。

尚未完成：

- `RYAN_CONTEXT` Python Model；
- Merge Runtime；
- Workflow Scope manager；
- Generic Workflow Agent Node；
- Chat Session Service；
- API；
- 右侧 Chat UI；
- 多模态统一 AssetRef Runtime；
- Demo Workflow；
- 新架构自动化测试。

不要把“设计文档和 Skill 已存在”误认为 Runtime 已实现。

---

# 22. 接手 Agent 的第一轮工作指令

推荐接手后第一步只做 Phase A，不同时开 UI。

执行顺序：

```text
1. 阅读三份 V1 设计文档
2. 检查现有 acp/contracts.py / runtime.py / session.py / workspace.py
3. 建 workflow_agent package
4. 实现 models.py
5. 实现 context_merge.py
6. 写 tests
7. 验证 fan-in / diamond / workflow isolation
8. 更新设计实现状态
9. 再进入 Generic Node
```

第一轮提交应尽可能是一个可独立 review 的垂直切片，例如：

```text
feat: add RYAN_CONTEXT core models and deterministic merge
```

不要第一轮同时改 Context、Node、API、Chat UI、Skill 和 ComfyTV。

---

# 23. 开发过程中的文档纪律

每完成一个 Phase：

1. 更新 `docs/agents/workflow-agent-workspace-v1-design.md` 中对应状态；
2. 若 Context 合同变化，同步 `workflow-agent-context-contract-v1.md`；
3. 若 Skill Runtime contract 变化，同步 `scene-forge-skill-migration-v1.md`；
4. 记录与设计不一致的实现决策和原因；
5. 增加/更新 `.handoff`，让下一个 Agent 可以直接继续。

不能只留代码、不留状态。

---

# 24. 设计中的一句话原则

后续遇到实现争议时，用下面几句话判断方向：

> **Workflow 管“属于哪个项目”。**
>
> **DAG 管“谁能看到什么”。**
>
> **Agent Chat 管“当前角色怎么讨论”。**
>
> **Commit 管“什么信息正式进入下游”。**
>
> **Skill 管“这个 Agent 是谁、怎么工作”。**
>
> **RYAN_CONTEXT 管“已确认 Canon 如何沿 DAG 传播”。**

如果某个实现让这几个职责混在一起，通常说明需要重新拆分。

---

# 25. 最终 V1 验收场景

V1 真正完成时，用户应该可以在 ComfyUI 中做到：

```text
1. 新建 Workflow
2. 放置 4~5 个同一种 Ryan Workflow Agent Node
3. 每个选择不同 Skill
4. 按自己的创作流程连成 DAG
5. 点击第一个 Agent，在右侧多轮讨论
6. 点击 Commit
7. 打开第二个 Agent，能看到上游已提交 Context
8. 第二个 Agent 私有聊天不会污染第一个或第三个
9. 多个 Agent 可以 fan-in 到一个 Agent
10. 下游能看到所有实际连入上游的已提交 Canon
11. Context 中同时能带文本和 AssetRef
12. 关闭右侧 Chat 后画布只剩干净的 Agent DAG
13. 保存、重启、重新打开 Workflow，Agent Session / Commit 可恢复
14. 未 Commit 的草稿不影响下游
15. 修改任意上游后，不需要自动让所有 Agent 自主重跑，用户仍掌控每一步
```

做到这里，V1 即达成产品目标。

---

## 交接结束

后续 Agent 请从 **Phase A：RYAN_CONTEXT Core** 开始，而不是再次进行产品方向讨论。

若需要调整架构，先明确说明：

```text
当前设计哪里无法实现
→ 具体 ComfyUI / ACP 技术约束是什么
→ 替代方案是什么
→ 对已有 Context / Session / Skill 合同影响是什么
```

再更新设计文档并实施。
