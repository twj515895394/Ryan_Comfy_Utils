Status: ready-for-agent

# 03 Thread 侧栏（多话题）

## 父问题

- `.scratch/creative-workspace-ui-v1/PRD.md`

## 要构建什么

Stage 内多 Thread：列表、新建、切换、显示标题/空状态；切换后加载对应历史并作为确认作用域（当前 Thread）。  
对接已有 create/list thread API；缺展示字段则最小扩展。

## 验收标准

- [ ] 可新建副 Thread 并切换
- [ ] 各 Thread 消息隔离显示
- [ ] 确认使用当前 Thread（与 CONTEXT 一致）
- [ ] 主 Thread 默认存在且可识别

## 被阻塞于

- `02-teman-layout-composer-history`

## 评论

