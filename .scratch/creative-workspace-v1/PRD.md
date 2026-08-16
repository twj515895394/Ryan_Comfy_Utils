Status: ready-for-agent

# Ryan Creative Workspace V1（构想台）

## 问题陈述

创作者在 ComfyUI 里做影视向 AI 创作时，被迫把「剧本 → 美术 → 分镜 → 音频 → 视频提示词」拆成多个 Workflow Agent 节点、连线传播 `RYAN_CONTEXT`、关心 Queue 与 Commit 边界。真实创作是反复回跳、比较方案、锁定版本的过程，不是单向 DAG。结果是：操作负担高、正式结论与聊天草稿混在一起、多次开跑容易把状态搞乱，生图/生视频也难稳定接到「当前锁定的那条提示词」。

## 解决方案

在 `Ryan_Comfy_Utils` 内交付 **Ryan Creative Workspace（构想台）**：全局浮动创作 IDE（UI 交互范式参照 TE_MAN，不复制实现）。用户在一个 **创作项目**（本地工作区目录，仅 `creative_project_id`）里按六 **阶段** 与 Agent 讨论，对当前 **Thread** **确认当前阶段** 后，由系统把正式事实写入项目目录（**项目 Canon** + **交付文档**）。画布侧用 **创作文本选择器** 按显式 `creative_project_id` 读取固定文档/条目，输出可直接用于生图/生视频的纯文本 STRING。

**重置工作区** 仅切换到新项目 ID；旧项目目录保留可再打开。废弃并删除 **Ryan Artifact Selector**；构想台 V1 主路径不灌 `RYAN_CONTEXT`。Workflow Agent 保留为高级 DAG 模式。

**本功能不是 SaaS：** 无登录注册、无 token/权限体系、无成员邀请与协作权限。此处「项目」= 本机创作工作区，不是多用户项目管理。

## 文档与讨论索引（实现与拆 issue 必读）

拆 issue / 实现前 **必须** 对照下列材料。冲突时优先级：

1. 本 PRD「实现决策」与 Grill 裁定  
2. `CONTEXT.md` 术语表  
3. 架构设计文档中**未被本 PRD 分叉**的章节  
4. 既有 ADR / 代码先例  

### 权威文档

| 文档 | 路径 | 用途 |
|---|---|---|
| 领域术语表 | `CONTEXT.md` | 唯一词汇表；Stage/Canon/重置/选择器等定义与示例对话 |
| 架构设计 v1 | `docs/architecture/Ryan-Creative-Workspace-Agent-Architecture-v1.md` | 产品全景、四平面、六 Stage、API 草图、UI 布局、Pi/Skill、ComfyTV Bridge 意向 |
| ComfyTV 资产 API 速查 | `docs/agents/comfytv-asset-api-notes-v1.md` | 现成 `/comfytv/assets*`、字段、DB、Bridge 约定 |
| Workflow Agent Pi ADR | `docs/adr/0001-workflow-agent-pi-runtime-v1.md` | Pi RPC、`--no-context-files`、Chat≠Commit 等可复用边界 |
| 问题追踪约定 | `docs/agents/issue-tracker.md` | `.scratch/<slug>/` 布局 |
| 分类标签 | `docs/agents/triage-labels.md` | `ready-for-agent` 等 |

### 架构文档中仍有效、可直接参照的部分

- §3 不可变决策：主工程 Ryan；TE_MAN 只借鉴交互；ComfyTV 为 Asset Provider；Coding AGENTS 隔离；V1 复用六 Skill  
- §4–5 总体架构与四平面（Creative / Project / Agent / Execution）  
- §7–8 六阶段与 Skill 映射  
- §10–11 `/` Skill Palette 与 Stage vs Utility Skill（Utility 不自动进 Canon）  
- §14 Stage ≠ Thread  
- §15–16 状态机与 STALE **概念**（磁盘文件策略以 Grill 为准）  
- §20–23 Creative Instructions、`--no-context-files`、仅 Pi Agent Runtime  
- §25–33 ComfyTV Bridge 意向与降级（具体 API 以速查文档+代码为准）  
- §41–47 存储树与 `/ryan/creative/*` API **草图**（落盘合同以本 PRD 为准）  
- §57–58 Workflow Agent 降为高级模式、能力复用  

### 相对架构文档的明确分叉（以 Grill / 本 PRD 为准）

| 主题 | 架构稿原意 | V1 裁定 |
|---|---|---|
| 执行桥 | 继续复用 Artifact Selector；可有 RYAN_CONTEXT | **删除 Artifact Selector**；**仅** 文件 + **创作文本选择器**；不灌 `RYAN_CONTEXT` |
| 产物对外合同 | Artifact Bundle 给选择器 | 对外 **`canon/` + `deliverables/` Markdown**；Agent 私有块 **`ryan-stage-export`** |
| 项目与画布 | `creative_project_id` 独立 | 维持；**全局 current**；不绑 `workflow_id` |
| 重置 | reopen/delete 为主 | **重置 = 新 ID + 切换 current**；旧目录 **保留** |
| UI 入口 | 面板化 | **全局浮动面板（TE_MAN）**；无宿主节点 |
| UI 争议 | 多处可讨论 | **TE_MAN 已有范式不再开争议** |

### Grill 裁定纪要（对话已收口，已写入 CONTEXT）

1. **重置工作区**：手动；新 `creative_project_id`；之后写入新目录；旧项目保留可切回。  
2. **创作文本选择器** 替换 Artifact Selector；绑定**显式** project_id（创建时快照 current；重置不改已有节点）。  
3. 选取粒度：普通 md **整篇**；`.items.md` **必须选条目**；生图/生视频 STRING = **纯提示词**。  
4. **当前工作区** = 全局上次 `current_creative_project_id` + 列表切换；与打开哪张 Comfy 图无关。  
5. 落盘：`canon/<stage>/latest.md`（+vNNN）+ `deliverables/<stage>/`；选择器扫 latest 与交付文件。  
6. **Ryan 写盘**；Agent 只出 `ryan-stage-export`；不直接写项目目录。  
7. 确认：默认再跑 Pi COMMIT；READY 时可「确认当前草稿」；对象 = **当前 Thread**。  
8. READY = 当前 Thread 最后完整助手结果可解析为合法 export。  
9. STALE：状态标记；**磁盘文件保留**；选择器仍可读并提示过期。  
10. production / storyboard / video_prompt：**每 Stage 一个主 `.items.md`**，多条 `## id — label`；`SHOT_xxx` 跨 storyboard/video 对齐。  
11. 再次确认：**整文件覆盖** latest + revision 历史快照。  
12. ComfyTV：Bridge 调**现有 API**；V1 引用进聊天；回写资产库后置；图尽力视觉附件，视频元数据/关键帧，音频元数据。  

## 用户故事

1. 作为创作者，我想从 ComfyUI 全局打开构想台浮动面板，以便不先拖节点就能开始创作。  
2. 作为创作者，我想创建或打开一个本地创作项目（工作区目录），以便长期沉淀同一作品的正式设定与提示词。  
3. 作为创作者，我想让系统记住上次使用的创作项目，以便下次打开直接续作。  
4. 作为创作者，我想从项目列表切换旧项目，以便继续历史作品。  
5. 作为创作者，我想手动重置工作区并获得新项目 ID，以便多次开新作而不混档。  
6. 作为创作者，我想在重置后仍能打开旧项目目录，以便误操作可恢复。  
7. 作为创作者，我想在六阶段主链间切换，以便按影视流程推进。  
8. 作为创作者，我想每个阶段用对应 Skill 与 Agent 对话，以便输出符合该阶段合同。  
9. 作为创作者，我想在阶段内开多个 Thread，以便并行试方案。  
10. 作为创作者，我想确认时只转正当前 Thread，以便把副方案提升为正式 Canon。  
11. 作为创作者，我想看到阶段状态（未开始/草稿/可确认/已锁定/过期/错误），以便知道下一步。  
12. 作为创作者，我想在讨论时流式看到回复并 Stop，以便控制生成。  
13. 作为创作者，我想默认「确认当前阶段」走正式规范化导出，以便得到 Canon 与交付文件。  
14. 作为创作者，我想在 READY 时「确认当前草稿」跳过再跑模型，以便快速锁定眼前版本。  
15. 作为创作者，我想确认后在项目目录看到 canon 与 deliverables，以便人读和节点读同一真源。  
16. 作为创作者，我想美术阶段导出多条角色/场景等生图提示词，以便逐条送进生图节点。  
17. 作为创作者，我想分镜阶段导出多条镜头提示词，以便按镜使用。  
18. 作为创作者，我想视频提示词阶段导出与分镜 SHOT id 对齐的多条视频提示词，以便按镜生视频。  
19. 作为创作者，我想再次确认时 latest 变为完整新版本且旧版进历史，以便删镜/删角色反映到最新文件。  
20. 作为创作者，我想上游改版后下游标 STALE 但旧文件仍在，以便旧链路可跑并提示更新。  
21. 作为创作者，我想 Reopen 已锁定阶段继续改，以便不必重置整个项目。  
22. 作为创作者，我想用 `/` 选择 Stage 或 Utility Skill，以便工具型结果不自动变成 Canon。  
23. 作为创作者，我想 @ ComfyTV 资产作为参考，以便基于素材库讨论。  
24. 作为创作者，我想在没有 ComfyTV 时仍能本地上传继续创作，以便环境降级可用。  
25. 作为创作者，我想用创作文本选择器绑定项目并选出一条纯提示词，以便直接连生图/生视频/H3。  
26. 作为创作者，我想选择器在重置后仍指向旧 project_id，以便未改动的图继续用旧交付物。  
27. 作为创作者，我不想再依赖 Artifact Selector 与 RYAN_CONTEXT 才能接到执行节点，以便链路简单可调试。  
28. 作为高级用户，我想继续使用 Workflow Agent DAG，以便自动化流水线不被删除。  
29. 作为创作者，我不想仓库 Coding AGENTS.md 污染创作 Agent，以便创作规则由构想台显式注入。  
30. 作为实现者，我想有稳定的目录合同与 export 合同，以便选择器只扫文件、后端可单测。  

## 实现决策

### 明确不做（防止范围漂移）

- **不做** 用户认证与授权（登录、注册、token、RBAC）。  
- **不做** 多用户「项目管理」（成员邀请、协作权限、组织/团队）。  
- **不做** 云端账号体系；创作项目 = 本机目录 + id。  

### 模块划分（仅本产品域）

- **Creative Project Repository**：本地工作区目录的创建/列表/打开/重置/current；无成员模型。  
- **Stage Registry / Pipeline**：六 Stage、依赖、deliverables 合同。  
- **Stage Export**：`ryan-stage-export` → canon/deliverables/history；READY。  
- **Stage Service**：确认 / 确认草稿 / Reopen / STALE。  
- **Creative Chat / Thread**：DISCUSS、Stop、多 Thread；复用 Pi。  
- **Context Compiler**：Canon 注入 + Asset 编译。  
- **ComfyTV Asset Bridge**：现有 HTTP API；AssetRef；降级。  
- **Creative Workspace UI**：TE_MAN 范式壳。  
- **创作文本选择器**：显式 project_id；文档+条目；纯文本 STRING。  
- **拆除 Artifact Selector**：节点与专用前端删除。  

### 身份与存储

- 键：`creative_project_id`（≠ `workflow_id`）。  
- 根：`output/ryan_creative_workspace/projects/<id>/`。  
- 含：`project.json`、`state.json`、`canon/`、`deliverables/`、`threads/`、`refs/`、`cache/`。  
- 全局 `current_creative_project_id`。  

### 确认与导出

- Agent 私有：单块 `ryan-stage-export`。  
- 主 items：`image_prompts.items.md` / `shot_prompts.items.md` / `shot_video_prompts.items.md`。  
- `## id — label` + 纯提示词正文；SHOT 跨阶段对齐。  
- 再确认：latest 整文件覆盖 + 历史快照。  

### 执行桥

- 文件 → 创作文本选择器 → STRING → 执行节点。  
- 删除 Artifact Selector；构想台不灌 RYAN_CONTEXT。  
- Workflow Agent 保留。  

### 运行时与资产

- Pi RPC + `--no-context-files`；创作 Instructions 显式注入。  
- 复用六 Stage Skill；Utility 不 promote Canon。  
- ComfyTV Bridge 只 HTTP；回写资产库非 V1 必做。  

## 测试决策

- 只测外部行为：目录、API JSON、状态迁移、选择器 STRING、STALE 后文件仍在、重置后旧目录仍在。  
- 不测：鉴权、成员权限、TE_MAN 像素、真实云模型供应商（用假 runner）。  
- 必测：Repository、Registry、Export/READY、Stage Service、Chat/Thread 确认源、Asset Bridge、创作文本选择器、Artifact Selector 已移除回归。  
- UI：契约/手测；先例 `tests/workflow_agent/*`、`tests/nodes/*`。  

## 超出范围

- 用户认证/授权/token/权限控制。  
- 多用户项目、成员邀请、权限分配、组织协作。  
- 复制或依赖 TE_MAN 源码。  
- Creative 业务写入 ComfyTV / 共享 DB。  
- V1 强制回写 ComfyTV 资产库。  
- 选择器跨文档自动 join。  
- 构想台主路径 RYAN_CONTEXT。  
- 保留 Artifact Selector。  
- V1 必做第七 Stage（cinematic-director）。  
- 多 Provider 普通 LLM Chat UI。  
- 用数据库替换文件系统项目仓库。  

## 进一步说明

- 架构稿 §35「复用 Artifact Selector」已废弃。  
- Issue 必须回链本 PRD 与「文档与讨论索引」。  
- ComfyTV 接口变更时更新 `docs/agents/comfytv-asset-api-notes-v1.md`。  
- 深度讨论已沉淀为 `CONTEXT.md` + 本 Grill 纪要，无需依赖聊天记录开工。  
