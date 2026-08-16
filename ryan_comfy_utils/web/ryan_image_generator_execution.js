import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

const NODE_NAME = "Ryan Image Generator";
const OVERLAY_TOP = 22;
const SHIMMER_CYCLE_MS = 1200;

function now() {
  return globalThis.performance?.now?.() ?? Date.now();
}

function matchesNode(node, detail) {
  const eventNodeIds = [detail?.node, detail?.node_id, detail?.display_node]
    .filter((value) => value !== undefined && value !== null);
  return eventNodeIds.some((value) => String(value) === String(node.id));
}

function samePrompt(execution, detail) {
  const eventPromptId = String(detail?.prompt_id ?? "");
  return !execution?.promptId || !eventPromptId || execution.promptId === eventPromptId;
}

function reducedMotion() {
  return Boolean(globalThis.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches);
}

function formatElapsed(milliseconds) {
  const seconds = Math.max(0, milliseconds) / 1000;
  return seconds < 60 ? `${seconds.toFixed(1)}s` : `${Math.floor(seconds / 60)}m ${(seconds % 60).toFixed(0)}s`;
}

function redraw(node) {
  node.graph?.setDirtyCanvas?.(true, false);
}

function cancelFrame(node) {
  const frame = node._ryanImageExecutionFrame;
  if (frame == null) return;

  if (node._ryanImageExecutionFrameType === "raf") {
    globalThis.cancelAnimationFrame?.(frame);
  } else {
    globalThis.clearTimeout?.(frame);
  }
  node._ryanImageExecutionFrame = null;
  node._ryanImageExecutionFrameType = "";
}

function scheduleFrame(node) {
  if (!node._ryanImageExecution || node._ryanImageExecutionFrame != null) return;

  const tick = () => {
    node._ryanImageExecutionFrame = null;
    node._ryanImageExecutionFrameType = "";
    if (!node._ryanImageExecution) return;
    redraw(node);
    scheduleFrame(node);
  };

  if (!reducedMotion() && typeof globalThis.requestAnimationFrame === "function") {
    node._ryanImageExecutionFrameType = "raf";
    node._ryanImageExecutionFrame = globalThis.requestAnimationFrame(tick);
  } else {
    // 降低动效模式仍然更新实时耗时，但不持续驱动高频视觉动画。
    node._ryanImageExecutionFrameType = "timeout";
    node._ryanImageExecutionFrame = globalThis.setTimeout(tick, 250);
  }
}

function startExecution(node, detail) {
  cancelFrame(node);
  node._ryanImageExecution = {
    promptId: String(detail?.prompt_id ?? ""),
    startedAt: now(),
  };
  redraw(node);
  scheduleFrame(node);
}

function finishExecution(node, detail) {
  const execution = node._ryanImageExecution;
  if (!execution || !samePrompt(execution, detail)) return;

  const duration = Math.max(0, now() - execution.startedAt);
  node._ryanImageLastDurationMs = duration;
  node._ryanImageExecution = null;
  cancelFrame(node);
  redraw(node);
}

function drawOverlay(ctx, node, execution, currentTime) {
  const width = Math.max(0, Number(node.size?.[0] || 0));
  const height = Math.max(0, Number(node.size?.[1] || 0));
  const overlayHeight = Math.max(0, height - OVERLAY_TOP);
  if (width <= 0 || overlayHeight <= 0) return;

  const elapsed = Math.max(0, currentTime - execution.startedAt);
  const motionReduced = reducedMotion();
  const phase = (elapsed % SHIMMER_CYCLE_MS) / SHIMMER_CYCLE_MS;

  ctx.save();
  ctx.fillStyle = "rgba(10, 16, 28, 0.78)";
  ctx.fillRect(0, OVERLAY_TOP, width, overlayHeight);

  ctx.strokeStyle = "rgba(126, 184, 255, 0.72)";
  ctx.lineWidth = 1;
  ctx.strokeRect(1, OVERLAY_TOP + 1, Math.max(0, width - 2), Math.max(0, overlayHeight - 2));

  ctx.fillStyle = "#d9e9ff";
  ctx.font = "bold 12px sans-serif";
  ctx.fillText("正在生成", 10, OVERLAY_TOP + 18);

  ctx.fillStyle = "#a9bdd7";
  ctx.font = "11px sans-serif";
  ctx.fillText(formatElapsed(elapsed), 10, OVERLAY_TOP + 36);

  const barX = 10;
  const barY = OVERLAY_TOP + 48;
  const barWidth = Math.max(0, width - 20);
  const barHeight = 4;
  ctx.fillStyle = "rgba(169, 205, 255, 0.20)";
  ctx.fillRect(barX, barY, barWidth, barHeight);

  if (barWidth > 0) {
    if (motionReduced) {
      ctx.fillStyle = "rgba(126, 184, 255, 0.75)";
      ctx.fillRect(barX, barY, barWidth, barHeight);
    } else {
      const sweepWidth = Math.max(28, barWidth * 0.28);
      const sweepX = barX - sweepWidth + (barWidth + sweepWidth) * phase;
      const gradient = ctx.createLinearGradient(sweepX, 0, sweepX + sweepWidth, 0);
      gradient.addColorStop(0, "rgba(126, 184, 255, 0)");
      gradient.addColorStop(0.5, "rgba(210, 235, 255, 0.95)");
      gradient.addColorStop(1, "rgba(126, 184, 255, 0)");
      ctx.fillStyle = gradient;
      ctx.fillRect(barX, barY, barWidth, barHeight);
    }
  }

  ctx.fillStyle = "rgba(217, 233, 255, 0.72)";
  ctx.font = "10px sans-serif";
  ctx.fillText("等待 API 返回…", 10, Math.max(OVERLAY_TOP + 66, height - 10));
  ctx.restore();
}

function setupExecutionUI(node) {
  if (node._ryanImageExecutionUIReady) return;
  node._ryanImageExecutionUIReady = true;

  const originalDrawForeground = node.onDrawForeground;
  node.onDrawForeground = function (ctx) {
    originalDrawForeground?.apply(this, arguments);
    const execution = this._ryanImageExecution;
    if (execution) drawOverlay(ctx, this, execution, now());
  };

  if (typeof api?.addEventListener !== "function") return;
  if (node._ryanImageExecutionEventsBound) return;
  node._ryanImageExecutionEventsBound = true;

  api.addEventListener("executing", (event) => {
    const detail = event?.detail || {};
    if (matchesNode(node, detail)) startExecution(node, detail);
  });

  api.addEventListener("executed", (event) => {
    const detail = event?.detail || {};
    if (matchesNode(node, detail)) finishExecution(node, detail);
  });

  api.addEventListener("execution_error", (event) => {
    const detail = event?.detail || {};
    if (matchesNode(node, detail)) finishExecution(node, detail);
  });

  api.addEventListener("execution_interrupted", (event) => {
    const detail = event?.detail || {};
    if (matchesNode(node, detail)) finishExecution(node, detail);
  });
}

app.registerExtension({
  name: "RyanComfyUtils.ImageGeneratorExecution",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_NAME) return;

    const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      originalOnNodeCreated?.apply(this, arguments);
      setupExecutionUI(this);
    };

    const originalConfigure = nodeType.prototype.configure;
    nodeType.prototype.configure = function () {
      const result = originalConfigure?.apply(this, arguments);
      setupExecutionUI(this);
      return result;
    };
  },

  loadedGraphNode(node) {
    if ((node.comfyClass || node.type) === NODE_NAME) setupExecutionUI(node);
  },
});
