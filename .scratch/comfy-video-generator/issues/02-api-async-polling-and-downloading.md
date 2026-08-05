Status: done

# 异步视频生成 API 投递、周期轮询与视频下载逻辑

## 父问题
`.scratch/comfy-video-generator/PRD.md`

## 要构建什么
实现后端 `generate` 方法中的异步调用流程：
1. **任务发起**：发送 POST 请求到 `{base_url}/videos/generations`：
   - 如果没有输入图片：纯文本模式。
   - 如果有 1 张输入图片：在 payload 中追加 `"image": {"url": "data:image/jpeg;base64,..."}`。
   - 如果有 >1 张输入图片：在 payload 中追加 `"reference_image_urls": [{"url": "data:image/jpeg;base64,..."}, ...]`。
   - 提取响应结果中的 `request_id`。
2. **周期性轮询**：
   - 循环发送 GET 请求到 `{base_url}/videos/{request_id}`。
   - 每次请求后根据 `polling_interval` 进行 `time.sleep`。
   - 检查返回的 `status`：
     - 如果为 `"pending"`，继续轮询（可在控制台打印 progress 进度以供了解）。
     - 如果为 `"failed"` 或 `"expired"`，引发 `RuntimeError` 报错任务失败。
     - 如果为 `"done"`，提取 `video.url` 跳出循环。
3. **视频下载与保存**：
   - 发送 GET 请求下载 `video.url` 的视频文件二进制数据。
   - 在 ComfyUI 的 `output` 目录下新建 `ryan_grok_video_{uuid}.mp4`，并将数据保存到本地该路径。

## 验收标准
- [x] 提交任务正常返回 `request_id` 并开始轮询。
- [x] 轮询任务在检测到 `"done"` 时提取 URL，检测到 `"failed"` 时正常报错。
- [x] 视频能成功保存到 ComfyUI 的 output 目录下，并返回该路径的 `STRING`。
