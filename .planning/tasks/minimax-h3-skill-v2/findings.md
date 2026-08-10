# Findings

## 当前 skill

- `SKILL.md` 已有模式判断、素材编号、素材用途锁定、视频编辑保持项、超限处理和中文输出策略。
- 当前模式仍以纯文生、普通图生、首尾帧、全能参考、视频编辑为主，未单独建模 L2VA、视频续接、音频复用和音频参考。
- 当前输出字段为参考素材说明、核心创意、画面过程说明、声音与文字、保持项与禁止项。
- 当前规则文件已覆盖输入数量、文件限制、素材角色、台词、镜头、声音和质量检查。

## 官方参考

来源：
- https://github.com/MiniMax-AI/MiniMax-H3/tree/main/skills
- https://github.com/MiniMax-AI/MiniMax-H3/tree/main/skills/h3-prompt-writing
- https://raw.githubusercontent.com/MiniMax-AI/MiniMax-H3/main/skills/h3-prompt-writing/references/base-en.txt
- https://raw.githubusercontent.com/MiniMax-AI/MiniMax-H3/main/skills/h3-prompt-writing/references/ref-en.txt

官方基础模式：T2VA、I2VA、FL2VA、L2VA。
官方基础字段：`integrated_multimodal_description`、`overall_soundscape`、`non_diegetic_music`。
官方全参考字段：`subject_definitions`、`summary`、`retention_analysis`、`detailed_description`、`overall_soundscape`、`non_diegetic_music`。
官方引用标签：`<Subject N>`、`<Picture N>`、`<Video N>`、`<Audio N>`。
官方还定义稳定 speaker ID、`<d>`、`<scenetrans>`、`<cutoff>`、严格时间标记和音频关系。

## 已确认决策

- 首版纳入官方当前八种风格 skill：极简产品广告、3D 动画短片、纸艺定格解释、品牌宣传片、音乐视频字幕、双人合作游戏开场、纸张拼贴解释、手绘实拍混合。
- 风格化能力采用通用核心 + 风格路由 + 风格配置；后续新增风格只增加配置和规则，不修改 H3 基础协议。
- 通用请求不自动套用风格；只有用户明确风格意图或任务类型时路由。
- 默认保留当前中文用户可读层，同时增加官方字段映射；最终 prompt 默认采用英文结构，用户对白、歌词、字幕、Logo 和 UI 文案保持原文。
