import { app } from "../../../scripts/app.js";

function findWidget(node, name) {
  return node.widgets?.find((w) => w.name === name);
}

function updatePromptDirVisibility(node) {
  const sourceWidget = findWidget(node, "template_source");
  const dirWidget = findWidget(node, "prompt_dir");

  if (!sourceWidget || !dirWidget) return;

  const isCustom = sourceWidget.value === "自定义目录";

  dirWidget.hidden = !isCustom;
  dirWidget.disabled = !isCustom;

  // 刷新大小和画布
  node.setSize?.(node.computeSize?.());
  if (node.graph) {
    node.graph.setDirtyCanvas(true, true);
  }
}

function setupPromptTemplateUI(node) {
  const sourceWidget = findWidget(node, "template_source");
  if (sourceWidget) {
    const originalCallback = sourceWidget.callback;
    sourceWidget.callback = function (value) {
      const r = originalCallback?.apply(this, arguments);
      updatePromptDirVisibility(node);
      return r;
    };
  }

  // 初始执行一次以同步状态
  updatePromptDirVisibility(node);
}

app.registerExtension({
  name: "RyanComfyUtils.PromptTemplate",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "Ryan Prompt Template") return;

    const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      originalOnNodeCreated?.apply(this, arguments);
      setupPromptTemplateUI(this);
    };

    const originalConfigure = nodeType.prototype.configure;
    nodeType.prototype.configure = function (info) {
      if (info?.widgets_values) {
        const mapping = {
          "built_in": "内置模板",
          "custom_dir": "自定义目录"
        };
        info.widgets_values = info.widgets_values.map(val => {
          if (typeof val === "string" && mapping[val]) {
            return mapping[val];
          }
          return val;
        });
      }
      const r = originalConfigure?.apply(this, arguments);
      updatePromptDirVisibility(this);
      return r;
    };
  },
});
