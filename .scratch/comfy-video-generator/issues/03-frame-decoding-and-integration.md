Status: done

# 视频帧解压解码集成与单元测试跑通

## 父问题
`.scratch/comfy-video-generator/PRD.md`

## 要构建什么
1. **视频帧解码集成**：
   - 引入项目原有的视频辅助库中的 `load_video_frames` 函数。
   - 对已下载的本地视频路径调用 `load_video_frames(video_path, backend_mode="auto", ...)` 将其解码。
   - 返回解码出来的 PyTorch `IMAGE` 帧张量和本地视频文件绝对路径的 `STRING`。
2. **单元测试编写**：
   - 新建 `tests/nodes/test_video_generator_node.py`。
   - Mock 视频生成 POST 接口返回的 `request_id`。
   - Mock 状态轮询 GET 接口的轮询进度（第一次返回 `pending`，第二次返回 `done` 及 `video.url`）。
   - Mock 视频流下载过程，并 Mock `load_video_frames` 的动作，使其返回期望大小的随机帧张量批次。
   - 验证节点能够成功处理整个过程并不产生报错。
3. **功能描述添加**：
   - 为 `RyanVideoGenerator` 类加上 `DESCRIPTION` 描述属性，指明其支持异步文生视频和参考图生视频。

## 验收标准
- [x] 视频张量帧能被顺利从本地文件解析解码。
- [x] 单元测试 `test_video_generator_node.py` 的 Mock 测试能够通过运行。
- [x] 所有的 102 个单元测试均全部通过。
