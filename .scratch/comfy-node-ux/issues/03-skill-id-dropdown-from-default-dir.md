Status: ready-for-agent

# 技能 ID 下拉选择：从节点默认 skill 目录自动列出

## 父问题
`.scratch/comfy-node-ux/PRD.md`

## 要构建什么
在 `Ryan ACP Universal Agent` 节点中，将 `skill_id` 从自由文本输入改为下拉选择（combo）。

下拉选项来源：节点包内默认 skill 存放目录（`ryan_comfy_utils/acp/fixtures/skills/`）下的子目录名称（image_prompt_generator、image_prompt_reverse、video_prompt_generator 等）。

固定 Prompt 节点（Image Prompt / Video Prompt / Image Analyze）仍使用 manifest 绑定的固定 skill_id，不暴露 skill_id 输入（或隐藏）。

端到端：用户在 Universal Agent 看到可用 skill 列表，选择后节点使用该 skill_id 进行 resolver 绑定；不填或非法值时有合理回退或报错提示。

## 验收标准
- [ ] Universal Agent 的 skill_id 呈现为下拉，选项来自默认 skill 目录扫描
- [ ] 目录扫描失败时有兜底（至少列出现有 3 个，或给默认）
- [ ] 固定节点不让用户通过界面改 skill_id
- [ ] 选择后执行能正确绑定对应 skill 并运行
- [ ] skill_root 为空时仍回退包内默认

## 被阻塞于
无 - 可以立即开始
