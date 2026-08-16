Status: ready-for-agent

# 05 单 Stage 聊天 Thread 与 Pi DISCUSS

## 父问题

- `.scratch/creative-workspace-v1/PRD.md`

## 必读索引

- `CONTEXT.md`（话题/线程、工作区）
- 架构文档 §14、§22–24、§47.3、§48
- ADR-0001（Pi RPC、Stop、不自动 Queue）
- PRD：Chat≠Canon；请求键 project+thread

## 要构建什么

在一个创作项目的单个 Stage 上：

- 主 Thread + 可建副 Thread  
- DISCUSS：复用现有 Pi RPC 流式事件（归一为创意事件）  
- Stop；不自动确认、不自动 Queue Comfy  
- 持久化 thread 消息（如 jsonl）  
- 为确认提供「当前 Thread 最后完整助手结果」读取接口  

Coding `AGENTS.md` 不得进入 Pi（`--no-context-files` + 显式创作 prompt 占位可后续 issue 加厚）。

## 验收标准

- [ ] 可对指定 project/stage/thread 发送讨论并收到流式/结束事件
- [ ] 可 Stop；不触发确认写盘
- [ ] 多 Thread 隔离；切换当前 Thread 影响「当前结果」读取
- [ ] 进程工作目录/session 不落在仓库根污染
- [ ] 单测用假 runner 覆盖 discuss/stop/thread 隔离

## 被阻塞于

- `01-creative-project-repository`
- `02-stage-registry-and-stale`

## 评论

