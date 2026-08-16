Status: ready-for-agent

# 07 构想台 UI Shell（TE_MAN 范式）

## 父问题

- `.scratch/creative-workspace-v1/PRD.md`

## 必读索引

- `CONTEXT.md` 开篇 UI 规则；工作区打开方式
- 架构文档 §12–13、§37–38（组件划分可参照，**交互照 TE_MAN**）
- PRD：不复制 TE_MAN 源码；无宿主节点

## 要构建什么

ComfyUI 内 **全局入口** 浮动/可停靠构想台面板（交互参照 TE_MAN：打开/关闭、流式消息、输入区、Stop 等已有范式）：

- 项目：当前项目展示、列表切换、新建、重置工作区  
- Stage 侧栏状态  
- Thread 列表与切换  
- 消息流 + Composer  
- 「确认当前阶段」「确认当前草稿」（按 READY 启用）  
- 不依赖画布宿主节点  

视觉 polish 可朴素，行为完整。

## 验收标准

- [ ] 全局可打开面板，无需拖 Creative 节点
- [ ] 可切换/新建/重置项目；重置后 UI current 为新 id，列表仍见旧项目
- [ ] 可切换 Stage/Thread 并完成一轮讨论与确认（接已有 API）
- [ ] 不引入登录/成员 UI
- [ ] 不复制 TE_MAN 源码进仓库

## 被阻塞于

- `01-creative-project-repository`
- `05-creative-chat-thread-discuss`
- 确认按钮完整启用还需 `04-confirm-stage-and-reopen`（可先接 API 占位，合并前应接通）

## 评论

