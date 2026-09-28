import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

const NODE_NAME = "Ryan Qwen Image 2.1";
const MAX_SLOTS = 16;
const DEFAULT_SLOT_COUNT = 2;
const SLOT_PREFIX = "image_";
const GALLERY_PREFIX = "gallery_";
const COUNT_WIDGET = "image_slot_count";

export function normalizeQwenSlotCount(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return DEFAULT_SLOT_COUNT;
  return Math.max(0, Math.min(MAX_SLOTS, Math.trunc(number)));
}

export function qwenImageSlotName(index) {
  return `${SLOT_PREFIX}${String(index).padStart(2, "0")}`;
}

export function qwenGallerySlotName(index) {
  return `${GALLERY_PREFIX}${String(index).padStart(2, "0")}`;
}

export function makeQwenAssetId() {
  if (globalThis.crypto?.randomUUID) return `gallery-${globalThis.crypto.randomUUID()}`;
  return `gallery-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function annotatedPathFromUpload(path) {
  if (!path || !path.name) return "";
  const subfolder = String(path.subfolder || "").replace(/^\/+|\/+$/g, "");
  const raw = subfolder ? `${subfolder}/${path.name}` : String(path.name);
  const type = path.type || "input";
  return type === "input" ? raw : `${raw} [type=${type}]`;
}

function findWidget(node, name) {
  return node.widgets?.find((widget) => widget.name === name);
}

function setWidgetValue(node, name, value) {
  const widget = findWidget(node, name);
  if (widget) widget.value = value;
}

function getManifest(node) {
  const value = findWidget(node, "gallery_manifest")?.value || "[]";
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed.filter((item) => item && typeof item === "object") : [];
  } catch (_error) {
    return [];
  }
}

function viewUrl(path) {
  if (!path?.name) return "";
  const query = new URLSearchParams({
    filename: path.name,
    subfolder: path.subfolder || "",
    type: path.type || "input",
  });
  return api.apiURL(`/view?${query.toString()}`);
}

function isExternalSlotConnected(node, slot) {
  const input = node._ryanQwenAllInputs?.find(
    (candidate) => candidate.name === qwenImageSlotName(slot),
  );
  return input?.link != null;
}

function updateGalleryHiddenWidgets(node, gallery) {
  for (let index = 1; index <= MAX_SLOTS; index += 1) {
    const asset = gallery[index - 1];
    setWidgetValue(node, qwenGallerySlotName(index), asset ? annotatedPathFromUpload(asset.path) : "");
  }
  setWidgetValue(node, "gallery_manifest", JSON.stringify(gallery));
}

function updateSlotVisibility(node, count) {
  const visibleCount = normalizeQwenSlotCount(count);
  if (!node._ryanQwenAllInputs) node._ryanQwenAllInputs = [...(node.inputs || [])];

  const visibleInputs = [];
  for (const input of node._ryanQwenAllInputs) {
    const match = input.name?.match(/^image_(\d+)$/);
    if (!match || Number(match[1]) <= visibleCount) visibleInputs.push(input);
  }
  node.inputs = visibleInputs;
  const countWidget = findWidget(node, COUNT_WIDGET);
  if (countWidget) countWidget.value = visibleCount;
  node.setSize?.(node.computeSize?.());
  app.graph?.setDirtyCanvas?.(true, true);
}

async function uploadImage(file) {
  const form = new FormData();
  form.append("image", file, file.name);
  form.append("type", "input");
  const response = await api.fetchApi("/upload/image", {
    method: "POST",
    body: form,
  });
  let data = null;
  try {
    data = await response.json();
  } catch (_error) {
    data = null;
  }
  if (!response.ok || !data?.name) {
    throw new Error(data?.error || `Image upload failed: HTTP ${response.status}`);
  }
  return {
    name: data.name,
    subfolder: data.subfolder || "",
    type: data.type || "input",
  };
}

function swapGalleryItems(gallery, from, to) {
  if (from === to || from < 0 || to < 0 || from >= gallery.length || to >= gallery.length) return;
  const [item] = gallery.splice(from, 1);
  gallery.splice(to, 0, item);
}

function createGalleryElement(node) {
  if (typeof document === "undefined") return null;
  const root = document.createElement("div");
  root.className = "ryan-qwen-image-gallery";
  root.style.cssText = "display:flex;flex-direction:column;gap:6px;padding:4px 0;min-height:48px;";

  const toolbar = document.createElement("div");
  toolbar.style.cssText = "display:flex;gap:6px;align-items:center;";
  const addButton = document.createElement("button");
  addButton.type = "button";
  addButton.textContent = "上传参考图";
  const fileInput = document.createElement("input");
  fileInput.type = "file";
  fileInput.accept = "image/*";
  fileInput.multiple = true;
  fileInput.style.display = "none";
  const hint = document.createElement("span");
  hint.textContent = "拖拽图片到这里，可排序";
  hint.style.cssText = "opacity:.65;font-size:11px;";
  toolbar.append(addButton, fileInput, hint);
  root.append(toolbar);

  const grid = document.createElement("div");
  grid.style.cssText = "display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:4px;";
  root.append(grid);

  const state = { gallery: getManifest(node), dragIndex: -1 };
  node.__ryanQwenGalleryState = state;

  const sync = () => {
    updateGalleryHiddenWidgets(node, state.gallery);
    render();
    node.setDirtyCanvas?.(true, true);
  };

  const addFiles = async (files) => {
    const remaining = MAX_SLOTS - state.gallery.length;
    for (const file of [...files].slice(0, remaining)) {
      try {
        const path = await uploadImage(file);
        state.gallery.push({
          asset_id: makeQwenAssetId(),
          slot: state.gallery.length + 1,
          filename: file.name,
          path,
        });
      } catch (error) {
        node.__ryanQwenLastUploadError = String(error?.message || error);
      }
    }
    state.gallery.forEach((item, index) => { item.slot = index + 1; });
    sync();
  };

  addButton.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => {
    if (fileInput.files?.length) void addFiles(fileInput.files);
    fileInput.value = "";
  });
  root.addEventListener("dragover", (event) => {
    event.preventDefault();
    root.style.outline = "1px dashed var(--fg-color)";
  });
  root.addEventListener("dragleave", () => { root.style.outline = ""; });
  root.addEventListener("drop", (event) => {
    event.preventDefault();
    root.style.outline = "";
    if (event.dataTransfer?.files?.length) void addFiles(event.dataTransfer.files);
  });

  function render() {
    grid.replaceChildren();
    state.gallery.forEach((item, index) => {
      const card = document.createElement("div");
      const slot = index + 1;
      const externallyConnected = isExternalSlotConnected(node, slot);
      card.draggable = true;
      card.style.cssText = "position:relative;min-height:60px;border:1px solid var(--border-color);border-radius:4px;overflow:hidden;cursor:grab;";
      card.title = externallyConnected
        ? `外部 IMAGE 已占用槽位 ${slot}`
        : `${item.filename || "参考图"} · @图片${slot}`;
      card.addEventListener("dragstart", () => { state.dragIndex = index; });
      card.addEventListener("dragover", (event) => event.preventDefault());
      card.addEventListener("drop", (event) => {
        event.preventDefault();
        swapGalleryItems(state.gallery, state.dragIndex, index);
        state.gallery.forEach((asset, position) => { asset.slot = position + 1; });
        state.dragIndex = -1;
        sync();
      });

      const image = document.createElement("img");
      image.src = viewUrl(item.path);
      image.alt = item.filename || `图片${index + 1}`;
      image.style.cssText = "display:block;width:100%;height:58px;object-fit:cover;";
      const label = document.createElement("span");
      label.textContent = externallyConnected ? `外部输入 ${slot}` : `@图片${slot}`;
      label.style.cssText = "position:absolute;left:2px;bottom:2px;background:rgba(0,0,0,.65);color:white;font-size:10px;padding:1px 3px;";
      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "×";
      remove.title = "删除图片";
      remove.disabled = externallyConnected;
      remove.style.cssText = "position:absolute;right:1px;top:1px;padding:0 4px;line-height:16px;";
      remove.addEventListener("click", () => {
        if (externallyConnected) return;
        state.gallery.splice(index, 1);
        state.gallery.forEach((asset, position) => { asset.slot = position + 1; });
        sync();
      });
      card.append(image, label, remove);
      grid.append(card);
    });
  }

  render();
  return root;
}

function setupNode(node) {
  if (node.__ryanQwenImage21Installed) return;
  node.__ryanQwenImage21Installed = true;
  if (!node._ryanQwenAllInputs) node._ryanQwenAllInputs = [...(node.inputs || [])];

  const countWidget = findWidget(node, COUNT_WIDGET);
  if (countWidget) {
    const originalCallback = countWidget.callback;
    countWidget.callback = (value) => {
      originalCallback?.(value);
      updateSlotVisibility(node, value);
    };
  }

  node.addWidget("button", "更新图片槽位", null, () => {
    updateSlotVisibility(node, findWidget(node, COUNT_WIDGET)?.value ?? DEFAULT_SLOT_COUNT);
  });
  updateSlotVisibility(node, countWidget?.value ?? DEFAULT_SLOT_COUNT);

  if (typeof node.addDOMWidget === "function" && typeof document !== "undefined") {
    const gallery = createGalleryElement(node);
    if (gallery) {
      node.addDOMWidget("ryan_qwen_image21_gallery", "gallery", gallery, {
        serialize: false,
        hideOnZoom: false,
      });
    }
  }
}

app.registerExtension({
  name: "RyanComfyUtils.QwenImage21",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_NAME) return;

    const originalCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function onNodeCreatedQwenImage21() {
      originalCreated?.apply(this, arguments);
      setupNode(this);
    };

    const originalConfigure = nodeType.prototype.configure;
    nodeType.prototype.configure = function configureQwenImage21(info) {
      if (this._ryanQwenAllInputs) this.inputs = [...this._ryanQwenAllInputs];
    const result = originalConfigure?.apply(this, arguments);
      if (this.inputs && this._ryanQwenAllInputs) {
        for (const input of this.inputs) {
          const backup = this._ryanQwenAllInputs.find((candidate) => candidate.name === input.name);
          if (backup) backup.link = input.link;
        }
      }
      if (!this.__ryanQwenImage21Installed) setupNode(this);
      updateSlotVisibility(this, findWidget(this, COUNT_WIDGET)?.value ?? DEFAULT_SLOT_COUNT);
      return result;
    };
  },
});
