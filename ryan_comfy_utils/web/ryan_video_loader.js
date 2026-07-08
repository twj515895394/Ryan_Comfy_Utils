import { app } from "../../../scripts/app.js";

function findWidget(node, name) {
  return node.widgets?.find((w) => w.name === name);
}

function addButton(node, label, delta) {
  node.addWidget("button", label, null, () => {
    const indexWidget = findWidget(node, "index");
    if (!indexWidget) return;
    const current = Number(indexWidget.value || 0);
    const next = Math.max(0, current + delta);
    indexWidget.value = next;
    indexWidget.callback?.(next);
    app.graph.setDirtyCanvas(true, true);
  });
}

app.registerExtension({
  name: "RyanComfyUtils.VideoLoaderNavigation",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "Ryan Batch Video Loader") return;

    const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      originalOnNodeCreated?.apply(this, arguments);
      addButton(this, "Ryan Previous Video", -1);
      addButton(this, "Ryan Next Video", 1);
    };
  },
});
