# Ryan Workflow Agent 视频创作内容合同设计规格

**日期：** 2026-08-12  
**状态：** 已实现；音频导演以视频节奏交接为主，独立音频 Prompt 按需输出

## 1. 目标

沿用 Ryan Workflow Agent 现有的 ComfyUI `Chat → Commit → Queue → RYAN_CONTEXT → 下游 Agent / Selector` 架构，只借鉴外部 Skill 的专业内容规范和质量维度，提升六类视频创作 Agent 的实际交付质量。

本次设计同时限制产物数量和上下文体积：每个 Agent 只提交一份中文权威阶段文档；只有真正需要连接图像、音频或视频生成节点的内容，才作为对象级 Prompt 进入结构化 Artifact Bundle。

## 2. 非目标

- 不迁移外部项目的流程、状态机、CLI、项目文件体系或路由机制。
- 不把思考过程、候选淘汰、内部 Review、工具调用、上下文解释写入正式产物。
- 不生成独立英文文档、英文 Prompt 版本、Review 文件或 Handoff 文件。
- 不把所有上游全文和所有 Prompt 自动拼接到下游 Agent。
- 不因本次设计重排旧 Workflow 的节点输入输出顺序。
- 不让剧本、视觉锁、音频设计等依据类内容伪装成图像/视频 Prompt。

## 3. 统一产物模型

### 3.1 对用户可见的正式产物

每次 Commit 只有一份 Canonical Markdown 文档：

```text
中文正文
→ 固定阶段章节
→ 最后一个“下游交接”章节
```

正文允许使用必要的英文专业词汇，例如 `Blocking`、`Continuity`、`Shot`、`Segment`、`Gaze`，但不提供独立英文版本。文档只写已确认、需要落地或会影响后续执行的内容。

### 3.2 结构化 Bundle

每个 Agent 最多附带一个 `ryan-artifact` Bundle。Bundle 不是第二份文档，而是用于上下文摘要和节点连线的机器可读索引：

```json
{
  "artifact_type": "production_design",
  "schema_version": 2,
  "content": {
    "summary": "供下游读取的精简确认结论",
    "handoff": "供下一阶段执行的必要约束",
    "locks": ["CHAR_001 ...", "SCENE_001 ..."]
  },
  "outputs": [
    {
      "output_id": "CHAR_001_REFERENCE",
      "kind": "image_prompt",
      "label": "CHAR_001 · 角色说明书板",
      "purpose": "character_sheet",
      "target_ids": ["CHAR_001"],
      "text": "中文可直接使用的 Prompt",
      "negative_constraints": ["..."],
      "aspect_ratio": "4:3",
      "priority": 50
    }
  ],
  "shots": []
}
```

约束：

- Prompt 统一使用 `text` 字段承载中文内容，不增加 `prompt_cn` / `prompt_en` 双字段。
- 每条 Prompt 必须有稳定 `output_id`、`kind`、`label`、`purpose` 和 `target_ids`。
- `negative_constraints`、`aspect_ratio`、`reference_roles` 只在该 Prompt 确实需要时出现。
- `outputs` 只存可连接生成节点的内容；故事依据、视觉锁、剧本、音频计划等不拆成 Prompt。
- `shots` 保留用于旧 Workflow 兼容；新产物统一优先使用 `outputs`，Shot/Segment 通过 `target_ids` 标识。
- `summary`、`handoff`、`locks` 是精简 Context 的元数据，不是额外文件。

## 4. 六类 Agent 合同

### 4.1 创意策划

**Context kind：** `creative.story`  
**Canonical 标题：** `Creative Story Canon`  
**Artifact type：** `creative_story`  

正文只保留：

- 项目意图与创作模式
- 故事核心、主题和情绪目标
- 角色叙事功能
- `Story Beats`：Setup、Escalation、Climax、Ending、Payoff
- 时长与节奏
- 必须保留 / 必须避免
- 必要的整体视觉方向
- 下游交接

默认不生成 Prompt。用户明确需要先生成概念图时，允许：

```text
kind: concept_image_prompt
purpose: concept_art 或 moodboard
target_ids: [PROJECT]
```

创意阶段不负责角色最终外观、场景细节、镜头设计或视频动作 Prompt。

### 4.2 美术 / 资产设计

**Context kind：** `production.design`  
**Canonical 标题：** `Production Design Canon`  
**Artifact type：** `production_design`  

正文只保留：

- 统一视觉语言
- 角色视觉锁与身份锚点
- 场景空间锁
- 关键道具状态与连续性
- 资产复用策略
- 角色、场景、道具的已确认设计结论
- 下游交接

允许的 Prompt：

```text
kind: image_prompt
purpose: character_reference | character_sheet | expression_sheet
purpose: scene_reference | spatial_reference | prop_reference
```

每条 Prompt 必须指向 `CHAR_###`、`SCENE_###`、`PROP_###` 等实体，并说明参考图的职责。角色说明书板应包含多视角、轮廓、表情、动作姿态、服装材质和比例等必要信息，不能退化为单人海报。

视觉锁和 Continuity 是正文依据，不单独生成 `continuity_constraint` Prompt。

### 4.3 剧本 / 表演导演

**Context kind：** `script.direction`  
**Canonical 标题：** `Script Direction Canon`  
**Artifact type：** `script_direction`  

正文只保留：

- `Beat → Scene` 映射
- 场次目标和冲突变化
- 对白与可见动作
- `Blocking`、道具交互和动作连续性
- 角色表演基线：`Gaze`、`Eye Line`、`Micro-expression`、身体重心、手部动作、停顿、反应节奏、声音节奏
- `Emotion Continuity`
- 分镜提示与时长检查
- 下游交接

不生成图像、故事板或视频 Prompt。剧本和表演内容是分镜与视频阶段必须使用的依据类内容。

### 4.4 分镜导演

**Context kind：** `storyboard.plan`  
**Canonical 标题：** `Storyboard Canon`  
**Artifact type：** `storyboard_plan`  

正文只保留：

- Scene 内容拆解
- `Shot List`
- 景别、角度、构图、焦段感觉和摄影机行为
- 角色运动、Blocking、空间关系
- `Shot → Segment` 对齐
- 每个 Segment 的首状态、主体动作、尾状态和连续性
- 必要的控制型 / 风格型故事板要求
- 下游交接

允许的 Prompt：

```text
kind: storyboard_prompt
purpose: control_storyboard | style_storyboard
kind: keyframe_prompt
purpose: start_frame | end_frame | reference_frame
```

只有确实需要生成故事板或关键帧时才产生对应输出。新输出通过 `target_ids` 指向 `SHOT_###` 或 `SEG_###`；旧 `storyboard_sheet_prompt`、`shot_prompt` 只作为读取兼容值。

### 4.5 音频导演

**Context kind：** `audio.design`  
**Canonical 标题：** `Audio Design Canon`  
**Artifact type：** `audio_design`  

正文只保留：

- 对白与声音表演
- 音乐设计
- 拟音设计
- 环境音设计
- 静默点和声音节奏
- 每个 Segment 的 `BGM / Foley-SFX / Ambience / Silence`
- 与视频 Prompt 对齐的声音执行要求
- 下游交接

音频导演的主要职责是为视频提示词导演提供按 Segment 对齐的声音设计。视频阶段必须消费已提交的 `audio.design` Canon，并把相关声音节拍翻译到对应 `video_prompt` 的 `audio_sync` 中。

只有项目实际连接音频生成节点或用户明确要求生成时，才允许：

```text
kind: audio_prompt
purpose: music | voice | foley | ambience
```

独立 `audio_prompt` 是可选的生成节点输入，不是视频 Prompt 生成的前置条件。如果只是导演设计，不生成 Prompt Artifact。

### 4.6 视频提示词导演

**Context kind：** `video.prompts`  
**Canonical 标题：** `Video Prompt Canon`  
**Artifact type：** `video_prompts`  

正文只保留：

- 继承的视觉、剧本、分镜和音频锁
- 全局视频执行规则
- `Segment Prompt Index`
- 每个 Segment 的动作时序、表演、摄影机、环境运动、首尾状态和连续性
- 每个 Segment 的 `BGM / Foley-SFX / Ambience / Silence`
- Negative / Avoid
- 下游交接

允许的 Prompt：

```text
kind: video_prompt
purpose: segment_execution
target_ids: [SEG_###]
```

视频 Agent 只翻译已确认的 Storyboard、Script、Production Design 和 Audio，不重新设计故事、镜头或声音。旧 `shot_video_prompt` 只作为读取兼容值。

## 5. 上下文与 Selector 边界

### 5.1 下游默认 Context

下游 Agent 的默认 `summary` 视图只注入：

1. 上游阶段的 `content.summary`；
2. `content.locks`；
3. `content.handoff`；
4. 当前阶段所需的必要资产摘要。

不自动注入完整 Canon、全部 Prompt、旧版本、私聊记录或内部思考。现有 Context 总预算继续生效；超出预算时按现有确定性裁剪并提示使用 Selector。

### 5.2 Selector

Selector 只负责从已提交的最新有效 Bundle 中选择一个可连接输出：

- 创意：概念图 Prompt（若存在）
- 美术：角色 / 场景 / 道具 / 空间参考图 Prompt
- 分镜：故事板 / 关键帧 Prompt
- 音频：音乐 / 配音 / 拟音 / 环境音 Prompt（若存在）
- 视频：指定 `SEG_###` 的视频 Prompt

剧本阶段没有 Prompt 时，Selector 不显示伪造的可选项。依据类内容由 Agent Context 读取，不通过 Prompt Selector 冒充生成输入。

## 6. 兼容策略

- 旧 Workflow 的节点顺序、Widget 顺序和现有输出索引不变。
- 旧 Bundle `schema_version: 1` 继续读取。
- 旧 `id`、`prompt`、`constraint` 字段只在读取归一化时兼容；新 Commit 只写规范字段。
- 旧 `shots`、`storyboard_sheet_prompt`、`shot_prompt`、`shot_video_prompt` 继续读取；新产物优先写 `outputs`。
- 没有结构化 Bundle 的旧 Entry 仍可作为摘要文本传递，但不自动伪造 Prompt。

## 7. 验收标准

1. 六类 Agent 每类只有一份中文 Canonical 文档。
2. 任何正式产物不包含英文独立版本、聊天记录、内部思考或工具说明。
3. 创意默认无 Prompt；剧本永远不生成 Prompt；音频 Prompt 按需生成。
4. 美术、分镜、视频 Prompt 都有稳定对象或 Segment ID、用途和中文可执行正文。
5. 依据类内容只进入 Canonical 文档和精简 Context，不被 Selector 当作 Prompt。
6. 下游默认 Context 不包含所有上游全文和全部 Prompt。
7. Selector 只能列出当前最新有效 Bundle 中实际存在的可连接 Prompt。
8. 旧 Bundle 和旧 Workflow 读取行为不回归。
9. Context、Commit、Artifact Parser、Selector 均有针对上述合同的模块测试。
