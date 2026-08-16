const TYPES = [
  { type: "document", label: "文档", icon: "▤", accept: ".txt,.md,.json,.csv,.pdf,.doc,.docx" },
  { type: "image", label: "图片", icon: "▧", accept: "image/*" },
  { type: "video", label: "视频", icon: "▹", accept: "video/*" },
  { type: "audio", label: "音频", icon: "♫", accept: "audio/*", disabled: true },
];

function el(tag, className, text = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

function iconFor(type) { return TYPES.find((item) => item.type === type)?.icon || "•"; }

export class AttachmentTray {
  constructor({ onUpload = async () => {}, onDetach = async () => {} } = {}) {
    this.onUpload = onUpload;
    this.onDetach = onDetach;
    this.root = el("section", "ryan-attachment-tray");
    this.controls = el("div", "ryan-attachment-controls");
    this.cards = el("div", "ryan-attachment-cards");
    this.input = document.createElement("input");
    this.input.type = "file";
    this.input.multiple = false;
    this.input.hidden = true;
    this.input.addEventListener("change", () => this.handleFiles(this.input.files));
    TYPES.forEach((config) => {
      const button = el("button", "ryan-attachment-button", `${config.icon} ${config.label}`);
      button.type = "button";
      button.disabled = Boolean(config.disabled);
      button.title = config.disabled ? "音频入口保留，当前版本暂不支持消费" : `添加${config.label}`;
      button.addEventListener("click", () => {
        if (config.disabled) return;
        this.input.accept = config.accept;
        this.input.click();
      });
      this.controls.append(button);
    });
    this.root.append(this.controls, this.cards, this.input);
  }

  mount(parent) { parent.append(this.root); }

  async handleFiles(files) {
    const file = files?.[0];
    if (!file) return;
    try { await this.onUpload(file); }
    catch (error) { this.root.dispatchEvent(new CustomEvent("error", { detail: error })); }
    finally { this.input.value = ""; }
  }

  render(attachments = []) {
    this.cards.replaceChildren();
    attachments.forEach((asset) => {
      const card = el("span", "ryan-attachment-card");
      card.append(el("span", "ryan-attachment-card__icon", iconFor(asset.type)), el("span", "ryan-attachment-card__name", asset.display_name || asset.asset_id || "资产"));
      if (asset.source) card.title = `来源：${asset.source}`;
      if (asset.asset_id) {
        const remove = el("button", "ryan-attachment-card__remove", "×");
        remove.type = "button";
        remove.title = "移除附件";
        remove.addEventListener("click", async () => {
          try { await this.onDetach(asset); }
          catch (error) { this.root.dispatchEvent(new CustomEvent("error", { detail: error })); }
        });
        card.append(remove);
      }
      this.cards.append(card);
    });
  }
}

export default AttachmentTray;
