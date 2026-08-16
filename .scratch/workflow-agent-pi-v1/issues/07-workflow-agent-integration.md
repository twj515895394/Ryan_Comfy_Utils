Status: ready-for-human

# Workflow Agent V1 集成、兼容性与 Demo 验收

## 父问题

`.scratch/workflow-agent-pi-v1/PRD.md`

## 要构建什么

用真实 ComfyUI Workflow 验收 Pi Runtime、Generic Agent Node、RYAN_CONTEXT、Chat / Commit、右侧 Workspace、Assets 和五个 Starter Skill 的端到端闭环。

本问题包含最终 UI Polish 和需要人工观察的 ComfyUI 兼容性验证，因此标记为 `ready-for-human`。

## 验收标准

- [ ] 串行五阶段 Workflow 可运行：Creative → Production → Script → Storyboard → Video Prompt。
- [ ] fan-out 分支可以独立讨论和 Commit。
- [ ] fan-in 和 diamond 图按 Entry ID 去重并保留真实来源 Agent 名称和 lineage。
- [ ] Save As / Duplicate 生成新的 Workflow Scope；原 Workflow 的 Chat、Draft、Commit、Assets 不串入新 Workflow。
- [ ] 复制节点、更换 Skill、删除节点和 Workflow reload 不造成 Session 或 Context 错乱。
- [ ] 旧 ACP Agent、现有 Image / Video / H3 Agent、固定图片 Slot 和原生 Canvas 操作不回归。
- [ ] Pi 缺失、能力不足、认证失败、超时、RPC 中断、非法 Asset 和跨 Workflow Context 都有可读错误。
- [ ] 不会在 Pi 失败时自动回退 Claude。
- [ ] UI 满足 1366 / 1920 / 2K / 4K、80%～125% 浏览器缩放、Dark Theme、长 Markdown、Panel resize 和关闭恢复。
- [ ] 5 个 Agent 同屏仍紧凑清晰，Node / Panel 状态一致。
- [ ] ComfyUI Canvas pan、zoom、node drag、box select、wire connect、workflow reload 和快捷键保持正常。
- [ ] 完整 Python 测试集通过，真实 ComfyUI 手工验收记录已更新到设计文档和交接文档。

## 被阻塞于

- Issue 01：Pi Runner。
- Issue 02：Workflow / Agent Scope。
- Issue 03：RYAN_CONTEXT 和 Generic Node。
- Issue 04：Chat / Commit / RPC。
- Issue 05：Workspace。
- Issue 06：Assets。
