Status: ready-for-agent

# Ryan Image Analyze Agent（图像反推提示词）

## 父问题

`.scratch/acp-runtime-foundation/PRD.md`

## 要构建什么

新增固定节点 `Ryan Image Analyze Agent`，从参考图**反推**可用于 AI 绘图的提示词（对齐产品资料「反推提示词」：拆解风格、光影、构图、色彩、质感等，产出可复用 prompt，而非质检报告）。

绑定 Skill（建议 id：`image_prompt_reverse` 或 `image_analyzer`），Skill 内收敛：

- **通用** 8 维反推框架（主体、风格、色彩、光影、构图、质感、分辨率、细节）
- **分类模板**（general / typography_logo / landscape / photography / illustration / render_3d / ip_character），与 Obsidian 剪藏《全网最全「反推提示词」指南》一致，**不**为每类单独拆 ComfyUI 节点

节点输入：

- 必填：`user_text`（可空但建议保留 multiline 补充要求）
- 必填之一：参考图 via `image_paths`（多行）；v1 与现 Prompt 节点相同，不接 IMAGE tensor
- 可选：`category`（枚举上述类型，默认 `general`）
- 可选：`output_language`：`bilingual`（默认）/ `zh` / `en`
- 可选：`extra_prompt`
- 运行参数同现有固定节点；`skill_root` 空则用包内 fixtures

输出（与现 ACP 固定节点一致）：

- `response_text`：默认可直接用于 AI 绘图的中英双语 prompt（`bilingual` 时中英同屏；单语时仅对应语言）
- `session_dir`、`raw_result_json`

可选同期（若本期不做则记入 issue 11）：

- BOOLEAN `export_to_file`：关则仅字符串；开则按 `docs/agents/acp-file-export-convention.md` 写入 `output/ryan_acp_exports/image_analyze/`

## 验收标准

- [ ] 节点已注册，分类 `Ryan Utils / ACP`，默认 manifest + 包内 Skill
- [ ] `category` 与 `output_language` 进入合并上下文，Skill 能区分反推模板
- [ ] 无 `image_paths` 时行为明确（拒绝或仅文本弱反推——实现前在 contract 文档写清，推荐：**至少一张图路径或后续 IMAGE**）
- [ ] 单元测试：manifest、节点 contract、mock runtime 参数含 `image_inputs` 与 category
- [ ] `docs/agents/acp-fixed-prompt-agent-contracts.md` 增加 Image Analyze 小节
- [ ] README 说明与 Image Prompt 的分工（创作 vs 反推）

## 被阻塞于

无（共享基础已在 issue 07 完成）— 可与 issue 11 设计并行，但实现可先做本 issue。

## 评论

### 2026-07-08 用户确认

- 第二批固定 Agent 优先 Image Analyze（反推），参考资料：Obsidian Clippings「全网最全反推提示词指南」
- 输出：默认可用于绘图的中英双语 prompt；7 类通过节点 `category` + Skill 模板实现