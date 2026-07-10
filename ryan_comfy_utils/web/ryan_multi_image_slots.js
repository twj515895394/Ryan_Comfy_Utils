import { app } from "../../../scripts/app.js";

const MAX_SLOTS = 10;
const SLOT_PREFIX = "image_";
const COUNT_WIDGET = "image_slot_count";

const RYAN_MULTI_IMAGE_NODES = new Set([
  "Ryan ACP Universal Agent",
  "Ryan ACP Image Prompt Agent",
  "Ryan ACP Video Prompt Agent",
  "Ryan ACP Image Analyze Agent",
  "Ryan LLM Vision Chat",
]);

function slotName(index) {
  return `${SLOT_PREFIX}${String(index).padStart(2, "0")}`;
}

function findWidget(node, name) {
  return node.widgets?.find((w) => w.name === name);
}

function applySlotVisibility(node, count) {
  const n = Math.max(1, Math.min(MAX_SLOTS, Number(count) || 2));

  // 1. 初始化原始 inputs 备份
  if (!node._all_inputs) {
    node._all_inputs = [...(node.inputs || [])];
  }

  // 2. 检查是否有需要隐藏的 slots 上还连着线，若有则断开
  for (let i = 1; i <= MAX_SLOTS; i++) {
    if (i > n) {
      const name = slotName(i);
      const input = node._all_inputs.find((inp) => inp.name === name);
      if (input) {
        const curIdx = node.inputs?.indexOf(input);
        if (curIdx !== undefined && curIdx !== -1 && node.inputs[curIdx].link !== null) {
          node.disconnectInput(curIdx);
        }
      }
    }
  }

  // 3. 构建新的 inputs 数组，仅包含非 image_xx 的输入和 image_01..image_n
  const newInputs = [];
  for (const input of node._all_inputs) {
    const match = input.name.match(/^image_(\d+)$/);
    if (match) {
      const idx = parseInt(match[1], 10);
      if (idx <= n) {
        newInputs.push(input);
      }
    } else {
      newInputs.push(input);
    }
  }

  node.inputs = newInputs;

  // 同步 widget value
  const countWidget = findWidget(node, COUNT_WIDGET);
  if (countWidget) {
    countWidget.value = n;
  }

  node.setSize?.(node.computeSize?.());
  app.graph.setDirtyCanvas(true, true);
}

function setupMultiImageUI(node) {
  let countWidget = findWidget(node, COUNT_WIDGET);
  if (!countWidget) {
    countWidget = node.addWidget(
      "number",
      COUNT_WIDGET,
      2,
      () => {},
      { min: 1, max: MAX_SLOTS, step: 1, precision: 0 },
    );
  } else {
    countWidget.callback = () => {};
  }
  countWidget.hidden = false;

  // 确保备份
  if (!node._all_inputs) {
    node._all_inputs = [...(node.inputs || [])];
  }

  node.addWidget("button", "Update", null, () => {
    const targetCount = Number(findWidget(node, COUNT_WIDGET)?.value || 2);
    applySlotVisibility(node, targetCount);
  });

  applySlotVisibility(node, countWidget.value || 2);
}

app.registerExtension({
  name: "RyanComfyUtils.MultiImageSlots",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (!RYAN_MULTI_IMAGE_NODES.has(nodeData.name)) return;

    const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      originalOnNodeCreated?.apply(this, arguments);
      setupMultiImageUI(this);
    };

    // 拦截 configure 钩子，解决工作流加载反序列化连接丢失的问题
    const originalConfigure = nodeType.prototype.configure;
    nodeType.prototype.configure = function (info) {
      // 在反序列化开始前还原全部 inputs
      if (this._all_inputs) {
        this.inputs = [...this._all_inputs];
      }

      const r = originalConfigure?.apply(this, arguments);

      // configure 完成后，重新备份并应用隐藏
      if (!this._all_inputs) {
        this._all_inputs = [...(this.inputs || [])];
      }

      const countWidget = findWidget(this, COUNT_WIDGET);
      const targetCount = Number(countWidget?.value || 2);
      applySlotVisibility(this, targetCount);

      return r;
    };
  },
});
