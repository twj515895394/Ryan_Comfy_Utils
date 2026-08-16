Status: ready-for-agent

# 08 ComfyTV AssetRef 与聊天引用

## 父问题

- `.scratch/creative-workspace-v1/PRD.md`

## 必读索引

- `CONTEXT.md`（资产引用）
- `docs/agents/comfytv-asset-api-notes-v1.md`（必读）
- 架构文档 §25–33
- PRD Grill 裁定 12

## 要构建什么

Ryan 侧 **ComfyTVAssetBridge**：

- 探测 ComfyTV；`GET /comfytv/assets`、categories 列表  
- 项目内只存 AssetRef（provider、id、payload_url 快照、semantic_role 等）  
- 聊天 @ / 附加引用进入 Context Compiler：图片尽力视觉附件（`/view` 解析或临时落地，失败降级元数据+URL）；视频元数据+可选关键帧（cache）；音频元数据  
- ComfyTV 不可用 → 本地上传降级，构想台仍可用  
- **不**做生成结果回写资产库（可留接口注释/后续）  
- **不** import ComfyTV Python 包硬耦合  

## 验收标准

- [ ] 有 ComfyTV 时可列表并添加 AssetRef 到项目
- [ ] discuss 请求能带上 ref 编译后的上下文（假 runner 可断言 prompt/附件侧写）
- [ ] 无 ComfyTV 时降级本地上传且不崩溃
- [ ] 项目目录无大文件副本作为主存储（ref+cache 策略符合 PRD）
- [ ] 单测 mock HTTP；不要求真实 ComfyTV 进程

## 被阻塞于

- `05-creative-chat-thread-discuss`
- `07-creative-workspace-ui-shell`（@ 资产交互；Bridge 后端可先于 UI 合入）

## 评论

