import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

const MAX_OUTPUTS = 12;
const OUTPUT_PREFIX = "image_";
const COUNT_WIDGET = "output_count";
const PREVIEW_BASE_H = 160;
const PREVIEW_ROW_H = 110;
const COLS = 3;

function outputSlotName(index) {
  return `${OUTPUT_PREFIX}${String(index).padStart(2, "0")}`;
}

function findWidget(node, name) {
  return node.widgets?.find((w) => w.name === name);
}

function cleanNativePreviewWidgets(node) {
  // 仅保留我们自定义的 widgets，移除 ComfyUI 自动添加的任何预览 widget
  if (node.widgets) {
    node.widgets = node.widgets.filter(
      (w) =>
        w.name === COUNT_WIDGET ||
        w.name === "Update Outputs" ||
        w.name === "image_preview"
    );
  }
}

function enforceWidgetsOrder(node) {
  if (!node.widgets) return;

  const ordered = [];

  const countWidget = node.widgets.find((w) => w.name === COUNT_WIDGET);
  if (countWidget) ordered.push(countWidget);

  const updateWidget = node.widgets.find((w) => w.name === "Update Outputs");
  if (updateWidget) ordered.push(updateWidget);

  const previewWidget = node.widgets.find((w) => w.name === "image_preview");
  if (previewWidget) ordered.push(previewWidget);

  // 保证其他 widget 不丢失
  for (const w of node.widgets) {
    if (!ordered.includes(w)) {
      ordered.push(w);
    }
  }

  node.widgets = ordered;
}

function calcPreviewHeight(imageCount) {
  const n = Math.max(0, Number(imageCount) || 0);
  if (n <= 0) return PREVIEW_BASE_H;
  const rows = Math.ceil(n / COLS);
  // 单行用 base；多行按行高累加，上限约 3 行
  return Math.min(PREVIEW_BASE_H + (Math.min(rows, 3) - 1) * PREVIEW_ROW_H, 380);
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

  const count = images?.length || 0;
  let columns = "1fr";
  if (count === 2) {
    columns = "1fr 1fr";
  } else if (count >= 3) {
    columns = "1fr 1fr 1fr";
  }

  node.previewContainer.style.display = count > 0 ? "grid" : "flex";
  node.previewContainer.style.gridTemplateColumns = columns;
  node.previewContainer.style.gap = "6px";
  node.previewContainer.style.padding = "6px";
  node.previewContainer.style.alignContent = "start";
  node.previewContainer.style.justifyContent = "center";
  node.previewContainer.style.alignItems = "center";

  const previewH = calcPreviewHeight(count);
  node.previewContainer.style.height = `${previewH}px`;
  node._preview_height = previewH;

  if (node.previewWidget) {
    node.previewWidget.computedHeight = previewH;
  }

  if (count === 0) {
    const empty = document.createElement("div");
    empty.style.cssText =
      "color:#666;font-size:12px;text-align:center;width:100%;";
    empty.innerText = "暂无预览";
    node.previewContainer.appendChild(empty);
    return;
  }

  images.forEach((img) => {
    const imgEl = document.createElement("img");
    imgEl.src = api.apiURL(
      `/view?filename=${encodeURIComponent(img.filename)}&type=${img.type}&subfolder=${encodeURIComponent(img.subfolder || "")}`
    );
    imgEl.style.cssText = [
      "width:100%",
      "height:100%",
      "max-height:100%",
      "aspect-ratio:16/9",
      "object-fit:contain",
      "object-position:center",
      "background-color:#111",
      "border-radius:4px",
      "box-sizing:border-box",
      "border:1px solid #333",
      "display:block",
    ].join(";");
    imgEl.loading = "lazy";
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
      { min: 1, max: MAX_OUTPUTS, step: 1, precision: 0 }
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

    // 自定义 computeSize：控件区 + 预览区，不再用 spacer 硬对齐输出槽
    nodeType.prototype.computeSize = function () {
      const width = Math.max(this.size?.[0] || 350, 320);
      // 标题 + count + button + 边距
      const controlsH = 90;
      const previewH = this._preview_height || PREVIEW_BASE_H;
      // 输出槽高度仅影响节点最小高度，不驱动预览位置
      const slotsH = (this.outputs ? this.outputs.length : 0) * 22 + 40;
      const contentH = controlsH + previewH + 20;
      const height = Math.max(contentH, slotsH, 200);
      return [width, height];
    };

    const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      originalOnNodeCreated?.apply(this, arguments);
      setupSplitterUI(this);

      this._preview_height = PREVIEW_BASE_H;

      // 通过定义 getter/setter 彻底屏蔽 ComfyUI 往该节点挂载和绘制原生预览图的任何尝试
      Object.defineProperty(this, "imgs", {
        get() {
          return null;
        },
        set(v) {},
        configurable: true,
        enumerable: true,
      });
      Object.defineProperty(this, "image", {
        get() {
          return null;
        },
        set(v) {},
        configurable: true,
        enumerable: true,
      });
      Object.defineProperty(this, "images", {
        get() {
          return null;
        },
        set(v) {},
        configurable: true,
        enumerable: true,
      });

      // 创建预览网格 DOM 容器
      const previewContainer = document.createElement("div");
      previewContainer.style.cssText = [
        "width:100%",
        `height:${PREVIEW_BASE_H}px`,
        "position:relative",
        "background-color:#000",
        "overflow-y:auto",
        "overflow-x:hidden",
        "border-radius:4px",
        "box-sizing:border-box",
        "display:flex",
        "align-items:center",
        "justify-content:center",
      ].join(";");

      const previewWidget = this.addDOMWidget("image_preview", "preview", previewContainer, {
        serialize: false,
        getValue() {
          return "";
        },
        setValue(v) {},
      });

      previewWidget.computeSize = (width) => {
        const h = this._preview_height || PREVIEW_BASE_H;
        return [width || 350, h];
      };

      this.previewContainer = previewContainer;
      this.previewWidget = previewWidget;

      const originalOnResize = this.onResize;
      this.onResize = function (size) {
        originalOnResize?.apply(this, arguments);
        if (this.previewContainer && this._preview_height) {
          this.previewContainer.style.height = `${this._preview_height}px`;
        }
      };

      enforceWidgetsOrder(this);
      this.size = this.computeSize();
    };

    const originalConfigure = nodeType.prototype.configure;
    nodeType.prototype.configure = function (info) {
      if (this._all_outputs) {
        this.outputs = [...this._all_outputs];
      }

      const r = originalConfigure?.apply(this, arguments);

      // 同步反序列化后的 outputs 连接状态到 _all_outputs 备份中
      if (this.outputs && this._all_outputs) {
        for (const output of this.outputs) {
          const backupOutput = this._all_outputs.find((out) => out.name === output.name);
          if (backupOutput) {
            backupOutput.links = output.links;
          }
        }
      }

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

        // 仅当用户当前 output_count 小于实际图片数时，自动扩到实际张数；
        // 不再强行把用户手动设的更大槽位数压回去
        const countWidget = findWidget(this, COUNT_WIDGET);
        const currentCount = Number(countWidget?.value || 4);
        const actualCount = message.images.length;
        if (actualCount > 0 && actualCount > currentCount) {
          applyOutputSlotVisibility(this, actualCount);
        } else {
          // 只刷新尺寸
          this.setSize?.(this.computeSize?.());
          if (this.graph) this.graph.setDirtyCanvas(true, true);
        }
      }

      // 强力清除与排序
      cleanNativePreviewWidgets(this);
      enforceWidgetsOrder(this);
      this.size = this.computeSize();
    };
  },
});
