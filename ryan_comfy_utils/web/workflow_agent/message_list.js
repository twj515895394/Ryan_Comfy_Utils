function el(tag, className, text = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

function renderMarkdown(text) {
  const fragment = document.createDocumentFragment();
  const lines = String(text || "").split(/\r?\n/);
  let code = null;
  let list = null;
  for (const line of lines) {
    if (line.trim().startsWith("```")) {
      if (code) { fragment.append(code); code = null; }
      else code = el("pre", "ryan-markdown-code");
      continue;
    }
    if (code) { code.append(document.createTextNode(`${line}\n`)); continue; }
    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) { list = null; fragment.append(el(`h${heading[1].length + 2}`, "ryan-markdown-heading", heading[2])); continue; }
    const bullet = line.match(/^\s*[-*]\s+(.+)$/);
    if (bullet) {
      if (!list) { list = el("ul", "ryan-markdown-list"); fragment.append(list); }
      list.append(el("li", "", bullet[1]));
      continue;
    }
    list = null;
    if (!line.trim()) { fragment.append(el("div", "ryan-markdown-spacer")); continue; }
    fragment.append(el("p", "ryan-markdown-paragraph", line));
  }
  if (code) fragment.append(code);
  return fragment;
}

function renderMessage(message) {
  const role = message.role === "user" ? "user" : message.role === "system" ? "system" : "assistant";
  const pending = Boolean(message.pending);
  const article = el("article", `ryan-message ryan-message--${role}${pending ? " ryan-message--pending" : ""}`);
  const header = el("div", "ryan-message__header", role === "user" ? "你" : role === "system" ? "Context" : "Ryan Agent");
  const body = el("div", "ryan-message__body");
  if (pending) {
    body.setAttribute("aria-busy", "true");
    body.append(el("span", "ryan-pending-dots", "Ryan Agent 正在思考"));
  } else {
    body.append(renderMarkdown(message.content || message.text || ""));
  }
  article.append(header, body);
  if (message.error) article.append(el("div", "ryan-message__error", String(message.error)));
  return article;
}

export class MessageList {
  constructor({ onNearBottom = () => {}, onScroll = () => {} } = {}) {
    this.root = el("section", "ryan-message-list");
    this.busyLayer = el("div", "ryan-message-list__busy");
    this.busyLayer.setAttribute("aria-live", "polite");
    this.busyLayer.setAttribute("role", "status");
    this.busyLayer.setAttribute("aria-hidden", "true");
    const spinner = el("span", "ryan-message-list__busy-spinner");
    spinner.setAttribute("aria-hidden", "true");
    this.busyLayer.append(spinner, el("span", "ryan-message-list__busy-text"));
    this.root.append(this.busyLayer);
    this.onNearBottom = onNearBottom;
    this.onScroll = onScroll;
    this.root.addEventListener("scroll", () => {
      const distance = this.root.scrollHeight - this.root.scrollTop - this.root.clientHeight;
      this.onNearBottom(distance < 120);
      this.onScroll(this.root.scrollTop);
    });
    this.setBusy(false);
  }

  setBusy(busy, status = "generating") {
    const visible = Boolean(busy);
    const label = status === "submitting" ? "正在连接 Pi…" : "Pi 正在思考…";
    this.busyLayer.classList.toggle("is-visible", visible);
    this.busyLayer.setAttribute("aria-hidden", String(!visible));
    this.busyLayer.querySelector(".ryan-message-list__busy-text").textContent = label;
    this.root.setAttribute("aria-busy", String(visible));
  }

  mount(parent) { parent.append(this.root); }

  render(messages = []) {
    const nearBottom = this.root.scrollHeight - this.root.scrollTop - this.root.clientHeight < 120;
    this.root.replaceChildren();
    if (!messages.length) {
      const empty = el("div", "ryan-message-empty");
      empty.append(el("div", "ryan-message-empty__icon", "✦"), el("h3", "", "开始一段有上下文的创作"), el("p", "", "你可以先查看上游 Context，或直接告诉 Agent 你想推进的方向。"));
      this.root.append(empty);
    } else messages.forEach((message) => this.root.append(renderMessage(message)));
    this.root.append(this.busyLayer);
    if (nearBottom) this.scrollToBottom();
  }

  append(message) {
    const wasNearBottom = this.root.scrollHeight - this.root.scrollTop - this.root.clientHeight < 120;
    const empty = this.root.querySelector(".ryan-message-empty");
    if (empty) empty.remove();
    this.root.insertBefore(renderMessage(message), this.busyLayer);
    if (wasNearBottom) this.scrollToBottom();
  }

  updateLast(message) {
    const messages = this.root.querySelectorAll(".ryan-message");
    const last = messages[messages.length - 1];
    if (!last || !last.classList.contains("ryan-message--assistant")) return this.append(message);
    const body = last.querySelector(".ryan-message__body");
    body.replaceChildren(renderMarkdown(message.content || message.text || ""));
    if (message.error) last.append(el("div", "ryan-message__error", String(message.error)));
  }

  scrollToBottom() { this.root.scrollTop = this.root.scrollHeight; }
  get scrollTop() { return this.root.scrollTop; }
  set scrollTop(value) { this.root.scrollTop = Number(value) || 0; }
}

export default MessageList;

