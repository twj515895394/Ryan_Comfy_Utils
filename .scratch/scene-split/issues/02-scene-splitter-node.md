Status: resolved

# 02: 新增 RyanVideoSceneSplitter 节点（后端）

## 要构建什么

在 `nodes/video_nodes.py` 中新增 `RyanVideoSceneSplitter` 节点类，接收视频路径，自动检测分镜并切割保存为多个独立视频文件。

输入参数：video_path、output_dir、filename_prefix、detector（中文 COMBO）、threshold、min_scene_len、merge_min_duration、fast_copy。

输出：scene_count (INT)、manifest_json (STRING)、output_dir (STRING)。

在 `__init__.py` 中注册节点类映射和显示名。中文选项映射：自适应检测→adaptive、内容突变检测→content、亮度阈值检测→threshold。

## 验收标准

- [x] `RyanVideoSceneSplitter` 类存在于 `video_nodes.py`
- [x] INPUT_TYPES 包含所有设计文档中定义的参数
- [x] RETURN_TYPES 为 `(INT, STRING, STRING)`
- [x] 中文 COMBO 选项正确映射到内部英文值
- [x] `__init__.py` 中注册了节点映射和显示名
- [x] `tests/nodes/test_scene_splitter_node.py` 覆盖节点合约和映射
- [x] 所有单元测试通过

## 被阻塞于

- `.scratch/scene-split/issues/01-core-scene-detect.md`
