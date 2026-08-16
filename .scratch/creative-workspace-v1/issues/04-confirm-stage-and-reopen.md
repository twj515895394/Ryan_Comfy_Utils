Status: ready-for-agent

# 04 确认当前阶段 / 确认草稿 / Reopen

## 父问题

- `.scratch/creative-workspace-v1/PRD.md`

## 必读索引

- `CONTEXT.md`（确认当前阶段、可确认草稿、Stage Reopen）
- 架构文档 §18–19（UI 词用「确认」；流程以 PRD 为准）
- PRD Grill 裁定 7–9、11

## 要构建什么

Stage 确认用例端到端（后端）：

1. **确认当前阶段**（默认）：对**当前 Thread** 再跑正式 COMMIT 向 Pi 取规范化 `ryan-stage-export`（可用假 runner），再经 Export 写盘 → Stage `LOCKED`，下游 STALE。  
2. **确认当前草稿**：仅当 READY 时跳过模型，直接用最后完整助手结果导出。  
3. **Reopen**：已锁定 Stage 可回到可编辑，不等于重置工作区。  

同一 `project+stage` 确认需互斥，避免双写 revision。

## 验收标准

- [ ] 默认确认调用正式导出路径并 LOCKED + 写盘
- [ ] READY 时确认草稿不调模型且写盘结果一致合同
- [ ] 非 READY 不能走确认草稿
- [ ] 确认作用域为当前 Thread，不合并多 Thread
- [ ] 确认后下游 STALE；文件仍在
- [ ] Reopen 不新建 creative_project_id
- [ ] 单测覆盖上述路径（假 Pi/夹具）

## 被阻塞于

- `02-stage-registry-and-stale`
- `03-stage-export-and-deliverables`

## 评论

