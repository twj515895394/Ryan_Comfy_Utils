function el(tag, className, text = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

export class Composer {
  constructor({ onSend = async () => {}, onStop = async () => {}, onDraft = () => {} } = {}) {
    this.onSend = onSend;
    this.onStop = onStop;
    this.onDraft = onDraft;
    this.root = el("form", "ryan-composer");
    this.tools = el("div", "ryan-composer__tools");
    this.hint = el("span", "ryan-composer__hint", "Enter 发送 · Shift+Enter 换行");
    this.textarea = document.createElement("textarea");
    this.textarea.className = "ryan-composer__input";
    this.textarea.rows = 2;
    this.textarea.maxLength = 20000;
    this.textarea.placeholder = "描述你的需求，或继续讨论…";
    this.textarea.addEventListener("input", () => { this.resize(); this.onDraft(this.textarea.value); });
    this.textarea.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
        event.preventDefault();
        this.submit();
      }
    });
    this.submitButton = el("button", "ryan-send-button", "↑");
    this.submitButton.type = "submit";
    this.submitButton.title = "发送消息";
    this.root.addEventListener("submit", (event) => { event.preventDefault(); this.submit(); });
    this.root.append(this.tools, this.textarea, this.hint, this.submitButton);
  }

  mount(parent) { parent.append(this.root); }

  setDraft(value) { this.textarea.value = value || ""; this.resize(); }
  get value() { return this.textarea.value.trim(); }
  clear() { this.setDraft(""); }
  focus() { this.textarea.focus(); }
  resize() { this.textarea.style.height = "auto"; this.textarea.style.height = `${Math.min(this.textarea.scrollHeight, 180)}px`; }

  setGenerating(busy, status = "generating") {
    const generating = status === "generating";
    this.submitButton.textContent = generating ? "■" : "…";
    this.submitButton.title = generating ? "停止生成" : "正在发送";
    this.submitButton.classList.toggle("is-stop", generating);
    this.submitButton.classList.toggle("is-busy", Boolean(busy));
    this.textarea.disabled = Boolean(busy);
  }

  async submit() {
    if (this.submitButton.classList.contains("is-stop")) return this.onStop();
    if (this.submitButton.classList.contains("is-busy")) return;
    const value = this.value;
    if (!value) return;
    await this.onSend(value);
  }
}

export default Composer;
