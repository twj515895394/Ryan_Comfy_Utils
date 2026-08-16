Status: ready-for-agent

# 01 创作项目仓库与重置/当前项目

## 父问题

- `.scratch/creative-workspace-v1/PRD.md`

## 必读索引

- `CONTEXT.md`（创作项目、重置工作区、工作区）
- `docs/architecture/Ryan-Creative-Workspace-Agent-Architecture-v1.md` §6、§41–42
- PRD「Grill 裁定」1、4 与「明确不做」

## 要构建什么

端到端交付本地 **创作项目** 生命周期：创建、列表、打开、记住全局 current、**重置工作区**（新 `creative_project_id` 并切换 current，**不删除**旧目录）。落盘根目录与 `project.json` / 空骨架目录可被后续 Stage 使用。

无用户账号、无成员、无权限。

## 验收标准

- [ ] 可创建创作项目并生成稳定 `creative_project_id` 与 `projects/<id>/` 目录骨架
- [ ] 可列表、按 id 打开；全局 `current_creative_project_id` 在打开/创建后更新
- [ ] 重置产生新 id、current 指向新项目、旧目录仍在且仍可打开
- [ ] 不引入登录/成员/邀请等模型或 API
- [ ] 单测覆盖创建/列表/current/重置保留旧目录

## 被阻塞于

无 - 可以立即开始

## 评论

