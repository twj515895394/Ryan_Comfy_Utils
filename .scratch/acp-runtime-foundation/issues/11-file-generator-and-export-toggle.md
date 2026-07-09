Status: ready-for-agent

# Ryan File Generator Agent 与节点导出开关

## 父问题

`.scratch/acp-runtime-foundation/PRD.md`

## 要构建什么

提供「把 Agent 优秀输出整理成文件」的能力，并在 ComfyUI **界面上用 BOOLEAN 开关**控制是否落盘（默认关，不破坏现有纯文本工作流）。

路径**写死**约定，见 `docs/agents/acp-file-export-convention.md`：

- 根：`ComfyUI output/ryan_acp_exports/<node_slug>/`
- 文件名：session + 时间戳或用户 `export_filename`

交付形态（二选一或组合，实现前 HITL 确认）：

1. 独立固定节点 `Ryan File Generator Agent`（专门整理/生成 prompt 库、清单类文件）
2. 共享模块 `export_prompt_artifact(...)`，供 Image Analyze / Image Prompt / Video Prompt 等节点通过 `export_to_file` 开关调用

用户诉求：**功能要有、界面能开/关、路径固定且带节点可识别命名**。

## 验收标准

- [ ] 至少一个节点暴露 `export_to_file`（BOOLEAN），默认 False
- [ ] 开启时文件写入 `output/ryan_acp_exports/<node_slug>/`，不写入 session 调试目录
- [ ] 关闭时与当前行为一致，无额外 IO
- [ ] 单元测试：mock output 根目录，断言路径与文件名规则
- [ ] README 或 contract 文档说明开关与目录规则

## 被阻塞于

- 建议于 issue 10 合并或紧随其后（若 10 含 `export_to_file` 则本 issue 聚焦独立 File Generator 节点与共享 exporter）

## 评论

### 2026-07-09 命名与范围 supersede

- 交接 `handoff-20260709-104808-acp-resolver-file-output.md`：**不再使用** `Ryan File Generator Agent`。
- **已完成**：`export_to_file` + `file_exporter.py`（三 Agent 节点 + 路径约定）。
- **未完成部分**迁至：
  - issue **13** `ryan-file-exporter-node.md`（`Ryan File Exporter` 工具节点）
  - issue **12** 与导出无关；issue **14** 文档校准

### 2026-07-08

- 用户确认需要 File Generator 能力，用于整理优秀提示词；路径写死 output 子目录；界面按钮开关。