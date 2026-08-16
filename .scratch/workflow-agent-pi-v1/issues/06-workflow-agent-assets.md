Status: ready-for-agent

# 图片 / 文本文档 / 视频 Asset 闭环

## 父问题

`.scratch/workflow-agent-pi-v1/PRD.md`

## 要构建什么

把 Chat 上传和 ComfyUI 节点输入统一映射为 `RyanAssetRef`，进入 Agent Session Asset Store，并在 DISCUSS / COMMIT 中实际消费。

V1 支持：

- 图片；
- `.txt`、`.md`、`.json`、`.csv` 文本类文档；
- 视频元数据、关键帧和场景首帧。

Audio 入口保留用于 UI 稳定性，但不实现转写和 Agent 消费。

## 验收标准

- [ ] Chat Upload 和节点输入都能生成包含 `asset_id`、Workflow、类型、mime、来源、URI、显示名、大小和创建者的 `RyanAssetRef`。
- [ ] Asset 复制到当前 Agent Session 目录，不允许 Pi 直接读取外部原路径。
- [ ] 图片可被 Pi / Skill 消费，原始文件和来源可追踪。
- [ ] `.txt`、`.md`、`.json`、`.csv` 可提取文本；单文件最大 20MB。
- [ ] Context 注入文本最大 100,000 字符；超出时返回明确截断信息。
- [ ] 视频能生成受限数量的元数据、关键帧、场景首帧和派生 AssetRef。
- [ ] 重复上传可按稳定 Asset ID 去重。
- [ ] 非法路径、文件不存在、大文件和视频无有效帧均返回明确错误。
- [ ] Attachment Tray 显示来源、文件名、类型、缩略图或派生状态。
- [ ] Audio 入口为 disabled，不能伪装为已消费。
- [ ] AssetRef 在 Context Inspector 中显示来源和数量。

## 被阻塞于

- Issue 02：需要 Agent Session Asset Store 和安全路径。
- Issue 04：需要 Chat Upload、Attach / Detach API 和 Commit 注入点。
- Issue 05：需要 Attachment Tray 和 Context Inspector UI。
