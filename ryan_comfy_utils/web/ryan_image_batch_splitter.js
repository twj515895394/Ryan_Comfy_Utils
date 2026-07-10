import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

const MAX_OUTPUTS = 12;
const OUTPUT_PREFIX = "image_";
const COUNT_WIDGET = "output_count";

function outputSlotName(index) {
  return `${OUTPUT_PREFIX}${String(index).padStart(2, "0")}`;
}

function findWidget(node, name) {
  return node.widgets?.find((w) => w.name === name);
}

function cleanNativePreviewWidgets(node) {
  // 仅保留我们自定义的 widgets，移除 ComfyUI 自动添加的任何预览 widget
  if (node.widgets) {
    node.widgets = node.widgets.filter((w) =>
      w.name === COUNT_WIDGET ||
      w.name === "Update Outputs" ||
      w.name === "spacer" ||
      w.name === "image_preview"
    );
  }
}

function enforceWidgetsOrder(node) {
  if (!node.widgets) return;

  const ordered = [];

  const countWidget = node.widgets.find(w => w.name === COUNT_WIDGET);
  if (countWidget) ordered.push(countWidget);

  const updateWidget = node.widgets.find(w => w.name === "Update Outputs");
  if (updateWidget) ordered.push(updateWidget);

  let spacerWidget = node.widgets.find(w => w.name === "spacer");
  if (!spacerWidget) {
    spacerWidget = {
      type: "spacer",
      name: "spacer",
      value: null,
      draw(ctx, node, widget_width, y, widget_height) {},
      computeSize(width) {
        return [width || 350, node._spacer_height || 0];
      }
    };
  }
  ordered.push(spacerWidget);

  const previewWidget = node.widgets.find(w => w.name === "image_preview");
  if (previewWidget) ordered.push(previewWidget);

  // 保证其他 widget 不丢失
  for (const w of node.widgets) {
    if (!ordered.includes(w)) {
      ordered.push(w);
    }
  }

  node.widgets = ordered;
}

function applyOutputSlotVisibility(node, count) {
  const n = Math.max(1, Math.min(MAX_OUTPUTS, Number(count) || 4));

  // 1. 初始化原始 outputs 备份
  if (!node._all_outputs) {
    node._all_outputs = [...(node.outputs || [])];
  }

  // 2. 检查是否有需要隐藏的 outputs 上还连着线，若有则断开
  for (let i = 1; i <= MAX_OUTPUTS; i++) {
    if (i > n) {
      const name = outputSlotName(i);
      const output = node._all_outputs.find((out) => out.name === name);
      if (output) {
        const curIdx = node.outputs?.indexOf(output);
        if (curIdx !== undefined && curIdx !== -1 && node.outputs[curIdx].links?.length > 0) {
          node.disconnectOutput(curIdx);
        }
      }
    }
  }

  // 3. 构建新的 outputs 数组，仅包含非 image_xx 的输出和 image_01..image_n
  const newOutputs = [];
  for (const output of node._all_outputs) {
    const match = output.name.match(/^image_(\d+)$/);
    if (match) {
      const idx = parseInt(match[1], 10);
      if (idx <= n) {
        newOutputs.push(output);
      }
    } else {
      newOutputs.push(output);
    }
  }

  node.outputs = newOutputs;

  // 同步 widget value
  const countWidget = findWidget(node, COUNT_WIDGET);
  if (countWidget) {
    countWidget.value = n;
  }

  node.setSize?.(node.computeSize?.());
  if (node.graph) {
    node.graph.setDirtyCanvas(true, true);
  }
}

function rebuildPreviewGrid(node, images) {
  if (!node.previewContainer) return;
  
  while (node.previewContainer.firstChild) {
    node.previewContainer.removeChild(node.previewContainer.firstChild);
  }

  const count = images.length;
  let columns = "1fr";
  if (count === 2) {
    columns = "1fr 1fr";
  } else if (count >= 3) {
    columns = "1fr 1fr 1fr";
  }
  
  node.previewContainer.style.display = "grid";
  node.previewContainer.style.gridTemplateColumns = columns;
  node.previewContainer.style.gap = "6px";
  node.previewContainer.style.padding = "6px";

  images.forEach(img => {
    const imgEl = document.createElement("img");
    imgEl.src = api.apiURL(`/view?filename=${encodeURIComponent(img.filename)}&type=${img.type}&subfolder=${encodeURIComponent(img.subfolder)}`);
    imgEl.style.width = "100%";
    imgEl.style.height = "auto";
    imgEl.style.aspectRatio = "16/9";
    imgEl.style.objectFit = "cover";
    imgEl.style.backgroundColor = "#111";
    imgEl.style.borderRadius = "4px";
    imgEl.style.boxSizing = "border-box";
    imgEl.style.border = "1px solid #333";
    node.previewContainer.appendChild(imgEl);
  });
}

function setupSplitterUI(node) {
  let countWidget = findWidget(node, COUNT_WIDGET);
  if (!countWidget) {
    countWidget = node.addWidget(
      "number",
      COUNT_WIDGET,
      4,
      () => {},
      { min: 1, max: MAX_OUTPUTS, step: 1, precision: 0 },
    );
  } else {
    countWidget.callback = () => {};
  }
  countWidget.hidden = false;

  if (!node._all_outputs) {
    node._all_outputs = [...(node.outputs || [])];
  }

  node.addWidget("button", "Update Outputs", null, () => {
    const targetCount = Number(findWidget(node, COUNT_WIDGET)?.value || 4);
    applyOutputSlotVisibility(node, targetCount);
  });

  applyOutputSlotVisibility(node, countWidget.value || 4);
}

app.registerExtension({
  name: "RyanComfyUtils.ImageBatchSplitter",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "Ryan Image Batch Splitter") return;

    // 自定义 computeSize 确保输出槽与预览网格不重叠
    nodeType.prototype.computeSize = function () {
      const size = [350, 200];
      const slotsHeight = (this.outputs ? this.outputs.length : 0) * 20 + 50;
      const widgetsHeightBeforePreview = 80; // title(30) + count(20) + button(20) + margin(10)
      
      const previewStart = Math.max(slotsHeight, widgetsHeightBeforePreview);
      
      // 计算用于推开预览组件的 spacer 高度
      this._spacer_height = Math.max(0, previewStart - 80);
      
      const spacerWidget = this.widgets?.find(w => w.name === "spacer");
      if (spacerWidget) {
        spacerWidget.height = this._spacer_height;
      }

      const previewHeight = 180;
      size[1] = 80 + this._spacer_height + previewHeight + 15;
      size[0] = 350;
      return size;
    };

    const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      originalOnNodeCreated?.apply(this, arguments);
      setupSplitterUI(this);

      // 通过定义 getter/setter 彻底屏蔽 ComfyUI 往该节点挂载和绘制原生预览图的任何尝试
      Object.defineProperty(this, "imgs", {
        get() { return null; },
        set(v) {},
        configurable: true,
        enumerable: true
      });
      Object.defineProperty(this, "image", {
        get() { return null; },
        set(v) {},
        configurable: true,
        enumerable: true
      });
      Object.defineProperty(this, "images", {
        get() { return null; },
        set(v) {},
        configurable: true,
        enumerable: true
      });

      // 创建预览网格 DOM 容器
      const previewContainer = document.createElement("div");
      previewContainer.style.width = "100%";
      previewContainer.style.height = "180px";
      previewContainer.style.position = "relative";
      previewContainer.style.backgroundColor = "#000";
      previewContainer.style.overflowY = "auto";
      previewContainer.style.borderRadius = "4px";
      previewContainer.style.boxSizing = "border-box";

      const previewWidget = this.addDOMWidget("image_preview", "preview", previewContainer, {
        serialize: false,
        getValue() {
          return "";
        },
        setValue(v) {}
      });

      previewWidget.computeSize = function (width) {
        return [width || 350, 180];
      };

      this.previewContainer = previewContainer;
      this.previewWidget = previewWidget;
      
      enforceWidgetsOrder(this);
      this.size = this.computeSize();
    };

    const originalConfigure = nodeType.prototype.configure;
    nodeType.prototype.configure = function (info) {
      if (this._all_outputs) {
        this.outputs = [...this._all_outputs];
      }

      const r = originalConfigure?.apply(this, arguments);

      if (!this._all_outputs) {
        this._all_outputs = [...(this.outputs || [])];
      }

      const countWidget = findWidget(this, COUNT_WIDGET);
      const targetCount = Number(countWidget?.value || 4);
      applyOutputSlotVisibility(this, targetCount);

      // 恢复预览图片网格
      const previewImages = this.properties?._preview_images;
      if (previewImages && this.previewContainer) {
        rebuildPreviewGrid(this, previewImages);
      }

      // 强制清理与排序
      cleanNativePreviewWidgets(this);
      enforceWidgetsOrder(this);

      this.size = this.computeSize();
      return r;
    };

    const originalOnExecuted = nodeType.prototype.onExecuted;
    nodeType.prototype.onExecuted = function (message) {
      // 阻止 ComfyUI 原生的多图预览渲染，避免双重预览和布局混乱
      const cleanMessage = { ...message };
      if (cleanMessage.images) {
        delete cleanMessage.images;
      }
      originalOnExecuted?.apply(this, [cleanMessage]);

      if (message?.images) {
        if (!this.properties) this.properties = {};
        this.properties._preview_images = message.images;
        rebuildPreviewGrid(this, message.images);
        
        // 自动将输出插槽数量调整到实际拆分出的图片数量
        applyOutputSlotVisibility(this, message.images.length);
      }

      // 强力清除与排序
      cleanNativePreviewWidgets(this);
      enforceWidgetsOrder(this);
    };
  },
});
