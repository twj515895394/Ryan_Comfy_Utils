# Findings

## SceneForge 可直接整合的能力

### 1. 总控状态机，而不是自由串联

`scene-forge/SKILL.md` 将总控限制为：识别项目、读取状态、选择唯一当前阶段、合并单阶段补丁、推进状态。`state.next_stage` 是唯一准入条件，不允许一口气跳过中间阶段。适合迁移为 Ryan Context 的阶段路由与上游依赖校验。

### 2. 阶段唯一权威文档

创意、美术、剧本、分镜、视频 Skill 都要求每阶段只产出一个权威阶段文档，并规定固定标题、YAML frontmatter、正文章节、Internal Quality Review、Downstream Handoff。当前 Ryan 的 `response_text` 应收敛为该 Canonical Text，不能包含内部工作说明。

### 3. 结构化字段比自由 Markdown 更重要

SceneForge 的 output-contract 为角色、Scene、Prop、Beat、Shot、Segment、Prompt 定义稳定 ID 和字段；Prompt 通过 `prompt_refs`/`prompt_id` 关联实体。Ryan Artifact V2 应吸收 `target_entities`、`purpose`、`reference_roles`、`negative_constraints`、`prompt_cn` 等字段。

### 4. 美术 Prompt 不是单条泛化 Prompt

`production-designer/references/output-contract.md` 要求 `image_prompts[]`，每条有 `prompt_id`、`purpose`、`target_entities`、参考图职责、中文 Prompt、负向约束、比例。角色说明书模板还要求多视角、轮廓、表情、微表情、动作姿态、道具交互、材质与比例对照，禁止退化成 single portrait/poster。

### 5. 表演应是独立中间层

SceneForge 有 `scene-performance-director`，明确把“角色如何表演”从“剧本写什么”拆开：眼神、微表情、身体重心、手部动作、停顿、反应节奏、动画物理、轻伤反应、反差表演、动作/情绪连续性。当前 Ryan 的剧本 Agent 应至少吸收其字段；是否拆成独立第七 Agent，需在设计中权衡，默认先作为剧本阶段的结构化子交付，避免节点数量过度膨胀。

### 6. 分镜 Prompt 必须是控制型故事板

`scene-storyboard-director` 与模板将控制故事板和风格故事板分开：控制板服务动作、镜头调度、空间连续性和状态继承；风格板服务角色渲染、质感、灯光与情绪。Prompt 要求镜头区内的红色人物运动箭头、蓝色摄影机箭头、节奏轨、状态轨和连续性规则；不能用逐镜头表格替代正式故事板 Prompt。

### 7. 音频是独立导演阶段，并服务视频

`scene-audio-director` 位于 storyboard → audio → video。输出包含 voice direction、music design、foley design、ambience design、silence points、expressive audio、segment_audio_plan、video_prompt_handoff。视频阶段必须把声音展开为每段 `BGM / Foley-SFX / Ambience / Silence`，不是只引用一个音频文件。

### 8. 视频 Prompt 是 Pack/Segment 对齐交付

`scene-video-prompt-builder` 要求中文 Pack 为默认主交付，每个 Segment 有技术控制、声音执行、逐镜头导演 Prompt、Prompt Trace、可直接复制块、Review。每个 Segment 必须继承 Storyboard 的 VGU/Shot/Segment、首尾状态、Blocking、Prop State、Audio、Design，不得重新导演。

### 9. 确认闸门与 Review

SceneForge 把创作型阶段分成“先预览、用户确认、正式落盘”，执行型阶段可自动落盘但必须 Review；硬错误包括 validator 失败、必填字段缺失、时长冲突、上游产物不存在。Ryan Commit 应增加同类质量闸门，失败时不写入 Context。

## 对 Ryan 当前实现的直接结论

- 现有五个 Agent Skill 已经是 SceneForge 规则的精简移植版，但丢失了阶段文档合同、对象级 Prompt 索引、Review 闸门和音频阶段。
- 不应简单把 SceneForge 全部 11 个 Skill 变成 11 个 Comfy 节点；推荐保留六个可见创作 Agent，将 topic/reference/asset/performance/publish 作为路由、校验或阶段子交付。
- `response_text` 必须只承载干净的 Canonical Document；`RYAN_ARTIFACT` 必须承载可连线的对象级 Prompt。
- 视频 Prompt 必须继承并显式整合音频四层，而不是视频 Agent 自己重新猜声音。
## 10. 可选入口阶段

SceneForge 还提供 `scene-video-intake`、`scene-topic-gate`、`scene-reference-decider`：

- 视频/截图作为源素材时，先生成 source intake、content priority map 和 5–10 个改写方向，不能直接进入剧本。
- 题材阶段负责制作价值、风格家族/导演风格和用户选择闸门。
- 参考裁定阶段把 `must_keep / should_keep / allowed_to_rewrite / must_avoid` 固化，供后续所有阶段继承。

Ryan 不应把这些全部变成常驻节点。建议：

- 普通创意输入：入口 Agent 内部执行最小 topic/reference gate，结果写入 `creative.story` 的结构化字段。
- 视频源输入：增加可选 `source_intake` 入口模式；未完成 source intake 时，不允许直接生成剧本/分镜/视频 Prompt。
- 参考边界和风格确认作为 Context metadata 与 Commit gate，不依赖模型自行记忆。

## 11. 用户范围校正

外部 SceneForge Skill 的用途是提供专业内容规范与思考维度，不是迁移其项目流程逻辑。以下内容不纳入 Ryan：

- `PROJECT_BOARD.md`、项目文件落盘体系和 CLI；
- SceneForge 的 11 阶段状态机与 `state.next_stage` 路由；
- SceneForge 的黑板补丁协议、项目索引和发布文件注册流程。

保留的参考范围：

- 每个 Agent 的专业职责边界；
- Canon 应包含的专业章节；
- 稳定实体 ID 和跨阶段继承字段；
- Prompt 的编译顺序、对象职责和用途；
- Review 清单中的质量维度；
- 音频与视频 Prompt 的专业字段。

## 12. 第二次范围校正：内容深度与最小产物

用户的目标不是迁移 SceneForge 流程，而是借鉴其专业内容规范，让 Ryan 原有 Workflow Agent 输出更专业、更有深度，同时严格控制产物数量和上下文体积。

设计原则：

- 每个 Agent 只产出一个中文版权威阶段文档；不额外拆出 review、handoff、中文包、英文包等文件。
- 英文只作为中文版中的专业词汇、模型锚词或必要术语；不生成独立英文产物。
- 思考过程、候选淘汰、内部 Review 过程不进入正式 Context。
- `Downstream Handoff` 作为权威阶段文档的最后一个精简章节，不独立成文件。
- 依据类内容（故事 Canon、视觉锁、剧本、Shot/Segment 计划、音频计划）与可执行 Prompt 分离标记。
- Prompt 只有在确实需要连接图像/音频/视频生成节点时才生成，且按实体/Shot/Segment 提供稳定 ID。
- 默认向下游 Agent 传递精简 Canon 摘要、锁和 Handoff，不自动注入所有 Prompt 正文；Prompt 通过 Artifact Selector 按需取用。

建议的最小产物：

| Agent | 权威文档 | 可选可连接 Prompt |
|---|---|---|
| 创意策划 | Creative Story Canon | 仅用户需要时的创意概念图 Prompt |
| 美术设计 | Production Design Canon | 角色、场景、道具、空间参考图 Prompt |
| 剧本/导演 | Script & Performance Canon | 无；表演信息是下游依据 |
| 分镜 | Storyboard Canon | 控制故事板 Prompt、必要的关键帧 Prompt |
| 音频 | Audio Design Canon | Music / Foley / Voice 生成所需 Prompt |
| 视频 | Video Prompt Canon | 按 SEG_### 的最终视频 Prompt |
