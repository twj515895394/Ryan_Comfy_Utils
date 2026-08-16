/**
 * Ryan Creative Workspace UI shell.
 * Entry must remain visible on modern ComfyUI topbar (no .comfy-menu).
 */
import { app } from "../../../../scripts/app.js";
import { api } from "../../../../scripts/api.js";

const PANEL_ID = "ryan-creative-workspace-panel";
const TOGGLE_ID = "ryan-creative-workspace-toggle";
const STYLE_ID = "ryan-cw-styles";

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "className") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (value === true) node.setAttribute(key, "");
    else if (value != null && value !== false) node.setAttribute(key, String(value));
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
  let data = null;
  try {
    data = await response.json();
  } catch (_err) {
    data = null;
  }
  if (!response.ok || data?.status === "error") {
    throw new Error(data?.error || `HTTP ${response.status} ${path}`);
  }
  return data;
}

function ensureStyles() {
  if (document.getElementById(STYLE_ID)) return;
  const style = el("style", { id: STYLE_ID });
  style.textContent = `
  #${TOGGLE_ID} {
    height: 32px;
    padding: 0 12px;
    border-radius: 8px;
    border: 1px solid rgba(255,255,255,.16);
    background: linear-gradient(180deg, #3a4a6a 0%, #2a3550 100%);
    color: #f3f6ff;
    font: 600 12px/32px system-ui, sans-serif;
    cursor: pointer;
    white-space: nowrap;
    flex: 0 0 auto;
  }
  #${TOGGLE_ID}:hover { filter: brightness(1.08); }
  #${TOGGLE_ID}.ryan-cw-toggle-fallback {
    position: fixed;
    top: 52px;
    right: 16px;
    z-index: 10060;
    box-shadow: 0 6px 18px rgba(0,0,0,.35);
  }
  #${PANEL_ID} {
    position: fixed; right: 24px; top: 96px; width: min(440px, calc(100vw - 24px)); max-height: calc(100vh - 112px);
    z-index: 10055; background: #1e1e1e; color: #f0f0f0; border: 1px solid #444;
    border-radius: 10px; box-shadow: 0 12px 40px rgba(0,0,0,.45);
    display: flex; flex-direction: column; font: 13px/1.4 system-ui, sans-serif;
  }
  #${PANEL_ID}.hidden { display: none !important; }
  #${PANEL_ID} .hdr {
    display:flex; align-items:center; gap:8px; padding:10px 12px;
    border-bottom:1px solid #333; cursor: move; user-select:none;
  }
  #${PANEL_ID} .hdr strong { flex:1; }
  #${PANEL_ID} .body { padding:10px 12px; overflow:auto; flex:1; min-height: 180px; }
  #${PANEL_ID} .row { display:flex; gap:6px; margin:6px 0; flex-wrap:wrap; align-items:center; }
  #${PANEL_ID} button, #${PANEL_ID} select, #${PANEL_ID} input, #${PANEL_ID} textarea {
    background:#2a2a2a; color:#eee; border:1px solid #555; border-radius:6px; padding:6px 8px;
  }
  #${PANEL_ID} textarea { width:100%; min-height:72px; resize:vertical; box-sizing:border-box; }
  #${PANEL_ID} .msg { white-space:pre-wrap; border-left:3px solid #555; padding:4px 8px; margin:6px 0; }
  #${PANEL_ID} .msg.user { border-color:#4a9; }
  #${PANEL_ID} .msg.assistant { border-color:#59f; }
  #${PANEL_ID} .muted { opacity:.75; font-size:12px; }
  #${PANEL_ID} .stage { padding:4px 6px; border-radius:4px; border:1px solid #444; cursor:pointer; }
  #${PANEL_ID} .stage.active { border-color:#6af; background:#243044; }
  #${PANEL_ID} .stage.STALE { outline:1px solid #c80; }
  #${PANEL_ID} .err { color:#f88; }
  `;
  document.head.appendChild(style);
}

function buttonLabel(node) {
  return `${node?.textContent || ""} ${node?.getAttribute?.("aria-label") || ""} ${node?.title || ""}`.replace(/\s+/g, " ").trim();
}

function findTeManToolbarAnchor() {
  const candidates = [
    ...document.querySelectorAll("button, [role='button'], a, .p-button, [class*='button']"),
  ];
  // Prefer TE_MAN 构想台 (exclude our own button)
  const te = candidates.find((node) => {
    if (node.id === TOGGLE_ID) return false;
    const label = buttonLabel(node);
    return label.includes("构想台") && !label.includes("Ryan");
  });
  if (te) return te;
  const asset = candidates.find((node) => buttonLabel(node).includes("资产库"));
  if (asset) return asset;
  const ctv = candidates.find((node) => {
    const label = buttonLabel(node);
    return label === "ComfyTV" || label.includes("ComfyTV");
  });
  return ctv || null;
}

function placeToggleInToolbar(btn) {
  const anchor = findTeManToolbarAnchor();
  if (!anchor || !anchor.parentElement) {
    btn.classList.add("ryan-cw-toggle-fallback");
    if (btn.parentElement !== document.body) document.body.appendChild(btn);
    return false;
  }
  btn.classList.remove("ryan-cw-toggle-fallback");
  const parent = anchor.parentElement;
  // Insert immediately before TE_MAN 构想台 when possible; otherwise after anchor.
  const anchorLabel = buttonLabel(anchor);
  if (anchorLabel.includes("构想台") && !anchorLabel.includes("Ryan")) {
    if (btn.nextSibling !== anchor) parent.insertBefore(btn, anchor);
  } else if (btn.previousSibling !== anchor) {
    anchor.insertAdjacentElement("afterend", btn);
  }
  return true;
}

class CreativeWorkspacePanel {
  constructor() {
    this.projectId = "";
    this.stageId = "creative";
    this.threadId = "";
    this.projects = [];
    this.stages = [];
    this.root = null;
    this._dragBound = false;
  }

  mount() {
    ensureStyles();
    this.ensureToggle();
    if (document.getElementById(PANEL_ID)) {
      this.root = document.getElementById(PANEL_ID);
      return;
    }
    this.root = el("div", { id: PANEL_ID, className: "hidden" });
    document.body.appendChild(this.root);
    this.render();
    this.bindDrag();
  }

  ensureToggle() {
    ensureStyles();
    let btn = document.getElementById(TOGGLE_ID);
    if (!btn) {
      btn = el("button", {
        id: TOGGLE_ID,
        type: "button",
        text: "Ryan 构想台",
        title: "打开/关闭 Ryan Creative Workspace",
        onClick: () => this.toggle(),
      });
    }
    const dock = () => {
      try {
        placeToggleInToolbar(btn);
      } catch (err) {
        console.warn("[Ryan Creative Workspace] dock toggle failed", err);
        btn.classList.add("ryan-cw-toggle-fallback");
        if (!btn.isConnected) document.body.appendChild(btn);
      }
    };
    dock();
    // Toolbar is often mounted asynchronously (TE_MAN / ComfyTV).
    if (!this._toggleObserver) {
      this._toggleObserver = new MutationObserver(() => dock());
      this._toggleObserver.observe(document.body, { childList: true, subtree: true });
      window.addEventListener("resize", dock);
      // Stop aggressive observing after toolbar settles.
      setTimeout(() => {
        try {
          this._toggleObserver?.disconnect();
        } catch (_err) {
          /* ignore */
        }
        this._toggleObserver = null;
        // final placement
        dock();
      }, 8000);
    }
    return btn;
  }

  show() {
    this.mount();
    this.root.classList.remove("hidden");
    this.refresh().catch((err) => this.setStatus(String(err?.message || err), true));
  }

  hide() {
    if (this.root) this.root.classList.add("hidden");
  }

  toggle() {
    this.mount();
    if (this.root.classList.contains("hidden")) this.show();
    else this.hide();
  }

  setStatus(text, isError = false) {
    const node = this.root?.querySelector("[data-status]");
    if (!node) return;
    node.textContent = text || "";
    node.classList.toggle("err", Boolean(isError));
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
      const current = this.stages.find((s) => s.stage_id === this.stageId);
      if (current?.current_thread_id) this.threadId = current.current_thread_id;
    }
    this.render();
    this.setStatus("就绪");
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
      this.setStatus(String(err.message || err), true);
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
      this.setStatus(String(err.message || err), true);
    }
  }

  appendMessage(role, text) {
    const box = this.root.querySelector("[data-messages]");
    if (!box) return;
    box.appendChild(el("div", { className: `msg ${role}`, text: text || "" }));
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
    const projectOptions = this.projects.map((p) => {
      const opt = el("option", {
        value: p.project_id,
        text: `${p.name || p.project_id}`,
      });
      if (p.project_id === this.projectId) opt.selected = true;
      return opt;
    });
    this.root.innerHTML = "";
    this.root.append(
      el("div", { className: "hdr" }, [
        el("strong", { text: "Ryan 构想台" }),
        el("button", {
          type: "button",
          text: "刷新",
          onClick: () => this.refresh().catch((e) => this.setStatus(String(e.message || e), true)),
        }),
        el("button", { type: "button", text: "关闭", onClick: () => this.hide() }),
      ]),
      el("div", { className: "body" }, [
        el("div", { className: "row" }, [
          el(
            "select",
            {
              "data-project": "1",
              onChange: async (ev) => {
                this.projectId = ev.target.value;
                try {
                  await apiJson(`/ryan/creative/projects/${encodeURIComponent(this.projectId)}`);
                  await this.refresh();
                } catch (err) {
                  this.setStatus(String(err.message || err), true);
                }
              },
            },
            projectOptions
          ),
          el("button", {
            type: "button",
            text: "新建",
            onClick: async () => {
              try {
                await apiJson("/ryan/creative/projects", { method: "POST", body: { name: "工作区" } });
                await this.refresh();
              } catch (err) {
                this.setStatus(String(err.message || err), true);
              }
            },
          }),
          el("button", {
            type: "button",
            text: "重置工作区",
            onClick: () => this.resetWorkspace().catch((e) => this.setStatus(String(e.message || e), true)),
          }),
        ]),
        el("div", { className: "muted", text: `project: ${this.projectId || "-"}` }),
        el("div", { className: "row", "data-stages": "1" }),
        el("div", { className: "muted", "data-status": "1", text: "就绪" }),
        el("div", { "data-messages": "1" }),
        el("textarea", { "data-input": "1", placeholder: "描述你的要求…" }),
        el("div", { className: "row" }, [
          el("button", { type: "button", text: "发送", onClick: () => this.send() }),
          el("button", { type: "button", text: "确认当前阶段", onClick: () => this.confirm("commit") }),
          el("button", { type: "button", text: "确认当前草稿", onClick: () => this.confirm("draft") }),
        ]),
      ])
    );
    this.renderStagesOnly();
  }

  bindDrag() {
    if (this._dragBound || !this.root) return;
    this._dragBound = true;
    let sx = 0;
    let sy = 0;
    let ox = 0;
    let oy = 0;
    let dragging = false;
    this.root.addEventListener("mousedown", (ev) => {
      const hdr = this.root.querySelector(".hdr");
      if (!hdr?.contains(ev.target)) return;
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

function boot() {
  try {
    panel.mount();
    console.info("[Ryan Creative Workspace] UI mounted (#ryan-creative-workspace-toggle)");
  } catch (err) {
    console.error("[Ryan Creative Workspace] mount failed", err);
  }
}

app.registerExtension({
  name: "Ryan.CreativeWorkspace",
  async setup() {
    boot();
  },
  async init() {
    // older/newer frontends may call init instead of/in addition to setup
    boot();
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
    } catch (_err) {
      /* routes may be offline during graph load */
    }
  },
});

// If extension registration is delayed, still expose a global opener.
globalThis.RyanCreativeWorkspace = panel;
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot, { once: true });
} else {
  // Defer one tick so body exists.
  setTimeout(boot, 0);
}
