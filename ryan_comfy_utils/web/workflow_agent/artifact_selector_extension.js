import { app } from "../../../../scripts/app.js";
import { api } from "../../../../scripts/api.js";

const NODE_NAME = "Ryan Artifact Selector";
const LEGACY_FIELDS = ["source_agent_uid", "artifact_type", "output_id", "shot_id", "kind", "revision"];
const HIDDEN_FIELDS = [...LEGACY_FIELDS, "source_agent", "shot_scope", "purpose", "target_id"];
const SELECTION_OPTIONS = [
  { value: "auto", label: "自动读取最新内容" },
  { value: "concept_image_prompt", label: "概念图提示词" },
  { value: "image_prompt", label: "图像提示词" },
  { value: "storyboard_prompt", label: "分镜提示词" },
  { value: "keyframe_prompt", label: "关键帧提示词" },
  { value: "audio_prompt", label: "音频提示词" },
  { value: "video_prompt", label: "视频提示词" },
  { value: "shot_prompt", label: "指定镜头提示词" },
];
const AUTO_SHOT = "自动选择镜头";
const EMPTY_TARGET = "上游暂无可选对象";
const SELECTION_KINDS = {
  concept_image_prompt: ["concept_image_prompt"],
  image_prompt: ["image_prompt"],
  storyboard_prompt: ["storyboard_prompt", "storyboard_sheet_prompt", "shot_prompt"],
  keyframe_prompt: ["keyframe_prompt"],
  audio_prompt: ["audio_prompt"],
  video_prompt: ["video_prompt", "shot_video_prompt"],
};
const KIND_LABELS = {
  concept_image_prompt: "概念图提示词",
  image_prompt: "图像提示词",
  storyboard_prompt: "分镜提示词",
  storyboard_sheet_prompt: "分镜表提示词",
  keyframe_prompt: "关键帧提示词",
  audio_prompt: "音频提示词",
  shot_prompt: "镜头提示词",
  video_prompt: "视频提示词",
  shot_video_prompt: "镜头视频提示词",
  continuity_constraint: "连续性约束",
};

function findWidget(node, name) {
  return node.widgets?.find(
    (widget) => widget?.name === name || widget?._ryanSelectorFieldName === name,
  );
}

function readableKind(value) {
  return KIND_LABELS[String(value)] || String(value || "未分类");
}

function ensureComboWidget(node, name, values) {
  let widget = findWidget(node, name);
  if (!widget) return widget;
  // 原生 COMBO 已由 ComfyUI 实例化为 ComboWidget；这里只更新选项。
  // 旧工作流中的 STRING Widget 仍需一次性替换为原生实例，不能只改 type。
  if (widget.type !== "combo") {
    const index = node.widgets.indexOf(widget);
    const replacement = node.addWidget?.(
      "combo",
      name,
      widget.value || (Array.isArray(values) && values[0]) || AUTO_SHOT,
      widget.callback,
      { values: Array.isArray(values) && values.length ? values : [widget.value || AUTO_SHOT] },
    );
    if (replacement) {
      replacement._ryanSelectorFieldName = name;
      node.widgets.splice(index, 1, replacement);
      widget = replacement;
    }
  }
  widget.type = "combo";
  widget.options ||= {};
  widget.options.values = Array.isArray(values) && values.length ? values : [widget.value || AUTO_SHOT];
  if (widget.value == null || widget.value === "") {
    widget.value = widget.options.values[0];
  }
  return widget;
}

function normalizeArtifactBundle(bundle) {
  if (!bundle || typeof bundle !== "object") return null;
  const normalized = { ...bundle, schema_version: bundle.schema_version ?? 1 };
  normalized.outputs = Array.isArray(bundle.outputs)
    ? bundle.outputs.map((item) => {
      if (!item || typeof item !== "object") return item;
      const output = { ...item };
      if (!Object.prototype.hasOwnProperty.call(output, "output_id")) output.output_id = output.id;
      if (!Object.prototype.hasOwnProperty.call(output, "text")) {
        output.text = output.prompt ?? output.constraint;
      }
      if (!Object.prototype.hasOwnProperty.call(output, "label")) output.label = output.role ?? output.id;
      if (!Object.prototype.hasOwnProperty.call(output, "priority")) output.priority = 50;
      return output;
    })
    : [];
  normalized.shots = Array.isArray(bundle.shots)
    ? bundle.shots.map((item) => {
      if (!item || typeof item !== "object") return item;
      const shot = { ...item };
      if (!Object.prototype.hasOwnProperty.call(shot, "shot_id")) shot.shot_id = shot.id;
      if (!Object.prototype.hasOwnProperty.call(shot, "prompt")) {
        shot.prompt = shot.text ?? shot.constraint;
      }
      if (!Object.prototype.hasOwnProperty.call(shot, "label")) shot.label = shot.role ?? shot.id;
      if (!Object.prototype.hasOwnProperty.call(shot, "priority")) shot.priority = 50;
      return shot;
    })
    : [];
  return normalized;
}

function validArtifactBundle(bundle) {
  const normalized = normalizeArtifactBundle(bundle);
  if (!normalized) return false;
  const schemaVersion = normalized.schema_version;
  if (![1, 2].includes(schemaVersion) || typeof normalized.artifact_type !== "string" || !normalized.artifact_type.trim()) return false;
  if (!Array.isArray(normalized.outputs) || !Array.isArray(normalized.shots)) return false;
  const validPriority = (value) => Number.isInteger(value ?? 50) && value >= 0 && value <= 100;
  const validStringArray = (value) => Array.isArray(value) && value.length > 0
    && value.every((item) => typeof item === "string" && item.trim());
  const validOutput = (item) => item && typeof item === "object"
    && typeof item.output_id === "string" && item.output_id.trim()
    && typeof item.kind === "string" && item.kind.trim()
    && typeof item.label === "string" && item.label.trim()
    && typeof item.text === "string" && item.text.trim()
    && validPriority(item.priority)
    && (schemaVersion !== 2 || (typeof item.purpose === "string" && item.purpose.trim() && validStringArray(item.target_ids)));
  const validShot = (item) => item && typeof item === "object"
    && typeof item.shot_id === "string" && item.shot_id.trim()
    && typeof item.prompt === "string" && item.prompt.trim()
    && (item.kind === undefined || (typeof item.kind === "string" && item.kind.trim()))
    && (item.label === undefined || typeof item.label === "string")
    && validPriority(item.priority);
  return normalized.outputs.every(validOutput) && normalized.shots.every(validShot);
}

function bundleFromEntry(entry) {
  const metadataBundle = normalizeArtifactBundle(entry?.metadata?.artifact_bundle);
  if (validArtifactBundle(metadataBundle)) return metadataBundle;
  const match = String(entry?.content || "").match(/```ryan-artifact(?:[ \t]+)?\r?\n([\s\S]*?)\r?\n?```/);
  if (!match) return null;
  try {
    const contentBundle = normalizeArtifactBundle(JSON.parse(match[1]));
    return validArtifactBundle(contentBundle) ? contentBundle : null;
  } catch (_error) {
    return null;
  }
}

function contextChoices(context) {
  const entries = (Array.isArray(context?.entries) ? context.entries : [])
    .filter((entry) => entry?.status === "active" && entry?.source_agent_uid);
  const invalidArtifactCount = entries.filter((entry) => entry?.metadata?.artifact_status === "invalid").length;
  const latestBundles = new Map();
  entries.forEach((entry) => {
    const bundle = bundleFromEntry(entry);
    if (!bundle) return;
    const key = `${entry.source_agent_uid}::${bundle.artifact_type || ""}`;
    const previous = latestBundles.get(key);
    if (!previous || Number(entry.revision || 0) >= Number(previous.entry.revision || 0)) {
      latestBundles.set(key, { entry, bundle });
    }
  });
  const outputs = [];
  const shots = [];
  const shotTargets = [];
  const items = [];
  [...latestBundles.values()].forEach(({ entry, bundle }) => {
    const agentLabel = entry.source_agent_name || "上游 Agent";
    bundle.outputs.forEach((output) => {
      const targetText = Array.isArray(output.target_ids) && output.target_ids.length
        ? output.target_ids.join(" / ")
        : "未指定对象";
      const purposeText = output.purpose ? ` · 用途：${output.purpose}` : "";
      const item = {
        type: "output",
        value: String(output.output_id),
        outputId: String(output.output_id),
        kind: String(output.kind),
        purpose: String(output.purpose || ""),
        targetIds: Array.isArray(output.target_ids) ? output.target_ids.map(String) : [],
        artifactType: String(bundle.artifact_type || ""),
        sourceAgentUid: String(entry.source_agent_uid),
        label: `${agentLabel} · ${readableKind(output.kind)} · ${targetText}${purposeText}`,
        text: output.text,
      };
      outputs.push(item);
      items.push(item);
      item.targetIds
        .filter((targetId) => /^(SHOT|SEG)_/.test(targetId))
        .forEach((targetId) => {
          const targetItem = {
            ...item,
            type: "target",
            value: targetId,
            outputId: "",
            shotId: targetId,
            label: `${agentLabel} · ${targetId} · ${readableKind(output.kind)}`,
          };
          shotTargets.push(targetItem);
          items.push(targetItem);
        });
    });
    bundle.shots.forEach((shot) => {
      const item = {
        type: "shot",
        value: String(shot.shot_id),
        shotId: String(shot.shot_id),
        kind: String(shot.kind || "shot_prompt"),
        purpose: "",
        targetIds: [String(shot.shot_id)],
        artifactType: String(bundle.artifact_type || ""),
        sourceAgentUid: String(entry.source_agent_uid),
        label: `${agentLabel} · ${readableKind(shot.kind || "shot_prompt")} · ${shot.label || "未命名镜头"}`,
        text: shot.prompt,
      };
      shots.push(item);
      items.push(item);
    });
  // 同一 Agent 可能输出多个同类型对象；重复展示文本会让下拉项无法区分。
  // 仅对重复 label 追加稳定 ID，单个对象仍保持原有可读 label。
  const labelCounts = new Map();
  items.forEach((item) => {
    labelCounts.set(item.label, (labelCounts.get(item.label) || 0) + 1);
  });
  items.forEach((item) => {
    if (labelCounts.get(item.label) <= 1) return;
    const suffix = item.outputId || item.shotId || item.value;
    item.label = `${item.label} · ${suffix}`;
  });
  return {
    hasContext: entries.length > 0,
    invalidArtifactCount,
    outputs,
    shots,
    shotTargets,
    items,
  };
}


function setHidden(widget, hidden) {
  if (!widget) return;
  widget.options ||= {};
  if (hidden) {
    if (!Object.prototype.hasOwnProperty.call(widget, "_ryanSelectorOriginalComputeSize")) {
      widget._ryanSelectorOriginalComputeSize = widget.computeSize;
      widget._ryanSelectorHadComputeSize = Object.prototype.hasOwnProperty.call(widget, "computeSize");
    }
    if (!Object.prototype.hasOwnProperty.call(widget, "_ryanSelectorOriginalType")) {
      widget._ryanSelectorOriginalType = widget.type;
    }
    widget.hidden = true;
    widget.disabled = false;
    widget.options.hidden = true;
    // ComfyUI 新版布局不仅检查尺寸，还会按 type 绘制 Widget；
    // 仅设置 hidden/computeSize 在部分前端版本仍会把字段画出来。
    widget.type = "hidden";
    widget.computeSize = () => [0, -4];
    if (widget.element) widget.element.style.display = "none";
    return;
  }
  widget.hidden = false;
  widget.disabled = false;
  widget.options.hidden = false;
  if (widget.element) widget.element.style.display = "";
  if (Object.prototype.hasOwnProperty.call(widget, "_ryanSelectorOriginalType")) {
    widget.type = widget._ryanSelectorOriginalType;
    delete widget._ryanSelectorOriginalType;
  }
  if (Object.prototype.hasOwnProperty.call(widget, "_ryanSelectorOriginalComputeSize")) {
    if (widget._ryanSelectorHadComputeSize) widget.computeSize = widget._ryanSelectorOriginalComputeSize;
    else delete widget.computeSize;
    delete widget._ryanSelectorOriginalComputeSize;
    delete widget._ryanSelectorHadComputeSize;
  }
}

function refreshNodeSize(node) {
  const computed = node.computeSize?.();
  if (!Array.isArray(computed)) return;
  const width = Math.max(Number(computed[0]) || 0, 280);
  const height = Math.max(Number(computed[1]) || 0, 120);
  node.setSize?.([width, height]);
}

function setSelectorStatus(node, status) {
  node._ryanSelectorStatus = String(status || "");
  node.graph?.setDirtyCanvas?.(true, true);
}

function installStatusRenderer(node) {
  if (node._ryanSelectorStatusRendererInstalled) return;
  node._ryanSelectorStatusRendererInstalled = true;
  const original = node.onDrawForeground;
  node.onDrawForeground = function () {
    original?.apply(this, arguments);
    const status = String(this._ryanSelectorStatus || "");
    if (!status) return;
    const ctx = arguments[0];
    ctx.save();
    ctx.font = "10px sans-serif";
    ctx.fillStyle = "#aab3ff";
    ctx.fillText(status, 8, this.size[1] - 8);
    ctx.restore();
  };
}

function installExecutionStatus(node) {
  if (node._ryanSelectorExecutionStatusInstalled) return;
  node._ryanSelectorExecutionStatusInstalled = true;
  const original = node.onExecuted;
  node.onExecuted = function (output) {
    original?.apply(this, arguments);
    const context = readExecutedContext(output);
    if (context) applySelectorContext(this, context, { markGraph: false });
    const value = Array.isArray(output) ? output[0] : output?.text ?? output?.string ?? output;
    if (String(value || "").trim()) setSelectorStatus(this, "已输出筛选后的提示词");
    else if (this._ryanSelectorChoices?.hasContext) setSelectorStatus(this, "没有找到符合条件的提示词");
  };
}

function semanticValue(widget) {
  const raw = String(widget?.value || "");
  return SELECTION_OPTIONS.find((option) => option.label === raw || option.value === raw)?.value || "auto";
}

function selectedArtifact(node) {
  const value = String(findWidget(node, "shot")?.value || "");
  return node._ryanSelectorChoices?.items?.find(
    (item) => item.label === value || item.value === value,
  ) || null;
}

function syncLegacyFromBasic(node) {
  const selected = selectedArtifact(node);
  const isOutput = selected?.type === "output";
  const isShot = selected?.type === "shot";
  const isTarget = selected?.type === "target";
  const values = {
    source_agent_uid: selected?.sourceAgentUid || "",
    artifact_type: selected?.artifactType || "",
    output_id: isOutput ? selected.outputId : "",
    shot_id: isShot || isTarget ? selected.shotId || selected.value : "",
    kind: selected?.kind || "",
    revision: 0,
  };
  LEGACY_FIELDS.forEach((name) => {
    const widget = findWidget(node, name);
    if (widget) widget.value = values[name] ?? "";
  });
  const targetWidget = findWidget(node, "target_id");
  const purposeWidget = findWidget(node, "purpose");
  const scopeWidget = findWidget(node, "shot_scope");
  if (targetWidget) targetWidget.value = selected?.targetIds?.[0] || "";
  if (purposeWidget) purposeWidget.value = selected?.purpose || "";
  // 选了具体对象后标记 selected，后端即可按 shot/label 解析；未选则保持 all。
  if (scopeWidget) scopeWidget.value = selected ? "selected" : "all";
}

function targetWidgetLabel(selection) {
  if (selection === "shot_prompt") return "选择镜头";
  if (selection === "audio_prompt" || selection === "video_prompt") return "选择 Segment";
  return "选择对象";
}

function emptyTargetLabel(selection) {
  if (selection === "shot_prompt") return "上游暂无可选镜头";
  if (selection === "audio_prompt" || selection === "video_prompt") return "上游暂无可选 Segment";
  return EMPTY_TARGET;
}

function updateTargetWidgetLabel(widget, selection) {
  if (!widget) return;
  const label = targetWidgetLabel(selection);
  // name 是 ComfyUI 提交给后端的输入键；只改 label，不能改成可读标题。
  widget.label = label;
}


function updateOptions(node) {
  const choices = contextChoices(node._ryanContext);
  const selectionWidget = findWidget(node, "selection");
  if (selectionWidget) {
    selectionWidget.type = "combo";
    selectionWidget.options ||= {};
    selectionWidget.options.values = SELECTION_OPTIONS.map((option) => option.label);
    if (!SELECTION_OPTIONS.some((option) => option.label === selectionWidget.value)) selectionWidget.value = SELECTION_OPTIONS[0].label;
  }
  const selection = semanticValue(selectionWidget);
  const kinds = SELECTION_KINDS[selection] || [];
  const visibleItems = selection === "shot_prompt"
    ? [...choices.shots, ...choices.shotTargets]
    : choices.outputs.filter((item) => !kinds.length || kinds.includes(item.kind));
  const shotWidget = ensureComboWidget(
    node,
    "shot",
    visibleItems.length
      ? [AUTO_SHOT, ...visibleItems.map((item) => item.label)]
      : [AUTO_SHOT, emptyTargetLabel(selection)],
  );
  updateTargetWidgetLabel(shotWidget, selection);
  if (shotWidget) {
    // 保持可序列化；无可选项时用占位值，不要 disabled（部分前端会丢弃 disabled widget）。
    shotWidget.disabled = false;
  }
  setHidden(shotWidget, selection === "auto");
  syncLegacyFromBasic(node);
  const originId = contextOriginId(node);
  if (!originId) setSelectorStatus(node, "请连接上游 Workflow Agent 的 context 输出");
  else if (!choices.hasContext) setSelectorStatus(node, "请 Queue 上游 Agent；若已 Queue 仍为空，检查 Agent 是否已 Commit 且 workflow_id/agent_uid 未变");
  else if (selection === "auto") setSelectorStatus(node, "自动模式输出最新 Canonical；选择类型后可取 Prompt");
  else if (choices.outputs.length || choices.shots.length || choices.shotTargets.length) setSelectorStatus(node, "已加载提示词，可选择类型与对象");
  else if (choices.invalidArtifactCount) setSelectorStatus(node, "上游结构化产物无效；自动模式仍可读取正文");
  else setSelectorStatus(node, "上游暂无结构化提示词，自动模式将读取最新正文");
  node._ryanSelectorChoices = choices;
}

function applySelectorContext(node, context, { markGraph = true } = {}) {
  if (!context || typeof context !== "object") return false;
  node._ryanContext = context;
  const originId = contextOriginId(node);
  if (originId) {
    globalThis.__ryanWorkflowAgentContexts ||= {};
    globalThis.__ryanWorkflowAgentContexts[String(originId)] = context;
  }
  updateOptions(node);
  if (markGraph) node.graph?.change?.();
  refreshNodeSize(node);
  return true;
}

function setupSelectorUI(node) {
  if (node._ryanSelectorReady) return;
  node._ryanSelectorReady = true;
  installStatusRenderer(node);
  installExecutionStatus(node);
  HIDDEN_FIELDS.forEach((name) => setHidden(findWidget(node, name), true));
  const selectionWidget = ensureComboWidget(
    node,
    "selection",
    SELECTION_OPTIONS.map((option) => option.label),
  );
  const shotWidget = ensureComboWidget(node, "shot", [AUTO_SHOT, EMPTY_TARGET]);
  if (shotWidget) shotWidget._ryanSelectorFieldName = "shot";
  node._ryanContext ||= cachedAgentContext(node);
  node._ryanSelectorChoices = contextChoices(node._ryanContext);
  updateOptions(node);
  refreshNodeSize(node);
  [selectionWidget, shotWidget].forEach((widget) => {
    if (!widget || widget._ryanSelectorCallbackBound) return;
    const originalCallback = widget.callback;
    widget.callback = function () {
      originalCallback?.apply(this, arguments);
      updateOptions(node);
      node.graph?.change?.();
      refreshNodeSize(node);
    };
    widget._ryanSelectorCallbackBound = true;
  });
  window.addEventListener("ryan-workflow-agent-context", (event) => {
    const detail = event.detail || {};
    const originId = contextOriginId(node);
    const eventNodeId = detail.nodeId != null ? String(detail.nodeId) : "";
    // origin 未解析时也接收，避免 links 结构差异导致永久空状态。
    if (originId && eventNodeId && eventNodeId !== String(originId)) return;
    applySelectorContext(node, detail.context || null);
  });
  if (!node._ryanSelectorExecutedApiBound && typeof api?.addEventListener === "function") {
    node._ryanSelectorExecutedApiBound = true;
    api.addEventListener("executed", (event) => {
      const detail = event?.detail || {};
      const executedId = String(detail.node ?? detail.node_id ?? "").split(":")[0];
      const originId = String(contextOriginId(node) || "");
      if (!executedId) return;
      // 上游 Agent 执行完：直接吃 context_json。
      if (originId && executedId === originId) {
        const ctx = readExecutedContext(detail.output || detail);
        if (ctx) applySelectorContext(node, ctx);
        return;
      }
      // Selector 自身执行完：优先使用 Selector 返回的真实 Context；
      // 若旧后端未返回 Context，再回退到来源 Agent 的页面缓存。
      if (String(node.id) === executedId) {
        const ctx = readExecutedContext(detail.output || detail);
        if (ctx) {
          applySelectorContext(node, ctx, { markGraph: false });
          return;
        }
        const cached = cachedAgentContext(node);
        if (cached) applySelectorContext(node, cached, { markGraph: false });
      }
    });
  }
  // 连线变化后立刻尝试从缓存灌入。
  const originalConnectionsChange = node.onConnectionsChange;
  node.onConnectionsChange = function () {
    originalConnectionsChange?.apply(this, arguments);
    const cached = cachedAgentContext(this);
    if (cached) applySelectorContext(this, cached, { markGraph: false });
    else updateOptions(this);
  };
}

function resolveGraphLink(linkId) {
  if (linkId == null || linkId === -1) return null;
  const graph = app.graph;
  const links = graph?.links;
  if (!links) return null;
  if (Array.isArray(links)) return links[linkId] || null;
  if (typeof links.get === "function") return links.get(linkId) || null;
  return links[linkId] || links[String(linkId)] || null;
}

function contextOriginId(node) {
  const input = node.inputs?.find((item) => item?.name === "context");
  if (!input) return "";
  const linkId = input.link ?? input.link_id ?? null;
  const direct = resolveGraphLink(linkId);
  if (direct) return String(direct.origin_id ?? direct.originId ?? "");
  // 兼容部分前端把多连接放在 links 数组。
  const multi = Array.isArray(input.links) ? input.links : [];
  for (const id of multi) {
    const link = resolveGraphLink(id);
    if (link) return String(link.origin_id ?? link.originId ?? "");
  }
  return "";
}

function readExecutedContext(value, depth = 0) {
  if (value == null || depth > 6) return null;
  const unwrap = (item) => (Array.isArray(item) ? item[0] : item);
  const candidate = unwrap(value);
  if (typeof candidate === "string") {
    const text = candidate.trim();
    if (!text) return null;
    try {
      return readExecutedContext(JSON.parse(text), depth + 1);
    } catch (_error) {
      return null;
    }
  }
  if (!candidate || typeof candidate !== "object") return null;
  if (candidate.workflow_id && Array.isArray(candidate.entries)) return candidate;
  return (
    readExecutedContext(candidate.context_json, depth + 1)
    || readExecutedContext(candidate.context, depth + 1)
    || readExecutedContext(candidate.output, depth + 1)
    || readExecutedContext(candidate.ui, depth + 1)
  );
}

function cachedAgentContext(node) {
  const originId = contextOriginId(node);
  if (!originId) return null;
  return globalThis.__ryanWorkflowAgentContexts?.[String(originId)] || null;
}

app.registerExtension({
  name: "RyanComfyUtils.ArtifactSelector",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_NAME) return;
    const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      originalOnNodeCreated?.apply(this, arguments);
      setupSelectorUI(this);
    };
    const originalConfigure = nodeType.prototype.configure;
    nodeType.prototype.configure = function () {
      const result = originalConfigure?.apply(this, arguments);
      setupSelectorUI(this);
      return result;
    };
  },
  loadedGraphNode(node) {
    if ((node.comfyClass || node.type) === NODE_NAME) setupSelectorUI(node);
  },
});

export { contextChoices, setupSelectorUI };
