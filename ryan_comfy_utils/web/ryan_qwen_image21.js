import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

const NODE_NAME = "Ryan Qwen Image 2.1";
const MAX_SLOTS = 16;
const SLOTS_PER_ROW = 4;
const DEFAULT_VISIBLE_SLOTS = SLOTS_PER_ROW;
const QWEN_NODE_MIN_WIDTH = 430;
const QWEN_IMAGE_SLOT_LAYOUT_POS = [12, 28];
const QWEN_HIDDEN_WIDGET_SIZE = [0, -4];
const QWEN_NUMERIC_DEFAULTS = {
  megapixels: 2.0,
  batch_size: 1,
  resolution: 1024,
};
const QWEN_ASPECT_RATIO_DEFAULT = "9:16 (Portrait Widescreen)";
const QWEN_MEGAPIXEL_OPTIONS = [0.5, 0.75, 0.98, 1.0, 1.5, 2.0, 3.0, 4.0];
const SLOT_PREFIX = "image_";
const GALLERY_PREFIX = "gallery_";
const SLOT_REORDER_MIME = "application/x-ryan-qwen-image-reorder";
const QWEN_LINKS_PROP = "ryan_qwen_image_links";
const QWEN_STATE_PROP = "ryan_qwen_image_state";
const QWEN_STATE_VERSION = 1;
const QWEN_PERSISTED_WIDGETS = [
  "prompt",
  "negative_prompt",
  "aspect_ratio",
  "megapixels",
  "batch_size",
  "resolution",
];
let qwenCanvasBridgeCanvas = null;
let qwenCanvasBridgeCleanup = null;

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

function readStoredQwenState(node) {
  let state = node?.properties?.[QWEN_STATE_PROP];
  if (typeof state === "string") {
    try {
      state = JSON.parse(state);
    } catch (_error) {
      state = null;
    }
  }
  return state && typeof state === "object" ? state : null;
}

function storedQwenGallery(state) {
  return normalizeGalleryForState(Array.isArray(state?.gallery) ? state.gallery : []);
}

function qwenStateGallery(node) {
  const gallery = normalizeGalleryForState(
    node.__ryanQwenGalleryState?.gallery || getManifest(node),
  );
  if (node.__ryanQwenGalleryState) node.__ryanQwenGalleryState.gallery = gallery;
  return gallery;
}

function persistQwenState(node) {
  if (!node) return null;
  node.properties ||= {};
  const gallery = qwenStateGallery(node);
  const promptMentions = getMentionManifest(node);
  const state = {
    version: QWEN_STATE_VERSION,
    prompt: String(findWidget(node, "prompt")?.value ?? ""),
    negative_prompt: String(findWidget(node, "negative_prompt")?.value ?? ""),
    aspect_ratio: String(findWidget(node, "aspect_ratio")?.value ?? ""),
    megapixels: Number(findWidget(node, "megapixels")?.value),
    batch_size: Number(findWidget(node, "batch_size")?.value),
    resolution: Number(findWidget(node, "resolution")?.value),
    gallery,
    prompt_mentions: promptMentions,
    gallery_expanded: isGalleryExpanded(node),
  };
  for (const name of ["megapixels", "batch_size", "resolution"]) {
    if (!Number.isFinite(state[name])) delete state[name];
  }
  node.properties[QWEN_STATE_PROP] = state;
  return state;
}

function restoreQwenState(node) {
  const state = readStoredQwenState(node);
  if (!state) return false;

  for (const name of QWEN_PERSISTED_WIDGETS) {
    if (state[name] !== undefined) setWidgetValue(node, name, state[name]);
  }
  const gallery = storedQwenGallery(state);
  updateGalleryHiddenWidgets(node, gallery);
  if (Array.isArray(state.prompt_mentions)) {
    setWidgetValue(node, "prompt_mentions", JSON.stringify(state.prompt_mentions));
  }
  if (typeof state.gallery_expanded === "boolean") {
    node.__ryanQwenGalleryExpanded = state.gallery_expanded;
  }
  if (node.__ryanQwenGalleryState) {
    node.__ryanQwenGalleryState.gallery = gallery;
  }
  return true;
}

function refreshQwenGalleryState(node) {
  if (!node.__ryanQwenGalleryState) return;
  node.__ryanQwenGalleryState.gallery = normalizeGalleryForState(getManifest(node));
  // Older workflows can leave stale hidden gallery widgets behind after the
  // DOM workbench has been inserted. Rebuild every backing slot from the
  // manifest so an empty gallery cannot submit values such as "1" or "".
  updateGalleryHiddenWidgets(node, node.__ryanQwenGalleryState.gallery);
}

function installQwenPersistenceHooks(node) {
  for (const name of QWEN_PERSISTED_WIDGETS) {
    const widget = findWidget(node, name);
    if (!widget || widget.__ryanQwenPersistenceBound) continue;
    widget.__ryanQwenPersistenceBound = true;
    const originalCallback = widget.callback;
    widget.callback = function persistQwenWidget(value) {
      const result = originalCallback?.apply(this, arguments);
      persistQwenState(node);
      app.graph?.change?.();
      return result;
    };
  }
  if (!node.__ryanQwenSerializePatched) {
    node.__ryanQwenSerializePatched = true;
    const originalSerialize = node.serialize;
    if (typeof originalSerialize === "function") {
      node.serialize = function serializeQwenImage21() {
        persistQwenState(this);
        const serialized = originalSerialize.apply(this, arguments);
        serialized.properties ||= {};
        serialized.properties[QWEN_STATE_PROP] = this.properties?.[QWEN_STATE_PROP];
        return serialized;
      };
    }
    const originalOnSerialize = node.onSerialize;
    node.onSerialize = function onSerializeQwenImage21(info) {
      const result = originalOnSerialize?.apply(this, arguments);
      persistQwenState(this);
      if (info && typeof info === "object") {
        info.properties ||= {};
        info.properties[QWEN_STATE_PROP] = this.properties?.[QWEN_STATE_PROP];
      }
      return result;
    };
  }
}

function formatQwenMegapixelOption(value) {
  const numeric = Number(value);
  if (!QWEN_MEGAPIXEL_OPTIONS.some((option) => option === numeric)) return String(value ?? "");
  return Number.isInteger(numeric) ? numeric.toFixed(1) : String(numeric);
}

function ensureQwenMegapixelDisplay(node) {
  const widget = findWidget(node, "megapixels");
  if (!widget) return;
  widget.options ||= {};
  if (widget.options.__ryanQwenMegapixelLabelPatched) return;
  const original = widget.options.getOptionLabel;
  widget.options.getOptionLabel = (value) => {
    const formatted = formatQwenMegapixelOption(value);
    return formatted || (typeof original === "function" ? original(value) : String(value ?? ""));
  };
  widget.options.__ryanQwenMegapixelLabelPatched = true;
}

function ensureQwenNumericDefaults(node) {
  const aspectRatio = findWidget(node, "aspect_ratio");
  if (aspectRatio) {
    const value = String(aspectRatio.value ?? "").trim();
    // A newly-created Vue widget can briefly expose its field name as the
    // value. Treat that, empty values, and non-ratio values as unhydrated.
    if (!/^\d+\s*:\s*\d+/.test(value)) setWidgetValue(node, "aspect_ratio", QWEN_ASPECT_RATIO_DEFAULT);
  }
  let resolution = findWidget(node, "resolution");
  const legacyResolution = findWidget(node, "reference_resolution");
  if (!resolution && legacyResolution) {
    legacyResolution.name = "resolution";
    resolution = legacyResolution;
  }
  for (const [name, fallback] of Object.entries(QWEN_NUMERIC_DEFAULTS)) {
    const widget = findWidget(node, name);
    if (!widget) continue;
    const value = Number(widget.value);
    let valid = Number.isFinite(value);
    if (name === "megapixels") {
      const option = QWEN_MEGAPIXEL_OPTIONS.find((candidate) => candidate === value);
      valid = option !== undefined;
      if (valid) setWidgetValue(node, name, option);
    } else if (name === "batch_size") {
      valid = Number.isInteger(value) && value >= 1 && value <= 64;
    } else if (name === "resolution") {
      // Resolution 1 (or any other value not aligned to 32) is a stale
      // serialized widget value, not a valid Qwen reference resolution.
      valid = Number.isInteger(value)
        && value >= 0
        && value <= 4096
        && (value === 0 || value % 32 === 0);
    }
    if (!valid) setWidgetValue(node, name, fallback);
  }
  ensureQwenMegapixelDisplay(node);
}

function repairQwenWidgetValuesSoon(node) {
  if (!node || node.__ryanQwenWidgetRepairScheduled) return;
  node.__ryanQwenWidgetRepairScheduled = true;
  // Vue may populate the visible widgets just after LiteGraph calls
  // onNodeCreated. Reapply only invalid values after that hydration window;
  // legitimate workflow values and later user selections remain untouched.
  for (const delay of [0, 80, 500]) {
    setTimeout(() => {
      if (!node) return;
      ensureQwenNumericDefaults(node);
      node.setDirtyCanvas?.(true, true);
    }, delay);
  }
}

function ensureQwenPromptInput(node) {
  if (!node) return null;
  let input = node.inputs?.find((item) => item?.name === "prompt");
  if (!input && typeof node.addInput === "function") {
    // This is the same migration used by the H3 node: append the socket so
    // old serialized input/link indexes are never shifted.
    node.addInput("prompt", "STRING", { widget: { name: "prompt" } });
    input = node.inputs?.find((item) => item?.name === "prompt");
  }
  if (input) {
    input.type = "STRING";
    input.widget ||= {};
    input.widget.name = "prompt";
    input.hidden = false;
  }

  // Nodes created by the earlier force-input implementation may still carry
  // a hidden prompt_text widget. Migrate its value into the official prompt
  // widget, but never expose prompt_text as a second input.
  const promptWidget = findWidget(node, "prompt");
  const legacyWidget = findWidget(node, "prompt_text");
  if (promptWidget && legacyWidget && !String(promptWidget.value || "").trim() && legacyWidget.value) {
    setWidgetValue(node, "prompt", legacyWidget.value);
  }
  if (!promptWidget && legacyWidget) {
    legacyWidget.name = "prompt";
    legacyWidget.hidden = false;
    legacyWidget.computeSize = undefined;
  }
  return input;
}

function ensureQwenTypedInputs(node) {
  if (!node?.inputs) return;
  for (const input of node.inputs) {
    if (input?.name === "clip") input.type = "CLIP";
    else if (input?.name === "vae") input.type = "VAE";
    else if (input?.name === "prompt") input.type = "STRING";
    else if (isQwenImageInput(input)) input.type = "IMAGE";
  }
}


function ensureQwenNodeSize(node) {
  const measured = node.computeSize?.() || node.size || [QWEN_NODE_MIN_WIDTH, 0];
  const width = Math.max(QWEN_NODE_MIN_WIDTH, Number(measured[0]) || 0, Number(node.size?.[0]) || 0);
  const height = Math.max(1, Number(measured[1]) || 0);
  node.setSize?.([width, height]);
}

function isQwenBackingWidget(widget) {
  const name = String(widget?.name || "");
  return /^gallery_\d+$/.test(name) || name === "gallery_manifest" || name === "prompt_mentions";
}

function compactQwenBackingWidgets(node) {
  for (const widget of node?.widgets || []) {
    if (!isQwenBackingWidget(widget)) continue;
    widget.hidden = true;
    widget.computeSize = () => QWEN_HIDDEN_WIDGET_SIZE;
    if (widget.options) {
      widget.options.hidden = true;
      widget.options.canvasOnly = true;
    }
    if (widget._state) {
      widget._state.hidden = true;
      widget._state.computedHeight = 0;
    }
    widget.computedHeight = 0;
  }
}

function withQwenImageInputsExcludedFromLayout(node, fn) {
  const originalInputs = node?.inputs;
  const originalConcrete = node?._concreteInputs;
  if (Array.isArray(originalInputs)) {
    node.inputs = originalInputs.filter((input) => !isQwenImageInput(input));
  }
  if (Array.isArray(originalConcrete)) {
    node._concreteInputs = originalConcrete.filter((input) => !isQwenImageInput(input));
  }
  try {
    return fn();
  } finally {
    if (originalInputs) node.inputs = originalInputs;
    if (originalConcrete) node._concreteInputs = originalConcrete;
  }
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

function qwenLinks(node) {
  node.properties ||= {};
  if (!Array.isArray(node.properties[QWEN_LINKS_PROP])) node.properties[QWEN_LINKS_PROP] = [];
  return node.properties[QWEN_LINKS_PROP];
}

function getNativeGraphLink(graph, linkId) {
  if (!graph || linkId == null) return null;
  for (const links of [graph.links, graph._links]) {
    if (!links) continue;
    if (typeof links.get === "function") {
      const link = links.get(linkId) ?? links.get(String(linkId));
      if (link) return link;
    }
    const link = links[linkId] ?? links[String(linkId)];
    if (link) return link;
  }
  return null;
}

function qwenNativeImageInput(node, slot) {
  const name = qwenImageSlotName(Number(slot));
  return (node?.inputs || []).find((input) => input?.name === name)
    || (node?._ryanQwenAllInputs || []).find((input) => input?.name === name)
    || null;
}

function qwenImageSlotSource(node, slot) {
  const input = qwenNativeImageInput(node, slot);
  const graph = node?.graph || app.graph;
  if (input?.link != null) {
    const index = node.inputs?.findIndex?.((item) => item?.name === input.name) ?? -1;
    const sourceNodeFromInput = index >= 0 && typeof node.getInputNode === "function"
      ? node.getInputNode(index)
      : null;
    const native = getNativeGraphLink(graph, input.link);
    const sourceId = sourceNodeFromInput?.id ?? native?.origin_id ?? native?.originId ?? native?.from_id;
    const sourceSlot = native?.origin_slot ?? native?.originSlot ?? 0;
    const sourceNode = sourceNodeFromInput
      || (sourceId != null ? graph?.getNodeById?.(Number(sourceId)) : null);
    if (sourceId != null) {
      return { sourceNode, sourceId, sourceSlot: Number(sourceSlot) || 0 };
    }
  }
  const link = qwenLinks(node).find((item) => Number(item.slot) === Number(slot));
  if (!link?.source_id) return null;
  return {
    sourceNode: graph?.getNodeById?.(Number(link.source_id)) || null,
    sourceId: link.source_id,
    sourceSlot: Number(link.source_slot) || 0,
  };
}

function qwenImageSlotPromptRef(node, slot) {
  const source = qwenImageSlotSource(node, slot);
  if (source?.sourceId == null) return null;
  return [String(source.sourceId), Number(source.sourceSlot) || 0];
}

function qwenWidgetImagePath(value) {
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) return null;
    return { name: trimmed, subfolder: "", type: "input" };
  }
  if (value && typeof value === "object" && value.name) {
    return {
      name: String(value.name),
      subfolder: String(value.subfolder || ""),
      type: String(value.type || "input"),
    };
  }
  return null;
}

function qwenSourcePreviewUrl(sourceNode) {
  if (!sourceNode) return "";
  const imageWidget = sourceNode.widgets?.find((widget) => String(widget?.name || "").toLowerCase() === "image");
  const imagePath = qwenWidgetImagePath(imageWidget?.value);
  if (imagePath) return viewUrl(imagePath);
  const fromImgs = (sourceNode.imgs || []).find((item) => item?.src);
  if (fromImgs?.src) return fromImgs.src;
  for (const widget of sourceNode.widgets || []) {
    const path = qwenWidgetImagePath(widget?.value);
    if (path && /\.(png|jpe?g|webp|gif|bmp)$/i.test(path.name)) return viewUrl(path);
  }
  return "";
}

function qwenSourceFilename(sourceNode) {
  const imageWidget = sourceNode?.widgets?.find((widget) => String(widget?.name || "").toLowerCase() === "image");
  return qwenWidgetImagePath(imageWidget?.value)?.name || "";
}

function refreshQwenSourcePreviewTargets(sourceNode) {
  for (const target of sourceNode?.__ryanQwenPreviewTargets || []) {
    target.__ryanQwenRenderGallery?.();
    target.setDirtyCanvas?.(true, true);
  }
}

function watchQwenImageSourceNode(sourceNode, targetNode) {
  if (!sourceNode || !targetNode) return;
  sourceNode.__ryanQwenPreviewTargets ||= new Set();
  sourceNode.__ryanQwenPreviewTargets.add(targetNode);
  for (const widget of sourceNode.widgets || []) {
    if (!widget || widget.__ryanQwenImageSourceWatchInstalled) continue;
    widget.__ryanQwenImageSourceWatchInstalled = true;
    const originalCallback = widget.callback;
    widget.callback = function onQwenImageSourceWidgetChange() {
      const result = originalCallback?.apply(this, arguments);
      refreshQwenSourcePreviewTargets(sourceNode);
      return result;
    };
    const element = widget.inputEl || widget.element;
    element?.addEventListener?.("change", () => refreshQwenSourcePreviewTargets(sourceNode), true);
  }
  if (sourceNode.__ryanQwenImageSourceWatchInstalled) return;
  sourceNode.__ryanQwenImageSourceWatchInstalled = true;
  const originalExecuted = sourceNode.onExecuted;
  sourceNode.onExecuted = function onExecutedQwenImageSource() {
    const result = originalExecuted?.apply(this, arguments);
    refreshQwenSourcePreviewTargets(sourceNode);
    return result;
  };
}



function writeQwenVirtualLink(node, targetSlot, sourceId, sourceSlot, sourceType = "IMAGE") {
  const slot = Number(targetSlot);
  if (!node || !Number.isInteger(slot) || slot < 1 || slot > MAX_SLOTS || sourceId == null) return false;
  const next = qwenLinks(node).filter((link) => Number(link.slot) !== slot);
  next.push({
    source_id: String(sourceId),
    source_slot: Number(sourceSlot) || 0,
    source_type: sourceType || "IMAGE",
    slot,
    order: slot,
  });
  node.properties[QWEN_LINKS_PROP] = next;
  return true;
}

function addQwenVirtualLink(node, sourceNode, sourceSlot, targetSlot) {
  if (!node || !sourceNode || Number(node.id) === Number(sourceNode.id)) return false;
  const output = sourceNode.outputs?.[Number(sourceSlot)] || {};
  const written = writeQwenVirtualLink(
    node,
    targetSlot,
    sourceNode.id,
    sourceSlot,
    output.type || output.datatype || output.label || "IMAGE",
  );
  if (!written) return false;
  node.setDirtyCanvas?.(true, true);
  app.graph?.setDirtyCanvas?.(true, true);
  app.graph?.change?.();
  updateGalleryVisibility(node);
  node.__ryanQwenRefreshMentions?.();
  return true;
}

function restoreQwenImageInputs(node) {
  if (!node || !Array.isArray(node.inputs)) return;
  const originalInputs = node._ryanQwenAllInputs || [];
  if (!originalInputs.length) {
    node._ryanQwenAllInputs = [...node.inputs];
    return;
  }
  const currentByName = new Map(node.inputs.map((input) => [input?.name, input]));
  const restored = originalInputs.map((input) => currentByName.get(input?.name) || input);
  const knownNames = new Set(restored.map((input) => input?.name));
  for (const input of node.inputs) {
    if (!knownNames.has(input?.name)) restored.push(input);
  }
  // These inputs are the real LiteGraph targets. They must remain in
  // node.inputs for LinkConnector to detect and snap to the green gallery
  // ports; visibility and geometry are handled separately below.
  node.inputs = restored;
}

// Compatibility for virtual links stored by earlier frontend revisions. New
// connections use the native inputs restored above and never enter this path.
function connectQwenImageInput(node, sourceNode, sourceSlot, slot) {
  return addQwenVirtualLink(node, sourceNode, sourceSlot, slot);
}

function removeQwenVirtualLink(node, slot) {
  const links = qwenLinks(node);
  const next = links.filter((link) => Number(link.slot) !== Number(slot));
  if (next.length === links.length) return false;
  node.properties[QWEN_LINKS_PROP] = next;
  node.setDirtyCanvas?.(true, true);
  app.graph?.setDirtyCanvas?.(true, true);
  app.graph?.change?.();
  updateGalleryVisibility(node);
  node.__ryanQwenRefreshMentions?.();
  return true;
}

function clearQwenImageSlot(node, slot) {
  const index = node?.inputs?.findIndex?.((input) => input?.name === qwenImageSlotName(slot)) ?? -1;
  if (index >= 0) node.disconnectInput?.(index);
  node.properties ||= {};
  node.properties[QWEN_LINKS_PROP] = qwenLinks(node).filter((link) => Number(link.slot) !== Number(slot));
  if (node.__ryanQwenGalleryState) {
    node.__ryanQwenGalleryState.gallery = (node.__ryanQwenGalleryState.gallery || []).filter(
      (asset) => Number(asset.slot) !== Number(slot),
    );
    updateGalleryHiddenWidgets(node, node.__ryanQwenGalleryState.gallery);
  }
  persistQwenState(node);
  updateGalleryVisibility(node);
  node.__ryanQwenRefreshMentions?.();
  node.setDirtyCanvas?.(true, true);
  app.graph?.setDirtyCanvas?.(true, true);
  app.graph?.change?.();
  return true;
}


function isExternalSlotConnected(node, slot) {
  const input = qwenNativeImageInput(node, slot);
  const linkId = input?.link;
  if (linkId != null && Number(linkId) >= 0 && getNativeGraphLink(node?.graph || app.graph, linkId)) {
    return true;
  }
  const virtual = qwenLinks(node).find((link) => Number(link.slot) === Number(slot));
  if (!virtual) return false;
  const graph = node?.graph || app.graph;
  return graph?.getNodeById?.(Number(virtual.source_id)) != null;
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

function hasHiddenGalleryContent(node) {
  const gallery = node.__ryanQwenGalleryState?.gallery || getManifest(node);
  for (let slot = DEFAULT_VISIBLE_SLOTS + 1; slot <= MAX_SLOTS; slot += 1) {
    if (isExternalSlotConnected(node, slot) || galleryAssetAtSlot(gallery, slot)) return true;
  }
  return false;
}

function isGalleryExpanded(node) {
  if (typeof node.__ryanQwenGalleryExpanded === "boolean") return node.__ryanQwenGalleryExpanded;
  return hasHiddenGalleryContent(node);
}


function visibleGallerySlotCount(node) {
  return isGalleryExpanded(node) ? MAX_SLOTS : DEFAULT_VISIBLE_SLOTS;
}

function updateGalleryVisibility(node) {
  const visibleCount = visibleGallerySlotCount(node);
  if (!node._ryanQwenAllInputs) node._ryanQwenAllInputs = [...(node.inputs || [])];
  for (const input of node.inputs || []) {
    if (!isQwenImageInput(input)) continue;
    // Keep the real LiteGraph inputs hidden from the left edge while their
    // custom positions are mapped to the gallery's green ports.
    input.hidden = true;
    input.pos = QWEN_IMAGE_SLOT_LAYOUT_POS;
    input.__ryanQwenSlotVisible = Number(input.name.slice(6)) <= visibleCount;
  }
  node.__ryanQwenVisibleSlotCount = visibleCount;
  compactQwenBackingWidgets(node);
  node.__ryanQwenRenderGallery?.();
  node._widgetSlotsDirty = true;
  // DOM gallery rendering above is synchronous. A second requestAnimationFrame
  // resize can re-enter ComfyUI's DOM-widget layout pass and make the node
  // height grow without bound, so size is calculated exactly once here.
  ensureQwenNodeSize(node);
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
  const count = visibleGallerySlotCount(node);
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

function qwenPromptInputIndex(node) {
  return node?.inputs?.findIndex?.((input) => input?.name === "prompt") ?? -1;
}

function qwenPromptElement(node) {
  return node?.__ryanQwenPromptEditor || node?.__ryanQwenPromptWrap?.querySelector?.(".ryan-qwen-prompt-editor") || null;
}

function qwenPromptGraphPos(node) {
  const element = qwenPromptElement(node);
  const rect = element?.getBoundingClientRect?.();
  if (!rect || (!rect.width && !rect.height)) return null;
  // Match the official Qwen widget: the STRING socket sits at the upper-left
  // edge of the Prompt textarea, rather than in the node's top input list.
  return clientToGraph(app.canvas, rect.left - 6, rect.top + 8);
}

function qwenPromptSlotHit(node, x, y) {
  const element = qwenPromptElement(node);
  const rect = element?.getBoundingClientRect?.();
  if (!rect || (!rect.width && !rect.height)) return false;
  const topLeft = clientToGraph(app.canvas, rect.left, rect.top);
  const bottomRight = clientToGraph(app.canvas, rect.right, rect.bottom);
  if (!topLeft || !bottomRight) return false;
  return x >= topLeft[0] - 14 && x <= bottomRight[0] && y >= topLeft[1] && y <= bottomRight[1];
}

function updateQwenPromptConnectionState(node) {
  const promptInput = node?.inputs?.find((input) => input?.name === "prompt");
  const connected = promptInput?.link != null;
  const editor = qwenPromptElement(node);
  if (editor) {
    editor.contentEditable = connected ? "false" : "true";
    editor.tabIndex = connected ? -1 : 0;
    editor.setAttribute("aria-readonly", connected ? "true" : "false");
    editor.classList.toggle("is-connected", connected);
    if (connected && document.activeElement === editor) editor.blur();
  }
  node?.__ryanQwenPromptWrap?.classList?.toggle("is-connected", connected);
}


function collapsedGalleryInputGraphPos(node) {
  // LiteGraph measures the bounding rectangle of every native input. A
  // synthetic off-canvas position therefore turns a collapsed slot into an
  // enormous node. Keep inactive inputs on the first in-grid port instead;
  // the gallery DOM covers their duplicate canvas labels and the first input
  // wins hit testing at that position.
  return galleryCellGraphPos(node, 1) || [
    (Number(node?.pos?.[0]) || 0) + 24,
    (Number(node?.pos?.[1]) || 0) + 32,
  ];
}

function qwenImageSlotGraphPos(node, input) {
  if (input?.__ryanQwenSlotVisible) {
    return galleryCellGraphPos(node, Number(input.name.slice(6))) || collapsedGalleryInputGraphPos(node);
  }
  return collapsedGalleryInputGraphPos(node);
}


function installSlotGeometry(node) {
  if (!node || node.__ryanQwenSlotGeometryInstalled) return;
  node.__ryanQwenSlotGeometryInstalled = true;
  const originalGetConnectionPos = node.getConnectionPos;
  node.getConnectionPos = function getConnectionPosQwen(isInput, slot, out) {
    if (isInput) {
      const input = this.inputs?.[slot];
      if (input?.name === "prompt") {
        const graph = qwenPromptGraphPos(this);
        if (graph) {
          const point = out || [0, 0];
          point[0] = graph[0];
          point[1] = graph[1];
          return point;
        }
      }
      if (isQwenImageInput(input)) {
        const graph = qwenImageSlotGraphPos(this, input);
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
      if (input?.name === "prompt") {
        const graph = qwenPromptGraphPos(this);
        if (graph) return graph;
      }
      if (isQwenImageInput(input)) {
        const graph = qwenImageSlotGraphPos(this, input);
        if (graph) return graph;
      }
      return originalGetInputPos.apply(this, arguments);
    };
  }
  const originalGetSlotInPosition = node.getSlotInPosition;
  if (typeof originalGetSlotInPosition === "function") {
    node.getSlotInPosition = function getSlotInPositionQwen(x, y) {
      if (qwenPromptSlotHit(this, x, y)) {
        const index = qwenPromptInputIndex(this);
        if (index >= 0) {
          return {
            input: true,
            slot: index,
            link_pos: qwenPromptGraphPos(this) || [x, y],
          };
        }
      }
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
    node.computeSize = function computeSizeWithoutQwenImageInputs() {
      return withQwenImageInputsExcludedFromLayout(this, () => originalComputeSize.apply(this, arguments));
    };
  }
  const originalArrange = node.arrange;
  if (typeof originalArrange === "function") {
    node.arrange = function arrangeWithoutQwenImageInputs() {
      // LinkConnector still sees image_* via getInputPos. arrange/_measureSlots
      // must not, or gallery DOM coordinates ratchet widgetStartY every frame.
      return withQwenImageInputsExcludedFromLayout(this, () => originalArrange.apply(this, arguments));
    };
  }
}

function qwenConnectingOutput(canvas) {
  const sourceNode = canvas?.connecting_node || canvas?.connectingNode;
  if (!sourceNode) return null;
  const raw = canvas.connecting_output ?? canvas.connecting_slot ?? canvas.connecting_output_slot;
  if (raw == null && canvas.connecting_input) return null;
  const candidateSlot = typeof raw === "number" || typeof raw === "string"
    ? raw
    : raw?.slot_index ?? raw?.slot ?? raw?.index;
  const parsedSlot = Number(candidateSlot);
  // Nodes 2.0 can store the output socket object itself instead of its index.
  // Mirror H3's fallback: keep a usable output endpoint instead of discarding
  // the gesture when that object has no slot metadata.
  const objectIndex = sourceNode.outputs?.indexOf?.(raw);
  const sourceSlot = Number.isFinite(parsedSlot)
    ? parsedSlot
    : (objectIndex >= 0 ? objectIndex : 0);
  const output = sourceNode.outputs?.[sourceSlot] || raw || {};
  return {
    sourceNode,
    sourceSlot,
    sourceType: output.type || output.datatype || output.label || "IMAGE",
  };
}

function qwenSlotIndex(slots, rawSlot) {
  if (typeof rawSlot === "number" && slots?.[rawSlot]) return rawSlot;
  if (typeof rawSlot === "string" && /^\d+$/.test(rawSlot) && slots?.[Number(rawSlot)]) return Number(rawSlot);
  for (const key of ["slot_index", "slot", "index"]) {
    const value = rawSlot?.[key];
    if (typeof value === "number" && slots?.[value]) return value;
    if (typeof value === "string" && /^\d+$/.test(value) && slots?.[Number(value)]) return Number(value);
  }
  if (Array.isArray(slots) && rawSlot) {
    const direct = slots.indexOf(rawSlot);
    if (direct >= 0) return direct;
    const name = typeof rawSlot === "string" ? rawSlot : rawSlot?.name;
    if (name) return slots.findIndex((slot) => slot?.name === name);
  }
  return -1;
}

function qwenPendingConnectorOutput(canvas) {
  const pending = qwenPendingConnectorLink(canvas);
  return pending?.direction === "from_output"
    ? {
      sourceNode: pending.sourceNode,
      sourceSlot: pending.sourceSlot,
      sourceType: pending.sourceType,
    }
    : null;
}

function qwenPendingConnectorLink(canvas) {
  const connecting = qwenConnectingOutput(canvas);
  if (connecting) {
    return { direction: "from_output", ...connecting };
  }
  const link = canvas?.linkConnector?.renderLinks?.at?.(0);
  if (link) {
    const endpointNode = link.node || link.fromNode || link.originNode || link.sourceNode
      || link.outputNode || link.toNode || link.targetNode || link.inputNode;
    const endpointSlot = link.fromSlot ?? link.slot ?? link.output ?? link.input ?? link.toSlot ?? {};
    const inputIndex = qwenSlotIndex(endpointNode?.inputs, endpointSlot);
    const outputIndex = qwenSlotIndex(endpointNode?.outputs, endpointSlot);
    const toType = String(link.toType || link.targetType || link.targetSlotType || "").toLowerCase();
    let direction = toType.includes("output") ? "from_input" : "from_output";
    if (inputIndex >= 0 && outputIndex < 0) direction = "from_input";
    if (outputIndex >= 0 && inputIndex < 0) direction = "from_output";
    if (direction === "from_input") return null;
    const indexed = Number(link.fromSlotIndex ?? link.outputIndex);
    const sourceSlot = outputIndex >= 0
      ? outputIndex
      : (Number.isInteger(indexed) && indexed >= 0 ? indexed : -1);
    if (endpointNode && sourceSlot >= 0) {
      const output = endpointNode.outputs?.[sourceSlot] || endpointSlot || {};
      return {
        direction: "from_output",
        sourceNode: endpointNode,
        sourceSlot,
        sourceType: output.type || output.datatype || output.label || "IMAGE",
      };
    }
    if (endpointNode) {
      const output = endpointSlot || endpointNode.outputs?.[0] || {};
      return {
        direction: "from_output",
        sourceNode: endpointNode,
        sourceSlot: 0,
        sourceType: output.type || output.datatype || output.label || "IMAGE",
      };
    }
  }
  return null;
}

function qwenEventClientPoint(event) {
  const detail = event?.detail;
  const candidates = [event, detail?.originalEvent, detail?.event, detail];
  for (const candidate of candidates) {
    const clientX = Number(candidate?.clientX);
    const clientY = Number(candidate?.clientY);
    if (Number.isFinite(clientX) && Number.isFinite(clientY)) return { clientX, clientY };
  }

  // LinkConnector dispatches `dropped-on-canvas` as a CustomEvent whose
  // detail is the LiteGraph canvas event. Some frontend builds expose only
  // graph-space coordinates there, so convert them back to screen space for
  // the DOM gallery hit test.
  for (const candidate of candidates) {
    const canvasX = Number(candidate?.canvasX);
    const canvasY = Number(candidate?.canvasY);
    const rect = app.canvas?.canvas?.getBoundingClientRect?.();
    if (!Number.isFinite(canvasX) || !Number.isFinite(canvasY) || !rect) continue;
    const scale = app.canvas?.ds?.scale || 1;
    const offset = app.canvas?.ds?.offset || [0, 0];
    return {
      clientX: (canvasX + Number(offset[0] || 0)) * scale + rect.left,
      clientY: (canvasY + Number(offset[1] || 0)) * scale + rect.top,
    };
  }
  return null;
}

function qwenNodeFromGallery(gallery, preferredNode) {
  if (preferredNode?.__ryanQwenImage21Installed) {
    if (!preferredNode.__ryanQwenGallery || preferredNode.__ryanQwenGallery === gallery) {
      return preferredNode;
    }
  }
  const graph = app.graph;
  const owned = graph?._nodes?.find((node) => node?.__ryanQwenGallery === gallery);
  if (owned) return owned;
  const rawId = gallery?.dataset?.qwenNodeId;
  if (rawId == null || rawId === "") return null;
  return graph?.getNodeById?.(Number(rawId))
    || graph?.getNodeById?.(rawId)
    || graph?.getNodeById?.(String(rawId))
    || null;
}

function qwenGalleryCellFromEvent(event, preferredNode = null) {
  const point = qwenEventClientPoint(event);
  const clientX = Number(point?.clientX);
  const clientY = Number(point?.clientY);
  if (!Number.isFinite(clientX) || !Number.isFinite(clientY)) return null;
  const element = document.elementFromPoint(clientX, clientY);
  const cell = element?.closest?.(".ryan-qwen-image-slot");
  if (!cell || cell.classList.contains("is-disabled")) return null;
  const gallery = cell.closest(".ryan-qwen-image-gallery");
  const slot = Number(cell.dataset.qwenSlot);
  if (!Number.isInteger(slot)) return null;
  const node = qwenNodeFromGallery(gallery, preferredNode);
  if (!node) return null;
  return { node, slot };
}

function qwenSourcePosition(node, slot) {
  const point = node?.getOutputPos?.(slot);
  if (Array.isArray(point)) return point;
  const out = [0, 0];
  try {
    const legacy = node?.getConnectionPos?.(false, slot, out);
    if (Array.isArray(legacy)) return legacy;
  } catch (_error) { /* Fall through to a stable fallback. */ }
  return [Number(node?.pos?.[0] || 0) + Number(node?.size?.[0] || 160), Number(node?.pos?.[1] || 0) + 40 + slot * 20];
}

function drawQwenVirtualLinks(canvas, context) {
  const graph = canvas?.graph || app.graph;
  const ctx = context || canvas?.ctx || canvas?.bgctx;
  if (!ctx || !graph?._nodes) return;
  for (const node of graph._nodes) {
    if (!node.__ryanQwenImage21Installed) continue;
    for (const link of qwenLinks(node)) {
      const sourceNode = graph.getNodeById?.(Number(link.source_id));
      const target = galleryCellGraphPos(node, Number(link.slot));
      if (!sourceNode || !target) continue;
      const source = qwenSourcePosition(sourceNode, Number(link.source_slot) || 0);
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(source[0], source[1]);
      ctx.bezierCurveTo(source[0] + 80, source[1], target[0] - 80, target[1], target[0], target[1]);
      ctx.lineWidth = (canvas.connections_width || 3) + 1;
      ctx.strokeStyle = "rgba(0,226,187,.9)";
      ctx.stroke();
      ctx.restore();
    }
  }
}

function installQwenCanvasBridge() {
  const canvas = app.canvas;
  if (!canvas?.canvas) return false;
  if (canvas === qwenCanvasBridgeCanvas && canvas.__ryanQwenCanvasBridgeInstalled) return true;

  // Nodes 2.0 can replace app.canvas during initialization or reload. Keep
  // exactly one live bridge so stale canvases cannot retain a competing drag
  // lifecycle after the replacement has taken over.
  qwenCanvasBridgeCleanup?.();
  qwenCanvasBridgeCleanup = null;
  qwenCanvasBridgeCanvas = canvas;
  canvas.__ryanQwenCanvasBridgeInstalled = true;
  let lastDraggedOutput = null;
  let lastCapturedDropAt = 0;
  const rememberOutput = () => {
    const current = qwenPendingConnectorLink(canvas);
    if (current?.direction === "from_output") {
      lastDraggedOutput = {
        sourceNode: current.sourceNode,
        sourceSlot: current.sourceSlot,
        sourceType: current.sourceType,
      };
    }
  };
  const handleDrop = (event) => {
    if (event?.button > 0 || (lastCapturedDropAt && performance.now() - lastCapturedDropAt < 80)) return;
    const preferredNode = event?.detail?.node?.__ryanQwenImage21Installed ? event.detail.node : null;
    const live = qwenPendingConnectorLink(canvas);
    if (live?.direction === "from_output") {
      lastDraggedOutput = {
        sourceNode: live.sourceNode,
        sourceSlot: live.sourceSlot,
        sourceType: live.sourceType,
      };
    }
    const current = live?.direction === "from_output" ? live : lastDraggedOutput;
    const hit = qwenGalleryCellFromEvent(event, preferredNode);
    if (!current || !hit || Number(current.sourceNode?.id) === Number(hit.node.id)) return;
    if (!connectQwenImageInput(hit.node, current.sourceNode, current.sourceSlot, hit.slot)) return;
    lastCapturedDropAt = performance.now();
    event.preventDefault?.();
    event.stopPropagation?.();
    event.stopImmediatePropagation?.();
    canvas.linkConnector?.reset?.();
    canvas.connecting_node = null;
    canvas.connecting_output = null;
    canvas.connecting_slot = null;
    canvas.connecting_input = null;
    lastDraggedOutput = null;
  };
  const pointerTargets = [window, document, canvas.canvas];
  for (const target of pointerTargets) {
    target.addEventListener("pointerdown", rememberOutput, true);
    target.addEventListener("pointermove", rememberOutput, true);
    target.addEventListener("pointerup", handleDrop, true);
    target.addEventListener("mouseup", handleDrop, true);
  }
  const events = canvas.linkConnector?.events;
  const beforeDropLinksHandler = () => rememberOutput();
  const droppedOnCanvasHandler = (event) => handleDrop(event);
  const resetHandler = () => rememberOutput();
  events?.addEventListener?.("before-drop-links", beforeDropLinksHandler, { capture: true });
  events?.addEventListener?.("dropped-on-canvas", droppedOnCanvasHandler, { capture: true });
  events?.addEventListener?.("dropped-on-node", handleDrop, { capture: true });
  events?.addEventListener?.("reset", resetHandler, { capture: true });
  const originalDraw = canvas.drawConnections;
  let drawConnectionsWithQwenLinks = null;
  if (typeof canvas.drawConnections === "function") {
    drawConnectionsWithQwenLinks = function drawConnectionsWithQwenLinks(context) {
      const result = originalDraw?.apply(this, arguments);
      drawQwenVirtualLinks(this, context || this.bgctx || this.ctx);
      return result;
    };
    canvas.drawConnections = drawConnectionsWithQwenLinks;
  }
  qwenCanvasBridgeCleanup = () => {
    for (const target of pointerTargets) {
      target.removeEventListener?.("pointerdown", rememberOutput, true);
      target.removeEventListener?.("pointermove", rememberOutput, true);
      target.removeEventListener?.("pointerup", handleDrop, true);
      target.removeEventListener?.("mouseup", handleDrop, true);
    }
    events?.removeEventListener?.("before-drop-links", beforeDropLinksHandler, { capture: true });
    events?.removeEventListener?.("dropped-on-canvas", droppedOnCanvasHandler, { capture: true });
    events?.removeEventListener?.("dropped-on-node", handleDrop, { capture: true });
    events?.removeEventListener?.("reset", resetHandler, { capture: true });
    if (canvas.drawConnections === drawConnectionsWithQwenLinks) canvas.drawConnections = originalDraw;
    canvas.__ryanQwenCanvasBridgeInstalled = false;
    if (qwenCanvasBridgeCanvas === canvas) qwenCanvasBridgeCanvas = null;
  };
  return true;
}

function ensureQwenCanvasBridgeSoon() {
  installQwenCanvasBridge();
  // ComfyUI can create this extension before the live canvas exists. Match
  // H3's delayed retries so gallery ports do not silently lose their bridge.
  setTimeout(() => installQwenCanvasBridge(), 0);
  setTimeout(() => installQwenCanvasBridge(), 500);
}

function patchQwenGraphToPrompt() {
  if (app.__ryanQwenGraphToPromptPatched || typeof app.graphToPrompt !== "function") return;
  app.__ryanQwenGraphToPromptPatched = true;
  const original = app.graphToPrompt;
  app.graphToPrompt = async function graphToPromptWithQwenImageLinks() {
    const promptData = await original.apply(this, arguments);
    for (const node of app.graph?._nodes || []) {
      if (!node.__ryanQwenImage21Installed) continue;
      const promptNode = promptData?.output?.[String(node.id)];
      if (!promptNode) continue;
      promptNode.inputs ||= {};
      for (let slot = 1; slot <= MAX_SLOTS; slot += 1) {
        const inputName = qwenImageSlotName(slot);
        const existing = promptNode.inputs[inputName];
        const ref = qwenImageSlotPromptRef(node, slot);
        if (ref) {
          if (!Array.isArray(existing) || existing.length < 2) {
            promptNode.inputs[inputName] = ref;
          }
          continue;
        }
        delete promptNode.inputs[inputName];
      }
      const promptInput = node.inputs?.find((input) => input.name === "prompt");
      const existingPrompt = promptNode.inputs.prompt;
      if (promptInput?.link == null) {
        // Keep the official prompt input name. The custom editor only changes
        // the value of that widget; it must not introduce prompt_text.
        promptNode.inputs.prompt = findWidget(node, "prompt")?.value ?? "";
      } else if (promptInput.link != null && (!Array.isArray(existingPrompt) || existingPrompt.length < 2)) {
        const native = getNativeGraphLink(node.graph || app.graph, promptInput.link);
        const originId = native?.origin_id ?? native?.originId;
        const originSlot = native?.origin_slot ?? native?.originSlot ?? 0;
        if (originId != null) promptNode.inputs.prompt = [String(originId), Number(originSlot) || 0];
      }
      delete promptNode.inputs.prompt_text;
      updateGalleryHiddenWidgets(node, qwenStateGallery(node));
      for (let slot = 1; slot <= MAX_SLOTS; slot += 1) {
        const galleryValue = findWidget(node, qwenGallerySlotName(slot))?.value;
        if (galleryValue) promptNode.inputs[qwenGallerySlotName(slot)] = galleryValue;
        else delete promptNode.inputs[qwenGallerySlotName(slot)];
      }
      promptNode.inputs.gallery_manifest = findWidget(node, "gallery_manifest")?.value || "[]";
      promptNode.inputs.prompt_mentions = findWidget(node, "prompt_mentions")?.value || "[]";
    }
    return promptData;
  };
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
  for (let slot = 1; slot <= MAX_SLOTS; slot += 1) {
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
  const count = visibleGallerySlotCount(node);
  const expanded = isGalleryExpanded(node);
  root.dataset.qwenNodeId = String(node.id ?? "");
  root.dataset.slotCount = String(count);
  root.dataset.expanded = expanded ? "true" : "false";
  const heading = root.querySelector(".ryan-qwen-image-heading");
  const headingLabel = heading?.querySelector?.(".ryan-qwen-image-heading-label");
  const toggle = heading?.querySelector?.(".ryan-qwen-image-toggle");
  if (headingLabel) headingLabel.textContent = `参考图片${expanded ? "" : " - 4"}`;
  if (toggle) {
    toggle.textContent = expanded ? "收起" : `展开其余 ${MAX_SLOTS - DEFAULT_VISIBLE_SLOTS} 个`;
    toggle.setAttribute("aria-expanded", expanded ? "true" : "false");
  }
  for (let slot = 1; slot <= MAX_SLOTS; slot += 1) {
    const cell = galleryCell(node, slot);
    if (!cell) continue;
    const active = slot <= count;
    const externallyConnected = isExternalSlotConnected(node, slot);
    const wired = externallyConnected;
    const item = galleryAssetAtSlot(state.gallery, slot);
    const source = wired ? qwenImageSlotSource(node, slot) : null;
    if (source?.sourceNode) watchQwenImageSourceNode(source.sourceNode, node);
    const previewSrc = item?.path ? viewUrl(item.path) : qwenSourcePreviewUrl(source?.sourceNode);
    const hasImage = Boolean(wired || item);
    cell.hidden = !active;
    cell.style.display = active ? "flex" : "none";
    cell.classList.toggle("is-disabled", !active);
    cell.classList.toggle("is-wired", wired);
    cell.classList.toggle("has-image", hasImage);
    cell.draggable = true;
    if (!item || wired) cell.draggable = false;
    cell.replaceChildren();

    if (previewSrc) {
      const preview = document.createElement("img");
      preview.className = "ryan-qwen-image-preview";
      preview.alt = "";
      preview.draggable = false;
      preview.src = previewSrc;
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
      ? (qwenSourceFilename(source?.sourceNode) || `外部输入 ${qwenImageSlotName(slot)}`)
      : item?.filename || "点击添加图片";
    cell.append(badge, port, status);

    if (hasImage) {
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "ryan-qwen-image-slot-clear";
      remove.textContent = "×";
      remove.title = "移除图片";
      remove.addEventListener("pointerdown", (event) => {
        event.preventDefault();
        event.stopPropagation();
      });
      remove.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        clearQwenImageSlot(node, slot);
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
  root.dataset.qwenNodeId = String(node.id ?? "");
  const heading = document.createElement("div");
  heading.className = "ryan-qwen-image-heading";
  const headingLabel = document.createElement("span");
  headingLabel.className = "ryan-qwen-image-heading-label";
  headingLabel.textContent = "参考图片";
  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "ryan-qwen-image-toggle";
  toggle.addEventListener("pointerdown", (event) => event.stopPropagation());
  toggle.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    node.__ryanQwenGalleryExpanded = !isGalleryExpanded(node);
    persistQwenState(node);
    updateGalleryVisibility(node);
  });
  heading.append(headingLabel, toggle);
  const grid = document.createElement("div");
  grid.className = "ryan-qwen-image-grid";
  const state = {
    gallery: getManifest(node),
    sync() {
      this.gallery = normalizeGalleryForState(this.gallery);
      updateGalleryHiddenWidgets(node, this.gallery);
      persistQwenState(node);
      updateGalleryVisibility(node);
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
  root.addEventListener("pointerup", (event) => {
    if (event.button > 0) return;
    const pending = qwenPendingConnectorLink(app.canvas);
    if (pending?.direction !== "from_output" || !pending.sourceNode) return;
    const cell = event.target?.closest?.(".ryan-qwen-image-slot");
    if (!cell || cell.classList.contains("is-disabled")) return;
    const slot = Number(cell.dataset.qwenSlot);
    if (!Number.isInteger(slot)) return;
    if (!connectQwenImageInput(node, pending.sourceNode, pending.sourceSlot, slot)) return;
    event.preventDefault();
    event.stopPropagation();
    app.canvas?.linkConnector?.reset?.();
  }, true);
  node.__ryanQwenGallery = root;
  node.__ryanQwenRenderGallery = () => renderImageGallery(node);
  renderImageGallery(node);
  return root;
}

function createPromptEditor(node, field, label, minHeight) {
  if (typeof document === "undefined") return null;
  const storageField = field;
  const widget = findWidget(node, storageField);
  if (!widget) return null;
  widget.hidden = true;
  widget.computeSize = () => [0, -4];

  const wrapper = document.createElement("section");
  wrapper.className = `ryan-qwen-prompt-wrap ryan-qwen-${field}-wrap`;
  wrapper.style.setProperty("--ryan-qwen-prompt-min-height", `${minHeight}px`);
  wrapper.style.setProperty("--ryan-qwen-prompt-height", `${minHeight + 19}px`);
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
    setWidgetValue(node, storageField, serializeEditor());
    setWidgetValue(node, "prompt_mentions", JSON.stringify([...existing, ...mentions]));
    persistQwenState(node);
    app.graph?.change?.();
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
  return { field, element: wrapper, editor, refresh };
}

function installQwenStyles() {
  let style = document.getElementById("ryan-qwen-image21-styles");
  if (!style) {
    style = document.createElement("style");
    style.id = "ryan-qwen-image21-styles";
    document.head.append(style);
  }
  style.textContent = `
    .ryan-qwen-workbench { display:flex; flex-direction:column; gap:8px; width:100%; max-width:100%; min-width:0; min-height:0; box-sizing:border-box; margin:2px 0 10px; padding:0 10px; overflow:hidden; color:var(--input-text,#ddd); font-family:system-ui,-apple-system,"Segoe UI",sans-serif; }
    .ryan-qwen-image-gallery { display:grid; grid-auto-rows:max-content; gap:4px; width:100%; max-width:100%; min-width:0; box-sizing:border-box; margin:2px 0 8px; padding:0 10px; overflow:hidden; color:var(--input-text,#ddd); font-family:system-ui,-apple-system,"Segoe UI",sans-serif; }
    .ryan-qwen-image-heading { display:flex; align-items:center; justify-content:space-between; min-width:0; color:rgba(255,255,255,.56); font-size:10px; font-weight:650; line-height:16px; letter-spacing:.035em; }
    .ryan-qwen-image-heading-label { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .ryan-qwen-image-toggle { appearance:none; padding:0 4px; border:0; border-radius:3px; background:transparent; color:rgba(255,255,255,.55); cursor:pointer; font:600 10px/16px system-ui,sans-serif; }
    .ryan-qwen-image-toggle:hover,.ryan-qwen-image-toggle:focus-visible { background:rgba(0,226,187,.12); color:rgba(255,255,255,.9); outline:none; }
    .ryan-qwen-prompt-heading { color:rgba(255,255,255,.56); font-size:10px; font-weight:650; line-height:16px; letter-spacing:.035em; }
    .ryan-qwen-image-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:4px; width:100%; max-width:100%; min-width:0; box-sizing:border-box; }
    .ryan-qwen-image-slot { appearance:none; position:relative; display:flex; align-items:center; justify-content:center; min-width:0; height:72px; overflow:hidden; box-sizing:border-box; padding:0; border:1px dashed rgba(255,255,255,.18); border-radius:7px; background:rgba(255,255,255,.035); color:rgba(255,255,255,.48); cursor:pointer; transition:border-color .12s ease,background-color .12s ease,opacity .12s ease,transform .12s ease; }
    .ryan-qwen-image-slot:hover,.ryan-qwen-image-slot:focus-visible,.ryan-qwen-image-slot.is-dragover { border-color:rgba(0,226,187,.64); background:rgba(0,226,187,.075); outline:none; }
    .ryan-qwen-image-slot.has-image[draggable="true"] { cursor:grab; }
    .ryan-qwen-image-slot.is-reordering { opacity:.45; cursor:grabbing; }
    .ryan-qwen-image-slot.is-reorder-target { border-color:rgba(79,150,255,.95); background:rgba(79,150,255,.16); box-shadow:inset 0 0 0 1px rgba(79,150,255,.4); }
    .ryan-qwen-image-slot:active:not(.is-disabled) { transform:scale(.985); }
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
    .ryan-qwen-image-slot-clear:hover,.ryan-qwen-image-slot-clear:focus-visible { background:rgba(212,70,70,.9); outline:none; }
    .ryan-qwen-prompt-wrap { position:relative; display:grid; grid-template-rows:max-content minmax(0,1fr); height:var(--ryan-qwen-prompt-height); flex:0 0 var(--ryan-qwen-prompt-height); gap:3px; min-width:0; min-height:calc(var(--ryan-qwen-prompt-min-height) + 19px); }
    .ryan-qwen-prompt-editor { display:block; width:100%; height:100%; min-width:0; min-height:0; max-height:none; box-sizing:border-box; padding:6px; overflow-y:auto; overflow-x:hidden; white-space:pre-wrap; overflow-wrap:anywhere; border:1px solid rgba(255,255,255,.14); border-radius:5px; outline:none; background:rgba(0,0,0,.28); color:var(--input-text,#ddd); caret-color:var(--input-text,#ddd); font-family:Consolas,"Courier New",monospace; font-size:12px; line-height:1.35; }
    .ryan-qwen-prompt-editor.is-connected { opacity:.58; cursor:not-allowed; background:rgba(255,255,255,.055); }
    .ryan-qwen-prompt-editor:focus { border-color:rgba(0,226,187,.7); }
    .ryan-qwen-prompt-editor:empty::before { content:attr(data-placeholder); color:rgba(255,255,255,.38); pointer-events:none; }
    .ryan-qwen-mention { display:inline-block; margin:0 2px; padding:1px 5px; border-radius:10px; background:#405b75; color:#fff; font-size:.9em; user-select:all; }
    .ryan-qwen-mention-menu { position:absolute; left:0; right:0; top:100%; z-index:30; display:flex; flex-direction:column; gap:2px; max-height:180px; overflow:auto; padding:4px; background:var(--comfy-menu-bg,#222); border:1px solid rgba(255,255,255,.18); border-radius:4px; box-shadow:0 4px 16px rgba(0,0,0,.38); }
    .ryan-qwen-mention-menu[hidden] { display:none; }
    .ryan-qwen-mention-menu button { appearance:none; text-align:left; padding:4px 6px; border:0; border-radius:3px; background:transparent; color:inherit; cursor:pointer; }
    .ryan-qwen-mention-menu button:hover { background:rgba(0,226,187,.16); }
  `;
}

function moveWidgetsBeforeResolution(node, widgets) {
  const anchor = node.widgets?.find((widget) => ["resolution_mode", "aspect_ratio", "megapixels"].includes(widget.name));
  if (!anchor || !Array.isArray(node.widgets)) return;
  const moving = widgets.filter((widget) => widget && node.widgets.includes(widget));
  if (!moving.length) return;
  for (let index = node.widgets.length - 1; index >= 0; index -= 1) {
    if (moving.includes(node.widgets[index])) node.widgets.splice(index, 1);
  }
  const target = node.widgets.indexOf(anchor);
  node.widgets.splice(target >= 0 ? target : node.widgets.length, 0, ...moving);
}

function setupNode(node) {
  if (!node || node.__ryanQwenImage21Installed) return;
  node.__ryanQwenImage21Installed = true;
  installQwenStyles();
  patchQwenGraphToPrompt();
  ensureQwenCanvasBridgeSoon();
  ensureQwenNumericDefaults(node);
  repairQwenWidgetValuesSoon(node);
  ensureQwenPromptInput(node);
  restoreQwenState(node);
  node._ryanQwenAllInputs ||= [...(node.inputs || [])];
  restoreQwenImageInputs(node);
  ensureQwenTypedInputs(node);
  installSlotGeometry(node);
  if (!node.__ryanQwenResizePatched) {
    node.__ryanQwenResizePatched = true;
    const originalResize = node.onResize;
    node.onResize = function onResizeQwenImage21() {
      const result = originalResize?.apply(this, arguments);
      if (Array.isArray(this.size) && this.size[0] < QWEN_NODE_MIN_WIDTH) {
        this.size[0] = QWEN_NODE_MIN_WIDTH;
      }
      return result;
    };
  }

  const gallery = createImageGallery(node);
  const promptEditors = [
    createPromptEditor(node, "prompt", "Prompt", 132),
    createPromptEditor(node, "negative_prompt", "Negative Prompt", 76),
  ].filter(Boolean);
  const positivePromptEditor = promptEditors.find((item) => item.field === "prompt");
  node.__ryanQwenPromptWrap = positivePromptEditor?.element || null;
  node.__ryanQwenPromptEditor = positivePromptEditor?.editor || null;
  updateQwenPromptConnectionState(node);
  const promptWorkbench = document.createElement("div");
  promptWorkbench.className = "ryan-qwen-workbench ryan-qwen-prompt-workbench";
  for (const editor of promptEditors) promptWorkbench.append(editor.element);

  if (typeof node.addDOMWidget === "function") {
    const galleryWidget = gallery && node.addDOMWidget(
      "ryan_qwen_image21_gallery",
      "ryan_qwen_image21_gallery",
      gallery,
      {
        serialize: false,
        hideOnZoom: false,
        margin: 0,
        getMinHeight: () => {
          const rows = Math.max(1, Math.ceil(visibleGallerySlotCount(node) / SLOTS_PER_ROW));
          return 16 + rows * 72 + Math.max(0, rows - 1) * 4 + 12;
        },
      },
    );
    const promptWidget = promptWorkbench.childElementCount && node.addDOMWidget(
      "ryan_qwen_image21_prompt_workbench",
      "ryan_qwen_image21_prompt_workbench",
      promptWorkbench,
      {
        serialize: false,
        hideOnZoom: false,
        margin: 0,
        getMinHeight: () => 151 + 8 + 95 + 12,
      },
    );
    const domWidgets = [galleryWidget, promptWidget].filter(Boolean);
    for (const domWidget of domWidgets) domWidget.serialize = false;
    moveWidgetsBeforeResolution(node, domWidgets);
    node.__ryanQwenWorkbench = promptWorkbench;
    node.__ryanQwenGalleryWidget = galleryWidget;
    node.__ryanQwenPromptWidget = promptWidget;
  }
  installQwenPersistenceHooks(node);
  ensureQwenNodeSize(node);

  node.__ryanQwenRefreshMentions = () => promptEditors.forEach((editor) => editor.refresh());
  const originalConnectionsChange = node.onConnectionsChange;
  node.onConnectionsChange = function onConnectionsChangeQwen() {
    const result = originalConnectionsChange?.apply(this, arguments);
    updateQwenPromptConnectionState(this);
    updateGalleryVisibility(this);
    this.__ryanQwenRefreshMentions?.();
    this.setDirtyCanvas?.(true, true);
    return result;
  };
  persistQwenState(node);
  updateGalleryVisibility(node);
}

app.registerExtension({
  name: "RyanComfyUtils.QwenImage21",
  setup() {
    ensureQwenCanvasBridgeSoon();
  },
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_NAME) return;

    const originalCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function onNodeCreatedQwenImage21() {
      originalCreated?.apply(this, arguments);
      setupNode(this);
    };

    const originalConfigure = nodeType.prototype.configure;
    nodeType.prototype.configure = function configureQwenImage21(info) {
      // Saved workflows made by older revisions may omit the hidden image_N
      // inputs. Restore them immediately after LiteGraph configures the node:
      // LinkConnector cannot snap to a port that is absent from node.inputs.
      if (Array.isArray(this._ryanQwenAllInputs) && this._ryanQwenAllInputs.length) {
        this.inputs = [...this._ryanQwenAllInputs];
      }
      const result = originalConfigure?.apply(this, arguments);
      const restored = restoreQwenState(this);
      this._ryanQwenAllInputs ||= [...(this.inputs || [])];
      if (!this.__ryanQwenImage21Installed) setupNode(this);
      restoreQwenImageInputs(this);
      ensureQwenNumericDefaults(this);
      repairQwenWidgetValuesSoon(this);
      ensureQwenPromptInput(this);
      ensureQwenTypedInputs(this);
      installQwenPersistenceHooks(this);
      // Restore after setup/default normalization as DOM widgets and combo
      // widgets can be inserted/reordered while configure is running.
      if (restored) restoreQwenState(this);
      else refreshQwenGalleryState(this);
      updateQwenPromptConnectionState(this);
      this.__ryanQwenRefreshMentions?.();
      persistQwenState(this);
      updateGalleryVisibility(this);
      return result;
    };
  },
});
