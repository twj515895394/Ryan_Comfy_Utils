Status: ready-for-agent

# 02 TE_MAN 式布局 + Composer + 历史消息

## 父问题

- `.scratch/creative-workspace-ui-v1/PRD.md`

## 要构建什么

把 Ryan 构想台从单栏表单壳，改成接近 TE_MAN 的可用布局：

- 左：项目/Stage（可折叠）+ 后续 Thread 槽位
- 右：消息流（主区域）+ 底栏 Composer
- Composer：Enter 发送、Shift+Enter 换行、发送/Stop 切换、占位提示
- 打开 Stage/Thread 时加载历史消息（需补 GET messages API，读 thread jsonl）
- 顶部：确认当前阶段 / 确认草稿 / 刷新 / 关闭
- 优先复用 `workflow_agent` 的 MessageList、Composer、styles；允许参照 TE_MAN 结构加快实现

## 验收标准

- [ ] 面板视觉分区清晰：侧栏 + 主聊天 + 底栏，不再是控件堆叠
- [ ] Enter/Shift+Enter 行为正确
- [ ] 切换 Stage 后消息区加载该 Stage 当前 Thread 历史
- [ ] 与 01 流式结合：历史 + 新流式消息同列表展示
- [ ] 按钮入口仍在工具条 Ryan 构想台

## 被阻塞于

- `01-streaming-discuss-stop`（流式气泡接入；布局可先并行但合并需接好）

## 评论

