Status: ready-for-agent

# 03 ryan-stage-export 解析与落盘

## 父问题

- `.scratch/creative-workspace-v1/PRD.md`

## 必读索引

- `CONTEXT.md`（阶段导出块、交付文档、项目 Canon）
- 架构文档 §17、§34、§41（路径以 PRD 为准）
- PRD Grill 裁定 5–6、10–11；分叉表「产物对外合同」

## 要构建什么

解析 Agent 回复中唯一的 `ryan-stage-export` fenced JSON，校验后写入：

- `canon/<stage>/latest.md` + `vNNN.md`
- `deliverables/<stage>/` 下整篇 `.md` 与主 `.items.md`（`## id — label` + 纯文本正文）
- 再次导出时 **整文件覆盖** latest，并保留与 revision 对齐的历史快照

提供 READY 判定：合法 export 且满足该 Stage deliverables 合同（script 等允许无 deliverables）。  
**不**实现 Artifact Selector；**不**把 bundle 作为节点输入合同。

## 验收标准

- [ ] 合法 export 写出 canon latest 与约定 deliverables 路径
- [ ] items 文件可按标题拆出条目纯文本（供选择器复用同一解析）
- [ ] production/storyboard/video_prompt 主 items 文件名符合 PRD
- [ ] 非法/缺失块 → 非 READY，不写半套 latest
- [ ] 二次导出覆盖 latest，历史快照可区分 revision
- [ ] 单测覆盖解析、写盘、覆盖、失败路径

## 被阻塞于

- `01-creative-project-repository`
- `02-stage-registry-and-stale`（Stage 合同与路径）

## 评论

