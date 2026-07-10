Status: resolved

# 03: 新增 select_video_file API + 前端文件选择器

## 要构建什么

为 RyanVideoSceneSplitter 节点提供视频文件选择交互：

后端：在 `video_nodes.py` 中注册 `/ryan_comfy_utils/select_video_file` POST 端点，弹出 tkinter 文件对话框，支持视频文件类型过滤（mp4/mov/mkv/avi/webm），返回用户选中的路径。

前端：新建 `ryan_scene_splitter.js`，在节点的 `video_path` 输入框旁添加「选择视频文件...」按钮，点击后调用上述端点并填入返回路径。

## 验收标准

- [x] `/ryan_comfy_utils/select_video_file` POST 端点存在且可用
- [x] 端点弹出系统文件选择对话框，过滤视频文件类型
- [x] `ryan_scene_splitter.js` 存在且注册了 ComfyUI 扩展
- [x] 节点 UI 上出现「选择视频文件...」按钮
- [x] 点击按钮后选中的路径正确填入 video_path 输入框

## 被阻塞于

- `.scratch/scene-split/issues/02-scene-splitter-node.md`
