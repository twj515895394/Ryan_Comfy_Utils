Status: ready-for-agent

# 10 STALE 提示与选择器过期可见性

## 父问题

- `.scratch/creative-workspace-v1/PRD.md`

## 必读索引

- `CONTEXT.md`（STALE）
- 架构文档 §16
- PRD Grill 裁定 9

## 要构建什么

在状态层 STALE 已存在的前提下，打通**可见性**：

- 构想台 Stage 列表/头显示过期与 `stale_causes`  
- 创作文本选择器在读取仍属 STALE 阶段的交付物时给出过期提示（UI 或节点提示），但 **仍返回可读纯文本**，不删文件、不改路径  
- 下游再次确认后清除自身 STALE，提示消失  

## 验收标准

- [ ] 上游确认后下游 UI 可见 STALE 原因
- [ ] 选择器在 STALE 时仍能输出条目纯文本
- [ ] 选择器/UI 有过期提示，而非静默
- [ ] 下游再确认后 STALE 清除
- [ ] 回归：STALE 不移动 deliverables 路径

## 被阻塞于

- `02-stage-registry-and-stale`
- `04-confirm-stage-and-reopen`
- `09-creative-text-selector-remove-artifact-selector`

## 评论

