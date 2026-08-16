const STORAGE_KEY = "ryan.workflow-agent.workspace.v1";

function clone(value) {
  try { return JSON.parse(JSON.stringify(value)); } catch (_error) { return value; }
}
function keyOf(workflowId, agentUid) { return `${String(workflowId || "")}::${String(agentUid || "")}`; }
function emptyState(workflowId, agentUid) {
  return { workflowId: String(workflowId || ""), agentUid: String(agentUid || ""), agentName: "Workflow Agent", skillId: "", status: "idle", draft: "", composerDraft: "", messages: [], attachments: [], context: { entries: [], assets: [], lineage: [] }, contextReceived: false, scrollTop: 0, commitRevision: 0, upstreamChanged: false, error: "", requestId: "", messageId: "", updatedAt: Date.now() };
}
export class AgentStateStore extends EventTarget {
  constructor(storage) {
    super();
    this.storage = storage;
    if (storage === undefined) {
      try { this.storage = globalThis.localStorage; } catch (_error) { this.storage = null; }
    }
    this.states = new Map();
    this.load();
  }
  load() { try { const raw = this.storage?.getItem(STORAGE_KEY); const saved = raw ? JSON.parse(raw) : {}; Object.entries(saved || {}).forEach(([key, value]) => { if (value && typeof value === "object") this.states.set(key, value); }); } catch (_error) { /* storage 不可用时使用内存状态。 */ } }
  persist() { try { this.storage?.setItem(STORAGE_KEY, JSON.stringify(Object.fromEntries(this.states))); } catch (_error) { /* 不阻塞当前会话。 */ } }
  get(workflowId, agentUid) { const key = keyOf(workflowId, agentUid); if (!this.states.has(key)) this.states.set(key, emptyState(workflowId, agentUid)); return clone(this.states.get(key)); }
  set(workflowId, agentUid, patch) { const key = keyOf(workflowId, agentUid); const current = this.states.get(key) || emptyState(workflowId, agentUid); const next = { ...current, ...clone(patch), updatedAt: Date.now() }; if (patch?.context) next.context = { ...current.context, ...clone(patch.context) }; this.states.set(key, next); this.persist(); this.dispatchEvent(new CustomEvent("change", { detail: { key, state: clone(next) } })); return clone(next); }
  update(workflowId, agentUid, updater) { const current = this.get(workflowId, agentUid); return this.set(workflowId, agentUid, updater(current) || current); }
  rememberScroll(workflowId, agentUid, scrollTop) { return this.set(workflowId, agentUid, { scrollTop: Number(scrollTop) || 0 }); }
}
export function stateKey(workflowId, agentUid) { return keyOf(workflowId, agentUid); }
export default AgentStateStore;
