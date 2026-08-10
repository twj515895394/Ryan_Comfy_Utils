# Progress

## 2026-08-10

- 已完成 MiniMax H3 skill v2 设计、实现和规则验证。
- 已完成 ACP H3 Agent 输入合同、资产传递、官方模式和风格路由同步。
- 已修复 H3 节点 widget 顺序兼容、模式值兼容以及无视频时忽略视频帧参数。
- 已修复 Smart Filter 刷新后连线丢失风险：固定保留 9 个输入和 9 个输出，不再重排 slot 数组。
- Smart Filter 四类节点现在统一输出连接数、有效输出数和 null 输出数日志；默认 example/default 资源统一输出 null。
- ACP runtime 现在在外部 CLI/LLM 调用边界输出开始和结束日志，包含 runner、skill、timeout、returncode、status 和 elapsed_ms；不输出命令参数、路径或密钥。
- 成功、非零返回码、异常调用均有对应结束状态日志。
- Runtime + ACP Agent 回归：25 tests passed。
- Python 语法检查：通过。
