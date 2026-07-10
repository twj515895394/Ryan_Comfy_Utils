Status: resolved

# 04: RyanVideoFrameSampler 新增分镜首帧采样模式

## 要构建什么

在现有 RyanVideoFrameSampler 节点中新增「分镜首帧采样」模式：

- sample_mode COMBO 增加 `"分镜首帧采样"` 选项
- 新增 optional 输入 `video_path` (STRING)，分镜模式下必须提供
- 新增分镜相关参数：scene_detector (COMBO)、scene_threshold (FLOAT)、scene_min_len (FLOAT)、scene_merge_min (FLOAT)
- 分镜模式执行逻辑：detect_scenes → merge_short_scenes → get_scene_first_frames
- 前端 JS 适配：向后兼容映射 + 分镜参数显隐控制

## 验收标准

- [x] SAMPLE_MODE_MAP 包含 `"分镜首帧采样": "scene_first_frame"` 映射
- [x] sample 方法在 scene_first_frame 模式下调用分镜检测核心函数
- [x] video_path 未提供时抛出明确错误提示
- [x] `ryan_video_frame_sampler.js` 包含 `scene_first_frame` 向后兼容映射
- [x] 分镜参数在非分镜模式下隐藏
- [x] 所有单元测试通过

## 被阻塞于

- `.scratch/scene-split/issues/01-core-scene-detect.md`
