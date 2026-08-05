Status: closed

# RyanACPMiniMaxH3VideoPromptAgent 节点实现与多模态插槽交互开发

## 父问题
`.scratch/minimax-h3-video-prompt/PRD.md`

## 要构建什么

1. **Manifest 与 Slug 注册**：
   - 新建 `minimax_h3_video_prompt_agent.json` 绑定 `minimax-h3-video-prompt` Skill。
   - 在 `file_exporter.py` 中添加 `NODE_SLUG_MINIMAX_H3_VIDEO_PROMPT` 常量。

2. **后端节点类实现 (`acp_nodes.py`)**：
   - 创建 `RyanACPMiniMaxH3VideoPromptAgent` 节点类并在 `__init__.py` 注册。
   - `INPUT_TYPES` 支持 9 个 `image_01..09` (IMAGE)、3 个 `video_01..03` (`*`)、3 个 `audio_01..03` (`*`) 以及槽位控制与抽帧参数。
   - 提取主视频源 `video_01` 在 `video_start_frame` ~ `video_frame_count` 区间的帧保存给 VLM 识别。

3. **前端扩展实现 (`ryan_minimax_h3_prompt.js`)**：
   - 独占处理 `Ryan ACP MiniMax H3 Video Prompt Agent` 节点。
   - 支持 `Update` 按钮联动 `image_slot_count`、`video_slot_count`、`audio_slot_count` 动态增减物理插槽。
   - 监听 `generation_mode` 模式变更，支持 `纯文生`（默认）/ `普通图生` / `首尾帧` / `全能参考` / `视频编辑` 自动预设与隐显控件。

## 验收标准

- [x] 节点可在 ComfyUI 正确检索并拉出。
- [x] `video_01`..`03` 与 `audio_01`..`03` 可与 `LoadVideo` 和 `LoadAudio` 节点直接拉线连接。
- [x] `Update` 按钮可对图像、视频、音频三类插槽同时进行动态拉伸与删除超范围线。
- [x] 模式切换默认处于“纯文生”，界面极简；切换模式时插槽自动预设。
- [x] 抽帧参数 `video_start_frame` 与 `video_frame_count` 仅对主视频源 `video_01` 生效。
