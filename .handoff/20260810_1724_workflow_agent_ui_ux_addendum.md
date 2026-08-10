# Ryan Workflow Agent Workspace V1 — UI / UX 交接补充

> 交接时间：2026-08-10 17:24 +08:00
> 仓库：`twj515895394/Ryan_Comfy_Utils`
> 分支：`main`
> 前置交接：`.handoff/20260810_1717_workflow_agent_workspace_v1_handoff.md`
> UI 设计 Source of Truth：`docs/agents/workflow-agent-ui-ux-v1.md`
> 重要级别：**必须阅读 / 不可把 UI 当成最后随便补的壳**

---

# 1. 为什么新增这份补充

用户明确补充：本项目不仅要求 Runtime、DAG Context、Chat/Commit 逻辑正确，**UI 也必须美观、实用，最好达到前面提供的 UpDream Agent 节点截图那种工作台体验。**

因此后续 Agent 不能把 UI 理解成：

```text
给 ComfyUI 节点加几个 textarea
+ 一个 send button
+ 一个普通 popup
```

这不符合产品目标。

V1 的 UI 体验本身就是产品的一部分。

---

# 2. 强制阅读顺序

接手开发的 Agent 应按下面顺序读取：

```text
1. .handoff/20260810_1717_workflow_agent_workspace_v1_handoff.md
2. docs/agents/workflow-agent-workspace-v1-design.md
3. docs/agents/workflow-agent-context-contract-v1.md
4. docs/agents/workflow-agent-ui-ux-v1.md
5. docs/agents/scene-forge-skill-migration-v1.md
```

其中 `workflow-agent-ui-ux-v1.md` 已经详细定义：

- Agent Node 视觉层级；
- Right-side Agent Workspace；
- Header；
- Context Bar / Context Inspector；
- Chat Stream；
- Draft / Commit Bar；
- Composer；
- Document / Image / Video / Audio 多模态入口；
- Panel hide / restore；
- Agent 切换；
- upstream_changed；
- streaming / stop；
- 状态机；
- 视觉风格；
- 前端模块拆分；
- ComfyUI 兼容约束；
- 20 条 UI 验收标准。

---

# 3. UI 总原则

后续实现必须遵循：

> **在 Canvas 上看流程，在右侧 Panel 里做创作。**

对应：

```text
Canvas
  = DAG / Agent 关系 / Context 流向

Agent Node
  = Agent 身份 + Skill + 状态 + Commit Revision

Right Panel
  = Private Chat + Context Inspector + Multimodal Assets + Commit
```

不要把大量聊天内容塞进节点。

---

# 4. UpDream 截图中必须保留的体验

用户前面提供的 UpDream 截图是重要交互参考。

V1 至少需要做到：

```text
简洁 Agent Node
+
右侧大型 Chat Workspace
+
长回复独立滚动
+
图片 / 文档 / 视频 / 音频入口
+
生成中的停止按钮
+
Panel 可关闭
+
关闭后画布只剩 Agent DAG
+
点击不同 Agent 时右侧切换对应 Session
```

不要追求 1:1 抄 UI，但整体体验应让用户感觉这是一个现代 AI 创作工作台，而不是传统 ComfyUI 配置节点。

---

# 5. Ryan 必须比普通 Chat 节点多出来的能力

不能只复刻 UpDream。

Ryan 的优势必须通过 UI 表达出来：

```text
Context Inspector
Commit Revision
Upstream Changed
DAG Source Attribution
Asset Lineage
```

特别是 Context Inspector：

当前 Agent 能看到哪些上游内容，必须让用户可以检查。

示例：

```text
当前可见上游：3 个 Agent

✓ 创意策划 · creative.story · rev 3
✓ 角色设计 · character.design · rev 2
✓ 场景设计 · location.design · rev 1

资产：6
```

不要后台偷偷拼上下文、UI 完全不显示。

---

# 6. Chat / Commit UI 必须非常明确

V1 架构中：

```text
Chat != Commit
```

所以 UI 必须明显区分：

```text
当前 Draft
vs
已提交到 DAG 的 Commit
```

推荐主要提交按钮：

```text
确认并提交到 DAG
```

不要使用模糊的：

```text
保存
完成
确定
```

用户每发一条聊天消息后，下游不能因此自动更新。

---

# 7. Agent Node 不应该做成大表单

推荐 Node 保持紧凑：

```text
┌──────────────────────────────┐
│ ● 剧本导演               ⋯  │
│   script-director            │
├──────────────────────────────┤
│ 💬 12  📎 4  Commit v3       │
│                              │
│ [打开聊天]                   │
└──────────────────────────────┘
```

状态至少：

```text
未开始
讨论中
生成中
已提交 · vN
上游已更新
调用失败
```

Panel 当前打开哪个 Agent，Canvas 上对应节点必须有选中/激活反馈。

---

# 8. Right Panel 是 V1 的正式 Workspace

不要用普通 Modal。

推荐 Docked Right Panel：

```text
default width: 480px
min width: 380px
max width: min(680px, 55vw)
```

支持 resize、close、restore。

结构：

```text
Header
Context Summary
Chat Stream
Draft / Commit Bar
Attachment Tray
Composer
Footer Controls
```

关闭 Panel 不能丢 Session、Draft 或正在进行的后台生成状态。

---

# 9. 多模态 UI 从 V1 就预留完整入口

UI 固定保留：

```text
Document
Image
Video
Audio
```

后端某类型暂未实现时可以 disabled，但不要频繁改变 Composer 布局。

上传后使用 attachment chip/card：

```text
🖼 女主参考.png
📄 世界观.pdf
🎬 参考镜头.mp4
🎵 配乐参考.wav
```

资产最终统一映射 `RyanAssetRef`。

---

# 10. Phase D 不再是“随便能用即可”

原交接中 Phase D 是 Right-side Chat Panel。

本补充明确：

**Phase D 的功能完成和 UI 验收是两件事，都必须完成。**

正确开发节奏：

```text
Phase A  Context Core
Phase B  Generic Node
Phase C  Session / Chat API
Phase D1 UI Functional Skeleton
Phase D2 UI State Integration
Phase D3 UI Polish + Compatibility Acceptance
Phase E  Multimodal Assets
Phase F  Film Pipeline Demo
```

UI polish 不等于只调颜色，而包括：

- 信息层级；
- 可读性；
- 交互反馈；
- Panel resize；
- 长文本阅读；
- Draft 不丢；
- Agent 切换；
- Context Inspector；
- Commit 状态；
- ComfyUI Canvas 不被破坏。

---

# 11. 前端实现不要堆成一个 JS 文件

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

具体可因 ComfyUI loader 限制调整，但职责边界不要消失。

---

# 12. UI 开发时必须保护 ComfyUI 原生体验

禁止因为自定义 UI 破坏：

```text
Canvas pan
zoom
node drag
box select
wire connect
workflow reload
keyboard shortcuts
```

尤其：

`context_01..context_N` 底层 Socket identity 保持稳定。

可以隐藏未使用 Socket，但不要动态删除/重建导致 workflow reload 丢连接。

---

# 13. UI 验收基线

后续 Agent 在宣称 Phase D 完成前，至少人工验证：

```text
1. 5 个 Agent 同屏仍然紧凑清晰
2. 点击节点右侧立即出现 Workspace 骨架
3. Panel 可 resize / hide / restore
4. 多 Agent 切换不丢 Draft
5. 长 Markdown / 剧本可阅读
6. Context 默认折叠但可检查来源
7. fan-in 能显示真实来源 Agent 名
8. 图片/文档/视频/音频入口明显
9. generating / stop 状态同步
10. Chat 与 Commit 清楚分离
11. Commit revision 立即同步到 Node
12. upstream_changed 清楚提示
13. 关闭 Panel 后 Canvas 干净
14. Dark Theme 视觉专业
15. 1366 / 1920 / 2K / 4K 宽度可用
16. 浏览器缩放 80%~125% 不明显错位
17. 不破坏 ComfyUI 连线/拖动/缩放
```

完整标准见：

```text
docs/agents/workflow-agent-ui-ux-v1.md
```

---

# 14. 给后续 Agent 的最终提醒

不要出现这种开发结果：

```text
后端架构很好
Context 也正确
Session 也能跑
但是 UI 只是一个丑陋 textarea + button
```

这不算这个项目 V1 达标。

用户想要的是：

> 在 ComfyUI 里可以长期使用的 AI 创作 Agent 工作台。

因此 UI 与 Runtime 同样属于核心产品能力。

后续如果 UI 实现与 `workflow-agent-ui-ux-v1.md` 存在重大偏差，必须在 handoff 中记录原因，而不是默默降低标准。
