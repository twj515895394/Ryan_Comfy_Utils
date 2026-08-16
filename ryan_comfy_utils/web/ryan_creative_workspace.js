/**
 * Bootstrap: mount Ryan 构想台 as a real sibling in the same toolbar row as
 * TE_MAN 构想台 / 资产库 — not a fixed overlay layer.
 */
import { app } from "../../../scripts/app.js";

const TOGGLE_ID = "ryan-creative-workspace-toggle";
const STYLE_ID = "ryan-cw-toggle-dock-styles";

function ensureToggleStyles() {
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = STYLE_ID;
  // Only minor polish; when docked we inherit toolbar button look from siblings.
  style.textContent = `
  #${TOGGLE_ID}.ryan-cw-docked{
    position: static !important;
    inset: auto !important;
    top: auto !important;
    right: auto !important;
    left: auto !important;
    bottom: auto !important;
    z-index: auto !important;
    margin: 0 0 0 6px !important;
    flex: 0 0 auto !important;
    align-self: center !important;
  }
  #${TOGGLE_ID}.ryan-cw-fallback{
    position: fixed !important;
    top: 52px !important;
    right: 16px !important;
    z-index: 10080 !important;
    height: 32px !important;
    padding: 0 12px !important;
    border-radius: 8px !important;
    border: 1px solid rgba(214,179,106,.45) !important;
    background: linear-gradient(180deg,#3f4f72 0%,#2a3550 100%) !important;
    color: #f3f6ff !important;
    font: 600 12px/32px system-ui,sans-serif !important;
    cursor: pointer !important;
    box-shadow: 0 8px 22px rgba(0,0,0,.35) !important;
  }
  `;
  document.head.appendChild(style);
}

function labelOf(node) {
  return `${node?.textContent || ""} ${node?.getAttribute?.("aria-label") || ""} ${node?.title || ""}`
    .replace(/\s+/g, " ")
    .trim();
}

function isInteractive(node) {
  if (!node || node.id === TOGGLE_ID) return false;
  const tag = (node.tagName || "").toLowerCase();
  if (tag === "button" || tag === "a") return true;
  if (node.getAttribute?.("role") === "button") return true;
  if (typeof node.onclick === "function") return true;
  if (node.className && /btn|button|p-button/i.test(String(node.className))) return true;
  return false;
}

function findToolbarAnchor() {
  const all = [...document.querySelectorAll("button, a, [role='button'], .p-button, [class*='button']")];
  const te = all.find((n) => {
    if (!isInteractive(n)) return false;
    const label = labelOf(n);
    return label.includes("构想台") && !label.includes("Ryan");
  });
  if (te) return te;
  const asset = all.find((n) => isInteractive(n) && labelOf(n).includes("资产库"));
  if (asset) return asset;
  return all.find((n) => isInteractive(n) && labelOf(n).includes("ComfyTV")) || null;
}

function copyToolbarLook(btn, anchor) {
  if (!anchor) return;
  // Match TE_MAN / toolbar control chrome as closely as possible.
  try {
    btn.className = `${anchor.className || ""} ryan-cw-docked`.trim();
  } catch (_err) {
    btn.className = "ryan-cw-docked";
  }
  // Clear any leftover fixed positioning from previous versions.
  btn.style.position = "";
  btn.style.top = "";
  btn.style.right = "";
  btn.style.left = "";
  btn.style.bottom = "";
  btn.style.zIndex = "";
  btn.style.boxShadow = "";
  // Prefer anchor computed metrics when classes alone are insufficient.
  try {
    const cs = getComputedStyle(anchor);
    if (cs.height && cs.height !== "auto") btn.style.height = cs.height;
    if (cs.borderRadius) btn.style.borderRadius = cs.borderRadius;
    if (cs.fontSize) btn.style.fontSize = cs.fontSize;
    if (cs.fontWeight) btn.style.fontWeight = cs.fontWeight;
    if (cs.padding && cs.padding !== "0px") btn.style.padding = cs.padding;
  } catch (_err) {
    /* ignore */
  }
}

function dockBesideAnchor(btn, anchor) {
  const parent = anchor.parentElement;
  if (!parent) return false;
  copyToolbarLook(btn, anchor);
  btn.classList.add("ryan-cw-docked");
  btn.classList.remove("ryan-cw-fallback");

  const label = labelOf(anchor);
  // Insert immediately before TE_MAN 构想台; otherwise after 资产库/ComfyTV.
  if (label.includes("构想台") && !label.includes("Ryan")) {
    if (btn.parentElement !== parent || btn.nextSibling !== anchor) {
      parent.insertBefore(btn, anchor);
    }
  } else if (btn.parentElement !== parent || btn.previousSibling !== anchor) {
    anchor.insertAdjacentElement("afterend", btn);
  }
  return parent.contains(btn);
}

function fallbackFixed(btn) {
  btn.classList.remove("ryan-cw-docked");
  btn.classList.add("ryan-cw-fallback");
  // reset className pollution from anchor copy
  if (!btn.className.includes("ryan-cw-fallback")) {
    btn.className = "ryan-cw-fallback";
  }
  btn.style.height = "";
  btn.style.padding = "";
  btn.style.borderRadius = "";
  if (btn.parentElement !== document.body) document.body.appendChild(btn);
}

function ensureToggle(onClick) {
  ensureToggleStyles();
  let btn = document.getElementById(TOGGLE_ID);
  if (!btn) {
    btn = document.createElement("button");
    btn.id = TOGGLE_ID;
    btn.type = "button";
    btn.textContent = "Ryan 构想台";
    btn.title = "打开/关闭 Ryan Creative Workspace";
    btn.addEventListener("click", (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      onClick();
    });
  }

  const anchor = findToolbarAnchor();
  if (anchor) {
    const ok = dockBesideAnchor(btn, anchor);
    if (!ok) fallbackFixed(btn);
  } else {
    fallbackFixed(btn);
  }
  return btn;
}

let panelModPromise = null;
function loadPanelModule() {
  if (!panelModPromise) {
    panelModPromise = import("./creative_workspace/index.js").catch((err) => {
      panelModPromise = null;
      console.error("[Ryan Creative Workspace] panel import failed", err);
      throw err;
    });
  }
  return panelModPromise;
}

async function togglePanel() {
  try {
    const mod = await loadPanelModule();
    const panel = mod.panel || mod.default || globalThis.RyanCreativeWorkspace;
    if (!panel?.toggle) throw new Error("panel module missing toggle()");
    panel.toggle();
  } catch (err) {
    console.error(err);
    window.alert(`Ryan 构想台加载失败：${err?.message || err}\n请打开 Console 查看详情。`);
  }
}

function bootToggle() {
  try {
    ensureToggle(() => togglePanel());
    if (!globalThis.__ryanCwToggleGuard) {
      globalThis.__ryanCwToggleGuard = setInterval(() => {
        const existing = document.getElementById(TOGGLE_ID);
        // If TE_MAN re-rendered toolbar and dropped us, re-dock as sibling again.
        const anchor = findToolbarAnchor();
        if (!existing || !existing.isConnected) {
          ensureToggle(() => togglePanel());
          return;
        }
        if (anchor && existing.parentElement !== anchor.parentElement) {
          dockBesideAnchor(existing, anchor);
        } else if (anchor) {
          // keep order stable before 构想台
          const label = labelOf(anchor);
          if (label.includes("构想台") && !label.includes("Ryan") && existing.nextSibling !== anchor) {
            anchor.parentElement?.insertBefore(existing, anchor);
          }
        }
      }, 1200);
    }
    console.info("[Ryan Creative Workspace] toolbar toggle docked");
  } catch (err) {
    console.error("[Ryan Creative Workspace] toggle boot failed", err);
  }
}

app.registerExtension({
  name: "Ryan.CreativeWorkspace.Toggle",
  async setup() {
    bootToggle();
  },
  async init() {
    bootToggle();
  },
});

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bootToggle, { once: true });
} else {
  setTimeout(bootToggle, 0);
}
