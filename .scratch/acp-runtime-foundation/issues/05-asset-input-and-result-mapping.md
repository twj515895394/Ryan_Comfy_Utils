Status: ready-for-agent

# 文件图片输入与结果映射扩展

## 父问题

`.scratch/acp-runtime-foundation/PRD.md`

## 要构建什么

在最小文本闭环稳定后，扩展 ACP runtime 对图片/文件输入和结构化结果映射的支持。

这一片要把第一阶段的 Foundation 从“只能传文本”推进到“能把 ComfyUI 资源变成 runtime 可消费的文件资产，并按 output contract 回传结果”。

它至少需要覆盖：

- 图片/文件资源落盘到 session `input/`
- `ACP Context` 中记录资源路径
- `Result Payload` 到节点输出字段的映射

完成后，后续固定绑定节点才有可复用的资源适配层，不需要各自重复实现。

## 验收标准

- [ ] runtime 可以将图片或文件输入保存到 session `input/` 目录
- [ ] `ACP Context` 中能引用这些输入资源的路径
- [ ] result mapping 可以把结构化 payload 映射回节点输出字段
- [ ] 至少有一组单元测试覆盖图片/文件路径注入和结果字段映射
- [ ] 该能力不破坏文本-only 的最小闭环

## 被阻塞于

- `.scratch/acp-runtime-foundation/issues/04-universal-agent-minimum-loop.md`
