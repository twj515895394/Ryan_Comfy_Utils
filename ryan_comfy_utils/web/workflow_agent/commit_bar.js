function el(tag, className, text = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

export class CommitBar {
  constructor({ onCommit = async () => {} } = {}) {
    this.onCommit = onCommit;
    this.root = el("section", "ryan-commit-bar");
    this.copy = el("div", "ryan-commit-bar__copy");
    this.title = el("strong", "ryan-commit-bar__title");
    this.detail = el("span", "ryan-commit-bar__detail");
    this.copy.append(this.title, this.detail);
    this.preview = el("button", "ryan-button ryan-button--quiet", "预览");
    this.preview.type = "button";
    this.preview.addEventListener("click", () => this.showPreview());
    this.commit = el("button", "ryan-button ryan-button--accent", "确认并提交到 DAG");
    this.commit.type = "button";
    this.commit.addEventListener("click", () => this.onCommit());
    this.actions = el("div", "ryan-commit-bar__actions");
    this.actions.append(this.preview, this.commit);
    this.root.append(this.copy, this.actions);
  }

  mount(parent) { parent.append(this.root); }

  update(state = {}) {
    const dirty = Boolean(state.draft);
    const busy = ["submitting", "generating", "committing"].includes(state.status) || state.commitStatus === "committing";
    const committing = state.status === "committing" || state.commitStatus === "committing";
    this.root.classList.toggle("is-dirty", dirty);
    this.root.classList.toggle("is-committing", committing);
    this.title.textContent = committing ? "正在提交到 DAG…" : dirty ? "当前 Draft 尚未进入 DAG" : "Draft 与 Commit 已同步";
    this.detail.textContent = committing
      ? "正在写入 Canonical Entry，请稍候"
      : state.commitRevision ? `上次提交：v${state.commitRevision}` : "尚无 Commit";
    this.commit.textContent = committing ? "提交中…" : "确认并提交到 DAG";
    this.commit.setAttribute("aria-busy", String(committing));
    this.commit.classList.toggle("is-loading", committing);
    this.commit.disabled = !dirty || busy;
    this.preview.disabled = !dirty || busy;
  }

  showPreview() {
    const preview = el("div", "ryan-commit-preview");
    preview.append(el("strong", "", "Commit 预览"), el("p", "", "当前 Draft 将以新的 revision 写入 DAG。"));
    this.root.append(preview);
    window.setTimeout(() => preview.remove(), 3500);
  }
}

export default CommitBar;
