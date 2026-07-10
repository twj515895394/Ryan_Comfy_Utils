Status: ready-for-agent

# 多图输入槽位：默认 2 张 + 指定数量 + Update 按钮刷新

## 父问题
`.scratch/comfy-node-ux/PRD.md`

## 要构建什么
修改涉及图片输入的节点（ACP 系列 + LLM Vision Chat），将默认可见图片槽位从 1 或 10 改为 **2**（image_01、image_02）。

提供一个数量输入（INT ≥1 ≤10），以及一个“Update”按钮。用户修改数量后，必须点击 Update 才真正增减可见的 IMAGE 输入槽位；不再使用实时 +/- 按钮。

端到端：用户看到默认 2 个图片输入；改数字后点 Update 刷新界面；内部 image_slot_count 正确同步；超出范围受控；节点功能不受影响。

## 验收标准
- [ ] 默认界面显示 2 个图片输入（image_01、image_02）
- [ ] 数量输入默认值为 2，支持 1~10
- [ ] 改数量后需点击 Update 才刷新可见槽位
- [ ] 增减后节点可正常连接图片并执行
- [ ] 前端 JS 逻辑与 Python build_image_slot_input_types 配合一致

## 被阻塞于
无 - 可以立即开始
