Status: ready-for-agent

# ACP Session 与 CLI Smoke 链路打通

## 父问题

`.scratch/acp-runtime-foundation/PRD.md`

## 要构建什么

实现 ACP 的最小 session/workspace 生命周期，并打通一次 CLI smoke 执行。

这个切片需要让一次调用具备完整的执行外壳：

- 创建 `session_xxx` 目录
- 建立 `input/`、`output/`、`logs/`
- 写入 `metadata.json` 和 `context.json`
- 执行一次本地命令
- 捕获 stdout、stderr、退出码

完成后，哪怕 skill/context 还很简单，也应该已经具备“一次节点执行等于一次独立 session”的可验证基础。

## 验收标准

- [ ] runtime 可以根据 session id 创建独立 workspace 目录
- [ ] session 元数据和 context 文件会落盘到 session 目录
- [ ] CLI 执行结果会返回 stdout、stderr 和 returncode
- [ ] smoke 测试不依赖真实 Codex/Claude CLI，也能稳定跑通
- [ ] 单元测试验证 session 目录结构和 CLI 结果捕获行为

## 被阻塞于

- `.scratch/acp-runtime-foundation/issues/01-acp-protocol-assets.md`
