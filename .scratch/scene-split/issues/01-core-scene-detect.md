Status: resolved

# 01: 新建 core/scene_detect.py 核心模块

## 要构建什么

创建分镜检测核心模块，封装四个纯函数，不依赖 ComfyUI：

- `detect_scenes(video_path, detector, threshold, min_scene_len_sec)` — 调用 PySceneDetect 检测镜头边界
- `merge_short_scenes(scene_list, min_duration_sec)` — 合并过短碎片镜头
- `split_video_to_files(video_path, scene_list, output_dir, filename_prefix, fast_copy)` — 调用 ffmpeg 切割视频
- `get_scene_first_frames(video_path, scene_list, custom_width, custom_height)` — 用 OpenCV 提取每个分镜首帧，返回 `[N,H,W,C]` float32 张量

默认检测器为 AdaptiveDetector，默认阈值 content=27 / adaptive=3 / threshold=12。

## 验收标准

- [x] `core/scene_detect.py` 存在且包含上述四个函数
- [x] `detect_scenes()` 返回 `[(start, end), ...]` 时间戳对列表
- [x] `merge_short_scenes()` 正确合并短于阈值的片段
- [x] `split_video_to_files()` 支持 fast_copy 和精确模式两种切割方式
- [x] `get_scene_first_frames()` 返回正确形状 of torch.Tensor
- [x] `tests/core/test_scene_detect.py` 覆盖上述函数的关键逻辑
- [x] 所有单元测试通过

## 被阻塞于

无 - 可以立即开始
