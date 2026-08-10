/**
 * Ryan Smart Filter — 稳定的输入/输出槽位布局。
 *
 * LiteGraph 工作流把连线保存为节点 ID + slot index。不能在工作流
 * 反序列化或刷新时过滤 node.inputs/node.outputs，否则隐藏槽位会改变
 * 后续 slot index，导致已保存的连线丢失或接到错误的输入。
 *
 * 后端节点始终声明完整的 9 个输入和 9 个输出；这里不再动态删除槽位。
 * 牺牲少量界面紧凑度，换取工作流保存、刷新和重载时的连线稳定性。
 */
import { app } from "../../../scripts/app.js";

const FILTER_NODES = new Set([
  "Ryan Smart Image Filter",
  "Ryan Smart Video Filter",
  "Ryan Smart Audio Filter",
  "Ryan Smart Text Filter",
]);

app.registerExtension({
  name: "RyanComfyUtils.SmartFilter",

  loadedGraphNode(node) {
    const typeName = node.comfyClass || node.type;
    if (!FILTER_NODES.has(typeName)) return;

    // 只重新计算节点尺寸，不改动 inputs/outputs 数组或连线索引。
    node.setSize?.(node.computeSize?.());
  },
});
