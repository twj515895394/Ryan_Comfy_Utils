const JSON_HEADERS = { "Content-Type": "application/json" };

async function request(path, options = {}) {
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  const response = await fetch(path, {
    credentials: "same-origin",
    ...options,
    headers: { ...(options.body && !isFormData ? JSON_HEADERS : {}), ...(options.headers || {}) },
  });
  let payload;
  try { payload = await response.json(); } catch (_error) { payload = {}; }
  if (!response.ok || payload.status === "error") {
    throw new Error(payload.error || `Request failed (${response.status})`);
  }
  return payload;
}

export class WorkflowAgentApi {
  getAgent(workflowId, agentUid) {
    return request(`/ryan/agent/workflows/${encodeURIComponent(workflowId)}/agents/${encodeURIComponent(agentUid)}`);
  }

  listSkills(skillRoot = "") {
    const query = skillRoot ? `?skill_root=${encodeURIComponent(skillRoot)}` : "";
    return request(`/ryan/agent/skills${query}`);
  }

  sendMessage(payload) {
    return request("/ryan/agent/chat", { method: "POST", body: JSON.stringify(payload) });
  }

  commit(payload) {
    return request("/ryan/agent/commit", { method: "POST", body: JSON.stringify(payload) });
  }

  stop(payload) {
    return request("/ryan/agent/stop", { method: "POST", body: JSON.stringify(payload) });
  }

  reset(payload) {
    return request("/ryan/agent/reset", { method: "POST", body: JSON.stringify(payload) });
  }

  listAssets(workflowId, agentUid) {
    return request(`/ryan/agent/workflows/${encodeURIComponent(workflowId)}/agents/${encodeURIComponent(agentUid)}/assets`);
  }

  async attachAsset({ workflowId, agentUid, file, source = "chat_upload" }) {
    const body = new FormData();
    body.append("workflow_id", workflowId);
    body.append("agent_uid", agentUid);
    body.append("source", source);
    body.append("file", file, file.name);
    return request("/ryan/agent/assets", { method: "POST", body, headers: {} });
  }

  detachAsset(workflowId, agentUid, assetId) {
    const query = new URLSearchParams({ workflow_id: workflowId, agent_uid: agentUid });
    return request(`/ryan/agent/assets/${encodeURIComponent(assetId)}?${query}`, { method: "DELETE" });
  }
}

export default WorkflowAgentApi;
