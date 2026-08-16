import ContextInspector from "./context_inspector.js";
import MessageList from "./message_list.js";
import Composer from "./composer.js";
import AttachmentTray from "./attachment_tray.js";
import CommitBar from "./commit_bar.js";

function el(tag, className, text = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

function normaliseMessage(record) {
  return { role: record.role || "assistant", content: record.content || record.text || "", requestId: record.request_id || record.requestId || "", messageId: record.message_id || record.messageId || "", pending: Boolean(record.pending), error: record.error || "" };
}

export class AgentPanel {
  constructor({ api, store, onClose = () => {}, onState = () => {}, toast = () => {} }) {
    this.api = api;
    this.store = store;
    this.onClose = onClose;
    this.onState = onState;
    this.toast = toast;
    this.agentNameValue = "Workflow Agent";
    this.workflowId = "";
    this.agentUid = "";
    this.skillId = "";
    this.context = { workflow_id: "", entries: [], assets: [], lineage: [] };
    this.openGeneration = 0;
    this.state = null;
    this.root = el("aside", "ryan-agent-panel");
    this.header = el("header", "ryan-agent-header");
    this.headerCopy = el("div", "ryan-agent-header__copy");
    this.agentName = el("h2", "ryan-agent-header__name", "Workflow Agent");
    this.skill = el("p", "ryan-agent-header__skill");
    this.status = el("span", "ryan-agent-header__status");
    this.headerCopy.append(this.agentName, this.skill, this.status);
    this.close = el("button", "ryan-panel-close", "×");
    this.close.type = "button";
    this.close.title = "关闭 Agent Workspace";
    this.close.addEventListener("click", () => this.onClose());
    this.header.append(this.headerCopy, this.close);
    this.contextInspector = new ContextInspector();
    this.messages = new MessageList({
      onNearBottom: (nearBottom) => { this._nearBottom = nearBottom; },
      onScroll: (scrollTop) => this.rememberScroll(scrollTop),
    });
    this.commitBar = new CommitBar({ onCommit: () => this.commit() });
    this.attachments = new AttachmentTray({ onUpload: (file) => this.upload(file), onDetach: (asset) => this.detach(asset) });
    this.attachments.root.addEventListener("error", (event) => this.setError(event.detail));
    this.composer = new Composer({ onSend: (message) => this.send(message), onStop: () => this.stop(), onDraft: (draft) => this.updateDraft(draft) });
    this.root.append(this.header);
    this.contextInspector.mount(this.root);
    this.messages.mount(this.root);
    this.commitBar.mount(this.root);
    this.attachments.mount(this.root);
    this.composer.mount(this.root);
  }

  mount(parent) { parent.append(this.root); }

  async open(detail = {}) {
    const generation = ++this.openGeneration;
    const requestedName = String(detail.agentName || detail.agent_name || "");
    this.agentNameValue = requestedName || "Workflow Agent";
    this.workflowId = String(detail.workflowId || detail.workflow_id || "");
    this.agentUid = String(detail.agentUid || detail.agent_uid || "");
    this.skillId = String(detail.skillId || detail.skill_id || "none");
    if (!this.workflowId || !this.agentUid) return;
    const storedContext = this.store.get(this.workflowId, this.agentUid).context;
    const providedContext = detail.context && typeof detail.context === "object" ? detail.context : null;
    const hasContext = Boolean(
      providedContext
      && (providedContext.entries?.length || providedContext.assets?.length || providedContext.lineage?.length),
    );
    this.context = hasContext
      ? providedContext
      : storedContext?.workflow_id
        ? storedContext
        : providedContext || { workflow_id: this.workflowId, entries: [], assets: [], lineage: [] };
    this.state = this.store.set(this.workflowId, this.agentUid, {
      ...this.store.get(this.workflowId, this.agentUid),
      agentName: this.agentNameValue,
      skillId: this.skillId,
      context: this.context,
      contextReceived: Boolean(
        this.store.get(this.workflowId, this.agentUid).contextReceived
        || hasContext
        || detail.contextReceived,
      ),
    });
    this.renderState();
    try {
      const [agent, assets] = await Promise.all([
        this.api.getAgent(this.workflowId, this.agentUid),
        this.api.listAssets(this.workflowId, this.agentUid),
      ]);
      if (generation !== this.openGeneration) return;
      this.skillId = agent.skill_id || this.skillId;
      const detailContext = detail.context;
      if (
        detailContext
        && typeof detailContext === "object"
        && (detailContext.entries?.length || detailContext.assets?.length || detailContext.lineage?.length)
      ) {
        this.context = detailContext;
      }
      this.state = this.store.set(this.workflowId, this.agentUid, {
        ...agent,
        agentName: this.agentNameValue,
        skillId: this.skillId,
        messages: Array.isArray(agent.messages) ? agent.messages.map(normaliseMessage) : this.state.messages,
        attachments: Array.isArray(assets.assets) ? assets.assets : this.state.attachments,
        context: this.context,
        draft: agent.draft ?? this.state.draft,
        commitRevision: Number(agent.commit_revision || this.state.commitRevision || 0),
        upstreamChanged: Boolean(agent.upstream_changed || this.state.upstreamChanged),
      });
      this.renderState();
    } catch (error) {
      if (generation === this.openGeneration) this.setError(error);
      return;
    }
    if (generation === this.openGeneration) this.composer.focus();
  }

  renderState() {
    const state = this.state || {};
    const agentName = state.agentName || state.agent_name || this.agentNameValue || "Workflow Agent";
    const scrollTop = Number(state.scrollTop ?? this.messages.root.scrollTop ?? 0);
    this.contextInspector.update(state.context || this.context, { received: Boolean(state.contextReceived) });
    this.skill.textContent = state.skillId || state.skill_id || this.skillId || "未选择 Skill";
    this.status.textContent = this.statusLabel(state);
    this.root.dataset.status = state.status || "idle";
    this.messages.render((state.messages || []).map(normaliseMessage));
    this.messages.setBusy?.(["submitting", "generating"].includes(state.status), state.status);
    this.messages.root.scrollTop = Number.isFinite(scrollTop) ? scrollTop : 0;
    this.attachments.render(state.attachments || []);
    this.composer.setDraft(state.composerDraft || "");
    this.composer.setGenerating(["submitting", "generating"].includes(state.status), state.status);
    this.commitBar.update(state);
    this.onState({ workflowId: this.workflowId, agentUid: this.agentUid, ...state });
  }

  statusLabel(state) {
    if (state.status === "error") return "● 执行失败";
    if (state.status === "stopped") return "● 已停止";
    if (state.status === "submitting") return "● 正在连接 Pi…";
    if (state.status === "generating") return "● Pi 正在思考…";

    if (state.upstreamChanged) return "● 上游已更新";
    if (state.commitRevision) return `● 已提交 · v${state.commitRevision}`;
    if (state.draft || state.status === "chatting" || state.composerDraft) return "● 讨论中 · 未提交";
    return "● 未开始";
  }

  updateDraft(draft) {
    if (!this.state) return;
    const status = draft ? "chatting" : this.state.status === "chatting" ? "idle" : this.state.status;
    this.state = this.store.set(this.workflowId, this.agentUid, { composerDraft: draft, status, error: "" });
    this.onState({ workflowId: this.workflowId, agentUid: this.agentUid, ...this.state });
  }
  rememberScroll(scrollTop) {
    if (!this.state || this.state.scrollTop === scrollTop) return;
    this.state = this.store.set(this.workflowId, this.agentUid, { scrollTop });
  }


  async send(message) {
    const submittedMessage = String(message || "").trim();
    if (!this.state || ["submitting", "generating"].includes(this.state.status) || !submittedMessage) return;
    const workflowId = this.workflowId;
    const agentUid = this.agentUid;
    const skillId = this.skillId;
    const agentName = this.agentNameValue;
    const context = this.context;
    const requestId = `request-${crypto.randomUUID?.() || `${Date.now()}-${Math.random()}`}`;
    const messageId = `message-${crypto.randomUUID?.() || `${Date.now()}-${Math.random()}`}`;
    const pendingMessage = { role: "assistant", content: "", pending: true, requestId, messageId };
    const messages = [...(this.state.messages || []), { role: "user", content: submittedMessage, requestId, messageId }, pendingMessage];
    const assetRefs = (this.state.attachments || []).map((asset) => asset.asset_id);
    const isCurrent = () => this.workflowId === workflowId && this.agentUid === agentUid;
    this.state = this.store.set(workflowId, agentUid, {
      messages, composerDraft: "", status: "submitting", requestId, messageId, error: "",
    });
    this.renderState();
    await new Promise((resolve) => {
      const frame = globalThis.requestAnimationFrame;
      if (typeof frame === "function") frame(resolve);
      else globalThis.setTimeout(resolve, 0);
    });
    if (!isCurrent()) return;
    this.state = this.store.set(workflowId, agentUid, { status: "generating" });
    this.renderState();
    try {
      const result = await this.api.sendMessage({
        workflow_id: workflowId,
        agent_uid: agentUid,
        skill_id: skillId,
        agent_name: agentName,
        message: submittedMessage,
        request_id: requestId,
        message_id: messageId,
        upstream_context: context,
        asset_refs: assetRefs,
      });
      if (result.status && !["completed", "stopped"].includes(result.status)) {
        throw new Error(result.error || `Agent request ${result.status}`);
      }
      const completedEvent = [...(result.events || [])].reverse().find(
        (event) => event.type === "completed" && event.text
      );
      const responseText = String(result.response_text ?? result.draft ?? completedEvent?.text ?? "");
      if (result.status === "stopped") {
        const visibleMessages = messages.filter((item) => !item.pending);
        const stoppedMessages = responseText
          ? [...visibleMessages, { role: "assistant", content: responseText, requestId, messageId }]
          : visibleMessages;
        const stoppedState = this.store.set(workflowId, agentUid, {
          messages: stoppedMessages, composerDraft: "", draft: responseText,
          status: "stopped", upstreamChanged: Boolean(result.upstream_changed), error: "",
        });
        if (isCurrent()) {
          this.state = stoppedState;
          this.renderState();
          this.messages.scrollToBottom();
        }
        return;
      }
      if (!responseText.trim()) throw new Error("Agent returned an empty response");
      const nextMessages = [...messages.filter((item) => !item.pending), { role: "assistant", content: responseText, requestId, messageId }];
      const nextState = this.store.set(workflowId, agentUid, {
        messages: nextMessages, composerDraft: "", draft: result.draft || responseText,
        status: "idle", upstreamChanged: Boolean(result.upstream_changed), error: "",
      });
      if (isCurrent()) {
        this.state = nextState;
        this.renderState();
        this.messages.scrollToBottom();
      }
    } catch (error) {
      const messageText = error instanceof Error ? error.message : String(error || "request failed");
      const errorMessage = { role: "system", content: "执行失败", error: messageText, requestId, messageId };
      const failedMessages = [...messages.filter((item) => !(item.role === "assistant" && item.pending)), errorMessage];
      const failedPatch = { messages: failedMessages, composerDraft: "" };
      if (isCurrent()) this.setError(error, failedPatch);
      else this.store.set(workflowId, agentUid, { ...failedPatch, status: "error", error: messageText });
    }
  }

  async stop() {
    const workflowId = this.workflowId;
    const agentUid = this.agentUid;
    const requestId = this.state?.requestId;
    const messageId = this.state?.messageId;
    const draft = this.state?.draft || "";
    const isCurrent = () => this.workflowId === workflowId && this.agentUid === agentUid;
    try {
      const result = await this.api.stop({
        workflow_id: workflowId,
        agent_uid: agentUid,
        request_id: requestId,
        message_id: messageId,
      });
      const nextState = this.store.set(workflowId, agentUid, {
        messages: (this.state?.messages || []).filter((item) => !item.pending),
        status: "stopped", draft: result.draft || draft, error: "",
      });
      if (isCurrent()) {
        this.state = nextState;
        this.renderState();
      }
    } catch (error) {
      if (isCurrent()) this.setError(error);
      else this.store.set(workflowId, agentUid, { status: "error", error: error instanceof Error ? error.message : String(error || "request failed") });
    }
  }

  async commit() {
    if (!this.state?.draft || ["submitting", "generating", "committing"].includes(this.state.status)) return;
    const workflowId = this.workflowId;
    const agentUid = this.agentUid;
    const skillId = this.skillId;
    const agentName = this.agentNameValue;
    const draft = this.state.draft;
    const context = this.context;
    const assetRefs = (this.state.attachments || []).map((asset) => asset.asset_id);
    const isCurrent = () => this.workflowId === workflowId && this.agentUid === agentUid;
    this.state = this.store.set(workflowId, agentUid, { status: "committing", error: "" });
    this.renderState();
    try {
      const result = await this.api.commit({
        workflow_id: workflowId,
        agent_uid: agentUid,
        skill_id: skillId,
        agent_name: agentName,
        draft,
        upstream_context: context,
        asset_refs: assetRefs,
      });
      const nextState = this.store.set(workflowId, agentUid, { status: "committed", draft: "", commitRevision: Number(result.commit_revision || result.entry?.revision || 0), upstreamChanged: false, error: "" });
      if (isCurrent()) {
        this.state = nextState;
        this.renderState();
        this.toast(`已提交到 DAG · v${this.state.commitRevision}`);
      }
    } catch (error) {
      if (isCurrent()) this.setError(error);
      else this.store.set(workflowId, agentUid, { status: "error", error: error instanceof Error ? error.message : String(error || "request failed") });
    }
  }

  async upload(file) {
    const workflowId = this.workflowId;
    const agentUid = this.agentUid;
    const result = await this.api.attachAsset({ workflowId, agentUid, file });
    const asset = result.asset;
    if (!asset) return;
    const current = this.store.get(workflowId, agentUid);
    const attachments = [...(current.attachments || []).filter((item) => item.asset_id !== asset.asset_id), asset];
    const nextState = this.store.set(workflowId, agentUid, { attachments });
    if (this.workflowId === workflowId && this.agentUid === agentUid) {
      this.state = nextState;
      this.renderState();
    }
  }

  async detach(asset) {
    const workflowId = this.workflowId;
    const agentUid = this.agentUid;
    await this.api.detachAsset(workflowId, agentUid, asset.asset_id);
    const current = this.store.get(workflowId, agentUid);
    const nextState = this.store.set(workflowId, agentUid, { attachments: (current.attachments || []).filter((item) => item.asset_id !== asset.asset_id) });
    if (this.workflowId === workflowId && this.agentUid === agentUid) {
      this.state = nextState;
      this.renderState();
    }
  }


  setError(error, patch = {}) {
    const message = error instanceof Error ? error.message : String(error || "request failed");
    this.state = this.store.set(this.workflowId, this.agentUid, { ...patch, status: "error", error: message });
    this.renderState();
    this.toast(message, "error");
  }
}

export default AgentPanel;
