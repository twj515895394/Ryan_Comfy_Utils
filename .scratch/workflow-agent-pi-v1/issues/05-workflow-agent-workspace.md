Status: ready-for-agent

# 功能完整的右侧 Agent Workspace

## 父问题

`.scratch/workflow-agent-pi-v1/PRD.md`

## 要构建什么

在 ComfyUI 原生 Canvas 右侧提供可长期使用的 Agent Workspace。UI 不能退化为节点内 textarea + button，也不能破坏 Canvas pan、zoom、拖动、框选、连线、保存和快捷键。

Workspace 至少由独立职责组成：Panel Manager、Agent Panel、State Store、API Client、Context Inspector、Message List、Composer、Attachment Tray、Commit Bar 和 styles。

## 验收标准

- [ ] 点击 Agent 节点右侧立即出现 Workspace；双击或节点按钮也可打开。
- [ ] Panel 默认约 480px，可 resize、hide、restore；关闭后 Canvas 干净。
- [ ] 5 个 Agent 同屏时节点紧凑、信息层级清晰，Canvas 不被大面板覆盖。
- [ ] Header 显示 Agent 名称、Skill、状态、消息数、附件数和 Commit revision。
- [ ] Chat、Draft、Commit、Context Inspector 明确分区。
- [ ] Agent 切换不丢 Draft、滚动位置和生成状态；重新打开可恢复。
- [ ] Chat 支持长 Markdown / 剧本阅读，不把内容压缩成不可读的一行。
- [ ] Send、Stop、loading、streaming、completed、error 状态同步。
- [ ] Context Inspector 显示真实来源 Agent 名、revision、kind、lineage 和资产数量。
- [ ] Commit Bar 清楚显示 Draft、当前 revision、确认提交、upstream_changed 和错误重试。
- [ ] 图片、文档、视频、音频入口明显；音频入口保留但禁用并说明原因。
- [ ] Panel 关闭不停止后台生成。
- [ ] UI 在 1366 / 1920 / 2K / 4K 和浏览器 80%～125% 缩放下可用。
- [ ] 不破坏 ComfyUI 原生节点拖动、缩放、框选、连线和 Workflow reload。

## 被阻塞于

- Issue 03：需要 Generic Agent Node 和 Context 状态。
- Issue 04：需要 Chat / Commit / RPC API 和状态事件。
