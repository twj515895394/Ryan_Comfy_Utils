import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

const NODE_NAME = "Ryan Qwen Image 2.1";
const MAX_SLOTS = 16;
const SLOTS_PER_ROW = 4;
const DEFAULT_VISIBLE_SLOTS = SLOTS_PER_ROW;
const QWEN_NODE_MIN_WIDTH = 430;
const QWEN_NUMERIC_DEFAULTS = {
  megapixels: 1.0,
  batch_size: 1,
  resolution: 1024,
};
const QWEN_MEGAPIXEL_OPTIONS = [0.5, 0.75, 0.98, 1.0, 1.5, 2.0, 3.0, 4.0];
const SLOT_PREFIX = "image_";
const GALLERY_PREFIX = "gallery_";
const SLOT_REORDER_MIME = "application/x-ryan-qwen-image-reorder";
const QWEN_LINKS_PROP = "ryan_qwen_image_links";

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

function ensureQwenNumericDefaults(node) {
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

function ensureQwenNodeSize(node) {
  const measured = node.computeSize?.() || node.size || [QWEN_NODE_MIN_WIDTH, 0];
  const width = Math.max(QWEN_NODE_MIN_WIDTH, Number(measured[0]) || 0, Number(node.size?.[0]) || 0);
  const height = Math.max(1, Number(measured[1]) || 0, Number(node.size?.[1]) || 0);
  node.setSize?.([width, height]);
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

function addQwenVirtualLink(node, sourceNode, sourceSlot, sourceType, slot) {
  if (!node || !sourceNode || Number(node.id) === Number(sourceNode.id)) return false;
  const sourceId = Number(sourceNode.id);
  const targetSlot = Number(slot);
  if (!Number.isFinite(sourceId) || !Number.isInteger(targetSlot) || targetSlot < 1 || targetSlot > MAX_SLOTS) return false;
  const links = qwenLinks(node).filter((link) => Number(link.slot) !== targetSlot);
  links.push({
    source_id: sourceId,
    source_slot: Number(sourceSlot) || 0,
    source_type: sourceType || "IMAGE",
    slot: targetSlot,
  });
  node.properties[QWEN_LINKS_PROP] = links;
  node.setDirtyCanvas?.(true, true);
  app.graph?.setDirtyCanvas?.(true, true);
  app.graph?.change?.();
  updateGalleryVisibility(node);
  node.__ryanQwenRefreshMentions?.();
  return true;
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

function isExternalSlotConnected(node, slot) {
  return qwenLinks(node).some((link) => Number(link.slot) === Number(slot));
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
  node.__ryanQwenVisibleSlotCount = visibleCount;
  node.__ryanQwenRenderGallery?.();
  node._widgetSlotsDirty = true;
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
  const topLeft = clientToGraph(app.canvas, rect.left - 18, rect.top - 8);
  const bottomRight = clientToGraph(app.canvas, rect.right, rect.bottom);
  return Boolean(
    topLeft && bottomRight
      && x >= topLeft[0]
      && x <= bottomRight[0]
      && y >= topLeft[1]
      && y <= bottomRight[1],
  );
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
      if (input?.name === "prompt") {
        const graph = qwenPromptGraphPos(this);
        if (graph) return graph;
      }
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

function pruneQwenImageInputs(node) {
  if (!node?.inputs) return;
  for (let index = node.inputs.length - 1; index >= 0; index -= 1) {
    const input = node.inputs[index];
    if (!isQwenImageInput(input)) continue;
    const slot = Number(String(input.name).slice(6));
    const linkId = input.link;
    if (linkId != null) {
      const graph = node.graph || app.graph;
      const native = getNativeGraphLink(graph, linkId);
      const sourceId = native?.origin_id ?? native?.originId ?? native?.from_id ?? native?.fromId;
      const sourceNode = native?.origin_node || native?.originNode || native?.fromNode
        || graph?.getNodeById?.(Number(sourceId));
      const sourceSlot = native?.origin_slot ?? native?.originSlot ?? native?.from_slot ?? native?.fromSlot ?? 0;
      const sourceType = sourceNode?.outputs?.[Number(sourceSlot)]?.type || native?.type || "IMAGE";
      if (sourceNode) addQwenVirtualLink(node, sourceNode, sourceSlot, sourceType, slot);
      try { node.disconnectInput?.(index); } catch (_error) { /* The input is removed below. */ }
      if (input.link != null) {
        try { graph?.removeLink?.(input.link); } catch (_error) { /* Ignore stale graph links. */ }
        input.link = null;
      }
    }
    if (typeof node.removeInput === "function") node.removeInput(index);
    else node.inputs.splice(index, 1);
  }
  node._widgetSlotsDirty = true;
}

function qwenConnectingOutput(canvas) {
  const sourceNode = canvas?.connecting_node || canvas?.connectingNode;
  if (!sourceNode) return null;
  const raw = canvas.connecting_output ?? canvas.connecting_slot ?? canvas.connecting_output_slot;
  if (raw == null && canvas.connecting_input) return null;
  const sourceSlot = typeof raw === "number"
    ? raw
    : Number(raw?.slot_index ?? raw?.slot ?? raw ?? 0);
  if (!Number.isFinite(sourceSlot)) return null;
  const output = sourceNode.outputs?.[sourceSlot] || {};
  return {
    sourceNode,
    sourceSlot,
    sourceType: output.type || output.datatype || output.label || "IMAGE",
  };
}

function qwenGalleryCellFromEvent(event) {
  const element = document.elementFromPoint(Number(event?.clientX), Number(event?.clientY));
  const cell = element?.closest?.(".ryan-qwen-image-slot");
  if (!cell || cell.classList.contains("is-disabled")) return null;
  const gallery = cell.closest(".ryan-qwen-image-gallery");
  const node = app.graph?.getNodeById?.(Number(gallery?.dataset?.qwenNodeId));
  const slot = Number(cell.dataset.qwenSlot);
  if (!node || !Number.isInteger(slot)) return null;
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
  if (!canvas?.canvas || canvas.__ryanQwenCanvasBridgeInstalled) return;
  canvas.__ryanQwenCanvasBridgeInstalled = true;
  let pendingOutput = null;
  const rememberOutput = () => {
    const current = qwenConnectingOutput(canvas);
    if (current) pendingOutput = current;
  };
  const handleDrop = (event) => {
    const current = qwenConnectingOutput(canvas) || pendingOutput;
    const hit = qwenGalleryCellFromEvent(event);
    if (!current || !hit || Number(current.sourceNode?.id) === Number(hit.node.id)) return;
    if (!addQwenVirtualLink(hit.node, current.sourceNode, current.sourceSlot, current.sourceType, hit.slot)) return;
    event.preventDefault?.();
    event.stopPropagation?.();
    event.stopImmediatePropagation?.();
    canvas.linkConnector?.reset?.();
    canvas.connecting_node = null;
    canvas.connecting_output = null;
    pendingOutput = null;
  };
  canvas.canvas.addEventListener("pointerdown", rememberOutput, true);
  canvas.canvas.addEventListener("pointermove", rememberOutput, true);
  window.addEventListener("pointerdown", rememberOutput, true);
  window.addEventListener("pointermove", rememberOutput, true);
  window.addEventListener("pointerup", handleDrop, true);
  window.addEventListener("mouseup", handleDrop, true);
  if (typeof canvas.drawConnections === "function") {
    const originalDraw = canvas.drawConnections;
    canvas.drawConnections = function drawConnectionsWithQwenLinks(context) {
      const result = originalDraw?.apply(this, arguments);
      drawQwenVirtualLinks(this, context || this.bgctx || this.ctx);
      return result;
    };
  }
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
        delete promptNode.inputs[qwenImageSlotName(slot)];
      }
      for (const link of qwenLinks(node)) {
        promptNode.inputs[qwenImageSlotName(Number(link.slot))] = [
          String(link.source_id),
          Number(link.source_slot) || 0,
        ];
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
    const hasImage = Boolean(wired || item);
    cell.hidden = !active;
    cell.style.display = active ? "flex" : "none";
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
  if (document.getElementById("ryan-qwen-image21-styles")) return;
  const style = document.createElement("style");
  style.id = "ryan-qwen-image21-styles";
  style.textContent = `
    .ryan-qwen-workbench { display:flex; flex-direction:column; gap:8px; width:auto; min-width:0; min-height:0; box-sizing:border-box; margin:2px 10px 10px; color:var(--input-text,#ddd); font-family:system-ui,-apple-system,"Segoe UI",sans-serif; }
    .ryan-qwen-image-gallery { display:grid; grid-auto-rows:max-content; gap:4px; min-width:0; margin:2px 10px 8px; color:var(--input-text,#ddd); font-family:system-ui,-apple-system,"Segoe UI",sans-serif; }
    .ryan-qwen-image-heading { display:flex; align-items:center; justify-content:space-between; min-width:0; color:rgba(255,255,255,.56); font-size:10px; font-weight:650; line-height:16px; letter-spacing:.035em; }
    .ryan-qwen-image-heading-label { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .ryan-qwen-image-toggle { appearance:none; padding:0 4px; border:0; border-radius:3px; background:transparent; color:rgba(255,255,255,.55); cursor:pointer; font:600 10px/16px system-ui,sans-serif; }
    .ryan-qwen-image-toggle:hover,.ryan-qwen-image-toggle:focus-visible { background:rgba(0,226,187,.12); color:rgba(255,255,255,.9); outline:none; }
    .ryan-qwen-prompt-heading { color:rgba(255,255,255,.56); font-size:10px; font-weight:650; line-height:16px; letter-spacing:.035em; }
    .ryan-qwen-image-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:4px; width:100%; min-width:0; box-sizing:border-box; }
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
  document.head.append(style);
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
  ensureQwenNumericDefaults(node);
  ensureQwenPromptInput(node);
  pruneQwenImageInputs(node);
  installSlotGeometry(node);
  installQwenCanvasBridge();
  setTimeout(() => installQwenCanvasBridge(), 0);
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
  updateGalleryVisibility(node);
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
      pruneQwenImageInputs(this);
      if (!this.__ryanQwenImage21Installed) setupNode(this);
      ensureQwenNumericDefaults(this);
      ensureQwenPromptInput(this);
      updateQwenPromptConnectionState(this);
      this.__ryanQwenRefreshMentions?.();
      updateGalleryVisibility(this);
      return result;
    };
  },
});
