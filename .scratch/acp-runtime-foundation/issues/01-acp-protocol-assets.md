Status: ready-for-agent

# ACP 协议与示例资产落库

## 父问题

`.scratch/acp-runtime-foundation/PRD.md`

## 要构建什么

为 ACP Foundation 建立第一批稳定协议资产，并让 runtime 可以读取一组最小示例。

这一片不是只写文档，而是要同时打通：

- `Node Manifest` 的最小字段定义
- `ACP Profile` 的最小字段定义
- `Result Payload` 的最小字段定义
- 一组可被测试读取的 manifest/profile/result fixture

完成后，仓库里应该存在一套可验证的协议样例，后续 session/runtime/node 都基于这些样例继续推进，而不是在代码里临时拼字段。

## 验收标准

- [ ] `ryan_comfy_utils/acp/` 下存在可复用的协议读取入口
- [ ] 仓库包含至少一份 `universal_agent` manifest fixture
- [ ] 仓库包含至少一份本地 CLI profile fixture
- [ ] 仓库包含至少一份文本结果 payload fixture
- [ ] 单元测试验证 manifest/profile/result fixture 可被成功加载和校验

## 被阻塞于

无 - 可以立即开始
