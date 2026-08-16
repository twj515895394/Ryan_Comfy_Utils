import { app } from "../../../../scripts/app.js";
import { api } from "../../../../scripts/api.js";

const NODE_NAME = "Ryan Workflow Agent";
const STATUS_WIDGET = "commit_revision";
const OPEN_EVENT = "ryan-workflow-agent-open-chat";
const MAX_CONTEXT_SLOTS = 8;

const MAX_IMAGE_SLOTS = 10;
const CONTEXT_CACHE_KEY = "__ryanWorkflowAgentContexts";
const STARTER_AGENT_NAMES = {
  "creative-story-planner": "创意策划",
  "production-designer": "美术 / 资产设计",
  "script-director": "剧本导演",
  "storyboard-director": "分镜导演",
  "audio-director": "音频导演",
  "video-prompt-director": "视频提示词导演",
};

function cacheAgentContext(node, context) {
  if (!node?.id || !context || typeof context !== "object") return;
  globalThis[CONTEXT_CACHE_KEY] ||= {};
  globalThis[CONTEXT_CACHE_KEY][String(node.id)] = context;
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
    || readExecutedContext(candidate.result, depth + 1)
  );
}

function findWidget(node, name) {
  return node.widgets?.find((widget) => widget.name === name);
}

function ensureCommitRevision(node) {
  const widget = findWidget(node, STATUS_WIDGET);
  if (!widget) return false;
  const value = Number(widget.value);
  const revision = Number.isFinite(value) && value >= 0 ? Math.trunc(value) : 0;
  const normalized = String(revision);
  if (String(widget.value ?? "") === normalized) return false;
  widget.value = normalized;
  node.graph?.change?.();
  return true;
}


function newId(prefix) {
  try {
    const uuid = globalThis.crypto?.randomUUID?.();
    if (uuid) return `${prefix}_${uuid.replaceAll("-", "")}`;
  } catch (_error) {
    // 旧版浏览器没有 crypto.randomUUID 时使用降级 ID。
  }
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
}

function ryanMetadata(node) {
  const graph = node.graph || app.graph;
  if (!graph) return null;
  graph.extra ||= {};
  graph.extra.ryan_agent ||= {};
  return graph.extra.ryan_agent;
}

function ensureIdentity(node) {
  const workflowWidget = findWidget(node, "workflow_id");
  const agentWidget = findWidget(node, "agent_uid");
  if (!workflowWidget || !agentWidget) return false;

  const metadata = ryanMetadata(node);
  if (!metadata) return false;
  let changed = false;

  // ComfyUI 的 graph._workflow_id 是画布运行时身份，可能在重新加载/重建
  // Graph 时变化；Ryan 的 Scope 必须以持久化 widget/extra 为准，不能因此
  // 把同一个画布切到新仓库，导致 Commit 与 Queue 读取不同目录。
  if (!metadata.workflow_id) {
    metadata.workflow_id = workflowWidget.value || newId("wf");
    changed = true;
  }
  if (workflowWidget.value !== metadata.workflow_id) {
    workflowWidget.value = metadata.workflow_id;
    changed = true;
  }
  if (!agentWidget.value) {
    agentWidget.value = newId("agent");
    changed = true;
  }
  if (changed) {
    node.graph?.change?.();
    redraw(node);
  }
  return changed;
}


function recommendedAgentName(skillId) {
  return STARTER_AGENT_NAMES[skillId] || (skillId && skillId !== "none" ? skillId : "Workflow Agent");
}

function syncAgentName(node) {
  const skillWidget = findWidget(node, "skill_id");
  const nameWidget = findWidget(node, "agent_name");
  if (!skillWidget || !nameWidget || nameWidget._ryanManualName) return;
  const value = recommendedAgentName(String(skillWidget.value || "none"));
  if (!nameWidget.value || nameWidget._ryanAutoName) {
    nameWidget.value = value;
    nameWidget._ryanAutoName = true;
  }
}

function bindSemanticWidgets(node) {
  const skillWidget = findWidget(node, "skill_id");
  if (skillWidget && !skillWidget._ryanCallbackBound) {
    node._ryanSkillId = String(skillWidget.value || "none");
    const originalCallback = skillWidget.callback;
    skillWidget.callback = function (value) {
      const nextSkillId = String(value || "none");
      const skillChanged = node._ryanSkillId && node._ryanSkillId !== nextSkillId;
      originalCallback?.apply(this, arguments);
      // Skill 切换代表新的工作阶段，必须隔离旧 Commit，避免沿用旧阶段的 UID。
      if (skillChanged) regenerateAgentIdentity(node);
      node._ryanSkillId = nextSkillId;
      syncAgentName(node);
      redraw(node);
    };
    skillWidget._ryanCallbackBound = true;
  }
  const nameWidget = findWidget(node, "agent_name");
  if (nameWidget && !nameWidget._ryanCallbackBound) {
    const originalCallback = nameWidget.callback;
    nameWidget.callback = function (value) {
      nameWidget._ryanManualName = true;
      nameWidget._ryanAutoName = false;
      originalCallback?.apply(this, arguments);
      redraw(node);
    };
    nameWidget._ryanCallbackBound = true;
  }
  syncAgentName(node);
}

function slotIndex(name, prefix) {
  const match = String(name || "").match(new RegExp(`^${prefix}_(\\d+)$`));
  return match ? Number(match[1]) : 0;
}

function countWidgetValue(node, name, maximum, fallback) {
  const widget = findWidget(node, name);
  const value = Number(widget?.value);
  return Math.max(0, Math.min(maximum, Number.isFinite(value) ? Math.round(value) : fallback));
}

function isConnected(input) {
  return input?.link !== null && input?.link !== undefined;
}

function applyInputVisibility(node) {
  if (!node._ryanAllInputs) node._ryanAllInputs = [...(node.inputs || [])];
  const contextCount = countWidgetValue(node, "context_slot_count", MAX_CONTEXT_SLOTS, 1);
  const imageCount = countWidgetValue(node, "image_slot_count", MAX_IMAGE_SLOTS, 1);
  const inputs = [];

  for (const input of node._ryanAllInputs) {
    const contextIndex = slotIndex(input.name, "context");
    const imageIndex = slotIndex(input.name, "image");
    const visible = contextIndex
      ? contextIndex <= contextCount || isConnected(input)
      : imageIndex
        ? imageIndex <= imageCount || isConnected(input)
        : true;
    if (visible) inputs.push(input);
  }
  node.inputs = inputs;
  const contextWidget = findWidget(node, "context_slot_count");
  const imageWidget = findWidget(node, "image_slot_count");
  if (contextWidget) contextWidget.value = contextCount;
  if (imageWidget) imageWidget.value = imageCount;
  node.setSize?.(node.computeSize?.());
  app.graph?.setDirtyCanvas?.(true, true);
}

function restoreAllInputs(node) {
  if (node._ryanAllInputs) node.inputs = [...node._ryanAllInputs];
}

function syncInputBackup(node) {
  if (!node._ryanAllInputs) return;
  for (const input of node.inputs || []) {
    const backup = node._ryanAllInputs.find((item) => item.name === input.name);
    if (backup) backup.link = input.link;
  }
}

function setupInputControls(node) {
  if (!node._ryanAllInputs) node._ryanAllInputs = [...(node.inputs || [])];
  let updateWidget = findWidget(node, "Update Inputs");
  if (!updateWidget) {
    updateWidget = node.addWidget?.("button", "Update Inputs", null, () => applyInputVisibility(node));
  }
  if (updateWidget) updateWidget._ryanInputControl = true;
  applyInputVisibility(node);
}

function redraw(node) {
  node.setSize?.(node.computeSize?.());
  node.graph?.setDirtyCanvas?.(true, true);
}

function setupAgentUI(node) {
  ensureIdentity(node);
  ensureCommitRevision(node);
  bindSemanticWidgets(node);
  setupInputControls(node);
  if (node._ryanWorkflowAgentUIReady) return;
  node._ryanWorkflowAgentUIReady = true;
  if (!node._ryanExecutedBridge && typeof api?.addEventListener === "function") {
    node._ryanExecutedBridge = true;
    api.addEventListener("executed", (event) => {
      const detail = event?.detail || {};
      if (String(detail.node) !== String(node.id)) return;
      node.onExecuted?.(detail.output || {});
    });
  }

  const openChat = () => {
    ensureIdentity(node);
    syncAgentName(node);
    window.dispatchEvent(new CustomEvent(OPEN_EVENT, {
      detail: {
        workflowId: findWidget(node, "workflow_id")?.value || "",
        agentUid: findWidget(node, "agent_uid")?.value || "",
        skillId: findWidget(node, "skill_id")?.value || "",
        agentName: findWidget(node, "agent_name")?.value || "",
        contextReceived: Boolean(node._ryanContext),
        context: node._ryanContext || {
          workflow_id: findWidget(node, "workflow_id")?.value || "",
          entries: [],
          assets: [],
        },
      },
    }));
    redraw(node);
  };

  let openWidget = node.widgets?.find((widget) => widget.name === "open_chat" || widget.name === "Open Chat");
  if (!openWidget) {
    openWidget = node.addWidget?.("button", "Open Chat", null, openChat);
  } else {
    openWidget.name = "Open Chat";
    openWidget.callback = openChat;
  }

  const originalDrawForeground = node.onDrawForeground;
  node.onDrawForeground = function (ctx) {
    originalDrawForeground?.apply(this, arguments);
    const state = this._ryanAgentState || {};
    const revision = Number(state.commitRevision || findWidget(this, STATUS_WIDGET)?.value || 0);
    const status = state.status === "error" ? "Error" :
      state.status === "submitting" ? "Sending…" :
      state.status === "generating" ? "Generating…" :
      state.status === "stopped" ? "Stopped" :
      state.upstreamChanged ? "Upstream changed" :
      revision > 0 ? `Committed v${revision}` :
      state.draft ? "Discussing" : "Not started";
    const errorDetail = state.status === "error" && state.error
      ? String(state.error).replace(/\s+/g, " ").trim().slice(0, 72)
      : "";
    if (this._ryanPanelOpen) {
      ctx.strokeStyle = "#aab3ff";
      ctx.lineWidth = 2;
      ctx.strokeRect(1, 1, this.size[0] - 2, this.size[1] - 2);
    }
    ctx.save();
    ctx.font = "11px sans-serif";
    const active = state.status === "submitting" || state.status === "generating";
    ctx.fillStyle = state.status === "error" ? "#ef8a8a" : active ? "#aab3ff" : state.upstreamChanged ? "#e8b86a" : revision > 0 ? "#8fd694" : "#a7a7a7";
    if (errorDetail) {
      ctx.font = "10px sans-serif";
      ctx.fillText(errorDetail, 8, this.size[1] - 22);
      ctx.font = "11px sans-serif";
    }
    ctx.fillText(status, 8, this.size[1] - 8);
    ctx.restore();
  };

  const originalDblClick = node.onDblClick;
  node.onDblClick = function () {
    originalDblClick?.apply(this, arguments);
    openChat();
  };
  const publishContext = (targetNode, raw) => {
    const context = readExecutedContext(raw);
    if (!context || !targetNode) return false;
    targetNode._ryanContext = context;
    cacheAgentContext(targetNode, context);
    window.dispatchEvent(new CustomEvent("ryan-workflow-agent-context", {
      detail: {
        nodeId: targetNode.id,
        workflowId: findWidget(targetNode, "workflow_id")?.value || "",
        agentUid: findWidget(targetNode, "agent_uid")?.value || "",
        context,
      },
    }));
    return true;
  };
  const originalExecuted = node.onExecuted;
  node.onExecuted = function (output) {
    originalExecuted?.apply(this, arguments);
    publishContext(this, output);
  };
  if (!node._ryanAgentExecutedApiBound && typeof api?.addEventListener === "function") {
    node._ryanAgentExecutedApiBound = true;
    api.addEventListener("executed", (event) => {
      const detail = event?.detail || {};
      const executedId = String(detail.node ?? detail.node_id ?? "");
      if (!executedId || String(node.id) !== executedId.split(":")[0]) return;
      publishContext(node, detail.output || detail);
    });
  }

  window.addEventListener("ryan-workflow-agent-state", (event) => {
    const detail = event.detail || {};
    const workflowId = findWidget(node, "workflow_id")?.value || "";
    const agentUid = findWidget(node, "agent_uid")?.value || "";
    if (String(detail.workflowId) !== String(workflowId) || String(detail.agentUid) !== String(agentUid)) return;
    if (detail.commitRevision !== undefined && Number.isFinite(Number(detail.commitRevision))) {
      const revisionWidget = findWidget(node, STATUS_WIDGET);
      if (revisionWidget) revisionWidget.value = String(Math.max(0, Math.trunc(Number(detail.commitRevision))));
      node.graph?.change?.();
    }
    node._ryanAgentState = detail;
    redraw(node);
  });
  window.addEventListener("ryan-workflow-agent-panel", (event) => {
    const detail = event.detail || {};
    node._ryanPanelOpen = Boolean(detail.open) && String(detail.agentUid) === String(findWidget(node, "agent_uid")?.value || "");
    redraw(node);
  });
  redraw(node);
}

app.registerExtension({
  name: "RyanComfyUtils.WorkflowAgent",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_NAME) return;
    const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      originalOnNodeCreated?.apply(this, arguments);
      setupAgentUI(this);
    };

    const originalConfigure = nodeType.prototype.configure;
    nodeType.prototype.configure = function () {
      restoreAllInputs(this);
      const result = originalConfigure?.apply(this, arguments);
      syncInputBackup(this);
      setupAgentUI(this);
      redraw(this);
      return result;
    };

    const originalClone = nodeType.prototype.clone;
    if (typeof originalClone === "function") {
      nodeType.prototype.clone = function () {
        const clone = originalClone.apply(this, arguments);
        if (clone) {
          regenerateAgentIdentity(clone);
          setupAgentUI(clone);
        }
        return clone;
      };
    }
  },

  loadedGraphNode(node) {
    if ((node.comfyClass || node.type) === NODE_NAME) setupAgentUI(node);
  },
});
