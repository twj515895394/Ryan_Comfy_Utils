function el(tag, className, text = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

function entryLabel(entry) {
  return entry.source_agent_name || entry.source_agent_uid || entry.kind || "上游 Agent";
}

function renderEntry(entry) {
  const details = el("details", "ryan-context-entry");
  const summary = el("summary", "ryan-context-entry__summary");
  const title = el("strong", "ryan-context-entry__agent", entryLabel(entry));
  const meta = el("span", "ryan-context-entry__meta", `${entry.kind || "context"} · rev ${Number(entry.revision || 0)}`);
  summary.append(title, meta);
  const body = el("div", "ryan-context-entry__body");
  body.append(
    el("p", "ryan-context-entry__summary-text", entry.summary || "暂无摘要"),
    el("p", "ryan-context-entry__source", `来源：${entry.source_agent_name || entry.source_agent_uid || "未知 Agent"}`),
  );
  if (entry.content) {
    const content = el("pre", "ryan-context-entry__content", String(entry.content));
    body.append(content);
  }
  const assets = Array.isArray(entry.asset_refs) ? entry.asset_refs : [];
  if (assets.length) body.append(el("p", "ryan-context-entry__assets", `${assets.length} 个关联资产`));
  renderArtifacts(entry, body);
  details.append(summary, body);
  return details;
}

function artifactCatalog(entry) {
  const bundle = entry?.metadata?.artifact_bundle;
  if (!bundle || typeof bundle !== "object") return [];
  const outputs = Array.isArray(bundle.outputs) ? bundle.outputs : [];
  const shots = Array.isArray(bundle.shots) ? bundle.shots : [];
  return [
    ...outputs.map((item) => ({
      id: item.output_id,
      kind: item.kind || "output",
      label: item.label || item.output_id || "产物",
      text: item.text,
    })),
    ...shots.map((item) => ({
      id: item.shot_id,
      kind: item.kind || "shot",
      label: item.label || item.shot_id || "镜头",
      text: item.prompt,
    })),
  ].filter((item) => item.id && typeof item.text === "string" && item.text.trim());
}

async function copyArtifactText(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const input = document.createElement("textarea");
  input.value = text;
  input.setAttribute("readonly", "");
  input.style.position = "fixed";
  input.style.opacity = "0";
  document.body.append(input);
  input.select();
  const copied = document.execCommand("copy");
  input.remove();
  if (!copied) throw new Error("clipboard unavailable");
}

function renderArtifactCatalog(entry) {
  const items = artifactCatalog(entry);
  if (!items.length) return null;
  const section = el("div", "ryan-context-artifacts");
  section.append(el("h4", "ryan-context-artifacts__title", "产物目录"));
  items.forEach((item) => {
    const button = el("button", "ryan-artifact-copy", `${item.label} · ${item.kind} · 复制`);
    button.type = "button";
    button.title = `复制 ${item.label}`;
    button.addEventListener("click", async () => {
      const originalText = button.textContent;
      try {
        await copyArtifactText(item.text);
        button.textContent = `${item.label} · 已复制`;
      } catch (_error) {
        button.textContent = `${item.label} · 复制失败`;
      }
      window.setTimeout(() => { button.textContent = originalText; }, 1600);
    });
    section.append(button);
  });
  return section;
}

function renderArtifacts(entry, body) {
  const catalog = renderArtifactCatalog(entry);
  if (catalog) body.append(catalog);
}

export class ContextInspector {
  constructor(onChange = () => {}) {
    this.onChange = onChange;
    this.root = el("section", "ryan-context-inspector");
    this.root.hidden = true;
    this.button = el("button", "ryan-context-bar", "暂无上游 Context");
    this.button.type = "button";
    this.button.addEventListener("click", () => {
      this.root.classList.toggle("is-expanded");
      this.details.hidden = !this.root.classList.contains("is-expanded");
      this.onChange(this.root.classList.contains("is-expanded"));
    });
    this.details = el("div", "ryan-context-details");
    this.root.append(this.button, this.details);
  }

  mount(parent) { parent.append(this.root); }

  update(context = {}, { received = false } = {}) {
    const entries = Array.isArray(context.entries) ? context.entries : [];
    const assets = Array.isArray(context.assets) ? context.assets : [];
    const sourceCount = new Set(entries.map((entry) => entry.source_agent_uid || entry.source_agent_name || entry.kind)).size;
    this.root.hidden = false;
    this.button.textContent = entries.length
      ? `↑ 上游 ${sourceCount} 个 Agent · ${entries.length} 个 Context Entries · ${assets.length} 个资产`
      : received
        ? `✓ 上游 Context 已流转 · 0 个 Entries · ${assets.length} 个资产`
        : `↑ 暂无上游 Context · ${assets.length} 个资产`;
    this.details.replaceChildren();
    if (!entries.length && !assets.length) {
      this.details.append(el("p", "ryan-context-empty", "本 Agent 将只使用当前聊天与直接连接素材。"));
      return;
    }
    entries.forEach((entry) => this.details.append(renderEntry(entry)));
    if (assets.length) {
      const assetList = el("div", "ryan-context-assets");
      assetList.append(el("h4", "ryan-context-assets__title", "可见资产"));
      assets.forEach((asset) => assetList.append(el("span", "ryan-asset-chip", `${asset.display_name || asset.asset_id || "资产"} · ${asset.source || "context"}`)));
      this.details.append(assetList);
    }
  }
}

export default ContextInspector;
