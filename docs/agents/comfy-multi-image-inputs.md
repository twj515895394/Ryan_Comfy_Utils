# Ryan 节点多图输入约定

## 槽位

- 最多 **10** 路：`image_01` … `image_10`（ComfyUI `IMAGE`）
- 默认界面只显示 **`image_01`**；通过节点按钮 **「Ryan + 图片」** / **「Ryan − 图片」** 增减可见槽位（最多 10）
- 内部 `image_slot_count` 由前端维护（默认 1）

## 适用节点

- Ryan ACP Universal / Image Prompt / Video Prompt / Image Analyze Agent
- Ryan LLM Vision Chat

ACP 节点可同时保留 **`image_paths`**（多行本地路径），与槽位落盘路径合并后进 session。

## 前端

`ryan_comfy_utils/web/ryan_multi_image_slots.js`（随 `WEB_DIRECTORY` 加载）

## 实现

`ryan_comfy_utils/nodes/comfy_image_inputs.py`