Status: ready-for-agent

# Creative Workspace UI V1（对齐 TE_MAN 可用聊天体验）

## 问题陈述

构想台后端已具备项目/Stage/确认/Chat API，但前端仍是联调壳：无 TE_MAN 级布局、无真正流式气泡、无 Stop/附件/@资产//Skill/多 Thread 交互，无法作为主创作界面使用。

## 解决方案

在**不强制从零自研**的前提下，优先复用本仓库 `workflow_agent` 前端组件与事件模型，并允许参照/移植 TE_MAN 构想台的布局与交互模式，把 Ryan 构想台做成可用的创作聊天 IDE：流式讨论、Stop、Thread、素材、Skill、确认条，视觉接近 TE_MAN。

父 PRD：`.scratch/creative-workspace-v1/PRD.md`  
术语：`CONTEXT.md`

## 范围

- 流式 discuss + Stop
- TE_MAN 式双栏布局 + Composer + 消息列表
- Thread 侧栏
- 资产引用 UI
- Skill 选择 UI
- 视觉 polish

## 非范围

- 登录/成员协作
- 重做后端 Canon/落盘合同
- 浏览器自动化验收（用户手测）
