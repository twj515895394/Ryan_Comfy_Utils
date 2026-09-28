import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

const NODE_NAME = "Ryan Qwen Image 2.1";
const MAX_SLOTS = 16;
const DEFAULT_SLOT_COUNT = 2;
const SLOT_PREFIX = "image_";
const GALLERY_PREFIX = "gallery_";
const COUNT_WIDGET = "image_slot_count";
const SLOT_REORDER_MIME = "application/x-ryan-qwen-image-reorder";

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
  if (!widget) return;
  widget.value = value;
  if (widget._state) widget._state.value = value;
}

function getManifest(node) {
  const value = findWidget(node, "gallery_manifest")?.value || "[]";
  let parsed;
  try {
    parsed = JSON.parse(value);
  } catch (_error) {
    parsed = [];
  }
  if (!Array.isArray(parsed)) return [];
  const usedSlots = new Set();
  return parsed
    .filter((item) => item && typeof item === "object")
    .map((item, index) => {
      const rawSlot = Number(item.slot ?? item.source_slot ?? index + 1);
      const slot = Number.isInteger(rawSlot) && rawSlot >= 1 && rawSlot <= MAX_SLOTS
        ? rawSlot
        : index + 1;
      return {
        ...item,
        slot,
        asset_id: String(item.asset_id || makeQwenAssetId()),
      };
    })
    .filter((item) => {
      if (usedSlots.has(item.slot)) return false;
      usedSlots.add(item.slot);
      return true;
    })
    .sort((left, right) => left.slot - right.slot);
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

function galleryAssetAtSlot(gallery, slot) {
  return gallery.find((item) => Number(item?.slot) === Number(slot)) || null;
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

function isQwenImageInput(input) {
  return /^image_\d+$/.test(String(input?.name || ""));
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
    const item = galleryAssetAtSlot(gallery, slot);
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
    const asset = galleryAssetAtSlot(gallery, index);
    setWidgetValue(node, qwenGallerySlotName(index), asset ? annotatedPathFromUpload(asset.path) : "");
  }
  setWidgetValue(node, "gallery_manifest", JSON.stringify(
    gallery.slice().sort((left, right) => left.slot - right.slot),
  ));
}

function activeSlotCount(node) {
  return normalizeQwenSlotCount(findWidget(node, COUNT_WIDGET)?.value ?? DEFAULT_SLOT_COUNT);
}

function updateSlotVisibility(node, count) {
  const visibleCount = normalizeQwenSlotCount(count);
  if (!node._ryanQwenAllInputs) node._ryanQwenAllInputs = [...(node.inputs || [])];
  node.inputs = node._ryanQwenAllInputs;
  for (const input of node.inputs) {
    if (!isQwenImageInput(input)) continue;
    // The real input remains in the graph for serialization and external wires,
    // but its visual socket is rendered inside the H3-style image cell.
    input.hidden = true;
    input.type = "IMAGE";
    input.__ryanQwenSlotVisible = Number(input.name.slice(6)) <= visibleCount;
  }
  const countWidget = findWidget(node, COUNT_WIDGET);
  if (countWidget) countWidget.value = visibleCount;
  node.__ryanQwenVisibleSlotCount = visibleCount;
  node.__ryanQwenRenderGallery?.();
  node._widgetSlotsDirty = true;
  node.setSize?.(node.computeSize?.());
  app.graph?.setDirtyCanvas?.(true, true);
}

async function uploadImage(file) {
  const form = new FormData();
  form.append("image", file, file.name || "qwen_reference.png");
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

function normalizeGalleryForState(gallery) {
  const usedSlots = new Set();
  return gallery
    .filter((item) => item && typeof item === "object")
    .map((item, index) => ({
      ...item,
      slot: Number(item.slot) || index + 1,
      asset_id: String(item.asset_id || makeQwenAssetId()),
    }))
    .filter((item) => {
      if (item.slot < 1 || item.slot > MAX_SLOTS || usedSlots.has(item.slot)) return false;
      usedSlots.add(item.slot);
      return true;
    })
    .sort((left, right) => left.slot - right.slot);
}

function swapGalleryItems(gallery, from, to) {
  if (from === to || from < 1 || to < 1 || from > MAX_SLOTS || to > MAX_SLOTS) return;
  const source = galleryAssetAtSlot(gallery, from);
  const target = galleryAssetAtSlot(gallery, to);
  if (!source) return;
  if (target) {
    source.slot = to;
    target.slot = from;
  } else {
    source.slot = to;
  }
  gallery.sort((left, right) => left.slot - right.slot);
}

function clientToGraph(canvas, clientX, clientY) {
  const rect = canvas?.canvas?.getBoundingClientRect?.();
  if (!rect || !Number.isFinite(clientX) || !Number.isFinite(clientY)) return null;
  const scale = canvas?.ds?.scale || 1;
  const offset = canvas?.ds?.offset || [0, 0];
  return [(clientX - rect.left) / scale - offset[0], (clientY - rect.top) / scale - offset[1]];
}

function galleryCell(node, slot) {
  return node.__ryanQwenGallery?.querySelector?.(`[data-qwen-slot="${slot}"]`) || null;
}

function galleryCellGraphPos(node, slot) {
  const cell = galleryCell(node, slot);
  const port = cell?.querySelector?.(".ryan-qwen-image-slot-port");
  const element = port || cell;
  if (!element) return null;
  const rect = element.getBoundingClientRect();
  if (!rect.width && !rect.height) return null;
  return clientToGraph(app.canvas, rect.left + rect.width * 0.5, rect.top + rect.height * 0.5);
}

function gallerySlotHit(node, x, y) {
  const count = activeSlotCount(node);
  for (let slot = 1; slot <= count; slot += 1) {
    const cell = galleryCell(node, slot);
    if (!cell || cell.classList.contains("is-disabled")) continue;
    const rect = cell.getBoundingClientRect();
    if (!rect.width && !rect.height) continue;
    const topLeft = clientToGraph(app.canvas, rect.left, rect.top);
    const bottomRight = clientToGraph(app.canvas, rect.right, rect.bottom);
    if (!topLeft || !bottomRight) continue;
    if (x >= topLeft[0] - 10 && x <= bottomRight[0] && y >= topLeft[1] && y <= bottomRight[1]) return slot;
  }
  return null;
}

function installSlotGeometry(node) {
  if (!node || node.__ryanQwenSlotGeometryInstalled) return;
  node.__ryanQwenSlotGeometryInstalled = true;
  const originalGetConnectionPos = node.getConnectionPos;
  node.getConnectionPos = function getConnectionPosQwen(isInput, slot, out) {
    if (isInput) {
      const input = this.inputs?.[slot];
      if (isQwenImageInput(input) && input.__ryanQwenSlotVisible) {
        const graph = galleryCellGraphPos(this, Number(input.name.slice(6)));
        if (graph) {
          const point = out || [0, 0];
          point[0] = graph[0];
          point[1] = graph[1];
          return point;
        }
      }
    }
    return originalGetConnectionPos?.apply(this, arguments);
  };
  const originalGetInputPos = node.getInputPos;
  if (typeof originalGetInputPos === "function") {
    node.getInputPos = function getInputPosQwen(slot) {
      const input = this.inputs?.[slot];
      if (isQwenImageInput(input) && input.__ryanQwenSlotVisible) {
        const graph = galleryCellGraphPos(this, Number(input.name.slice(6)));
        if (graph) return graph;
      }
      return originalGetInputPos.apply(this, arguments);
    };
  }
  const originalGetSlotInPosition = node.getSlotInPosition;
  if (typeof originalGetSlotInPosition === "function") {
    node.getSlotInPosition = function getSlotInPositionQwen(x, y) {
      const slot = gallerySlotHit(this, x, y);
      if (slot) {
        const index = this.inputs?.findIndex?.((input) => input.name === qwenImageSlotName(slot)) ?? -1;
        if (index >= 0) {
          return {
            input: true,
            slot: index,
            link_pos: galleryCellGraphPos(this, slot) || [x, y],
          };
        }
      }
      return originalGetSlotInPosition.apply(this, arguments);
    };
  }
  const originalComputeSize = node.computeSize;
  if (typeof originalComputeSize === "function") {
    node.computeSize = function computeSizeWithoutQwenImageInputs(out) {
      const originalInputs = this.inputs;
      this.inputs = (originalInputs || []).filter((input) => !isQwenImageInput(input));
      try {
        return originalComputeSize.apply(this, arguments);
      } finally {
        this.inputs = originalInputs;
      }
    };
  }
}

function chooseImageFile(node, slot) {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "image/*";
  input.style.display = "none";
  input.addEventListener("change", () => {
    const file = input.files?.[0];
    input.remove();
    if (file) void uploadIntoSlot(node, slot, file);
  }, { once: true });
  document.body.append(input);
  input.click();
}

async function uploadIntoSlot(node, slot, file) {
  if (isExternalSlotConnected(node, slot)) return;
  const state = node.__ryanQwenGalleryState;
  if (!state) return;
  const cell = galleryCell(node, slot);
  cell?.classList.add("is-uploading");
  try {
    const path = await uploadImage(file);
    state.gallery = normalizeGalleryForState([
      ...state.gallery.filter((item) => item.slot !== slot),
      {
        asset_id: makeQwenAssetId(),
        slot,
        filename: file.name,
        path,
      },
    ]);
    state.sync();
  } catch (error) {
    node.__ryanQwenLastUploadError = String(error?.message || error);
  } finally {
    galleryCell(node, slot)?.classList.remove("is-uploading");
  }
}

function firstFreeSlot(node, gallery) {
  const count = activeSlotCount(node);
  for (let slot = 1; slot <= count; slot += 1) {
    if (!isExternalSlotConnected(node, slot) && !galleryAssetAtSlot(gallery, slot)) return slot;
  }
  return 0;
}

function createImageSlot(node, state, slot) {
  const cell = document.createElement("div");
  cell.className = "ryan-qwen-image-slot";
  cell.dataset.qwenSlot = String(slot);
  cell.tabIndex = 0;
  cell.setAttribute("role", "button");
  cell.addEventListener("pointerdown", (event) => event.stopPropagation());
  cell.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (cell.classList.contains("is-disabled") || cell.classList.contains("is-wired") || cell.classList.contains("is-uploading")) return;
    if (Date.now() < (cell.__qwenSuppressClickUntil || 0)) return;
    chooseImageFile(node, slot);
  });
  cell.addEventListener("keydown", (event) => {
    if (!["Enter", " "].includes(event.key)) return;
    event.preventDefault();
    event.stopPropagation();
    if (!cell.classList.contains("is-disabled") && !cell.classList.contains("is-wired")) chooseImageFile(node, slot);
  });
  cell.addEventListener("dragstart", (event) => {
    const item = galleryAssetAtSlot(state.gallery, slot);
    if (!item || cell.classList.contains("is-wired") || cell.classList.contains("is-disabled")) {
      event.preventDefault();
      return;
    }
    cell.__qwenSuppressClickUntil = Date.now() + 350;
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData(SLOT_REORDER_MIME, JSON.stringify({ node_id: String(node.id ?? ""), slot }));
    cell.classList.add("is-reordering");
  });
  cell.addEventListener("dragend", () => {
    node.__ryanQwenGallery?.querySelectorAll?.(".is-reordering, .is-reorder-target, .is-dragover")
      .forEach((element) => element.classList.remove("is-reordering", "is-reorder-target", "is-dragover"));
  });
  cell.addEventListener("dragover", (event) => {
    if (cell.classList.contains("is-disabled") || cell.classList.contains("is-wired")) return;
    const payload = event.dataTransfer?.getData(SLOT_REORDER_MIME);
    event.preventDefault();
    event.stopPropagation();
    if (payload) {
      try {
        const data = JSON.parse(payload);
        if (data.node_id === String(node.id ?? "") && Number(data.slot) !== slot) cell.classList.add("is-reorder-target");
      } catch (_error) { /* It is a file drag, not an internal reorder. */ }
      return;
    }
    cell.classList.add("is-dragover");
  });
  cell.addEventListener("dragleave", () => cell.classList.remove("is-dragover", "is-reorder-target"));
  cell.addEventListener("drop", (event) => {
    cell.classList.remove("is-dragover", "is-reorder-target");
    if (cell.classList.contains("is-disabled") || cell.classList.contains("is-wired")) return;
    event.preventDefault();
    event.stopPropagation();
    const payload = event.dataTransfer?.getData(SLOT_REORDER_MIME);
    if (payload) {
      try {
        const data = JSON.parse(payload);
        if (data.node_id === String(node.id ?? "")) {
          swapGalleryItems(state.gallery, Number(data.slot), slot);
          state.sync();
        }
      } catch (_error) { /* Ignore malformed drag metadata. */ }
      return;
    }
    const file = event.dataTransfer?.files?.[0];
    if (file) void uploadIntoSlot(node, slot, file);
  });
  return cell;
}

function renderImageGallery(node) {
  const root = node.__ryanQwenGallery;
  const state = node.__ryanQwenGalleryState;
  if (!root || !state) return;
  const count = activeSlotCount(node);
  root.dataset.slotCount = String(count);
  const heading = root.querySelector(".ryan-qwen-image-heading");
  if (heading) heading.textContent = `参考图片 - ${count}`;
  for (let slot = 1; slot <= MAX_SLOTS; slot += 1) {
    const cell = galleryCell(node, slot);
    if (!cell) continue;
    const active = slot <= count;
    const externallyConnected = active && isExternalSlotConnected(node, slot);
    const wired = externallyConnected;
    const item = active ? galleryAssetAtSlot(state.gallery, slot) : null;
    const hasImage = Boolean(wired || item);
    cell.hidden = !active;
    cell.classList.toggle("is-disabled", !active);
    cell.classList.toggle("is-wired", wired);
    cell.classList.toggle("has-image", hasImage);
    cell.draggable = true;
    if (!item || wired) cell.draggable = false;
    cell.replaceChildren();

    if (item?.path) {
      const preview = document.createElement("img");
      preview.className = "ryan-qwen-image-preview";
      preview.alt = "";
      preview.draggable = false;
      preview.src = viewUrl(item.path);
      cell.append(preview);
    }

    const badge = document.createElement("span");
    badge.className = "ryan-qwen-image-slot-badge";
    badge.textContent = String(slot);
    const port = document.createElement("span");
    port.className = "ryan-qwen-image-slot-port";
    port.title = "外部 IMAGE 输入";
    port.addEventListener("pointerdown", (event) => event.stopPropagation());
    const status = document.createElement("span");
    status.className = "ryan-qwen-image-slot-status";
    status.textContent = wired
      ? `外部输入 ${qwenImageSlotName(slot)}`
      : item?.filename || "点击添加图片";
    cell.append(badge, port, status);

    if (hasImage) {
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "ryan-qwen-image-slot-clear";
      remove.textContent = "×";
      remove.title = "移除图片";
      remove.disabled = wired;
      remove.addEventListener("pointerdown", (event) => {
        event.preventDefault();
        event.stopPropagation();
      });
      remove.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        if (wired) return;
        state.gallery = state.gallery.filter((asset) => asset.slot !== slot);
        state.sync();
      });
      cell.append(remove);
    }
  }
  node._widgetSlotsDirty = true;
  node.setDirtyCanvas?.(true, true);
}

function createImageGallery(node) {
  if (typeof document === "undefined") return null;
  const root = document.createElement("section");
  root.className = "ryan-qwen-image-gallery";
  const heading = document.createElement("div");
  heading.className = "ryan-qwen-image-heading";
  const grid = document.createElement("div");
  grid.className = "ryan-qwen-image-grid";
  const state = {
    gallery: getManifest(node),
    sync() {
      this.gallery = normalizeGalleryForState(this.gallery);
      updateGalleryHiddenWidgets(node, this.gallery);
      renderImageGallery(node);
      node.__ryanQwenRefreshMentions?.();
      app.graph?.change?.();
      node.setDirtyCanvas?.(true, true);
    },
  };
  node.__ryanQwenGalleryState = state;
  for (let slot = 1; slot <= MAX_SLOTS; slot += 1) grid.append(createImageSlot(node, state, slot));
  root.append(heading, grid);
  root.addEventListener("dragover", (event) => {
    if (event.dataTransfer?.types?.includes?.(SLOT_REORDER_MIME)) return;
    event.preventDefault();
  });
  root.addEventListener("drop", (event) => {
    if (!event.dataTransfer?.files?.length) return;
    event.preventDefault();
    let slot = firstFreeSlot(node, state.gallery);
    for (const file of [...event.dataTransfer.files]) {
      if (!slot) break;
      void uploadIntoSlot(node, slot, file);
      state.gallery.push({ asset_id: makeQwenAssetId(), slot, filename: file.name, path: null });
      slot = firstFreeSlot(node, state.gallery);
    }
  });
  node.__ryanQwenGallery = root;
  node.__ryanQwenRenderGallery = () => renderImageGallery(node);
  renderImageGallery(node);
  return root;
}

function createPromptEditor(node, field, label, minHeight) {
  if (typeof document === "undefined") return null;
  const widget = findWidget(node, field);
  if (!widget) return null;
  widget.hidden = true;
  widget.computeSize = () => [0, -4];

  const wrapper = document.createElement("section");
  wrapper.className = `ryan-qwen-prompt-wrap ryan-qwen-${field}-wrap`;
  wrapper.style.setProperty("--ryan-qwen-prompt-min-height", `${minHeight}px`);
  const heading = document.createElement("div");
  heading.className = "ryan-qwen-prompt-heading";
  heading.textContent = label;
  const editor = document.createElement("div");
  editor.className = "ryan-qwen-prompt-editor";
  editor.contentEditable = "true";
  editor.spellcheck = true;
  editor.dataset.placeholder = field === "prompt" ? "Prompt..." : "Negative Prompt...";
  const menu = document.createElement("div");
  menu.className = "ryan-qwen-mention-menu";
  menu.hidden = true;
  wrapper.append(heading, editor, menu);

  const state = { triggerRange: null };

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
    return chip;
  }

  function renderValue() {
    const value = String(widget.value || "");
    const savedMentions = getMentionManifest(node).filter(
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
      const savedIndex = savedMentions.findIndex((item, index) => !used.has(index) && (item.display || token) === token);
      const saved = savedIndex >= 0 ? savedMentions[savedIndex] : null;
      if (savedIndex >= 0) used.add(savedIndex);
      const option = saved?.asset_id ? byAsset.get(saved.asset_id) : options[Number(match[1]) - 1];
      editor.append(makeChip(option?.display || token, option, saved?.asset_id || option?.asset_id || ""));
      cursor = start + token.length;
    }
    if (cursor < value.length) editor.append(document.createTextNode(value.slice(cursor)));
    widget.value = serializeEditor();
  }

  function closeMenu() {
    menu.hidden = true;
    state.triggerRange = null;
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

  function openMenu() {
    const options = activeMentionOptions(node);
    menu.replaceChildren();
    if (!options.length) {
      const empty = document.createElement("div");
      empty.textContent = "当前没有可引用的图片";
      menu.append(empty);
    }
    for (const option of options) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = `${option.display}  ${option.filename}`;
      button.addEventListener("mousedown", (event) => event.preventDefault());
      button.addEventListener("click", () => insertMention(option));
      menu.append(button);
    }
    menu.hidden = false;
    const selection = window.getSelection();
    state.triggerRange = selection?.rangeCount ? selection.getRangeAt(0).cloneRange() : null;
  }

  editor.addEventListener("input", () => {
    updateMentionManifest();
    const selection = window.getSelection();
    const range = selection?.rangeCount ? selection.getRangeAt(0) : null;
    const container = range?.startContainer;
    if (container?.nodeType === Node.TEXT_NODE && container.textContent.slice(0, range.startOffset).endsWith("@")) openMenu();
  });
  editor.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMenu();
  });
  editor.addEventListener("blur", () => window.setTimeout(closeMenu, 100));
  wrapper.addEventListener("pointerdown", (event) => event.stopPropagation());

  const refresh = () => renderValue();
  refresh();
  return { element: wrapper, refresh };
}

function installQwenStyles() {
  if (document.getElementById("ryan-qwen-image21-styles")) return;
  const style = document.createElement("style");
  style.id = "ryan-qwen-image21-styles";
  style.textContent = `
    .ryan-qwen-workbench { display:flex; flex-direction:column; gap:8px; width:auto; min-width:0; margin:2px 10px 10px; color:var(--input-text,#ddd); font-family:system-ui,-apple-system,"Segoe UI",sans-serif; }
    .ryan-qwen-image-gallery { display:grid; grid-auto-rows:max-content; gap:4px; min-width:0; }
    .ryan-qwen-image-heading,.ryan-qwen-prompt-heading { color:rgba(255,255,255,.56); font-size:10px; font-weight:650; line-height:16px; letter-spacing:.035em; }
    .ryan-qwen-image-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:4px; min-width:0; }
    .ryan-qwen-image-slot { appearance:none; position:relative; display:flex; align-items:center; justify-content:center; min-width:0; height:72px; overflow:hidden; box-sizing:border-box; padding:0; border:1px dashed rgba(255,255,255,.18); border-radius:7px; background:rgba(255,255,255,.035); color:rgba(255,255,255,.48); cursor:pointer; transition:border-color .12s ease,background-color .12s ease,opacity .12s ease,transform .12s ease; }
    .ryan-qwen-image-slot:hover,.ryan-qwen-image-slot:focus-visible,.ryan-qwen-image-slot.is-dragover { border-color:rgba(0,226,187,.64); background:rgba(0,226,187,.075); outline:none; }
    .ryan-qwen-image-slot.has-image[draggable="true"] { cursor:grab; }
    .ryan-qwen-image-slot.is-reordering { opacity:.45; cursor:grabbing; }
    .ryan-qwen-image-slot.is-reorder-target { border-color:rgba(79,150,255,.95); background:rgba(79,150,255,.16); box-shadow:inset 0 0 0 1px rgba(79,150,255,.4); }
    .ryan-qwen-image-slot:active:not(.is-disabled) { transform:scale(.985); }
    .ryan-qwen-image-slot.has-image { border-style:solid; border-color:rgba(255,255,255,.18); background:rgba(0,0,0,.28); }
    .ryan-qwen-image-slot.is-disabled { opacity:.24; cursor:not-allowed; filter:grayscale(.8); }
    .ryan-qwen-image-slot.is-wired { cursor:default; border-style:solid; border-color:rgba(0,226,187,.55); }
    .ryan-qwen-image-slot.is-uploading { cursor:wait; opacity:.68; }
    .ryan-qwen-image-preview { position:absolute; inset:0; width:100%; height:100%; object-fit:cover; background:#111; pointer-events:none; }
    .ryan-qwen-image-slot-badge { position:absolute; left:4px; top:4px; z-index:2; display:inline-flex; align-items:center; justify-content:center; width:17px; height:17px; border-radius:5px; background:rgba(0,0,0,.68); color:rgba(255,255,255,.9); font:700 9px/1 Consolas,monospace; pointer-events:none; }
    .ryan-qwen-image-slot-port { position:absolute; left:6px; top:24px; z-index:4; width:10px; height:10px; box-sizing:border-box; border:1.5px solid rgba(0,226,187,.92); border-radius:50%; background:#1a1c20; pointer-events:auto; box-shadow:0 0 0 1px rgba(0,0,0,.45); }
    .ryan-qwen-image-slot.is-wired .ryan-qwen-image-slot-port { background:rgba(0,226,187,.95); }
    .ryan-qwen-image-slot-status { position:absolute; left:4px; right:4px; bottom:4px; z-index:2; overflow:hidden; padding:2px 4px; border-radius:4px; background:rgba(0,0,0,.62); color:rgba(255,255,255,.8); font:500 8px/12px system-ui,sans-serif; text-overflow:ellipsis; white-space:nowrap; pointer-events:none; }
    .ryan-qwen-image-slot:not(.has-image) .ryan-qwen-image-slot-status { background:transparent; color:inherit; white-space:normal; text-align:center; }
    .ryan-qwen-image-slot-clear { appearance:none; position:absolute; right:4px; top:4px; z-index:3; display:inline-flex; align-items:center; justify-content:center; width:18px; height:18px; padding:0; border:0; border-radius:5px; background:rgba(0,0,0,.7); color:#fff; cursor:pointer; font:700 14px/1 system-ui; }
    .ryan-qwen-image-slot-clear:hover:not(:disabled),.ryan-qwen-image-slot-clear:focus-visible { background:rgba(212,70,70,.9); outline:none; }
    .ryan-qwen-image-slot-clear:disabled { opacity:.4; cursor:not-allowed; }
    .ryan-qwen-prompt-wrap { position:relative; display:grid; grid-template-rows:max-content minmax(var(--ryan-qwen-prompt-min-height),1fr); gap:3px; min-width:0; min-height:calc(var(--ryan-qwen-prompt-min-height) + 19px); }
    .ryan-qwen-prompt-editor { display:block; width:100%; min-width:0; min-height:var(--ryan-qwen-prompt-min-height); max-height:240px; box-sizing:border-box; padding:6px; overflow-y:auto; overflow-x:hidden; white-space:pre-wrap; overflow-wrap:anywhere; border:1px solid rgba(255,255,255,.14); border-radius:5px; outline:none; background:rgba(0,0,0,.28); color:var(--input-text,#ddd); caret-color:var(--input-text,#ddd); font-family:Consolas,"Courier New",monospace; font-size:12px; line-height:1.35; }
    .ryan-qwen-prompt-editor:focus { border-color:rgba(0,226,187,.7); }
    .ryan-qwen-prompt-editor:empty::before { content:attr(data-placeholder); color:rgba(255,255,255,.38); pointer-events:none; }
    .ryan-qwen-mention { display:inline-block; margin:0 2px; padding:1px 5px; border-radius:10px; background:#405b75; color:#fff; font-size:.9em; user-select:all; }
    .ryan-qwen-mention-menu { position:absolute; left:0; right:0; top:100%; z-index:30; display:flex; flex-direction:column; gap:2px; max-height:180px; overflow:auto; padding:4px; background:var(--comfy-menu-bg,#222); border:1px solid rgba(255,255,255,.18); border-radius:4px; box-shadow:0 4px 16px rgba(0,0,0,.38); }
    .ryan-qwen-mention-menu[hidden] { display:none; }
    .ryan-qwen-mention-menu button { appearance:none; text-align:left; padding:4px 6px; border:0; border-radius:3px; background:transparent; color:inherit; cursor:pointer; }
    .ryan-qwen-mention-menu button:hover { background:rgba(0,226,187,.16); }
  `;
  document.head.append(style);
}

function moveWorkbenchBeforeResolution(node, domWidget) {
  const anchor = node.widgets?.find((widget) => widget.name === "resolution_mode");
  const from = node.widgets?.indexOf(domWidget) ?? -1;
  const to = node.widgets?.indexOf(anchor) ?? -1;
  if (from >= 0 && to >= 0 && from > to) {
    node.widgets.splice(from, 1);
    node.widgets.splice(to, 0, domWidget);
  }
}

function setupNode(node) {
  if (!node || node.__ryanQwenImage21Installed) return;
  node.__ryanQwenImage21Installed = true;
  installQwenStyles();
  node._ryanQwenAllInputs = [...(node.inputs || [])];
  installSlotGeometry(node);

  const countWidget = findWidget(node, COUNT_WIDGET);
  if (countWidget && !countWidget.__ryanQwenCallbackBound) {
    countWidget.__ryanQwenCallbackBound = true;
    const originalCallback = countWidget.callback;
    countWidget.callback = (value) => {
      originalCallback?.(value);
      updateSlotVisibility(node, value);
    };
  }

  const gallery = createImageGallery(node);
  const promptEditors = [
    createPromptEditor(node, "prompt", "Prompt", 132),
    createPromptEditor(node, "negative_prompt", "Negative Prompt", 76),
  ].filter(Boolean);
  const workbench = document.createElement("div");
  workbench.className = "ryan-qwen-workbench";
  if (gallery) workbench.append(gallery);
  for (const editor of promptEditors) workbench.append(editor.element);

  if (typeof node.addDOMWidget === "function" && workbench.childElementCount) {
    const domWidget = node.addDOMWidget("ryan_qwen_image21_workbench", "ryan_qwen_image21_workbench", workbench, {
      serialize: false,
      hideOnZoom: false,
      margin: 0,
      getMinHeight: () => {
        const rows = Math.max(1, Math.ceil(activeSlotCount(node) / 3));
        return 16 + rows * 76 + 8 + 151 + 8 + 95;
      },
    });
    if (domWidget) {
      domWidget.serialize = false;
      moveWorkbenchBeforeResolution(node, domWidget);
      node.__ryanQwenWorkbench = workbench;
    }
  }

  node.__ryanQwenRefreshMentions = () => promptEditors.forEach((editor) => editor.refresh());
  const originalConnectionsChange = node.onConnectionsChange;
  node.onConnectionsChange = function onConnectionsChangeQwen() {
    const result = originalConnectionsChange?.apply(this, arguments);
    this.__ryanQwenRenderGallery?.();
    this.__ryanQwenRefreshMentions?.();
    this.setDirtyCanvas?.(true, true);
    return result;
  };
  updateSlotVisibility(node, countWidget?.value ?? DEFAULT_SLOT_COUNT);
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
      const result = originalConfigure?.apply(this, arguments);
      this._ryanQwenAllInputs = [...(this.inputs || [])];
      if (!this.__ryanQwenImage21Installed) setupNode(this);
      this.__ryanQwenRefreshMentions?.();
      this.__ryanQwenRenderGallery?.();
      updateSlotVisibility(this, findWidget(this, COUNT_WIDGET)?.value ?? DEFAULT_SLOT_COUNT);
      return result;
    };
  },
});
