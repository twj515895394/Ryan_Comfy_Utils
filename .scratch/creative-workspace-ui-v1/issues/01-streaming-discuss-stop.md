Status: ready-for-agent

# 01 流式讨论与 Stop 端到端

## 父问题

- `.scratch/creative-workspace-ui-v1/PRD.md`
- `.scratch/creative-workspace-v1/PRD.md`

## 要构建什么

用户在构想台发送消息后，助手气泡**边生成边更新**；生成中可 **Stop**；结束后可确认草稿/阶段。

后端：Creative chat 在生成过程中通过 ComfyUI `send_sync` 推送事件（建议事件名 `ryan_creative_event`，payload 含 project/stage/thread/request_id/type/text）。discuss HTTP 可仍返回终态，但 UI 不依赖等整包才显示。  
前端：订阅事件，按 thread/request 路由到当前气泡；Stop 调现有 stop API 并翻转按钮态。

可复用 Workflow Agent 的 `ryan_agent_event` 模式与 Composer Stop 交互。

## 验收标准

- [ ] 发送后立即出现用户气泡与 pending/streaming 助手气泡
- [ ] delta 事件持续追加助手文本（假 runner 多 chunk 可测）
- [ ] 生成中点 Stop 停止追加并保留已生成部分为草稿态消息
- [ ] end/error 事件正确收尾；READY 状态可刷新
- [ ] 单测覆盖 publisher 被调用；前端关键状态机可用纯函数/最小测或文档化手测步骤

## 被阻塞于

无 - 可以立即开始

## 评论

