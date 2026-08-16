import { api } from "../../../../scripts/api.js";
import "./node_extension.js";
import "./artifact_selector_extension.js";
import WorkflowAgentApi from "./api_client.js";
import AgentStateStore from "./state_store.js";
import PanelManager from "./panel_manager.js";
import { installStyles } from "./styles.js";

const GLOBAL_KEY = "__ryanWorkflowAgentWorkspace";

function createWorkspace() {
  if (globalThis[GLOBAL_KEY]) return globalThis[GLOBAL_KEY];
  installStyles();
  const store = new AgentStateStore();
  const manager = new PanelManager({ api: new WorkflowAgentApi(), store });
  manager.mount(document.body);
  if (typeof api?.addEventListener === "function") {
    api.addEventListener("ryan_agent_event", (event) => manager.handleAgentEvent?.(event.detail || event));
  }
  globalThis[GLOBAL_KEY] = manager;
  return manager;
}

if (document.body) createWorkspace();
else window.addEventListener("DOMContentLoaded", createWorkspace, { once: true });

export { createWorkspace };
export default createWorkspace;
