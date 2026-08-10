# SceneForge -> Ryan Workflow Agent Skill 迁移说明 V1

> 来源：`twj515895394/scene_forge` 分支 `codex/v10-text-skill-pipeline`
> 目标：`Ryan_Comfy_Utils` 的 Generic Workflow Agent Starter Skill Pack

## 1. 迁移结论

SceneForge 当前分支中已经存在一套非常适合 Ryan Workflow Agent V1 的五阶段文本主链：

```text
creative-story-planner
production-designer
script-director
storyboard-director
video-prompt-director
```

这五个 Skill 已经把早期更碎的 SceneForge 阶段做过一次合并：

- `creative-story-planner` 吸收 topic gate / reference decider / story development；
- `production-designer` 合并 asset checker / design builder；
- `script-director` 合并 script adapter / performance director；
- `storyboard-director` 负责剧本 -> Shot/Segment；
- `video-prompt-director` 负责 Shot/Segment -> 可复制视频 Prompt。

因此 V1 不建议把 SceneForge 早期十多个细粒度 Skill 全部迁过来。先迁这 5 个 consolidated skills，正好可以验证 Ryan Generic Agent + DAG Context。

## 2. 为什么它们匹配本次 Agent 设计

它们天然符合：

```text
上游 Canon
-> 当前专业角色讨论/整理
-> 当前阶段 Canonical Artifact
-> 下游继续消费
```

这和 `RYAN_CONTEXT` 的 Commit Entry 模型完全一致。

对应关系：

| Skill | Ryan Context Kind | 推荐显示名 |
|---|---|---|
| creative-story-planner | `creative.story` | 创意策划 |
| production-designer | `production.design` | 美术/资产设计 |
| script-director | `script.direction` | 剧本导演 |
| storyboard-director | `storyboard.plan` | 分镜导演 |
| video-prompt-director | `video.prompts` | 视频提示词导演 |

这些只是 Starter Skills，不代表 Ryan 以后固定只能有这五种 Agent。

## 3. 本次迁移不是原样复制

SceneForge Skill 原版存在一些项目绑定：

- 默认读取 `01_CREATIVE_STORY.md` / `02_PRODUCTION_DESIGN.md` 等固定文件；
- 文案中把自己称为 SceneForge Stage 01/02/03/04/05；
- 部分旧 Skill 依赖 `PROJECT_BOARD.md`、`state.next_stage`、SceneForge blackboard；
- 默认按“执行一次并落盘阶段文件”思考，而不是长期 Chat Session。

Ryan Workflow Agent 的目标不同，因此迁移版做以下适配：

1. 输入改为“当前用户消息 + 当前 Agent Private Chat + DAG 上游 `RYAN_CONTEXT`”；
2. 不要求存在固定文件名；
3. 增加 `DISCUSS` / `COMMIT` 两种模式；
4. DISCUSS 阶段允许与用户持续迭代，不把临时方案视为 Canon；
5. COMMIT 阶段才生成唯一权威 Markdown Artifact；
6. 输出通过 `agent-contract.json` 声明 `produces_context_kind`；
7. 保留稳定实体 ID、Continuity、下游 handoff 等 SceneForge 中成熟的生产约束；
8. 去掉 SceneForge 根 `AGENTS.md`、PROJECT_BOARD、next_stage 等硬依赖。

## 4. 五个 Skill 的推荐 DAG

最小串行：

```text
creative-story-planner
  -> production-designer
  -> script-director
  -> storyboard-director
  -> video-prompt-director
```

更符合真实创作的 fan-out/fan-in 也支持：

```text
creative-story-planner
   ├──> production-designer ----┐
   └──> script-director --------+--> storyboard-director
                                └--> video-prompt-director
```

甚至用户可以增加自己的 Skill：

```text
creative.story
   ├──> character specialist
   ├──> location specialist
   └──> script-director

三路 RYAN_CONTEXT -> storyboard-director
```

因为底层 Socket 仍然只有 `RYAN_CONTEXT`，不需要新增 CharacterContext/ScriptContext 等专用节点类型。

## 5. 为什么暂不迁移旧细粒度 Skills

SceneForge 分支还存在：

```text
scene-topic-gate
scene-reference-decider
scene-story-development
scene-asset-checker
scene-design-builder
scene-script-adapter
scene-performance-director
scene-storyboard-director
scene-video-prompt-builder
scene-audio-director
scene-video-intake
scene-publish-review
...
```

其中多项能力已被新五阶段主链吸收。V1 全迁会造成：

- Skill 列表过多；
- 用户不知道应该选新旧哪个；
- DAG 被迫过度细分；
- Context Entry 数量膨胀；
- 把 SceneForge 的旧编排模型带进 Ryan。

所以本次只迁移 consolidated 主链。旧 Skill 作为能力资料保留在 SceneForge，后续有明确需求再拆成可选专业 Agent。

## 6. 各 Skill 迁移重点

### 6.1 creative-story-planner

保留：

- original / rewrite_adaptation / preserve_original；
- Logline / Premise / 核心冲突；
- 角色叙事功能；
- Story Beats；
- must_keep / must_avoid；
- 稳定 `CHAR_###` / `BEAT_###`；
- 下游 Handoff。

Ryan 适配：输出 `creative.story`。

### 6.2 production-designer

保留：

- Canonical Design -> Continuity Lock -> Prompt；
- 角色/场景/关键道具设计；
- reference role 区分；
- spatial lock；
- 图片 Prompt。

Ryan 适配：输出 `production.design`，输入优先消费 `creative.story`，但不硬编码必须有该 kind。

### 6.3 script-director

保留：

- Story Beat -> Scene；
- 正式对白/动作；
- 表演导演信息；
- gaze / micro-expression / blocking；
- action/emotion continuity；
- storyboard hints。

Ryan 适配：输出 `script.direction`。

### 6.4 storyboard-director

保留：

- `BEAT -> SCN -> SHOT` trace；
- Cinematic Language；
- Shot/Segment；
- Hero / Bridge Shot；
- continuity in/out；
- Storyboard/Keyframe Prompt；
- start/end state。

Ryan 适配：输出 `storyboard.plan`。

### 6.5 video-prompt-director

保留：

- 不重新导演上游 Storyboard；
- Global Execution Rules；
- 每个 Segment 的时序化 Director Prompt；
- start/end state；
- camera / performance / environment motion；
- model-neutral -> model-specific adapter；
- continuity / negative rules。

Ryan 适配：输出 `video.prompts`。

## 7. Chat 模式统一规则

迁移 Skill 均采用：

```text
RYAN_AGENT_MODE=DISCUSS
```

时：

- 当前回复面向讨论；
- 可以追问真正会改变结果的关键问题；
- 用户只是纠错/补充时继续工作；
- 不强制每轮生成完整权威文档。

```text
RYAN_AGENT_MODE=COMMIT
```

时：

- 综合当前 Session 中用户最后确认的方向；
- 忽略已被否定的旧方案；
- 生成完整 Canonical Artifact；
- 不把“还有待讨论”的内容伪装成已确认事实；
- 必须给下游足够的 Handoff。

## 8. Context 消费规则

每个 Skill 的 `agent-contract.json` 会给出推荐 `accepts_context_kinds`。

Runtime 的 Context Selector 可用这些信息做 token 优先级，但 V1 不应把它当硬类型检查。

例如 `storyboard-director` 推荐：

```json
[
  "creative.story",
  "production.design",
  "script.direction"
]
```

如果用户直接把一份完整剧本作为聊天输入，也允许该 Skill 工作。

## 9. 与 Ryan 现有固定 Prompt Skills 的关系

迁移的 `video-prompt-director` 是“导演级、跨 Segment 的视频 Prompt 编排”。Ryan 当前已有：

```text
video_prompt_generator
minimax-h3-video-prompt
```

两者不冲突。

推荐未来关系：

```text
storyboard.plan
 -> video-prompt-director        # 先得到 model-neutral / director-level prompts
 -> MiniMax H3 Prompt Agent      # 如用户选择 H3，再做具体模型协议编译
```

或者用户也可让 `video-prompt-director` 直接针对 Seedance/Kling/Veo 等模型生成目标表达。

V1 不强制绑定某一种视频模型。

## 10. 后续可能迁移的 Skill

等 Generic Workflow Agent 跑通后，优先考虑：

- `scene-video-intake` -> `source.video.analysis`：视频参考解析入口；
- `scene-audio-director` -> `audio.direction`：声音/音乐专业支路；
- `scene-publish-review` -> `review.report`：最终质量审查；
- 专门 Character Designer / Location Designer：当 Production Designer 太大时再拆。

这些都应继续作为同一种 Generic Agent Node 的 Skill，而不是新建固定 Python 节点类。

## 11. 本次落地文件

迁移后的 Starter Skills 放置在：

```text
ryan_comfy_utils/acp/fixtures/skills/
├── creative-story-planner/
├── production-designer/
├── script-director/
├── storyboard-director/
└── video-prompt-director/
```

每个目录至少包含：

```text
SKILL.md
agent-contract.json
```

它们当前即可被现有 `_list_skills()` 扫描到；真正的 `RYAN_CONTEXT + Chat/Commit` 语义将在 Workflow Agent V1 实现后启用。
