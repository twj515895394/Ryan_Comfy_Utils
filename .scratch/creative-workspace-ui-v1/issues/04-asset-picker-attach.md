Status: ready-for-agent

# 04 素材引用 UI（@ / 附件）

## 父问题

- `.scratch/creative-workspace-ui-v1/PRD.md`

## 要构建什么

Composer 工具区支持：

- 打开资产选择（ComfyTV 列表；不可用时本地文件/说明）
- 选中后写入项目 asset-refs，并在发送时带 `asset_ref_ids`
- 输入 `@` 可弹出简易选择（不必一次做完所有语义 role，默认 reference）
- 消息中展示已引用素材芯片

复用后端 Asset Bridge / routes。

## 验收标准

- [ ] 有 ComfyTV 时可浏览并引用资产
- [ ] 无 ComfyTV 时不崩，可本地降级或明确提示
- [ ] 发送请求包含所选 ref id
- [ ] UI 可见已选素材并可移除

## 被阻塞于

- `02-teman-layout-composer-history`

## 评论

