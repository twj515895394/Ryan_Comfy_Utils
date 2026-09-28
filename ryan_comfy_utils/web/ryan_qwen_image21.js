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

function getMentionManifest(node) {
  const value = findWidget(node, "prompt_mentions")?.value || "[]";
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

function activeMentionOptions(node) {
  const gallery = getManifest(node);
  const options = [];
  for (let slot = 1; slot <= MAX_SLOTS; slot += 1) {
    if (isExternalSlotConnected(node, slot)) {
      options.push({
        asset_id: `external-slot-${String(slot).padStart(2, "0")}`,
        slot,
        ordinal: options.length + 1,
        filename: `外部输入 ${qwenImageSlotName(slot)}`,
        source: "external",
      });
      continue;
    }
    const item = gallery[slot - 1];
    if (item) {
      options.push({
        asset_id: item.asset_id,
        slot,
        ordinal: options.length + 1,
        filename: item.filename || `图片${options.length + 1}`,
        path: item.path,
        source: "gallery",
      });
    }
  }
  return options.map((option) => ({
    ...option,
    display: `@图片${option.ordinal}`,
  }));
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
    node.__ryanQwenRefreshMentions?.();
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

function createPromptEditor(node, field) {
  if (typeof document === "undefined") return null;
  const widget = findWidget(node, field);
  if (!widget) return null;
  widget.hidden = true;
  widget.computeSize = () => [0, -4];

  const wrapper = document.createElement("div");
  wrapper.className = `ryan-qwen-${field}-editor`;
  wrapper.style.cssText = "position:relative;display:flex;flex-direction:column;gap:4px;padding:4px 0;";
  const editor = document.createElement("div");
  editor.contentEditable = "true";
  editor.spellcheck = true;
  editor.style.cssText = "min-height:56px;max-height:150px;overflow:auto;padding:6px;border:1px solid var(--border-color);border-radius:4px;background:var(--comfy-input-bg);white-space:pre-wrap;line-height:1.35;";
  const menu = document.createElement("div");
  menu.hidden = true;
  menu.style.cssText = "position:absolute;left:4px;right:4px;top:100%;z-index:30;display:flex;flex-direction:column;gap:2px;padding:4px;background:var(--comfy-menu-bg,#222);border:1px solid var(--border-color);border-radius:4px;max-height:180px;overflow:auto;";
  wrapper.append(editor, menu);

  const state = { triggerRange: null, usedManifest: new Set() };

  function serializeEditor() {
    return [...editor.childNodes].map((child) => {
      if (child.nodeType === Node.ELEMENT_NODE && child.classList.contains("ryan-qwen-mention")) {
        return child.dataset.display || child.textContent || "";
      }
      return child.textContent || "";
    }).join("");
  }

  function updateMentionManifest() {
    const existing = getMentionManifest(node).filter(
      (item) => (item.field || item.prompt || "positive") !== field,
    );
    const mentions = [...editor.querySelectorAll(".ryan-qwen-mention")].map((chip) => ({
      field,
      display: chip.dataset.display || chip.textContent || "",
      asset_id: chip.dataset.assetId || "",
      fallback_ordinal: Number(chip.dataset.ordinal || 0),
    }));
    setWidgetValue(node, field, serializeEditor());
    setWidgetValue(node, "prompt_mentions", JSON.stringify([...existing, ...mentions]));
  }

  function makeChip(display, option, assetId = "") {
    const chip = document.createElement("span");
    chip.className = "ryan-qwen-mention";
    chip.contentEditable = "false";
    chip.dataset.display = display;
    chip.dataset.assetId = assetId || option?.asset_id || "";
    chip.dataset.ordinal = String(option?.ordinal || 0);
    chip.textContent = display;
    chip.style.cssText = "display:inline-block;margin:0 2px;padding:1px 5px;border-radius:10px;background:#405b75;color:#fff;font-size:.9em;user-select:all;";
    return chip;
  }

  function renderValue() {
    const value = String(widget.value || "");
    const mentionManifest = getMentionManifest(node).filter(
      (item) => (item.field || item.prompt || "positive") === field,
    );
    const options = activeMentionOptions(node);
    const byAsset = new Map(options.map((option) => [option.asset_id, option]));
    const used = new Set();
    editor.replaceChildren();
    let cursor = 0;
    for (const match of value.matchAll(/@(?:图片|image)(\d+)/g)) {
      const start = match.index ?? 0;
      if (start > cursor) editor.append(document.createTextNode(value.slice(cursor, start)));
      const token = match[0];
      const saved = mentionManifest.find((item, index) => (
        !used.has(index) && (item.display || token) === token
      ));
      if (saved) used.add(mentionManifest.indexOf(saved));
      const option = saved?.asset_id ? byAsset.get(saved.asset_id) : options[Number(match[1]) - 1];
      const display = option?.display || token;
      editor.append(makeChip(display, option, saved?.asset_id || option?.asset_id || ""));
      cursor = start + token.length;
    }
    if (cursor < value.length) editor.append(document.createTextNode(value.slice(cursor)));
    widget.value = serializeEditor();
  }

  function closeMenu() {
    menu.hidden = true;
    state.triggerRange = null;
  }

  function openMenu() {
    const options = activeMentionOptions(node);
    menu.replaceChildren();
    if (!options.length) {
      const empty = document.createElement("span");
      empty.textContent = "当前没有可引用的图片";
      empty.style.opacity = "0.7";
      menu.append(empty);
    }
    for (const option of options) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = `${option.display}  ${option.filename}`;
      button.style.cssText = "text-align:left;padding:4px 6px;background:transparent;color:inherit;border:0;cursor:pointer;";
      button.addEventListener("mousedown", (event) => event.preventDefault());
      button.addEventListener("click", () => insertMention(option));
      menu.append(button);
    }
    menu.hidden = false;
    const selection = window.getSelection();
    state.triggerRange = selection?.rangeCount ? selection.getRangeAt(0).cloneRange() : null;
  }

  function insertMention(option) {
    editor.focus();
    const selection = window.getSelection();
    const range = state.triggerRange || (selection?.rangeCount ? selection.getRangeAt(0) : null);
    if (!range) return closeMenu();
    const insertion = range.cloneRange();
    const container = insertion.startContainer;
    const offset = insertion.startOffset;
    if (container.nodeType === Node.TEXT_NODE && offset > 0 && container.textContent[offset - 1] === "@") {
      insertion.setStart(container, offset - 1);
      insertion.deleteContents();
    }
    insertion.collapse(true);
    const chip = makeChip(option.display, option);
    insertion.insertNode(chip);
    const spacer = document.createTextNode(" ");
    chip.after(spacer);
    const caret = document.createRange();
    caret.setStart(spacer, 1);
    caret.collapse(true);
    selection.removeAllRanges();
    selection.addRange(caret);
    updateMentionManifest();
    closeMenu();
  }

  editor.addEventListener("input", () => {
    updateMentionManifest();
    const selection = window.getSelection();
    const container = selection?.rangeCount ? selection.getRangeAt(0).startContainer : null;
    if (container?.nodeType === Node.TEXT_NODE && container.textContent.slice(0, selection.getRangeAt(0).startOffset).endsWith("@")) {
      openMenu();
    }
  });
  editor.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMenu();
  });
  editor.addEventListener("blur", () => {
    window.setTimeout(closeMenu, 100);
  });

  const refresh = () => renderValue();
  refresh();
  return { element: wrapper, refresh };
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
    const promptEditors = ["prompt", "negative_prompt"]
      .map((field) => createPromptEditor(node, field))
      .filter(Boolean);
    for (const editor of promptEditors) {
      node.addDOMWidget(`ryan_qwen_${editor.element.className}`, "prompt", editor.element, {
        serialize: false,
        hideOnZoom: false,
      });
    }
    node.__ryanQwenRefreshMentions = () => promptEditors.forEach((editor) => editor.refresh());
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
      this.__ryanQwenRefreshMentions?.();
      updateSlotVisibility(this, findWidget(this, COUNT_WIDGET)?.value ?? DEFAULT_SLOT_COUNT);
      return result;
    };
  },
});
