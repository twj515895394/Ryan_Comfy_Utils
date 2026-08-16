Status: ready-for-agent

# 05 Skill / 斜杠选择面板

## 父问题

- `.scratch/creative-workspace-ui-v1/PRD.md`

## 要构建什么

Composer 支持 `/` 打开 Skill 面板（Stage Skill 列表来自 `/ryan/creative/skills`）；选择后：

- Stage Skill：切换当前 Stage/skill_id
- 显示当前 Skill chip
- 发送时带 skill_id / skill_scope

Utility Skill 若列表暂无，可先只做 Stage Skill，预留 turn scope。

## 验收标准

- [ ] `/` 或按钮打开面板，可键盘/鼠标选择
- [ ] 选择 Stage Skill 后侧栏 Stage 与发送参数一致
- [ ] Esc 关闭；选择后输入区聚焦
- [ ] 不把 `/skill` 原文原样当唯一用户消息协议（结构化字段优先）

## 被阻塞于

- `02-teman-layout-composer-history`

## 评论

