/**
 * Ryan Creative Workspace — TE_MAN-like chat IDE shell.
 * Reuses workflow_agent MessageList/Composer/styles; streams via ryan_creative_event.
 */
import { app } from "../../../../scripts/app.js";
import { api } from "../../../../scripts/api.js";
import MessageList from "../workflow_agent/message_list.js";
import Composer from "../workflow_agent/composer.js";
import { installStyles as installAgentStyles } from "../workflow_agent/styles.js";

const PANEL_ID = "ryan-creative-workspace-panel";
const TOGGLE_ID = "ryan-creative-workspace-toggle";
const STYLE_ID = "ryan-cw-ui-styles";

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "className") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (value === true) node.setAttribute(key, key);
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

function buttonLabel(node) {
  return `${node?.textContent || ""} ${node?.getAttribute?.("aria-label") || ""} ${node?.title || ""}`
    .replace(/\s+/g, " ")
    .trim();
}

function findToolbarAnchor() {
  const candidates = [...document.querySelectorAll("button, [role='button'], a, .p-button")];
  const te = candidates.find((n) => n.id !== TOGGLE_ID && buttonLabel(n).includes("构想台") && !buttonLabel(n).includes("Ryan"));
  if (te) return te;
  const asset = candidates.find((n) => buttonLabel(n).includes("资产库"));
  if (asset) return asset;
  return candidates.find((n) => buttonLabel(n).includes("ComfyTV")) || null;
}

function ensureStyles() {
  installAgentStyles();
  if (document.getElementById(STYLE_ID)) return;
  const style = el("style", { id: STYLE_ID });
  style.textContent = `
  #${TOGGLE_ID}{
    height:32px;padding:0 12px;border-radius:8px;border:1px solid rgba(255,255,255,.16);
    background:linear-gradient(180deg,#3a4a6a 0%,#2a3550 100%);color:#f3f6ff;
    font:600 12px/32px system-ui,sans-serif;cursor:pointer;white-space:nowrap;flex:0 0 auto;
  }
  #${TOGGLE_ID}:hover{filter:brightness(1.08)}
  #${TOGGLE_ID}.ryan-cw-toggle-fallback{position:fixed;top:52px;right:16px;z-index:10060;box-shadow:0 6px 18px rgba(0,0,0,.35)}
  #${PANEL_ID}{
    --ryan-bg-panel:var(--comfy-menu-bg,#14161c);
    --ryan-bg-elevated:var(--comfy-input-bg,#1c2028);
    --ryan-bg-input:#10131a;
    --ryan-border:rgba(255,255,255,.10);
    --ryan-border-strong:rgba(255,255,255,.18);
    --ryan-text-primary:#f2f4f7;
    --ryan-text-secondary:rgba(242,244,247,.62);
    --ryan-accent:#8d9cff;
    --ryan-accent-strong:#c4cbff;
    --ryan-gold:#d6b36a;
    position:fixed;right:18px;top:72px;width:min(980px,calc(100vw - 28px));height:min(720px,calc(100vh - 96px));
    z-index:10055;display:flex;flex-direction:column;overflow:hidden;color:var(--ryan-text-primary);
    font:13px/1.45 Inter,ui-sans-serif,system-ui,sans-serif;
    background:linear-gradient(180deg,rgba(28,32,40,.98),rgba(14,16,22,.98));
    border:1px solid rgba(214,179,106,.28);border-radius:16px;
    box-shadow:0 24px 64px rgba(0,0,0,.48),0 0 0 1px rgba(255,255,255,.03) inset;
  }
  #${PANEL_ID}.hidden{display:none!important}
  #${PANEL_ID} .cw-header{display:flex;align-items:center;gap:10px;padding:12px 14px;border-bottom:1px solid var(--ryan-border);cursor:move;user-select:none;background:linear-gradient(180deg,rgba(214,179,106,.08),transparent)}
  #${PANEL_ID} .cw-header h1{margin:0;font-size:15px;font-weight:650;letter-spacing:.01em}
  #${PANEL_ID} .cw-header .sub{color:var(--ryan-text-secondary);font-size:11px}
  #${PANEL_ID} .cw-header .spacer{flex:1}
  #${PANEL_ID} .cw-body{display:grid;grid-template-columns:240px 1fr;min-height:0;flex:1}
  #${PANEL_ID} .cw-side{display:flex;flex-direction:column;gap:10px;min-height:0;padding:12px;border-right:1px solid var(--ryan-border);background:rgba(0,0,0,.18);overflow:auto}
  #${PANEL_ID} .cw-main{display:flex;flex-direction:column;min-width:0;min-height:0}
  #${PANEL_ID} .cw-toolbar{display:flex;flex-wrap:wrap;gap:6px;align-items:center;padding:10px 12px;border-bottom:1px solid var(--ryan-border);background:rgba(255,255,255,.02)}
  #${PANEL_ID} .cw-status{padding:0 14px 8px;color:var(--ryan-text-secondary);font-size:11px}
  #${PANEL_ID} .cw-status.err{color:#f0a0a0}
  #${PANEL_ID} .cw-messages{flex:1;min-height:0;display:flex;flex-direction:column}
  #${PANEL_ID} .cw-messages .ryan-message-list{flex:1}
  #${PANEL_ID} .cw-composer{border-top:1px solid var(--ryan-border);background:rgba(0,0,0,.14)}
  #${PANEL_ID} .cw-composer .ryan-composer{margin:12px}
  #${PANEL_ID} select, #${PANEL_ID} button.cw-btn{
    background:rgba(255,255,255,.04);color:var(--ryan-text-primary);border:1px solid var(--ryan-border-strong);
    border-radius:9px;padding:6px 10px;font:inherit;cursor:pointer
  }
  #${PANEL_ID} button.cw-btn.primary{background:linear-gradient(180deg,#e0c07a,#b89245);color:#1a1408;border-color:transparent;font-weight:650}
  #${PANEL_ID} button.cw-btn:disabled{opacity:.5;cursor:not-allowed}
  #${PANEL_ID} .cw-block-title{margin:0 0 6px;color:var(--ryan-text-secondary);font-size:10px;letter-spacing:.08em;text-transform:uppercase}
  #${PANEL_ID} .cw-stage, #${PANEL_ID} .cw-thread{
    width:100%;text-align:left;margin:0 0 6px;padding:8px 10px;border-radius:10px;border:1px solid var(--ryan-border);
    background:rgba(255,255,255,.03);color:var(--ryan-text-primary);cursor:pointer
  }
  #${PANEL_ID} .cw-stage.active, #${PANEL_ID} .cw-thread.active{border-color:rgba(214,179,106,.55);background:rgba(214,179,106,.10)}
  #${PANEL_ID} .cw-stage.STALE{outline:1px solid rgba(232,184,106,.7)}
  #${PANEL_ID} .cw-stage small, #${PANEL_ID} .cw-thread small{display:block;color:var(--ryan-text-secondary);font-size:10px;margin-top:2px}
  #${PANEL_ID} .cw-chips{display:flex;flex-wrap:wrap;gap:6px;padding:0 16px}
  #${PANEL_ID} .cw-chip{display:inline-flex;align-items:center;gap:6px;padding:4px 8px;border-radius:999px;border:1px solid var(--ryan-border);background:rgba(255,255,255,.04);font-size:11px;color:var(--ryan-text-secondary)}
  #${PANEL_ID} .cw-chip button{border:0;background:transparent;color:inherit;cursor:pointer}
  #${PANEL_ID} .cw-pop{
    position:absolute;left:16px;right:16px;bottom:110px;z-index:5;max-height:240px;overflow:auto;
    border:1px solid var(--ryan-border-strong);border-radius:12px;background:#1a1e27;box-shadow:0 16px 40px rgba(0,0,0,.4)
  }
  #${PANEL_ID} .cw-pop button{display:block;width:100%;text-align:left;padding:10px 12px;border:0;border-bottom:1px solid var(--ryan-border);background:transparent;color:var(--ryan-text-primary);cursor:pointer}
  #${PANEL_ID} .cw-pop button:hover{background:rgba(255,255,255,.04)}
  #${PANEL_ID} .cw-empty-guide{padding:28px;color:var(--ryan-text-secondary);text-align:center}
  `;
  document.head.appendChild(style);
}

class CreativeWorkspaceApp {
  constructor() {
    this.projectId = "";
    this.stageId = "creative";
    this.threadId = "";
    this.skillId = "";
    this.projects = [];
    this.stages = [];
    this.threads = {};
    this.skills = [];
    this.messages = [];
    this.assetRefs = [];
    this.selectedAssetIds = [];
    this.generating = false;
    this.activeRequestId = "";
    this.root = null;
    this.messageList = null;
    this.composer = null;
    this._dragBound = false;
  }

  mount() {
    ensureStyles();
    // Toggle button is owned by ryan_creative_workspace.js bootstrap.
    if (!this.root) {
      this.root = el("div", { id: PANEL_ID, className: "hidden" });
      document.body.appendChild(this.root);
      this.bindDrag();
      this.bindEvents();
      this.renderShell();
    }
  }

  ensureToggle() {
    // compatibility no-op: durable toggle lives in entry bootstrap
    return document.getElementById(TOGGLE_ID);
  }
  bindEvents() {
    if (this._eventsBound) return;
    this._eventsBound = true;
    if (typeof api?.addEventListener === "function") {
      api.addEventListener("ryan_creative_event", (event) => {
        this.onCreativeEvent(event.detail || event);
      });
    }
  }

  show() {
    this.mount();
    this.root.classList.remove("hidden");
    this.refreshAll().catch((e) => this.setStatus(String(e.message || e), true));
  }

  hide() {
    this.root?.classList.add("hidden");
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

  setGenerating(busy) {
    this.generating = Boolean(busy);
    this.composer?.setGenerating(this.generating, this.generating ? "generating" : "idle");
    this.messageList?.setBusy(false);
  }

  onCreativeEvent(event) {
    if (!event || typeof event !== "object") return;
    if (this.projectId && event.project_id && event.project_id !== this.projectId) return;
    if (this.stageId && event.stage_id && event.stage_id !== this.stageId) return;
    if (this.threadId && event.thread_id && event.thread_id !== this.threadId) return;
    const type = String(event.type || "");
    if (type === "start") {
      this.activeRequestId = event.request_id || "";
      this.setGenerating(true);
      if (event.user_message) {
        // user bubble may already exist from optimistic UI
      }
      this.upsertStreamingAssistant("");
      this.setStatus("生成中…");
      return;
    }
    if (type === "delta") {
      if (event.request_id && this.activeRequestId && event.request_id !== this.activeRequestId) return;
      this.activeRequestId = event.request_id || this.activeRequestId;
      const last = this.messages[this.messages.length - 1];
      if (!last || last.role !== "assistant" || !last.streaming) {
        this.upsertStreamingAssistant(String(event.text || ""));
      } else {
        last.content = `${last.content || ""}${event.text || ""}`;
        this.messageList?.updateLast(last);
      }
      return;
    }
    if (type === "end" || type === "error") {
      if (event.request_id && this.activeRequestId && event.request_id !== this.activeRequestId) return;
      const text = String(event.text || "");
      const last = this.messages[this.messages.length - 1];
      if (last?.role === "assistant" && last.streaming) {
        last.streaming = false;
        last.pending = false;
        if (text) last.content = text;
        if (event.error) last.error = event.error;
        this.messageList?.updateLast(last);
      } else if (text) {
        this.messages.push({ role: "assistant", content: text, error: event.error || "" });
        this.messageList?.append(this.messages[this.messages.length - 1]);
      }
      this.setGenerating(false);
      this.activeRequestId = "";
      this.setStatus(type === "error" ? String(event.error || "生成失败") : event.ready ? "READY：可确认草稿" : "已完成");
      this.refreshStages().catch(() => {});
    }
  }

  upsertStreamingAssistant(text) {
    const last = this.messages[this.messages.length - 1];
    if (last?.role === "assistant" && last.streaming) {
      last.content = text;
      this.messageList?.updateLast(last);
      return;
    }
    const msg = { role: "assistant", content: text || "", streaming: true, pending: !text };
    this.messages.push(msg);
    this.messageList?.append(msg);
  }

  async refreshAll() {
    await this.refreshProjects();
    await Promise.all([this.refreshStages(), this.refreshSkills(), this.refreshThreads()]);
    await this.refreshMessages();
    this.renderSide();
    this.renderToolbarMeta();
  }

  async refreshProjects() {
    const data = await apiJson("/ryan/creative/projects");
    this.projects = data.projects || [];
    this.projectId = data.current_creative_project_id || this.projects[0]?.project_id || "";
    if (!this.projectId) {
      const created = await apiJson("/ryan/creative/projects", { method: "POST", body: { name: "默认工作区" } });
      this.projectId = created.project?.project_id || "";
      this.projects = [created.project].filter(Boolean);
    } else {
      await apiJson(`/ryan/creative/projects/${encodeURIComponent(this.projectId)}`);
    }
  }

  async refreshStages() {
    if (!this.projectId) return;
    const data = await apiJson(`/ryan/creative/projects/${encodeURIComponent(this.projectId)}/stages`);
    this.stages = data.stages || [];
    if (!this.stages.find((s) => s.stage_id === this.stageId) && this.stages[0]) {
      this.stageId = this.stages[0].stage_id;
    }
    const cur = this.stages.find((s) => s.stage_id === this.stageId);
    if (cur?.skill_id) this.skillId = cur.skill_id;
    if (cur?.current_thread_id) this.threadId = cur.current_thread_id;
  }

  async refreshThreads() {
    if (!this.projectId) return;
    const data = await apiJson(`/ryan/creative/projects/${encodeURIComponent(this.projectId)}/threads`);
    this.threads = data.threads || {};
    if (!this.threadId) {
      const cur = this.stages.find((s) => s.stage_id === this.stageId);
      this.threadId = cur?.current_thread_id || cur?.main_thread_id || "";
    }
  }

  async refreshSkills() {
    try {
      const data = await apiJson("/ryan/creative/skills");
      this.skills = data.skills || [];
    } catch (_err) {
      this.skills = [];
    }
  }

  async refreshMessages() {
    this.messages = [];
    if (!this.projectId || !this.stageId || !this.threadId) {
      this.messageList?.render([]);
      return;
    }
    try {
      const data = await apiJson(
        `/ryan/creative/projects/${encodeURIComponent(this.projectId)}/stages/${encodeURIComponent(this.stageId)}/threads/${encodeURIComponent(this.threadId)}/messages`
      );
      this.messages = (data.messages || []).map((m) => ({
        role: m.role,
        content: m.content || "",
        error: m.error || "",
      }));
    } catch (_err) {
      this.messages = [];
    }
    this.messageList?.render(this.messages);
  }

  renderShell() {
    if (!this.root) return;
    this.root.innerHTML = "";
    const header = el("div", { className: "cw-header" }, [
      el("div", {}, [
        el("h1", { text: "Ryan 构想台" }),
        el("div", { className: "sub", "data-project-label": "1", text: this.projectId || "未选择项目" }),
      ]),
      el("div", { className: "spacer" }),
      el("button", { className: "cw-btn", type: "button", text: "刷新", onClick: () => this.refreshAll().catch((e) => this.setStatus(String(e.message || e), true)) }),
      el("button", { className: "cw-btn", type: "button", text: "关闭", onClick: () => this.hide() }),
    ]);
    const side = el("aside", { className: "cw-side", "data-side": "1" });
    const toolbar = el("div", { className: "cw-toolbar", "data-toolbar": "1" });
    const status = el("div", { className: "cw-status", "data-status": "1", text: "就绪" });
    const messagesHost = el("div", { className: "cw-messages" });
    this.messageList = new MessageList();
    this.messageList.mount(messagesHost);
    const composerHost = el("div", { className: "cw-composer", style: "position:relative" });
    this.composer = new Composer({
      onSend: (text) => this.send(text),
      onStop: () => this.stop(),
      onDraft: () => {},
    });
    // tool buttons
    const tools = this.composer.tools;
    tools.append(
      el("button", {
        type: "button",
        className: "ryan-attachment-button",
        text: "@ 资产",
        onClick: () => this.openAssetPicker().catch((e) => this.setStatus(String(e.message || e), true)),
      }),
      el("button", {
        type: "button",
        className: "ryan-attachment-button",
        text: "/ Skill",
        onClick: () => this.openSkillPalette(),
      })
    );
    this.composer.textarea.addEventListener("input", () => {
      const v = this.composer.textarea.value;
      if (v.endsWith("/")) this.openSkillPalette();
      if (v.endsWith("@")) this.openAssetPicker().catch(() => {});
    });
    this.composer.mount(composerHost);
    const chips = el("div", { className: "cw-chips", "data-chips": "1" });
    const main = el("section", { className: "cw-main" }, [toolbar, status, chips, messagesHost, composerHost]);
    const body = el("div", { className: "cw-body" }, [side, main]);
    this.root.append(header, body);
    this.renderSide();
    this.renderToolbarMeta();
    this.messageList.render(this.messages);
  }

  renderToolbarMeta() {
    const toolbar = this.root?.querySelector("[data-toolbar]");
    if (!toolbar) return;
    toolbar.innerHTML = "";
    const projectSelect = el("select", {
      onChange: async (ev) => {
        this.projectId = ev.target.value;
        await apiJson(`/ryan/creative/projects/${encodeURIComponent(this.projectId)}`);
        await this.refreshAll();
      },
    });
    for (const p of this.projects) {
      const opt = el("option", { value: p.project_id, text: p.name || p.project_id });
      if (p.project_id === this.projectId) opt.selected = true;
      projectSelect.append(opt);
    }
    toolbar.append(
      projectSelect,
      el("button", {
        className: "cw-btn",
        type: "button",
        text: "新建项目",
        onClick: async () => {
          await apiJson("/ryan/creative/projects", { method: "POST", body: { name: "工作区" } });
          await this.refreshAll();
        },
      }),
      el("button", {
        className: "cw-btn",
        type: "button",
        text: "重置工作区",
        onClick: async () => {
          const data = await apiJson("/ryan/creative/workspace/reset", { method: "POST", body: { name: "新工作区" } });
          this.projectId = data.project?.project_id || "";
          this.threadId = "";
          await this.refreshAll();
        },
      }),
      el("button", {
        className: "cw-btn primary",
        type: "button",
        text: "确认当前阶段",
        onClick: () => this.confirm("commit"),
      }),
      el("button", {
        className: "cw-btn",
        type: "button",
        text: "确认当前草稿",
        onClick: () => this.confirm("draft"),
      })
    );
    const label = this.root.querySelector("[data-project-label]");
    if (label) label.textContent = this.projectId || "未选择项目";
    this.renderChips();
  }

  renderSide() {
    const side = this.root?.querySelector("[data-side]");
    if (!side) return;
    side.innerHTML = "";
    side.append(el("div", { className: "cw-block-title", text: "阶段" }));
    for (const stage of this.stages) {
      side.append(
        el("button", {
          type: "button",
          className: `cw-stage ${stage.status || ""} ${stage.stage_id === this.stageId ? "active" : ""}`,
          onClick: async () => {
            this.stageId = stage.stage_id;
            this.skillId = stage.skill_id || this.skillId;
            this.threadId = stage.current_thread_id || stage.main_thread_id || "";
            await this.refreshThreads();
            await this.refreshMessages();
            this.renderSide();
            this.renderChips();
          },
        }, [
          document.createTextNode(stage.display_name || stage.stage_id),
          el("small", { text: `${stage.status || "?"} · r${stage.revision || 0}` }),
        ])
      );
    }
    side.append(el("div", { className: "cw-block-title", text: "话题 Thread" }));
    const stageThreads = Object.values(this.threads || {}).filter((t) => t.stage_id === this.stageId);
    if (!stageThreads.length) {
      side.append(el("div", { className: "sub", text: "发送消息后自动创建主讨论" }));
    }
    for (const thread of stageThreads) {
      side.append(
        el("button", {
          type: "button",
          className: `cw-thread ${thread.thread_id === this.threadId ? "active" : ""}`,
          onClick: async () => {
            this.threadId = thread.thread_id;
            await this.refreshMessages();
            this.renderSide();
          },
        }, [
          document.createTextNode(thread.title || thread.thread_id),
          el("small", { text: thread.is_main ? "主讨论" : thread.thread_id.slice(0, 12) }),
        ])
      );
    }
    side.append(
      el("button", {
        className: "cw-btn",
        type: "button",
        text: "+ 新话题",
        onClick: async () => {
          if (!this.projectId || !this.stageId) return;
          const data = await apiJson(
            `/ryan/creative/projects/${encodeURIComponent(this.projectId)}/stages/${encodeURIComponent(this.stageId)}/threads`,
            { method: "POST", body: { title: "新话题" } }
          );
          this.threadId = data.thread?.thread_id || this.threadId;
          await this.refreshThreads();
          await this.refreshMessages();
          this.renderSide();
        },
      })
    );
  }

  renderChips() {
    const host = this.root?.querySelector("[data-chips]");
    if (!host) return;
    host.innerHTML = "";
    const stage = this.stages.find((s) => s.stage_id === this.stageId);
    host.append(el("span", { className: "cw-chip", text: `Stage: ${stage?.display_name || this.stageId || "-"}` }));
    if (this.skillId) host.append(el("span", { className: "cw-chip", text: `Skill: ${this.skillId}` }));
    for (const id of this.selectedAssetIds) {
      const ref = this.assetRefs.find((a) => a.asset_ref_id === id);
      const chip = el("span", { className: "cw-chip" }, [
        document.createTextNode(ref?.display_name || id.slice(0, 8)),
        el("button", {
          type: "button",
          text: "×",
          onClick: () => {
            this.selectedAssetIds = this.selectedAssetIds.filter((x) => x !== id);
            this.renderChips();
          },
        }),
      ]);
      host.append(chip);
    }
  }

  async send(text) {
    const message = String(text || "").trim();
    if (!message || !this.projectId || this.generating) return;
    this.messages.push({ role: "user", content: message });
    this.messageList?.append(this.messages[this.messages.length - 1]);
    this.composer?.clear();
    this.setGenerating(true);
    this.setStatus("发送中…");
    try {
      const result = await apiJson("/ryan/creative/chat", {
        method: "POST",
        body: {
          project_id: this.projectId,
          stage_id: this.stageId,
          thread_id: this.threadId,
          message,
          skill_id: this.skillId,
          skill_scope: "stage",
          asset_ref_ids: this.selectedAssetIds,
        },
      });
      this.threadId = result.thread_id || this.threadId;
      // If no WS events arrived, fall back to final text.
      const last = this.messages[this.messages.length - 1];
      if (!(last?.role === "assistant" && (last.content || last.streaming))) {
        this.messages.push({ role: "assistant", content: result.text || "" });
        this.messageList?.append(this.messages[this.messages.length - 1]);
      } else if (last.streaming) {
        last.streaming = false;
        last.pending = false;
        if (result.text) last.content = result.text;
        this.messageList?.updateLast(last);
      }
      this.setGenerating(false);
      this.setStatus(result.ready?.ready ? "READY：可确认草稿" : "已回复");
      await this.refreshStages();
      await this.refreshThreads();
      this.renderSide();
    } catch (err) {
      this.setGenerating(false);
      this.setStatus(String(err.message || err), true);
    }
  }

  async stop() {
    if (!this.projectId || !this.threadId) return;
    try {
      await apiJson("/ryan/creative/chat/stop", {
        method: "POST",
        body: { project_id: this.projectId, thread_id: this.threadId },
      });
      this.setStatus("正在停止…");
    } catch (err) {
      this.setStatus(String(err.message || err), true);
    }
  }

  async confirm(mode) {
    if (!this.projectId || !this.stageId) return;
    this.setStatus(mode === "draft" ? "确认草稿…" : "确认阶段…");
    try {
      const result = await apiJson(
        `/ryan/creative/projects/${encodeURIComponent(this.projectId)}/stages/${encodeURIComponent(this.stageId)}/confirm`,
        { method: "POST", body: { mode, thread_id: this.threadId } }
      );
      this.setStatus(`已锁定 r${result.stage?.revision || "?"}`);
      await this.refreshStages();
      this.renderSide();
    } catch (err) {
      this.setStatus(String(err.message || err), true);
    }
  }

  closePop() {
    this.root?.querySelector(".cw-pop")?.remove();
  }

  openSkillPalette() {
    this.closePop();
    const host = this.root?.querySelector(".cw-composer");
    if (!host) return;
    const pop = el("div", { className: "cw-pop" });
    const items = this.skills.length
      ? this.skills
      : this.stages.map((s) => ({ skill_id: s.skill_id, display_name: s.display_name, stage_id: s.stage_id }));
    for (const skill of items) {
      pop.append(
        el("button", {
          type: "button",
          text: `${skill.display_name || skill.skill_id} · ${skill.skill_id}`,
          onClick: () => {
            this.skillId = skill.skill_id;
            if (skill.stage_id) this.stageId = skill.stage_id;
            // strip trailing slash trigger
            if (this.composer?.textarea?.value?.endsWith("/")) {
              this.composer.textarea.value = this.composer.textarea.value.slice(0, -1);
            }
            this.closePop();
            this.renderSide();
            this.renderChips();
            this.composer?.focus();
          },
        })
      );
    }
    if (!items.length) pop.append(el("button", { type: "button", text: "暂无 Skill", onClick: () => this.closePop() }));
    host.append(pop);
  }

  async openAssetPicker() {
    this.closePop();
    const host = this.root?.querySelector(".cw-composer");
    if (!host || !this.projectId) return;
    const pop = el("div", { className: "cw-pop" });
    pop.append(el("button", { type: "button", text: "加载中…", disabled: true }));
    host.append(pop);
    let assets = [];
    try {
      const providers = await apiJson("/ryan/creative/assets/providers");
      const comfy = (providers.providers || []).find((p) => p.id === "comfytv" && p.available);
      if (comfy) {
        const data = await apiJson("/ryan/creative/assets?provider=comfytv&limit=50");
        assets = data.assets || [];
      }
    } catch (_err) {
      assets = [];
    }
    pop.innerHTML = "";
    if (!assets.length) {
      pop.append(
        el("button", {
          type: "button",
          text: "无 ComfyTV 资产（可稍后接本地上传）",
          onClick: () => this.closePop(),
        })
      );
      return;
    }
    for (const asset of assets.slice(0, 40)) {
      pop.append(
        el("button", {
          type: "button",
          text: `${asset.name || asset.id} · ${asset.media_type || "asset"}`,
          onClick: async () => {
            try {
              const data = await apiJson(
                `/ryan/creative/projects/${encodeURIComponent(this.projectId)}/asset-refs`,
                { method: "POST", body: { asset, semantic_role: "reference" } }
              );
              const ref = data.asset_ref;
              this.assetRefs = data.asset_refs || this.assetRefs;
              if (ref?.asset_ref_id && !this.selectedAssetIds.includes(ref.asset_ref_id)) {
                this.selectedAssetIds.push(ref.asset_ref_id);
              }
              if (this.composer?.textarea?.value?.endsWith("@")) {
                this.composer.textarea.value = this.composer.textarea.value.slice(0, -1);
              }
              this.renderChips();
              this.closePop();
              this.setStatus(`已引用 ${ref?.display_name || "资产"}`);
            } catch (err) {
              this.setStatus(String(err.message || err), true);
            }
          },
        })
      );
    }
  }

  bindDrag() {
    if (this._dragBound || !this.root) return;
    this._dragBound = true;
    let dragging = false;
    let sx = 0;
    let sy = 0;
    let ox = 0;
    let oy = 0;
    this.root.addEventListener("mousedown", (ev) => {
      const hdr = this.root.querySelector(".cw-header");
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

const panel = new CreativeWorkspaceApp();

app.registerExtension({
  name: "Ryan.CreativeWorkspace.Panel",
  async nodeCreated(node) {
    if (node?.comfyClass !== "Ryan Creative Text Selector") return;
    try {
      const data = await apiJson("/ryan/creative/projects");
      const current = data.current_creative_project_id || "";
      const widget = node.widgets?.find((w) => w.name === "creative_project_id");
      if (widget && current && !String(widget.value || "").trim()) widget.value = current;
    } catch (_err) {
      /* ignore */
    }
  },
});

globalThis.RyanCreativeWorkspace = panel;

export { panel };
export default panel;
