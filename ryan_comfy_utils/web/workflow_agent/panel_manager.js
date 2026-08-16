import AgentPanel from "./agent_panel.js";

const WIDTH_KEY = "ryan.workflow-agent.panel-width";
const OPEN_EVENT = "ryan-workflow-agent-open-chat";

function el(tag, className) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  return node;
}

export class PanelManager {
  constructor({ api, store }) {
    this.api = api;
    this.store = store;
    this.active = null;
    this.root = el("div", "ryan-agent-dock");
    this.root.hidden = true;
    this.resizeHandle = el("div", "ryan-agent-dock__resize");
    this.panel = new AgentPanel({ api, store, onClose: () => this.close(), onState: (state) => this.publishState(state), toast: (message, tone) => this.toast(message, tone) });
    this.root.append(this.resizeHandle);
    this.panel.mount(this.root);
    this.setupResize();
    this.restoreWidth();
    window.addEventListener(OPEN_EVENT, (event) => this.open(event.detail || {}));
    window.addEventListener("ryan-workflow-agent-context", (event) => this.handleContextEvent(event.detail || {}));

    window.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && this.isOpen() && document.activeElement?.tagName !== "TEXTAREA") this.close();
    });
  }
  handleContextEvent(detail = {}) {
    if (!this.active || String(detail.workflowId || detail.workflow_id) !== String(this.active.workflowId) || String(detail.agentUid || detail.agent_uid) !== String(this.active.agentUid)) return;
    if (!detail.context || typeof detail.context !== "object") return;
    this.panel.context = detail.context;
    this.panel.state = this.store.set(this.active.workflowId, this.active.agentUid, { context: detail.context, contextReceived: true });
    this.panel.renderState();
  }

  mount(parent = document.body) { parent.append(this.root); }
  isOpen() { return !this.root.hidden; }

  async open(detail) {
    this.active = { workflowId: String(detail.workflowId || detail.workflow_id || ""), agentUid: String(detail.agentUid || detail.agent_uid || "") };
    if (!this.active.workflowId || !this.active.agentUid) return;
    this.root.hidden = false;
    this.root.classList.add("is-open");
    this.publishPanel(true);
    await this.panel.open(detail);
  }

  close() {
    if (!this.isOpen()) return;
    this.root.classList.remove("is-open");
    this.root.hidden = true;
    this.publishPanel(false);
  }

  publishPanel(open) {
    window.dispatchEvent(new CustomEvent("ryan-workflow-agent-panel", { detail: { ...this.active, open } }));
  }

  publishState(state) {
    if (!state?.agentUid) return;
    window.dispatchEvent(new CustomEvent("ryan-workflow-agent-state", { detail: state }));
  }

  handleAgentEvent(event = {}) {
    if (!this.active || String(event.workflow_id || event.workflowId) !== String(this.active.workflowId) || String(event.agent_uid || event.agentUid) !== String(this.active.agentUid)) return;
    const state = this.store.get(this.active.workflowId, this.active.agentUid);
    const patch = {};
    const lifecycleStatus = event.status;
    const requestInFlight = ["submitting", "generating", "committing"].includes(state.status);
    const terminalEvent = ["completed", "idle", "committed", "error"].includes(lifecycleStatus);
    if (
      ["generating", "completed", "stopped", "error", "idle", "committing", "committed"].includes(lifecycleStatus)
      && !(requestInFlight && terminalEvent)
    ) {
      patch.status = lifecycleStatus === "completed" ? "idle" : lifecycleStatus;
    }
    if (
      event.text
      && (event.type === "delta" || (event.type === "message_update" && event.status === "delta"))
    ) {
      patch.draft = `${state.draft || ""}${event.text}`;
    }
    if (event.type === "completed" && event.text) patch.draft = event.text;
    if (event.error) patch.error = event.error;
    if (Object.keys(patch).length === 0) return;
    this.panel.state = this.store.set(this.active.workflowId, this.active.agentUid, patch);
    this.panel.renderState();
  }

  toast(message, tone = "info") {
    const node = el("div", `ryan-toast ryan-toast--${tone}`);
    node.textContent = message;
    this.root.append(node);
    window.setTimeout(() => node.remove(), 3000);
  }

  restoreWidth() {
    try {
      const value = Number(localStorage.getItem(WIDTH_KEY));
      if (value) this.setWidth(value);
    } catch (_error) { /* localStorage 可能被浏览器策略禁用。 */ }
  }

  setWidth(width) {
    const value = Math.max(380, Math.min(Math.round(window.innerWidth * 0.55), width));
    this.root.style.setProperty("--ryan-panel-width", `${value}px`);
    try { localStorage.setItem(WIDTH_KEY, String(value)); } catch (_error) { /* non-blocking */ }
  }

  setupResize() {
    let startX = 0;
    let startWidth = 480;
    const move = (event) => this.setWidth(startWidth + (startX - event.clientX));
    const stop = () => {
      document.removeEventListener("pointermove", move);
      document.removeEventListener("pointerup", stop);
      this.resizeHandle.releasePointerCapture?.();
    };
    this.resizeHandle.addEventListener("pointerdown", (event) => {
      startX = event.clientX;
      startWidth = this.root.getBoundingClientRect().width || 480;
      this.resizeHandle.setPointerCapture?.(event.pointerId);
      document.addEventListener("pointermove", move);
      document.addEventListener("pointerup", stop, { once: true });
      event.preventDefault();
    });
  }
}

export default PanelManager;
