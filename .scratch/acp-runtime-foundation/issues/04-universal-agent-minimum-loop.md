Status: ready-for-agent

# Universal Agent 节点最小闭环

## 父问题

`.scratch/acp-runtime-foundation/PRD.md`

## 要构建什么

新增 `Ryan ACP Universal Agent`，并打通文本输入到文本输出的最小闭环。

这个切片要覆盖 ComfyUI 适配层与 runtime 层的连接：

- 节点接收 `skill_id` 与 `user_text`
- 节点加载 manifest/profile
- 节点调用 runtime 发起一次 ACP Session
- 节点返回 `response_text`、`session_dir` 和原始结果

完成后，仓库里应首次出现可从 ComfyUI 入口使用的 ACP 节点，即使它暂时只支持文本链路。

## 验收标准

- [ ] `Ryan ACP Universal Agent` 已注册到 ComfyUI 节点映射
- [ ] 节点分类独立为 `Ryan Utils / ACP`
- [ ] 节点可以接收文本输入并返回文本输出
- [ ] 返回值至少包含 `response_text`、`session_dir`、`raw_result_json`
- [ ] 单元测试验证节点 contract 和最小 runtime 调用结果

## 被阻塞于

- `.scratch/acp-runtime-foundation/issues/02-acp-session-cli-smoke.md`
- `.scratch/acp-runtime-foundation/issues/03-acp-skill-context-builder.md`
