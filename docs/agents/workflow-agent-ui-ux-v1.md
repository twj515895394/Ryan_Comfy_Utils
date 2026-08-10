# Ryan Workflow Agent Workspace V1 — UI / UX 详细设计

> 状态：V1 UI 设计基线
> 日期：2026-08-10 17:24 +08:00
> 目标：在原生 ComfyUI 中实现一个**接近 UpDream Agent 节点体验、但更适合 ComfyUI DAG 工作方式**的美观、实用、长期可扩展的 Agent 交互界面。

---

# 1. UI 设计目标

本 UI 不是普通 ComfyUI 节点表单，也不是把聊天框硬塞进节点内部。

目标体验是：

```text
画布负责“流程结构”
节点负责“Agent 身份 + 状态”
右侧面板负责“深度聊天 + 上下文 + 多模态资料 + Commit”
```

视觉参考优先接近用户提供的 UpDream 截图：

- 深色工作台；
- Agent 节点简洁、像一个“工作角色卡片”；
- 右侧为可隐藏、可持续对话的大型 Chat Panel；
- Chat Panel 与节点选择联动；
- 节点本体不承担大段聊天内容；
- 聊天区支持图片、文档、视频、音频；
- 用户关闭面板后，画布仍然保持干净的 Agent DAG。

但不要做 1:1 视觉抄袭。Ryan 需要形成自己的视觉语言，并优先适配 ComfyUI 的缩放、连线、节点选中、Queue 状态和插件兼容性。

---

# 2. 核心 UX 原则

## 2.1 Canvas First

Agent UI 不能喧宾夺主。

用户关闭 Chat Panel 后，应只看到清晰的 DAG：

```text
Agent A ───────┐
               ├──> Agent D
Agent B ───────┘
```

节点不显示大段正文，不在节点里塞聊天记录，不让节点高度随着聊天内容无限增长。

## 2.2 Node = Anchor，Panel = Workspace

Agent Node 是该 Agent 在 DAG 中的“锚点”。

Right-side Chat Panel 才是用户工作的地方。

节点只显示：

- Agent 名称；
- Skill；
- 当前状态；
- Chat 消息数；
- 资产数；
- Commit revision；
- Upstream changed 状态；
- 打开聊天入口。

## 2.3 Chat 与 Commit 必须视觉上分离

不能让用户误以为 Agent 每回复一次，下游就自动更新。

UI 必须明确展示：

```text
当前讨论 Draft
≠
已提交 Commit
```

推荐把 Commit 按钮文案写成：

```text
确认并提交到 DAG
```

而不是模糊的：

```text
保存
完成
确定
```

## 2.4 Context 必须可见、可解释

用户必须知道当前 Agent 看到了什么。

不能只在后台偷偷把上游 Context 拼给模型。

Right Panel 必须提供 Context Inspector：

```text
当前可见上游
- 创意策划 · rev 3
- 角色设计 · rev 2
- 场景设计 · rev 1

资产
- 5 张图片
- 1 个 PDF
- 1 个视频
```

并允许展开查看每个 Context Entry 的来源、kind、revision、摘要和资产。

## 2.5 UI 状态优先于“炫技动画”

V1 可以有轻量过渡动画，但不能为了视觉效果牺牲状态清晰度。

必须优先让用户一眼看懂：

- 谁正在生成；
- 谁有未提交 Draft；
- 谁已经 Commit；
- 谁的上游发生变化；
- 谁报错；
- 哪个 Agent 当前在右侧面板中打开。

---

# 3. 整体页面布局

推荐采用：

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│                       ComfyUI Canvas                                     │
│                                                                          │
│     Agent A ───→ Agent B ───→ Agent C                                   │
│                                                                          │
│                                                                          │
│                                         ┌──────────────────────────────┐ │
│                                         │ Right Agent Workspace        │ │
│                                         │                              │ │
│                                         │ Header                       │ │
│                                         │ Context summary              │ │
│                                         │ Chat                         │ │
│                                         │ Draft / Commit               │ │
│                                         │ Composer                     │ │
│                                         └──────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

## 3.1 面板形态

V1 推荐使用 **Docked Right Panel**，而不是 Modal。

默认：

```text
width: 480px
min-width: 380px
max-width: min(680px, 55vw)
```

支持拖拽左边缘调整宽度。

用户关闭后，不保留半透明遮罩，不影响 Canvas 操作。

再次点击 Agent 节点即可重新打开。

## 3.2 面板不能挤坏 Canvas

实现时优先选择：

- overlay dock；或
- 使用 ComfyUI 原生可扩展 sidebar/layout 能力；

不要直接粗暴修改 Canvas 固定宽度导致缩放中心、鼠标坐标、节点拖拽位置异常。

如果采用 overlay，面板需要有明确阴影/边框与 Canvas 区隔，但避免过重。

---

# 4. Agent Node 视觉设计

## 4.1 推荐尺寸

默认：

```text
width: 260~300px
height: 128~160px
```

不要超过普通 ComfyUI 节点过多。

## 4.2 节点结构

```text
┌────────────────────────────────┐
│ ●  AI 剧本导演             ⋯   │
│    script-director             │
├────────────────────────────────┤
│ Skill                          │
│ script-director                │
│                                │
│ 💬 12     📎 4     Commit v3   │
│                                │
│ [ 打开聊天 ]                   │
└────────────────────────────────┘
```

节点标题优先显示 `agent_name`，Skill 作为次级信息。

不要让 `skill_id` 抢过 Agent 名称。

## 4.3 节点状态

至少支持以下状态：

```text
idle                未开始
chatting             有聊天但未提交
generating           Agent 正在回复 / Commit 正在生成
committed            已提交
upstream_changed      上游 Commit 已发生变化
error                 调用失败
```

建议节点顶部使用：

- 小圆点状态灯；
- 轻量边框高亮；
- 状态短文案；

不要整块背景大面积闪烁。

### 状态文案建议

```text
未开始
讨论中
生成中…
已提交 · v3
上游已更新
调用失败
```

## 4.4 Upstream Changed 是一级状态

当上游 Agent 提交新 revision，而当前 Agent 上一次 Commit 基于旧上游时：

节点应该出现明显但不打断用户的提示：

```text
⚠ 上游已更新
```

Right Panel Header 同时显示：

```text
当前 Commit 基于旧版上游 Context
[查看变化]
```

不要自动重跑当前 Agent，也不要自动覆盖当前 Commit。

## 4.5 当前打开 Agent 的视觉反馈

右侧 Panel 当前对应哪个 Agent，Canvas 上必须看得出来。

推荐：

- 节点外框增加 1~2px accent ring；
- Header 状态点高亮；
- 不使用大面积发光。

---

# 5. Right Agent Workspace 结构

推荐结构：

```text
┌────────────────────────────────────────┐
│ Header                                 │
├────────────────────────────────────────┤
│ Context Bar / Context Inspector        │
├────────────────────────────────────────┤
│                                        │
│ Chat Message Stream                    │
│                                        │
│                                        │
├────────────────────────────────────────┤
│ Draft / Commit Bar                     │
├────────────────────────────────────────┤
│ Attachment Tray                        │
│ Composer                               │
│ Footer Controls                        │
└────────────────────────────────────────┘
```

---

# 6. Header 设计

参考 UpDream 的紧凑 Header，但增加 Ryan 的状态信息。

推荐：

```text
🤖 剧本导演
script-director

已提交 v3 · 12 条消息 · 4 个资产
                                  [×]
```

右侧可以有：

```text
⋯
```

二级菜单：

- 重命名 Agent；
- 更换 Skill；
- 重启当前 Chat Session；
- 查看 Commit 历史；
- 清理未提交 Draft；
- 调试信息（开发模式）。

不要把高危动作直接做成 Header 一级按钮。

---

# 7. Context Bar / Context Inspector

这是 Ryan 相比普通聊天插件非常重要的一块。

## 7.1 默认折叠态

默认只占一小条：

```text
↑ 上游 3 个 Agent · 7 个 Context Entries · 6 个资产    [展开]
```

不要默认占用大量聊天空间。

## 7.2 展开态

```text
当前 Agent 可见上下文

✓ 创意策划
  creative.story · rev 3
  2,180 字 · 1 asset

✓ 角色设计
  character.design · rev 2
  3,420 字 · 3 assets

✓ 场景设计
  location.design · rev 1
  1,220 字 · 2 assets
```

每个来源支持展开：

- Context 摘要；
- 完整 Markdown；
- asset refs；
- source agent；
- created_at；
- upstream lineage。

V1 不要求做复杂 Graph Viewer，但必须让用户知道内容来源。

## 7.3 多路 fan-in 的视觉表达

如果当前 Agent 有多路 Context 输入，不要只显示：

```text
context_01
context_02
context_03
```

用户层应显示真实来源 Agent 名称。

Socket 名只用于底层实现。

---

# 8. Chat Message Stream

## 8.1 消息布局

参考现代 AI Chat，但保持工作台风格。

推荐：

- 用户消息靠右或使用明显卡片；
- Agent 消息靠左；
- 长 Markdown 正文占满内容区；
- code block、table、heading 正常渲染；
- 不要每条消息都套厚重气泡。

对于长剧本/分镜内容，推荐 Agent 回答使用“文档式正文”，比圆角聊天气泡更适合阅读。

## 8.2 消息辅助操作

每条 Agent 消息 hover 时允许：

```text
复制
引用到输入框
标记为 Commit 候选
```

V1 不需要复杂点赞/反应系统。

## 8.3 Streaming

如果 Provider 支持流式：

- 内容逐步显示；
- 底部 Send 按钮变为 Stop；
- 节点状态同步为 `generating`；
- 切换到其他 Agent 后，后台生成可继续；
- 返回时恢复流式/最终状态。

不要把用户锁死在当前 Agent Panel。

---

# 9. Draft / Commit UI

这是整个 V1 最关键的 UI 状态。

## 9.1 Draft 状态

用户开始新一轮讨论后：

```text
Draft has changes
```

UI 显示：

```text
● 当前有未提交讨论
上次 Commit：v3
```

节点同时显示：

```text
讨论中 · 基于 v3
```

## 9.2 Commit Bar

推荐固定在 Composer 上方：

```text
┌────────────────────────────────────────┐
│ 当前 Draft 尚未进入 DAG               │
│ 上次提交：v3                           │
│                    [预览] [确认并提交] │
└────────────────────────────────────────┘
```

按钮文案推荐：

```text
确认并提交到 DAG
```

## 9.3 Commit Preview

点击 Commit 前可以出现轻量 Preview Drawer：

```text
即将产生：script.direction · rev 4
将继承：7 upstream entries
关联资产：4

[取消] [确认 Commit]
```

V1 不强制做复杂 Diff，但至少显示：

- 新 revision；
- kind；
- 当前上游数量；
- asset 数；
- 是否基于最新 upstream。

## 9.4 Commit 完成反馈

成功后：

- Node 状态变 `已提交 · vN`；
- Commit Bar 变为稳定状态；
- 显示短暂 toast：`已提交到 DAG · vN`；
- 不弹阻断 Modal。

---

# 10. Composer 设计

参考用户截图中的 UpDream 底部输入区。

推荐：

```text
┌────────────────────────────────────────┐
│ [📄] [🖼] [🎬] [🎵]                    │
│                                        │
│ 描述你的需求，或继续讨论…              │
│                                        │
│ Agent模式  Skill ▼  Provider ▼      ↑  │
└────────────────────────────────────────┘
```

## 10.1 输入框

要求：

- 自动增高，但设置最大高度；
- 超过最大高度后内部滚动；
- 支持粘贴图片；
- 支持拖文件到 Composer；
- Enter / Shift+Enter 行为可配置或遵循常见 Chat 习惯。

建议：

```text
Enter        发送
Shift+Enter  换行
```

并允许设置切换。

## 10.2 Send / Stop

发送时使用圆形或方圆按钮。

生成中切换为 Stop 图标，参考用户截图右下角停止按钮的交互逻辑。

不要同时显示 Send 和 Stop 两个按钮。

---

# 11. Multimodal Attachment Tray

V1 UI 从一开始就应保留四类入口：

```text
Document
Image
Video
Audio
```

即使后端某类型尚未完全支持，UI 也不要反复改变整体布局；未支持时可以 disabled + tooltip。

## 11.1 上传后的资产卡片

Composer 上方展示小型 chip/card：

```text
🖼 女主参考.png      ×
📄 世界观.pdf        ×
🎬 参考镜头.mp4      ×
```

图片可以显示 thumbnail。

视频可显示首帧 thumbnail + duration。

文档显示文件类型图标 + 文件名。

## 11.2 来源标识

Asset 不只来自 Chat Upload。

同一套 UI 应兼容：

```text
聊天上传
节点输入
上游 Context
未来 ComfyTV Asset Library
```

在 Context Inspector 中显示来源：

```text
来源：角色参考图节点 #31
来源：创意 Agent rev 2
来源：本次聊天上传
```

---

# 12. Panel 隐藏 / 恢复

用户明确需要：聊天框可以隐藏，只剩下 Agent 节点。

因此必须支持：

```text
Close Panel
```

关闭后：

- Agent Session 继续存在；
- 正在进行的生成不被默认取消；
- Canvas 恢复完整可操作区域；
- 再次点击 Agent 节点恢复对应 Session。

可以考虑在 ComfyUI sidebar / toolbar 保留一个极简：

```text
🤖 Agent
```

入口，用于恢复最近打开的 Agent Panel。

但 V1 不强制。

---

# 13. Agent 切换体验

用户在多个 Agent 间切换应该非常快。

交互：

```text
点击 Agent A -> Panel A
点击 Agent B -> Panel B
点击 Agent C -> Panel C
```

不要每次打开新 Modal。

Panel 本身保持同一个容器，只替换 Session 内容。

需要保留每个 Agent 的：

- 滚动位置；
- Draft 输入；
- 已上传但未发送附件；
- 当前生成状态。

如果实现成本高，V1 至少保留 Draft 文本，避免误删用户输入。

---

# 14. 视觉风格

目标是“现代深色创作工作台”，接近用户提供的 UpDream 截图，而不是传统 ComfyUI 原生灰色表单。

## 14.1 色彩层级

推荐通过 CSS variables 设计，不在组件里散落硬编码色值。

示意：

```css
--ryan-bg-canvas-overlay
--ryan-bg-panel
--ryan-bg-elevated
--ryan-bg-input
--ryan-border
--ryan-border-strong
--ryan-text-primary
--ryan-text-secondary
--ryan-accent
--ryan-success
--ryan-warning
--ryan-error
```

优先继承/适配 ComfyUI 当前主题变量；Ryan 变量提供 fallback。

用户切换 ComfyUI 主题时，不应整块 UI 失去可读性。

## 14.2 圆角

建议：

```text
Panel outer: 14~18px
Cards: 10~12px
Composer: 14~16px
Small chips: 8~10px
```

不要所有层级都使用同样圆角。

## 14.3 间距

使用统一 spacing scale：

```text
4 / 8 / 12 / 16 / 20 / 24
```

不要出现大量随机 7px、13px、19px。

## 14.4 字体层级

建议：

```text
Agent Name       14~16px semibold
Body             13~14px
Secondary        11~12px
Code/metadata    11~12px monospace optional
```

长文正文行高至少 1.5，避免剧本和 Prompt 挤成一团。

## 14.5 阴影与边框

深色界面优先靠：

```text
1px border
+ very subtle shadow
```

区分层级。

不要大量 neon glow。

---

# 15. 与 UpDream 截图对齐的关键点

V1 至少要保留用户看中的这些体验：

1. **Agent Node 很简洁。**
2. **右侧是一个完整 Chat Workspace，不是节点内 textarea。**
3. **右侧 Panel 可以关闭。**
4. **关闭后只留下 Agent Node 和 DAG。**
5. **Chat 输入区支持图片 / 文档 / 视频 / 音频入口。**
6. **Agent 正在处理时有明确状态。**
7. **长回复可以在右侧面板中独立滚动。**
8. **节点选中与右侧 Agent 联动。**
9. **整体深色、克制、专业。**
10. **操作状态比装饰更突出。**

Ryan 在此基础上额外增加：

- Context Inspector；
- Commit revision；
- Upstream changed；
- DAG source attribution；
- Context/Asset lineage。

这些是 Ryan 相比普通 Agent Chat 节点真正应该做强的地方。

---

# 16. 推荐前端模块拆分

不要把全部逻辑写进一个 `ryan_workflow_agent.js` 巨文件。

推荐：

```text
ryan_comfy_utils/web/workflow_agent/
├── index.js
├── node_extension.js
├── panel_manager.js
├── agent_panel.js
├── context_inspector.js
├── message_list.js
├── composer.js
├── attachment_tray.js
├── commit_bar.js
├── api_client.js
├── state_store.js
├── styles.css
└── components/
```

如果 ComfyUI extension loader 对目录/模块加载方式有限制，可以构建时合并，但源码职责应保持清楚。

## 16.1 State Store

前端至少维护：

```text
activeAgentUid
panelOpen
panelWidth
agentSessionStateByUid
agentDraftByUid
agentScrollPositionByUid
agentGenerationStateByUid
```

不要把所有状态挂在 DOM dataset 上。

---

# 17. API 与 UI 状态映射

建议 UI 使用明确状态机，不要通过“按钮是否 disabled”反推业务状态。

示例：

```text
session_status:
  idle
  ready
  generating
  error

commit_status:
  none
  clean
  dirty
  committing
  committed
  upstream_changed
```

Panel 与 Node 都消费同一份状态。

避免 Node 显示 `已完成`，Panel 却显示 `未提交` 的状态分裂。

---

# 18. 错误体验

Agent 调用失败时：

节点：

```text
● 调用失败
```

Panel：

```text
本次回复失败
<简短错误摘要>

[重试]
[复制错误详情]
```

错误详情默认折叠。

不要把 Python stack trace 直接塞进主聊天区。

开发模式可以查看 raw error。

附件失败必须精确指出是哪一个文件失败。

---

# 19. Loading / Empty 状态

## Empty Session

```text
🤖 剧本导演

当前已收到 2 个上游 Context。
你可以直接开始讨论，或先查看上游内容。
```

不要只留一个空白聊天框。

## Loading History

使用 skeleton / lightweight spinner。

不要整个 Panel 白屏。

## No Upstream

显示：

```text
暂无上游 Context
本 Agent 将只使用当前聊天与直接连接素材。
```

---

# 20. Context Token / 内容规模提示

V1 不要求精准 token 计费 UI，但 Context Inspector 建议至少显示近似规模：

```text
7 entries
12.4k chars
6 assets
```

后续可以升级为：

```text
estimated tokens
context budget
truncated entries
```

如果 Runtime 做了裁剪，UI 必须明确提示“部分上游 Context 已被压缩/裁剪”，不能静默发生。

---

# 21. 可用性细节

建议支持：

- Esc：关闭 Panel（输入框 IME 状态需谨慎）；
- Ctrl/Cmd + Enter：可选 Commit 快捷键，但默认不要启用，避免误提交；
- 拖文件到 Panel；
- 粘贴截图；
- 复制 Agent 输出 Markdown；
- Chat 自动滚动仅在用户当前接近底部时执行；
- 用户上滚查看历史时，不强行把滚动条拉到底部；
- 生成期间可以切换 Agent；
- Panel resize 宽度持久化到前端设置。

---

# 22. ComfyUI 兼容性约束

## 22.1 不破坏节点连线

前端美化不能动态重排底层 slot identity。

`context_01..context_N` 底层顺序稳定。

UI 可以隐藏未使用输入，但不能删除/重建导致 workflow reload 丢线。

## 22.2 不接管 Canvas 核心事件

Right Panel / Agent Node 点击增强不得破坏：

- Canvas pan；
- zoom；
- box select；
- node drag；
- wire connect；
- keyboard shortcuts。

## 22.3 不要求 ComfyTV

Native ComfyUI + Ryan_Comfy_Utils 必须完整可用。

未来 ComfyTV 可以复用同一 Backend API 和 Session Store，做更高级 Workspace，但不能成为基础依赖。

---

# 23. V1 UI 实施顺序

不要第一天就打磨阴影和动画。

推荐：

```text
D1. Panel 容器 + Agent 节点联动
D2. Session / Message List
D3. Composer + Send / Stop
D4. Context Bar / Inspector
D5. Draft / Commit Bar
D6. Attachments
D7. Node 状态同步
D8. upstream_changed
D9. 主题、间距、圆角、细节 polish
D10. keyboard / resize / restore
```

但从 D1 开始就应使用最终布局骨架，避免后面大改 DOM 结构。

---

# 24. V1 UI 验收标准

UI 不能只满足“功能能点”。

至少通过以下验收：

1. 用户把 5 个 Agent 放在一张 Workflow 中，节点仍然紧凑、清晰，不像 5 个大表单。
2. 点击任意 Agent，右侧 Panel 在 150~250ms 内出现基础框架，不等待后端历史接口完全返回才显示。
3. Panel 默认宽度适合阅读长文本，也不完全遮住 Canvas。
4. Panel 可 resize、可关闭、可恢复。
5. Agent 切换时不会丢失未发送 Draft。
6. Chat 中可以清楚分辨用户消息、Agent 消息、System/Context 信息。
7. 上游 Context 默认折叠，但用户可一键查看完整来源。
8. 多路 fan-in 时用户能看到每一路实际来源 Agent，而不是 `context_01` 这种底层名字。
9. Chat 上传图片/文档/视频/音频的入口与用户提供的 UpDream 截图一样容易发现。
10. 生成状态在 Node 和 Panel 同步。
11. Commit 与普通发送视觉上明确不同。
12. Commit 成功后 revision 立即更新。
13. 上游新 Commit 后，当前 Agent 显示 `上游已更新`，但不自动覆盖现有 Commit。
14. 长剧本、长分镜 Markdown 阅读体验良好。
15. 关闭 Panel 后 Canvas 回归干净 DAG，没有残留大块浮层。
16. Dark Theme 下整体视觉接近现代创作工具，而不是传统配置面板。
17. 浏览器缩放 80%~125% 时没有明显错位。
18. 1366px、1920px、2K/4K 常见桌面宽度下均可使用。
19. 不破坏 ComfyUI 原有节点拖拽、连线、缩放、框选。
20. UI 代码结构可维护，不把 Panel、API、Node patch、CSS 全塞进一个 JS 文件。

---

# 25. 设计结论

Ryan Workflow Agent 的 UI 应围绕一句话设计：

> **在 Canvas 上看流程，在右侧 Panel 里做创作。**

用户提供的 UpDream 截图非常适合作为 V1 的体验参考：

```text
简洁 Agent Node
+
右侧大型 Chat Workspace
+
多模态输入
+
Panel 可隐藏
```

Ryan 不需要改变这个方向，而是在它上面补足真正适合 ComfyUI DAG 的能力：

```text
Context Inspector
+ Commit Revision
+ Upstream Changed
+ DAG 来源追踪
+ Asset Lineage
```

最终目标不是做一个“看起来像 ChatGPT 的节点”，而是做一个**AI 创作工作台中的专业 Agent 节点系统**。
