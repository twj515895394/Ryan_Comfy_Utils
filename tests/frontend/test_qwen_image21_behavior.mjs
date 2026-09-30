import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

const source = await readFile(
  new URL("../../ryan_comfy_utils/web/ryan_qwen_image21.js", import.meta.url),
  "utf8",
);

const app = {
  canvas: null,
  graph: null,
  registerExtension(extension) { this.extension = extension; },
};

globalThis.__qwenImage21TestContext = {
  app,
  api: { apiURL: (path) => path },
};

const instrumentedSource = source
  .replace(
    /^import \{ app \} from "\.\.\/\.\.\/\.\.\/scripts\/app\.js";\nimport \{ api \} from "\.\.\/\.\.\/\.\.\/scripts\/api\.js";$/m,
    "const { app, api } = globalThis.__qwenImage21TestContext;",
  )
  .concat(`
export const __qwenImage21TestHooks = {
  installQwenCanvasBridge,
  persistQwenState,
  restoreQwenState,
  ensureQwenNumericDefaults,
  repairQwenWidgetValuesSoon,
  ensureQwenCanvasBridgeSoon,
  updateGalleryVisibility,
  restoreQwenImageInputs,
  installSlotGeometry,
  compactQwenBackingWidgets,
  patchQwenGraphToPrompt,
  qwenImageSlotPromptRef,
  qwenSourcePreviewUrl,
  clearQwenImageSlot,
  watchQwenImageSourceNode,
  ensureQwenTypedInputs,
  isExternalSlotConnected,
  qwenPendingConnectorLink,
};
`);

const { __qwenImage21TestHooks: hooks } = await import(
  `data:text/javascript;base64,${Buffer.from(instrumentedSource).toString("base64")}`,
);

function eventTarget() {
  const listeners = new Map();
  return {
    addEventListener(type, listener) {
      const registered = listeners.get(type) || [];
      registered.push(listener);
      listeners.set(type, registered);
    },
    removeEventListener(type, listener) {
      listeners.set(type, (listeners.get(type) || []).filter((item) => item !== listener));
    },
    emit(type, event = {}) {
      for (const listener of [...(listeners.get(type) || [])]) listener(event);
    },
    listenerCount(type) {
      return (listeners.get(type) || []).length;
    },
  };
}

function installDomForGallery(targetNode) {
  const windowTarget = eventTarget();
  const documentTarget = eventTarget();
  const gallery = { dataset: { qwenNodeId: String(targetNode.id) } };
  const cell = {
    dataset: { qwenSlot: "2" },
    classList: { contains: () => false },
    closest(selector) {
      if (selector === ".ryan-qwen-image-slot") return this;
      if (selector === ".ryan-qwen-image-gallery") return gallery;
      return null;
    },
  };
  targetNode.__ryanQwenImage21Installed = true;
  targetNode.__ryanQwenGallery = gallery;
  globalThis.window = windowTarget;
  globalThis.document = {
    ...documentTarget,
    elementFromPoint: () => cell,
  };
}

function makeCanvas() {
  const element = eventTarget();
  const connectorEvents = eventTarget();
  const canvas = {
    canvas: element,
    linkConnector: {
      events: connectorEvents,
      renderLinks: [],
      reset() {
        canvas.connecting_node = null;
        canvas.connecting_output = null;
        canvas.connecting_slot = null;
        canvas.connecting_input = null;
        this.renderLinks.length = 0;
      },
    },
  };
  return canvas;
}

function galleryTarget(id = 200) {
  return {
    id,
    properties: {},
    inputs: [],
    size: [430, 140],
    computeSize() { return [430, 140]; },
    setSize(size) { this.size = size; },
    setDirtyCanvas() {},
  };
}

function qwenWidgets(values = {}) {
  const names = [
    "prompt",
    "negative_prompt",
    "aspect_ratio",
    "megapixels",
    "batch_size",
    "resolution",
    "gallery_manifest",
    "prompt_mentions",
    ...Array.from({ length: 16 }, (_, index) => `gallery_${String(index + 1).padStart(2, "0")}`),
  ];
  return names.map((name) => ({ name, value: values[name] ?? "" }));
}

test("gallery connector survives native reset and accepts an output-slot object", () => {
  const target = galleryTarget();
  const sourceNode = { id: 100, outputs: [{ type: "IMAGE" }, { type: "IMAGE" }] };
  const canvas = makeCanvas();
  installDomForGallery(target);
  app.canvas = canvas;
  app.graph = {
    getNodeById: (id) => (Number(id) === target.id ? target : null),
    change() {},
    setDirtyCanvas() {},
  };

  hooks.installQwenCanvasBridge();
  canvas.connecting_node = sourceNode;
  // Recent LiteGraph exposes the output socket object here, without a numeric
  // slot field. The bridge must retain the output endpoint before reset.
  canvas.connecting_output = sourceNode.outputs[1];
  canvas.canvas.emit("pointerdown");
  canvas.linkConnector.events.emit("before-drop-links");
  canvas.linkConnector.reset();
  canvas.canvas.emit("pointerup", {
    button: 0,
    clientX: 20,
    clientY: 20,
    preventDefault() {},
    stopPropagation() {},
    stopImmediatePropagation() {},
  });

  assert.deepEqual(target.properties.ryan_qwen_image_links, [{
    source_id: "100",
    source_slot: 1,
    source_type: "IMAGE",
    slot: 2,
    order: 2,
  }]);
});

test("gallery connector accepts the detail payload used by ComfyUI dropped-on-canvas", () => {
  const target = galleryTarget();
  const sourceNode = { id: 14, outputs: [{ name: "IMAGE", type: "IMAGE" }] };
  const canvas = makeCanvas();
  installDomForGallery(target);
  app.canvas = canvas;
  app.graph = {
    getNodeById: (id) => (Number(id) === target.id ? target : null),
    change() {},
    setDirtyCanvas() {},
  };

  hooks.installQwenCanvasBridge();
  canvas.connecting_node = sourceNode;
  canvas.connecting_output = sourceNode.outputs[0];
  canvas.canvas.emit("pointerdown");
  canvas.linkConnector.events.emit("dropped-on-canvas", {
    detail: { clientX: 20, clientY: 20 },
    preventDefault() {},
    stopPropagation() {},
    stopImmediatePropagation() {},
  });

  assert.equal(target.properties.ryan_qwen_image_links.length, 1);
  assert.equal(target.properties.ryan_qwen_image_links[0].source_id, "14");
  assert.equal(target.properties.ryan_qwen_image_links[0].slot, 2);
});

test("gallery connector converts graph coordinates from a dropped-on-canvas detail payload", () => {
  const target = galleryTarget();
  const sourceNode = { id: 15, outputs: [{ name: "IMAGE", type: "IMAGE" }] };
  const canvas = makeCanvas();
  installDomForGallery(target);
  canvas.canvas.getBoundingClientRect = () => ({ left: 10, top: 20 });
  canvas.ds = { scale: 2, offset: [3, 4] };
  let hitPoint = null;
  const elementFromPoint = document.elementFromPoint;
  document.elementFromPoint = (clientX, clientY) => {
    hitPoint = [clientX, clientY];
    return elementFromPoint(clientX, clientY);
  };
  app.canvas = canvas;
  app.graph = {
    getNodeById: (id) => (Number(id) === target.id ? target : null),
    change() {},
    setDirtyCanvas() {},
  };

  hooks.installQwenCanvasBridge();
  canvas.connecting_node = sourceNode;
  canvas.connecting_output = sourceNode.outputs[0];
  canvas.canvas.emit("pointerdown");
  canvas.linkConnector.events.emit("dropped-on-canvas", {
    detail: { canvasX: 7, canvasY: 11 },
    preventDefault() {},
    stopPropagation() {},
    stopImmediatePropagation() {},
  });

  assert.deepEqual(hitPoint, [30, 50]);
  assert.equal(target.properties.ryan_qwen_image_links[0].source_id, "15");
});

test("canvas bridge detaches discarded canvas listeners before binding a replacement", () => {
  const target = galleryTarget();
  installDomForGallery(target);
  app.graph = { getNodeById: () => target, change() {}, setDirtyCanvas() {} };
  const discarded = makeCanvas();
  app.canvas = discarded;
  hooks.installQwenCanvasBridge();
  assert.equal(discarded.canvas.listenerCount("pointerup"), 1);

  const replacement = makeCanvas();
  app.canvas = replacement;
  hooks.installQwenCanvasBridge();

  assert.equal(discarded.linkConnector.events.listenerCount("before-drop-links"), 0);
  assert.equal(discarded.linkConnector.events.listenerCount("dropped-on-node"), 0);
  assert.equal(replacement.canvas.listenerCount("pointerup"), 1);
  assert.equal(replacement.linkConnector.events.listenerCount("dropped-on-node"), 1);
});

test("canvas bridge retries after ComfyUI publishes the live canvas", () => {
  const target = galleryTarget();
  installDomForGallery(target);
  app.graph = { getNodeById: () => target, change() {}, setDirtyCanvas() {} };
  const originalSetTimeout = globalThis.setTimeout;
  const retries = [];
  globalThis.setTimeout = (callback) => {
    retries.push(callback);
    return retries.length;
  };
  try {
    app.canvas = null;
    hooks.ensureQwenCanvasBridgeSoon();
    const liveCanvas = makeCanvas();
    app.canvas = liveCanvas;
    for (const retry of retries) retry();
    assert.equal(liveCanvas.canvas.listenerCount("pointerup"), 1);
  } finally {
    globalThis.setTimeout = originalSetTimeout;
  }
});

test("extension setup installs the canvas bridge without a test-only hook call", () => {
  const target = galleryTarget();
  installDomForGallery(target);
  app.graph = { getNodeById: () => target, change() {}, setDirtyCanvas() {} };
  const canvas = makeCanvas();
  app.canvas = canvas;
  const originalSetTimeout = globalThis.setTimeout;
  globalThis.setTimeout = () => 0;
  try {
    app.extension.setup();
    assert.equal(canvas.canvas.listenerCount("pointerup"), 1);
    assert.equal(canvas.linkConnector.events.listenerCount("before-drop-links"), 1);
  } finally {
    globalThis.setTimeout = originalSetTimeout;
  }
});

test("dropped-on-node writes a virtual IMAGE link and cancels native findInputByType", () => {
  const target = galleryTarget();
  const sourceNode = { id: 14, outputs: [{ name: "IMAGE", type: "IMAGE" }] };
  const canvas = makeCanvas();
  installDomForGallery(target);
  target.__ryanQwenGallery.dataset.qwenNodeId = "";
  app.canvas = canvas;
  app.graph = {
    getNodeById: () => null,
    change() {},
    setDirtyCanvas() {},
  };

  hooks.installQwenCanvasBridge();
  canvas.linkConnector.renderLinks = [{
    node: sourceNode,
    fromSlot: sourceNode.outputs[0],
    fromSlotIndex: 0,
    toType: "input",
    outputNode: sourceNode,
    outputSlot: sourceNode.outputs[0],
    outputIndex: 0,
  }];

  let cancelled = false;
  canvas.linkConnector.events.emit("dropped-on-node", {
    detail: {
      node: target,
      event: { button: 0, clientX: 20, clientY: 20 },
    },
    preventDefault() { cancelled = true; },
    stopPropagation() {},
    stopImmediatePropagation() {},
  });

  assert.equal(target.properties.ryan_qwen_image_links.length, 1);
  assert.equal(target.properties.ryan_qwen_image_links[0].source_id, "14");
  assert.equal(target.properties.ryan_qwen_image_links[0].slot, 2);
  assert.equal(cancelled, true);
});

test("pending output drop keeps Load Image when renderLinks only exposes fromSlotIndex", () => {
  const sourceNode = { id: 100, outputs: [{ type: "IMAGE" }] };
  const canvas = {
    linkConnector: {
      renderLinks: [{
        node: sourceNode,
        fromSlot: { type: "IMAGE" },
        fromSlotIndex: 0,
        toType: "input",
      }],
    },
  };

  const pending = hooks.qwenPendingConnectorLink(canvas);

  assert.equal(pending.direction, "from_output");
  assert.equal(pending.sourceNode, sourceNode);
  assert.equal(pending.sourceSlot, 0);
});

test("restoring hidden native image inputs preserves their saved LiteGraph links", () => {
  const node = {
    id: 201,
    properties: {},
    inputs: [
      { name: "prompt", link: null },
      { name: "image_01", link: 41 },
    ],
    _ryanQwenAllInputs: [
      { name: "clip", link: null },
      { name: "prompt", link: null },
      { name: "image_01", link: null },
      { name: "image_02", link: null },
    ],
  };

  hooks.restoreQwenImageInputs(node);

  assert.deepEqual(node.inputs.map((input) => input.name), ["clip", "prompt", "image_01", "image_02"]);
  assert.equal(node.inputs[2].link, 41);
});

test("native image inputs use the gallery green-port geometry for LinkConnector hit testing", () => {
  const node = {
    id: 202,
    pos: [0, 0],
    size: [430, 500],
    inputs: [{ name: "image_01", __ryanQwenSlotVisible: true }],
    getInputPos: () => [-100, -100],
  };
  const port = {
    getBoundingClientRect: () => ({ left: 30, top: 40, width: 10, height: 10 }),
  };
  const cell = { querySelector: () => port };
  node.__ryanQwenGallery = { querySelector: () => cell };
  app.canvas = {
    canvas: { getBoundingClientRect: () => ({ left: 10, top: 20 }) },
    ds: { scale: 2, offset: [3, 4] },
  };

  hooks.installSlotGeometry(node);

  assert.deepEqual(node.getInputPos(0), [9.5, 8.5]);
});

test("collapsed gallery inputs share the first green-port position instead of expanding node bounds", () => {
  const node = {
    id: 203,
    pos: [0, 0],
    size: [430, 500],
    inputs: [
      { name: "image_01", __ryanQwenSlotVisible: true },
      { name: "image_05", __ryanQwenSlotVisible: false },
    ],
    getInputPos: (slot) => [-12, 40 + slot * 20],
  };
  const port = {
    getBoundingClientRect: () => ({ left: 30, top: 40, width: 10, height: 10 }),
  };
  const cell = { querySelector: () => port };
  node.__ryanQwenGallery = { querySelector: () => cell };
  app.canvas = {
    canvas: { getBoundingClientRect: () => ({ left: 10, top: 20 }) },
    ds: { scale: 2, offset: [3, 4] },
  };

  hooks.installSlotGeometry(node);

  // LiteGraph includes every native input position when measuring node
  // bounds. Off-canvas coordinates create an enormous body height, while a
  // shared in-grid anchor keeps collapsed slots invisible and measurable.
  assert.deepEqual(node.getInputPos(1), [9.5, 8.5]);
});

test("serialized Qwen workbench state restores prompt, options, gallery, and virtual links", () => {
  const original = {
    properties: {
      ryan_qwen_image_links: [{ source_id: "66", source_slot: 0, source_type: "IMAGE", slot: 2, order: 2 }],
    },
    widgets: qwenWidgets({
      prompt: "a portrait @图片1",
      negative_prompt: "blur",
      aspect_ratio: "16:9",
      megapixels: 0.98,
      batch_size: 3,
      resolution: 1536,
      gallery_manifest: JSON.stringify([{ asset_id: "asset-a", slot: 1, filename: "a.png", path: { name: "a.png", type: "input" } }]),
      prompt_mentions: JSON.stringify([{ field: "prompt", display: "@图片1", asset_id: "asset-a", fallback_ordinal: 1 }]),
    }),
    __ryanQwenGalleryState: {
      gallery: [{ asset_id: "asset-a", slot: 1, filename: "a.png", path: { name: "a.png", type: "input" } }],
    },
    __ryanQwenGalleryExpanded: true,
  };
  hooks.persistQwenState(original);

  const restored = {
    properties: structuredClone(original.properties),
    widgets: qwenWidgets(),
    __ryanQwenGalleryState: { gallery: [] },
  };
  assert.equal(hooks.restoreQwenState(restored), true);

  const value = (name) => restored.widgets.find((widget) => widget.name === name).value;
  assert.equal(value("prompt"), "a portrait @图片1");
  assert.equal(value("negative_prompt"), "blur");
  assert.equal(value("aspect_ratio"), "16:9");
  assert.equal(value("megapixels"), 0.98);
  assert.equal(value("batch_size"), 3);
  assert.equal(value("resolution"), 1536);
  assert.match(value("gallery_manifest"), /asset-a/);
  assert.equal(restored.properties.ryan_qwen_image_links[0].slot, 2);
  assert.equal(restored.__ryanQwenGalleryExpanded, true);
});

test("workflow configure restores persisted workbench values after default normalization", async () => {
  const nodeType = {
    prototype: {
      configure(info) {
        this.properties = structuredClone(info.properties);
      },
    },
  };
  await app.extension.beforeRegisterNodeDef(nodeType, { name: "Ryan Qwen Image 2.1" });
  const saved = {
    ryan_qwen_image_links: [{ source_id: "55", source_slot: 0, source_type: "IMAGE", slot: 3, order: 3 }],
    ryan_qwen_image_state: {
      version: 1,
      prompt: "keep this prompt",
      negative_prompt: "keep this negative prompt",
      aspect_ratio: "3:2",
      megapixels: 0.98,
      batch_size: 2,
      resolution: 1536,
      gallery: [{ asset_id: "asset-b", slot: 1, filename: "b.png", path: { name: "b.png", type: "input" } }],
      prompt_mentions: [{ field: "prompt", display: "@图片1", asset_id: "asset-b", fallback_ordinal: 1 }],
      gallery_expanded: true,
    },
  };
  const node = Object.assign(Object.create(nodeType.prototype), {
    id: 301,
    __ryanQwenImage21Installed: true,
    inputs: [{ name: "prompt", link: null }],
    widgets: qwenWidgets({
      prompt: "default prompt",
      negative_prompt: "default negative prompt",
      aspect_ratio: "1:1",
      megapixels: 1.0,
      batch_size: 1,
      resolution: 1024,
    }),
    size: [430, 140],
    computeSize() { return [430, 140]; },
    setSize(size) { this.size = size; },
    setDirtyCanvas() {},
    __ryanQwenGalleryState: { gallery: [] },
  });
  app.graph = { change() {}, setDirtyCanvas() {} };
  node.configure({ properties: saved });

  const value = (name) => node.widgets.find((widget) => widget.name === name).value;
  assert.equal(value("prompt"), "keep this prompt");
  assert.equal(value("negative_prompt"), "keep this negative prompt");
  assert.equal(value("aspect_ratio"), "3:2");
  assert.equal(value("megapixels"), 0.98);
  assert.equal(value("batch_size"), 2);
  assert.equal(value("resolution"), 1536);
  assert.match(value("gallery_manifest"), /asset-b/);
  assert.equal(node.properties.ryan_qwen_image_links[0].slot, 3);
  assert.equal(node.__ryanQwenGalleryExpanded, true);
});

test("frontend repairs unhydrated controls to the requested new-node defaults", () => {
  const node = {
    widgets: qwenWidgets({
      aspect_ratio: "aspect_ratio",
      megapixels: "",
      batch_size: "",
      resolution: 1,
    }),
  };

  hooks.ensureQwenNumericDefaults(node);

  const value = (name) => node.widgets.find((widget) => widget.name === name).value;
  assert.equal(value("aspect_ratio"), "9:16 (Portrait Widescreen)");
  assert.equal(value("megapixels"), 2.0);
  assert.equal(value("batch_size"), 1);
  assert.equal(value("resolution"), 1024);
});

test("frontend repairs widget values written late by Vue hydration", () => {
  const node = { widgets: qwenWidgets(), setDirtyCanvas() {} };
  const originalSetTimeout = globalThis.setTimeout;
  const repairs = [];
  globalThis.setTimeout = (callback) => {
    repairs.push(callback);
    return repairs.length;
  };
  try {
    hooks.repairQwenWidgetValuesSoon(node);
    const value = (name) => node.widgets.find((widget) => widget.name === name);
    value("aspect_ratio").value = "aspect_ratio";
    value("megapixels").value = "";
    value("batch_size").value = "";
    value("resolution").value = 1;
    for (const repair of repairs) repair();
    assert.equal(value("aspect_ratio").value, "9:16 (Portrait Widescreen)");
    assert.equal(value("megapixels").value, 2.0);
    assert.equal(value("batch_size").value, 1);
    assert.equal(value("resolution").value, 1024);
  } finally {
    globalThis.setTimeout = originalSetTimeout;
  }
});

test("delayed widget repair preserves valid values restored from a workflow", () => {
  const node = {
    widgets: qwenWidgets({
      aspect_ratio: "3:2",
      megapixels: 0.98,
      batch_size: 2,
      resolution: 1536,
    }),
    setDirtyCanvas() {},
  };
  const originalSetTimeout = globalThis.setTimeout;
  const repairs = [];
  globalThis.setTimeout = (callback) => {
    repairs.push(callback);
    return repairs.length;
  };
  try {
    hooks.repairQwenWidgetValuesSoon(node);
    for (const repair of repairs) repair();
    const value = (name) => node.widgets.find((widget) => widget.name === name).value;
    assert.equal(value("aspect_ratio"), "3:2");
    assert.equal(value("megapixels"), 0.98);
    assert.equal(value("batch_size"), 2);
    assert.equal(value("resolution"), 1536);
  } finally {
    globalThis.setTimeout = originalSetTimeout;
  }
});

test("gallery visibility changes size once without scheduling another resize cycle", () => {
  const frames = [];
  globalThis.requestAnimationFrame = (callback) => {
    frames.push(callback);
    return frames.length;
  };
  const sizes = [];
  const node = {
    properties: {},
    inputs: [],
    size: [430, 500],
    computeSize: () => [430, node.__ryanQwenVisibleSlotCount === 4 ? 180 : 500],
    setSize: (size) => sizes.push(size),
  };
  app.graph = { change() {}, setDirtyCanvas() {} };

  hooks.updateGalleryVisibility(node);

  assert.equal(frames.length, 0);
  assert.deepEqual(sizes.at(-1), [430, 180]);
});

test("gallery backing widgets collapse to zero layout height", () => {
  const node = {
    widgets: [
      { name: "gallery_01", hidden: false, computeSize: () => [220, 120], options: {} },
      { name: "gallery_manifest", hidden: false, computeSize: () => [220, 80], options: {} },
      { name: "prompt_mentions", hidden: false, computeSize: () => [220, 80], options: {} },
      { name: "aspect_ratio", hidden: false, computeSize: () => [220, 20], options: {} },
    ],
  };

  hooks.compactQwenBackingWidgets(node);

  assert.equal(node.widgets[0].hidden, true);
  assert.deepEqual(node.widgets[0].computeSize(), [0, -4]);
  assert.equal(node.widgets[1].hidden, true);
  assert.deepEqual(node.widgets[1].computeSize(), [0, -4]);
  assert.equal(node.widgets[2].hidden, true);
  assert.equal(node.widgets[3].hidden, false);
  assert.deepEqual(node.widgets[3].computeSize(), [220, 20]);
});

test("arrange ignores gallery port coordinates so node height cannot ratchet", () => {
  const sizes = [];
  const node = {
    id: 204,
    pos: [100, 200],
    size: [430, 280],
    inputs: [
      { name: "clip" },
      { name: "image_01", __ryanQwenSlotVisible: true },
      { name: "image_05", __ryanQwenSlotVisible: false },
    ],
    _concreteInputs: [
      { name: "clip" },
      { name: "image_01", __ryanQwenSlotVisible: true },
      { name: "image_05", __ryanQwenSlotVisible: false },
    ],
    getInputPos(slot) {
      return [this.pos[0], this.pos[1] + 20 + slot * 800];
    },
    setSize(size) {
      this.size = size;
      sizes.push([...size]);
    },
    arrange() {
      // Mirrors LiteGraph: widgetStartY comes from every measured input's
      // getInputPos(), then the node grows if widgets land below bodyHeight.
      let maxY = this.pos[1];
      for (let index = 0; index < this.inputs.length; index += 1) {
        const pos = this.getInputPos(index);
        if (pos) maxY = Math.max(maxY, pos[1]);
      }
      const widgetStartY = maxY - this.pos[1] + 120;
      if (widgetStartY > this.size[1]) this.setSize([this.size[0], widgetStartY]);
    },
  };
  const port = {
    getBoundingClientRect: () => ({ left: 30, top: 900, width: 10, height: 10 }),
  };
  const cell = { querySelector: () => port };
  node.__ryanQwenGallery = { querySelector: () => cell };
  app.canvas = {
    canvas: { getBoundingClientRect: () => ({ left: 10, top: 20 }) },
    ds: { scale: 1, offset: [0, 0] },
  };

  hooks.installSlotGeometry(node);
  const before = node.size[1];
  node.arrange();
  node.arrange();
  node.arrange();

  assert.equal(node.size[1], before);
  assert.equal(sizes.length, 0);
  assert.deepEqual(node.getInputPos(1), [25, 885]);
});

test("gallery visibility pins image inputs off the default left column", () => {
  const node = {
    properties: {},
    size: [430, 280],
    inputs: [
      { name: "clip" },
      { name: "image_01" },
      { name: "image_05" },
    ],
    widgets: [],
    computeSize: () => [430, 280],
    setSize() {},
  };
  app.graph = { change() {}, setDirtyCanvas() {} };

  hooks.updateGalleryVisibility(node);

  assert.deepEqual(node.inputs[1].pos, [12, 28]);
  assert.equal(node.inputs[1].hidden, true);
  assert.deepEqual(node.inputs[2].pos, [12, 28]);
  assert.equal(node.inputs[0].pos, undefined);
});

test("native image links are written into graphToPrompt when ComfyUI omitted hidden slots", async () => {
  app.__ryanQwenGraphToPromptPatched = false;
  app.graphToPrompt = async () => ({ output: { 21: { inputs: { prompt: "" } } } });
  const sourceNode = { id: 12, widgets: [{ name: "image", value: "portrait.png" }] };
  const qwenNode = {
    id: 21,
    __ryanQwenImage21Installed: true,
    inputs: [{ name: "image_01", link: 7 }, { name: "prompt" }],
    widgets: qwenWidgets(),
    graph: {
      links: { 7: { origin_id: 12, origin_slot: 0 } },
      getNodeById: (id) => (Number(id) === 12 ? sourceNode : null),
    },
  };
  app.graph = { _nodes: [qwenNode], getNodeById: qwenNode.graph.getNodeById };

  hooks.patchQwenGraphToPrompt();
  const promptData = await app.graphToPrompt();

  assert.deepEqual(promptData.output["21"].inputs.image_01, ["12", 0]);
});

test("native image slot prompt refs prefer LiteGraph links over empty virtual links", () => {
  const node = {
    inputs: [{ name: "image_01", link: 3 }],
    properties: { ryan_qwen_image_links: [] },
    graph: { links: { 3: { origin_id: 88, origin_slot: 0 } } },
  };

  assert.deepEqual(hooks.qwenImageSlotPromptRef(node, 1), ["88", 0]);
});

test("Load Image widgets provide a gallery preview url for wired slots", () => {
  const sourceNode = {
    widgets: [{ name: "image", value: "portrait.png" }],
    imgs: [],
  };

  assert.match(hooks.qwenSourcePreviewUrl(sourceNode), /filename=portrait\.png/);
});

test("Load Image widget filename wins over a stale imgs preview", () => {
  const sourceNode = {
    widgets: [{ name: "image", value: "new.png" }],
    imgs: [{ src: "/view?filename=old.png" }],
  };

  assert.match(hooks.qwenSourcePreviewUrl(sourceNode), /filename=new\.png/);
  assert.doesNotMatch(hooks.qwenSourcePreviewUrl(sourceNode), /old\.png/);
});

test("watching a Load Image source refreshes the Qwen gallery after the file changes", () => {
  const renders = [];
  const target = {
    __ryanQwenRenderGallery: () => renders.push("render"),
    setDirtyCanvas() {},
  };
  const widget = { name: "image", value: "old.png" };
  const sourceNode = { widgets: [widget] };

  hooks.watchQwenImageSourceNode(sourceNode, target);
  widget.callback("new.png");

  assert.equal(renders.length, 1);
});

test("clearing a wired gallery slot disconnects the native image input", () => {
  const disconnected = [];
  const node = {
    properties: {
      ryan_qwen_image_links: [{ source_id: "12", source_slot: 0, source_type: "IMAGE", slot: 1, order: 1 }],
    },
    inputs: [{ name: "image_01", link: 9 }],
    widgets: [],
    __ryanQwenGalleryState: { gallery: [{ slot: 1, filename: "a.png", path: { name: "a.png" } }] },
    disconnectInput(index) {
      disconnected.push(index);
      this.inputs[index].link = null;
    },
    computeSize: () => [430, 180],
    setSize() {},
    setDirtyCanvas() {},
  };
  app.graph = { change() {}, setDirtyCanvas() {} };

  hooks.clearQwenImageSlot(node, 1);

  assert.deepEqual(disconnected, [0]);
  assert.equal(node.inputs[0].link, null);
  assert.equal(node.properties.ryan_qwen_image_links.length, 0);
  assert.equal(node.__ryanQwenGalleryState.gallery.length, 0);
});

test("clip vae and image inputs stay strictly typed", () => {
  const node = {
    inputs: [
      { name: "clip", type: "*" },
      { name: "vae", type: "*" },
      { name: "prompt", type: "*" },
      { name: "image_01", type: "*" },
    ],
  };

  hooks.ensureQwenTypedInputs(node);

  assert.equal(node.inputs[0].type, "CLIP");
  assert.equal(node.inputs[1].type, "VAE");
  assert.equal(node.inputs[2].type, "STRING");
  assert.equal(node.inputs[3].type, "IMAGE");
});

test("unresolved or sentinel image links do not mark a gallery slot as wired", () => {
  const node = {
    inputs: [{ name: "image_01", link: -1 }],
    properties: {},
  };
  app.graph = { links: {}, getNodeById: () => null };

  assert.equal(hooks.isExternalSlotConnected(node, 1), false);

  node.inputs[0].link = 99;
  assert.equal(hooks.isExternalSlotConnected(node, 1), false);

  node.inputs[0].link = null;
  node.properties.ryan_qwen_image_links = [{
    source_id: "12",
    source_slot: 0,
    source_type: "IMAGE",
    slot: 1,
    order: 1,
  }];
  assert.equal(hooks.isExternalSlotConnected(node, 1), false);

  app.graph.getNodeById = (id) => (Number(id) === 12 ? { id: 12 } : null);
  assert.equal(hooks.isExternalSlotConnected(node, 1), true);
});

test("pending gallery drop keeps the Load Image output when LinkConnector hovers a hidden image input", () => {
  const sourceNode = { id: 100, outputs: [{ type: "IMAGE" }] };
  const target = {
    id: 21,
    inputs: [{ name: "image_01" }],
  };
  const canvas = {
    connecting_node: sourceNode,
    connecting_output: sourceNode.outputs[0],
    linkConnector: {
      renderLinks: [{
        node: target,
        fromSlot: target.inputs[0],
        toType: "input",
      }],
    },
  };

  const pending = hooks.qwenPendingConnectorLink(canvas);

  assert.equal(pending.direction, "from_output");
  assert.equal(pending.sourceNode, sourceNode);
  assert.equal(pending.sourceSlot, 0);
});

