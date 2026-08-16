Status: ready-for-agent

# 09 创作文本选择器 + 删除 Artifact Selector

## 父问题

- `.scratch/creative-workspace-v1/PRD.md`

## 必读索引

- `CONTEXT.md`（创作文本选择器；已废弃 Artifact Selector）
- PRD 分叉表「执行桥」；Grill 裁定 2–3、10
- 架构文档 §35 以 PRD 分叉为准（不再复用 Artifact Selector）

## 要构建什么

1. 新节点 **创作文本选择器**：  
   - 显式 `creative_project_id`（创建节点时默认快照 current；**重置不自动改**）  
   - 文档列表来自该项目 `canon/**/latest.md` 与 `deliverables/**/*.md`  
   - 普通 md 可整篇输出  
   - `.items.md` **必须选条目**，STRING = 条目纯提示词（无 JSON/围栏/套话）  
   - 未选条目 → 失败/空并明确提示  

2. **删除** Ryan Artifact Selector 节点、专用前端扩展及注册；清理失效测试，改为选择器测试。  

构想台不灌 RYAN_CONTEXT 作为本切片范围。

## 验收标准

- [ ] 选择器可读 fixture 项目目录并输出正确纯文本
- [ ] items 整篇不选条目不得当提示词成功输出
- [ ] 节点保存的 project_id 不随全局重置而变
- [ ] 包加载后不存在 Artifact Selector 注册名
- [ ] 单测覆盖选择器；旧 Artifact Selector 测试删除或改写

## 被阻塞于

- `01-creative-project-repository`
- `03-stage-export-and-deliverables`（真实目录合同与 items 格式）

## 评论

