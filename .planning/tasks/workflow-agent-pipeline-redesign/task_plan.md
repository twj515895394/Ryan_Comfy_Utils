# Task Plan: Workflow Agent 视频创作流水线重设计

## Goal
将 Ryan Workflow Agent 从“整篇 Markdown + 第一条 Prompt Selector”改造成可追溯、可校验、可连线的阶段化视频创作流水线。

## Phases

### Phase 1: 外部能力梳理
- [x] 读取 SceneForge 总控路由与状态机
- [x] 对比创意、美术、剧本、表演、分镜、音频、视频 Prompt Skill
- [x] 提取阶段输出合同、Review 清单与 Prompt 模板
- [x] 识别六阶段端到端流程：创意 → 美术 → 剧本 → 分镜 → 音频 → 视频提示词。
- [x] 五类原有 Agent 与实际六阶段能力核对：目录中包含 audio-director，实际为六类；五类说法会漏掉音频阶段。
- [x] 约束每个 Agent 的 Canonical 正文与可连接 Prompt Bundle；仅必要阶段输出对应 kind。
- [x] 完成 Artifact Bundle V2 最小字段校验，并增加按阶段 `kind/purpose` 白名单
- [x] 固化六类 Agent 的中文输出合同与 Skill 规则
- [x] 运行 Queue/Selector 数据缩减 Smoke
- [x] 验证代码与合同自审

### Phase 2: 目标设计
- [x] 定义六阶段 Context 链路
- [x] 定义 Stage Document 与 Artifact Bundle 的边界
- [x] 定义对象级 Prompt 选择和 Commit 质量闸门
- **Status:** complete

### Phase 3: 用户确认后实现
- [x] 编写并确认设计规格
- [x] 实现 Artifact Bundle V2 与最小字段校验
- [x] 固化六类 Agent 的中文输出合同与 Skill 规则
- [x] 收敛 Context 默认摘要与 Selector 按需取用
- [x] 增加 Audio Agent 合同与节点支持
- [x] 补齐回归测试和固定 Fixture
- **Status:** complete

### Phase 4: 验证
- [x] 运行结构化 Commit/Selector 链路 smoke
- [x] 运行模块测试、语法检查与字段合同检查（专项通过；全量测试仍受既有缺失依赖阻断）
- [ ] 用户明确要求后进行 ComfyUI 手工画布验收
- **Status:** complete（代码侧）

## Decisions

- 保留现有 Context DAG，不把六个阶段合并成一段不可追溯文本。
- 引入独立 `audio.design` 阶段；Audio Design Canon 是视频阶段的主要声音依据，视频 Prompt 通过 `audio_sync` 继承相关节拍；独立音频 Prompt 仅按需生成，不把音频设计塞成自由文本。
- 每个阶段只有一个中文权威 Canonical Text；可连线 Prompt 作为带有 target/purpose 的结构化 Artifact。
- 只吸收外部 Skill 的专业章节、stable ID、Prompt 用途和质量维度；不吸收其流程、项目文件、确认闸门或路由机制。
- 旧 Bundle、旧 shots 和旧字段只在读取时兼容；新 Commit 只写 V2 规范字段。
- 不改变旧 Workflow 的 widgets、节点顺序和既有输出索引。

## Risks

- 旧 Workflow 的 widgets_values 与输出索引不可重排。
- 模型可能仍生成低质量正文；Skill 输出合同和固定 Fixture 只能约束结构，不能替代内容验收。
- 旧提交可能没有结构化 Bundle；必须保留摘要文本回退，不能静默伪造 Prompt。
- 新增 Audio Agent 合同和节点支持会扩大测试面，但不应改变现有五类节点顺序。

## Scope Correction

- 外部 SceneForge Skill 只作为专业内容规范、创作思考维度、Prompt 体裁和质量检查参考。
- 不迁移 SceneForge 的项目文件体系、PROJECT_BOARD、CLI 状态机、阶段路由或 11 阶段流程逻辑。
- Ryan 保留现有 ComfyUI Context/DAG/Chat/Commit/Queue 架构；本任务重点改 Agent 内容合同和输出质量。

## Content Scope Correction

- 每个 Agent 只保留一个中文版权威文档；不拆分独立 review/handoff/英文文件。
- 依据类内容和 Prompt 分离；只有确实需要连接生成节点的 Prompt 才进入 Artifact Bundle。
- 思考过程、候选方案、内部 review 不进入 Context。
- 下游默认接收精简摘要/锁/Handoff；完整 Prompt 通过 Selector 按需取用，避免上下文膨胀。
