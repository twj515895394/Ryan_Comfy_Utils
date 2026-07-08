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

function setSlotVisible(node, index, visible) {
  const name = slotName(index);
  const input = node.inputs?.find((i) => i.name === name);
  if (input) {
    input.hidden = !visible;
  }
  const widget = findWidget(node, name);
  if (widget) {
    widget.hidden = !visible;
    widget.disabled = !visible;
  }
}

function applySlotVisibility(node, count) {
  const n = Math.max(1, Math.min(MAX_SLOTS, Number(count) || 1));
  for (let i = 1; i <= MAX_SLOTS; i++) {
    setSlotVisible(node, i, i <= n);
  }
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
      1,
      (v) => applySlotVisibility(node, v),
      { min: 1, max: MAX_SLOTS, step: 1, precision: 0 },
    );
    countWidget.hidden = true;
  }

  for (let i = 2; i <= MAX_SLOTS; i++) {
    setSlotVisible(node, i, false);
  }
  setSlotVisible(node, 1, true);

  node.addWidget("button", "Ryan + 图片", null, () => {
    const current = Number(findWidget(node, COUNT_WIDGET)?.value || 1);
    if (current >= MAX_SLOTS) return;
    applySlotVisibility(node, current + 1);
  });

  node.addWidget("button", "Ryan − 图片", null, () => {
    const current = Number(findWidget(node, COUNT_WIDGET)?.value || 1);
    if (current <= 1) return;
    applySlotVisibility(node, current - 1);
  });

  applySlotVisibility(node, countWidget.value || 1);
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
  },
});