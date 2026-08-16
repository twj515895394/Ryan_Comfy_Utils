# Ryan Creative Workspace

在 ComfyUI 内以 Pi Agent 驱动的影视创作工作区（构想台）：用 Project Canon 与阶段确认管理正式产物，而不是用节点 DAG 作为主创作交互。**UI 交互范式参照 TE_MAN 构想台**（全局浮动面板、话题、流式、附件、Skill 状态等）；不复制 TE_MAN 实现、不依赖其安装。仅当能力为 TE_MAN 所无且设计文档未写清时，才单独裁定。

## 术语

### 工作区身份

**创作项目（Creative Project）**：
一次完整影视创作过程的持久边界；所有阶段状态、讨论、Canon 与产物都归属它。
_应避免_：工作流、Workflow、Session、话题

**创作项目 ID（creative_project_id）**：
创作项目的唯一标识；对应本地目录 `output/ryan_creative_workspace/projects/<creative_project_id>/`。
_应避免_：workflow_id、agent_uid、session_id

**工作区（Workspace）**：
用户当前正在使用的那个创作项目实例；由 Ryan 侧全局 `current_creative_project_id`（上次使用记忆）标识，可在构想台项目列表中切换。UI 为参照 TE_MAN 的全局浮动/可停靠面板，不依赖画布宿主节点，也不由 ComfyUI 画布决定当前项目。
_应避免_：把 Workspace 说成 ComfyUI 画布或单次 Chat；每张工作流图强制绑定一个项目；为打开构想台强制放置宿主节点

**重置工作区（Reset Workspace）**：
用户手动触发的操作：生成新的 `creative_project_id`，将全局当前工作区切换到该新项目；此后讨论与确认内容写入新项目目录。旧项目目录保留可再打开；已有创作文本选择器节点上的显式 ID 不变。
_应避免_：清空当前目录后复用同一 ID、自动重置、与 Stage Reopen 混用、重置时删除旧项目

### 阶段与事实

**阶段（Stage）**：
影视主链上的正式创作环节（如创意、美术、剧本、分镜、音频、视频提示词）；有默认 Skill、状态、依赖与 Canon。
_应避免_：节点、Agent 节点、Topic

**话题 / 线程（Thread）**：
某一 Stage 内的临时讨论分支；默认不成为正式事实。每个 Stage 有一条主 Thread；确认时取**当前正在查看的 Thread** 的可确认结果转正为该 Stage 的 Canon/deliverables，不自动合并多 Thread。
_应避免_：Stage、Project、静默把副 Thread 当主结果

**项目 Canon（Project Canon）**：
用户确认后的正式事实层；落在 `canon/<stage_id>/latest.md`（及可选历史 `vNNN.md`），供人阅读与上游 Agent 消费。
_应避免_：Chat 历史、Draft、消息记录

**确认当前阶段（Confirm Stage）**：
将**当前 Thread** 的可确认结果锁定为该 Stage 新的 Canon Revision。默认再跑一轮 Pi COMMIT 后由 Ryan 写盘；若该 Thread 结果已 READY，可显式「确认当前草稿」跳过模型直接导出。写盘时 `canon/<stage>/latest.md` 与主 `deliverables/**/*.items.md` **整文件覆盖**为本次完整真源，并保留与 revision 对齐的历史快照；完成后 Stage 为 LOCKED，并可能标记下游 STALE。
_应避免_：Commit（对用户）、按条目静默合并残留旧条、Agent 直接写项目目录、只存聊天不落 deliverables

**可确认草稿（READY）**：
当前 Thread 上最后一份完整助手结果，已被后端确定性解析为合法 `ryan-stage-export`：非空 `canon_markdown` + 该 Stage 合同要求的 deliverables（无执行物的 Stage 允许 deliverables 为空）。流式未完成、Stop 残稿、Utility 单轮结果、解析失败均非 READY，只能走默认再跑 Pi 的确认。
_应避免_：把任意聊天最后一条当作 READY

**Stage Reopen**：
将已锁定 Stage 重新打开以便修改；不等于重置工作区。
_应避免_：Reset Workspace

**STALE**：
上游 Canon 更新后，下游 Stage 在状态层被标记为可能过期；磁盘上既有 canon/deliverables 保留，选择器仍可读，但 UI/节点应提示过期。再次确认该下游后覆盖 latest 并清除自身 STALE。
_应避免_：STALE 时自动删文件、自动改路径导致选择器断线

### 产物与执行

**创作文本选择器（Creative Text Selector）**：
构想台 V1 进入执行节点的主桥：绑定显式 `creative_project_id`（创建时默认快照当前工作区，重置不改已有节点）；从该项目 `canon/**/latest.md` 与 `deliverables/**/*.md` 选文档。普通 `.md` 可整篇输出；`.items.md` **必须再选条目**，STRING 为该条目纯提示词正文。未选条目则失败/空并提示，不把整份 items Markdown 当提示词。
_应避免_：Ryan Artifact Selector、RYAN_CONTEXT 总线、动态 Bundle 归一化、默认跟随全局当前工作区、把结构化包或 items 标题清单整篇塞进生图/生视频

**阶段导出块（ryan-stage-export）**：
确认时 Agent 回复中的唯一私有结构合同（fenced JSON）。含 `canon_markdown` 与 `deliverables[]`；由 Ryan 解析后写盘。选择器与执行节点不消费该块本身。
_应避免_：Agent 直接写项目目录、多套 fenced 合同并行、让节点解析 export 块

**产物包（Artifact Bundle）**：
历史/兼容概念；构想台 V1 确认主路径改为 `ryan-stage-export` → 目录文件。不再作为选择器输入。
_应避免_：以 Artifact Selector 为构想台执行桥

**交付文档（Deliverable Document）**：
`deliverables/` 下供执行节点消费的 Markdown。整篇为 `.md`；多条目为 `.items.md`（`## id — label` + **纯文本正文**）。`production` / `storyboard` / `video_prompt` 各用一个主 items 文件承载多条。`SHOT_xxx` 在 storyboard 与 video_prompt 之间保持同一 id 对齐；`CHAR_` / `LOC_` 等 production id 保持稳定供引用，V1 选择器不做跨文档自动 join。
_应避免_：条目正文内嵌 JSON/围栏、整篇 items 不经选条当提示词、一实体一文件、跨阶段随意改名镜号

**资产引用（AssetRef）**：
对外部或本地媒体的引用。V1 构想台通过 Ryan `ComfyTVAssetBridge` 调用 ComfyTV **现有** HTTP API 列举与引用资产；项目内只存 ref（provider + asset id + payload_url 快照 + semantic_role），不复制 ComfyTV DB 行、不大文件入库。无 ComfyTV 时降级本地上传。向资产库回写为后续能力。Agent 侧：图片尽力附视觉输入（`/view` 解析本地或临时落地，失败则元数据+URL 文本）；视频不整段塞模型，元数据+可选关键帧（缓存于项目 `cache/`）；音频 V1 以元数据为主。
_应避免_：Creative 业务写入 ComfyTV、共享 DB 对象、ComfyTV 依赖 Ryan、无 ComfyTV 无法开构想台、视频整段文本化硬塞模型

**交付文档（Deliverable Document）**：
`deliverables/` 下供执行节点消费的 Markdown；整篇为 `.md`，多条目为 `.items.md`（`## id — label` + 正文）。
_应避免_：任意 JSON bundle 作为选择器主合同、把历史 revision 默认塞进选择器列表

## 已标记的歧义

（架构框架层主要歧义已在本轮 grill 闭合；若进入实现切片再打开更细的 Stage 合同字段级问题。）

**已废弃：Ryan Artifact Selector**：
不再作为构想台 → 执行节点的主路径；实现上应删除该节点及其专用前端，改走创作文本选择器。构想台 V1 主路径不灌 RYAN_CONTEXT。

## 示例对话

开发：用户点了“重置工作区”，旧的雨夜项目 Canon 还在吗？  
专家：在。重置只切换到新的创作项目 ID；旧目录保留，可以从项目列表再打开雨夜。  
开发：那和“重新打开分镜阶段”是一回事吗？  
专家：不是。Stage Reopen 仍在同一个创作项目里改某一阶段；Reset Workspace 换的是整个创作项目边界。  
开发：生图节点怎么读到确认后的提示词？  
专家：用创作文本选择器，绑当前（或指定的）creative_project_id，从该项目固定文档目录里选文本；不要再走旧的 Artifact Selector。
开发：选择器一次读整份分镜，还是一条镜头提示词？  
专家：先选文档，若文档是多条列表再可选一条；没有条目结构就整篇输出。
开发：重置工作区后，画布上旧的文本选择器会指向新项目吗？  
专家：不会。节点里是显式 project_id 快照；要读新项目就改节点上的 ID 或新建选择器。
开发：打开构想台时怎么知道当前是哪个项目？  
专家：看全局上次使用的 creative_project_id；没有或失效就新建或从列表选。跟当前打开哪张 Comfy 图无关。
开发：选择器去哪找文件？  
专家：扫该项目的 `canon/**/latest.md` 和 `deliverables/**/*.md`；多条用 `.items.md` 的二级标题拆条。
开发：确认时是 Agent 自己把 md 写进项目文件夹吗？  
专家：不是。Agent 只给结构化结果；Ryan 校验后写 canon 与 deliverables，选择器只认这些固定文件。
开发：确认一定会再问一次模型吗？  
专家：默认会再跑正式 COMMIT；若已经 READY，也可以显式确认当前草稿，不再调 Pi，由 Ryan 直接导出文件。
开发：构想台确认后还要往画布连 RYAN_CONTEXT 吗？  
专家：V1 不用。确认只写项目目录；执行节点用创作文本选择器读文件。Workflow Agent 的 CONTEXT/DAG 仍是另一套高级模式。
开发：剧本改版后，旧的分镜提示词文件还在吗？  
专家：在。下游标 STALE，文件不删；选择器还能跑旧图，但界面会提示可能过期，直到分镜再确认覆盖。
开发：构想台怎么打开？要不要先拖个节点？  
专家：不用。全局入口浮动面板，交互参照 TE_MAN；画布上只需创作文本选择器和执行节点。
开发：什么时候能点「确认当前草稿」？  
专家：当前 Thread 最后一份完整助手结果能解析为合法 ryan-stage-export 时；否则只能再跑正式确认。
开发：items 文档能整篇送进视频节点吗？  
专家：不能。items 必须选到某一条，输出该条纯提示词；整篇选 items 直接失败提示。
开发：构想台怎么用 ComfyTV 素材？  
专家：Ryan Bridge 调现有 /comfytv/assets 等 API，项目里只存 AssetRef；聊天引用这些 ref。生成结果写回资产库是后续，V1 不强制。
开发：@ 了 ComfyTV 图，Agent 实际看得到图吗？  
专家：会尽量把 /view 解析成可读文件做视觉附件；解析失败就降级成元数据和 URL 说明，聊天不中断。视频只给元数据或关键帧。
开发：三个角色图、十二个镜头提示词怎么存？  
专家：各 Stage 一个主 items 文件，多条 ## id — label；选择器选到某一条输出纯提示词，不给每个角色/镜头单独建文件。
开发：分镜 SHOT_003 和视频提示词怎么对应？  
专家：两边用同一个 SHOT_003 id。选择器仍手动选条目；V1 不自动把角色图 join 进镜头节点。
开发：第二次确认分镜只改了两镜，旧的 SHOT_010 还在 items 里吗？  
专家：若本次导出完整列表里没有 SHOT_010，latest items 里就没有；旧版在 history/vNNN 快照里。
开发：副 Thread「运镜测试」里确认，会写进分镜正式 Canon 吗？  
专家：会。确认的是当前 Thread；它会覆盖该 Stage 的 latest 与 deliverables，不会和主 Thread 自动合并。
开发：选择器选中某条分镜视频提示词后，STRING 里是什么？  
专家：只有可直接用的纯提示词正文，不带 JSON、不带 ryan-stage-export、不带说明套话。
