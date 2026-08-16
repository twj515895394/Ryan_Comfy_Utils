Status: ready-for-agent

# 02 Stage 注册表、状态与 STALE 规则

## 父问题

- `.scratch/creative-workspace-v1/PRD.md`

## 必读索引

- `CONTEXT.md`（阶段、STALE、Stage Reopen）
- 架构文档 §7–8、§15–16、§44–45
- PRD Grill 裁定 9–10

## 要构建什么

配置化六 Stage 管道（依赖、默认 Skill、deliverables 合同占位）与 Stage 状态模型：`NOT_STARTED | DRAFT | READY | LOCKED | STALE | ERROR`。上游 Canon revision 变化时标记下游 **STALE**（只改状态与 `stale_causes`，**不删**磁盘交付文件）。提供读取 stages 快照的 API/服务接口供后续确认与 UI。

## 验收标准

- [ ] `cinematic_v1` 含六 Stage 与依赖图（与架构/PRD 一致）
- [ ] 可查询项目内各 Stage 状态与 revision 元数据
- [ ] 模拟上游锁定新版本后，下游变为 STALE 且原因可读
- [ ] STALE 不删除任何 `canon/` / `deliverables/` 文件
- [ ] 单测覆盖依赖传播与状态迁移

## 被阻塞于

- `01-creative-project-repository`

## 评论

