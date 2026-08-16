/**
 * Ryan Creative Workspace UI shell (TE_MAN-like floating panel).
 * Visual polish is intentionally minimal; browser QA is manual.
 */
import { app } from "../../../../scripts/app.js";
import { api } from "../../../../scripts/api.js";

const PANEL_ID = "ryan-creative-workspace-panel";

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "className") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (value != null) node.setAttribute(key, String(value));
  }
  for (const child of children) {
    if (child == null) continue;
    node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
  }
  return node;
}

async function apiJson(path, options = {}) {
  const response = await api.fetchApi(path, {
    method: options.method || "GET",
    headers: options.body ? { "Content-Type": "application/json" } : undefined,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const data = await response.json();
  if (!response.ok || data.status === "error") {
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  return data;
}

function ensureStyles() {
  if (document.getElementById("ryan-cw-styles")) return;
  const style = el("style", { id: "ryan-cw-styles" });
  style.textContent = `
  #${PANEL_ID} {
    position: fixed; right: 24px; top: 72px; width: 420px; max-height: 80vh;
    z-index: 10050; background: #1e1e1e; color: #f0f0f0; border: 1px solid #444;
    border-radius: 10px; box-shadow: 0 12px 40px rgba(0,0,0,.45);
    display: flex; flex-direction: column; font: 13px/1.4 sans-serif;
  }
  #${PANEL_ID}.hidden { display: none; }
  #${PANEL_ID} .hdr {
    display:flex; align-items:center; gap:8px; padding:10px 12px;
    border-bottom:1px solid #333; cursor: move; user-select:none;
  }
  #${PANEL_ID} .hdr strong { flex:1; }
  #${PANEL_ID} .body { padding:10px 12px; overflow:auto; flex:1; min-height: 180px; }
  #${PANEL_ID} .row { display:flex; gap:6px; margin:6px 0; flex-wrap:wrap; }
  #${PANEL_ID} button, #${PANEL_ID} select, #${PANEL_ID} input, #${PANEL_ID} textarea {
    background:#2a2a2a; color:#eee; border:1px solid #555; border-radius:6px; padding:6px 8px;
  }
  #${PANEL_ID} textarea { width:100%; min-height:72px; resize:vertical; }
  #${PANEL_ID} .msg { white-space:pre-wrap; border-left:3px solid #555; padding:4px 8px; margin:6px 0; }
  #${PANEL_ID} .msg.user { border-color:#4a9; }
  #${PANEL_ID} .msg.assistant { border-color:#59f; }
  #${PANEL_ID} .muted { opacity:.7; font-size:12px; }
  #${PANEL_ID} .stage { padding:4px 6px; border-radius:4px; border:1px solid #444; cursor:pointer; }
  #${PANEL_ID} .stage.active { border-color:#6af; background:#243044; }
  #${PANEL_ID} .stage.STALE { outline:1px solid #c80; }
  `;
  document.head.appendChild(style);
}

class CreativeWorkspacePanel {
  constructor() {
    this.projectId = "";
    this.stageId = "creative";
    this.threadId = "";
    this.projects = [];
    this.stages = [];
    this.root = null;
  }

  mount() {
    ensureStyles();
    if (document.getElementById(PANEL_ID)) {
      this.root = document.getElementById(PANEL_ID);
      return;
    }
    this.root = el("div", { id: PANEL_ID, className: "hidden" });
    document.body.appendChild(this.root);
    this.render();
    this.makeDraggable();
  }

  show() {
    this.mount();
    this.root.classList.remove("hidden");
    this.refresh().catch((err) => this.setStatus(String(err)));
  }

  hide() {
    if (this.root) this.root.classList.add("hidden");
  }

  toggle() {
    this.mount();
    if (this.root.classList.contains("hidden")) this.show();
    else this.hide();
  }

  setStatus(text) {
    const node = this.root?.querySelector("[data-status]");
    if (node) node.textContent = text || "";
  }

  async refresh() {
    const data = await apiJson("/ryan/creative/projects");
    this.projects = data.projects || [];
    this.projectId = data.current_creative_project_id || this.projects[0]?.project_id || "";
    if (!this.projectId) {
      const created = await apiJson("/ryan/creative/projects", {
        method: "POST",
        body: { name: "默认工作区" },
      });
      this.projectId = created.project?.project_id || "";
      this.projects = [created.project].filter(Boolean);
    }
    if (this.projectId) {
      await apiJson(`/ryan/creative/projects/${encodeURIComponent(this.projectId)}`);
      const stages = await apiJson(
        `/ryan/creative/projects/${encodeURIComponent(this.projectId)}/stages`
      );
      this.stages = stages.stages || [];
      if (!this.stages.find((s) => s.stage_id === this.stageId) && this.stages[0]) {
        this.stageId = this.stages[0].stage_id;
      }
    }
    this.render();
  }

  async resetWorkspace() {
    const data = await apiJson("/ryan/creative/workspace/reset", {
      method: "POST",
      body: { name: "新工作区" },
    });
    this.projectId = data.project?.project_id || "";
    this.threadId = "";
    await this.refresh();
  }

  async send() {
    const input = this.root.querySelector("[data-input]");
    const message = input?.value?.trim() || "";
    if (!message || !this.projectId) return;
    this.setStatus("发送中…");
    try {
      const result = await apiJson("/ryan/creative/chat", {
        method: "POST",
        body: {
          project_id: this.projectId,
          stage_id: this.stageId,
          thread_id: this.threadId,
          message,
        },
      });
      this.threadId = result.thread_id || this.threadId;
      if (input) input.value = "";
      this.appendMessage("user", message);
      this.appendMessage("assistant", result.text || "");
      this.setStatus(result.ready?.ready ? "READY：可确认草稿" : "已回复");
      const stages = await apiJson(
        `/ryan/creative/projects/${encodeURIComponent(this.projectId)}/stages`
      );
      this.stages = stages.stages || [];
      this.renderStagesOnly();
    } catch (err) {
      this.setStatus(String(err.message || err));
    }
  }

  async confirm(mode) {
    if (!this.projectId) return;
    this.setStatus(mode === "draft" ? "确认草稿…" : "确认阶段…");
    try {
      const result = await apiJson(
        `/ryan/creative/projects/${encodeURIComponent(this.projectId)}/stages/${encodeURIComponent(this.stageId)}/confirm`,
        {
          method: "POST",
          body: { mode, thread_id: this.threadId },
        }
      );
      this.setStatus(`已锁定 r${result.stage?.revision || "?"}`);
      await this.refresh();
    } catch (err) {
      this.setStatus(String(err.message || err));
    }
  }

  appendMessage(role, text) {
    const box = this.root.querySelector("[data-messages]");
    if (!box) return;
    box.appendChild(el("div", { className: `msg ${role}`, text }));
    box.scrollTop = box.scrollHeight;
  }

  renderStagesOnly() {
    const host = this.root.querySelector("[data-stages]");
    if (!host) return;
    host.innerHTML = "";
    for (const stage of this.stages) {
      const node = el("div", {
        className: `stage ${stage.status || ""} ${stage.stage_id === this.stageId ? "active" : ""}`,
        text: `${stage.display_name || stage.stage_id} · ${stage.status || "?"} r${stage.revision || 0}`,
        onClick: () => {
          this.stageId = stage.stage_id;
          this.threadId = stage.current_thread_id || "";
          this.render();
        },
      });
      host.appendChild(node);
    }
  }

  render() {
    if (!this.root) return;
    const projectOptions = this.projects.map((p) =>
      el("option", {
        value: p.project_id,
        text: `${p.name || p.project_id}`,
        ...(p.project_id === this.projectId ? { selected: "selected" } : {}),
      })
    );
    this.root.innerHTML = "";
    this.root.append(
      el("div", { className: "hdr" }, [
        el("strong", { text: "Ryan 构想台" }),
        el("button", { text: "刷新", onClick: () => this.refresh().catch((e) => this.setStatus(String(e))) }),
        el("button", { text: "关闭", onClick: () => this.hide() }),
      ]),
      el("div", { className: "body" }, [
        el("div", { className: "row" }, [
          el("select", {
            "data-project": "1",
            onChange: async (ev) => {
              this.projectId = ev.target.value;
              await apiJson(`/ryan/creative/projects/${encodeURIComponent(this.projectId)}`);
              await this.refresh();
            },
          }, projectOptions),
          el("button", {
            text: "新建",
            onClick: async () => {
              await apiJson("/ryan/creative/projects", { method: "POST", body: { name: "工作区" } });
              await this.refresh();
            },
          }),
          el("button", {
            text: "重置工作区",
            onClick: () => this.resetWorkspace().catch((e) => this.setStatus(String(e))),
          }),
        ]),
        el("div", { className: "muted", text: `project: ${this.projectId || "-"}` }),
        el("div", { className: "row", "data-stages": "1" }),
        el("div", { className: "muted", "data-status": "1", text: "就绪" }),
        el("div", { "data-messages": "1" }),
        el("textarea", { "data-input": "1", placeholder: "描述你的要求…" }),
        el("div", { className: "row" }, [
          el("button", { text: "发送", onClick: () => this.send() }),
          el("button", { text: "确认当前阶段", onClick: () => this.confirm("commit") }),
          el("button", { text: "确认当前草稿", onClick: () => this.confirm("draft") }),
        ]),
      ])
    );
    this.renderStagesOnly();
  }

  makeDraggable() {
    const hdr = () => this.root.querySelector(".hdr");
    let sx = 0;
    let sy = 0;
    let ox = 0;
    let oy = 0;
    let dragging = false;
    this.root.addEventListener("mousedown", (ev) => {
      if (!hdr()?.contains(ev.target)) return;
      dragging = true;
      sx = ev.clientX;
      sy = ev.clientY;
      const rect = this.root.getBoundingClientRect();
      ox = rect.left;
      oy = rect.top;
      ev.preventDefault();
    });
    window.addEventListener("mousemove", (ev) => {
      if (!dragging) return;
      this.root.style.left = `${ox + ev.clientX - sx}px`;
      this.root.style.top = `${oy + ev.clientY - sy}px`;
      this.root.style.right = "auto";
    });
    window.addEventListener("mouseup", () => {
      dragging = false;
    });
  }
}

const panel = new CreativeWorkspacePanel();

app.registerExtension({
  name: "Ryan.CreativeWorkspace",
  async setup() {
    const btn = el("button", {
      text: "Ryan 构想台",
      title: "打开 Ryan Creative Workspace",
      onClick: () => panel.toggle(),
    });
    btn.style.cssText = "margin-left:8px;";
    const host =
      document.querySelector(".comfy-menu") ||
      document.querySelector(".comfyui-menu") ||
      document.body;
    host.appendChild(btn);

    // default project id snapshot helper for text selector widgets
    app.canvas?.canvas?.addEventListener?.("drop", () => {});
  },
  async nodeCreated(node) {
    if (node?.comfyClass !== "Ryan Creative Text Selector") return;
    try {
      const data = await apiJson("/ryan/creative/projects");
      const current = data.current_creative_project_id || "";
      const widget = node.widgets?.find((w) => w.name === "creative_project_id");
      if (widget && current && !String(widget.value || "").trim()) {
        widget.value = current;
      }
    } catch (_) {
      /* offline / routes not ready */
    }
  },
});
