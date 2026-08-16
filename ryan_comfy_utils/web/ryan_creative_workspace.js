/**
 * Bootstrap only: always show a durable toggle.
 * Heavy panel is lazy-imported so a panel bug cannot hide the entry.
 */
import { app } from "../../../scripts/app.js";

const TOGGLE_ID = "ryan-creative-workspace-toggle";
const STYLE_ID = "ryan-cw-toggle-only-styles";

function ensureToggleStyles() {
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = `
  #${TOGGLE_ID}{
    position: fixed !important;
    top: 52px !important;
    right: 132px !important;
    z-index: 10080 !important;
    height: 32px !important;
    padding: 0 12px !important;
    border-radius: 8px !important;
    border: 1px solid rgba(214,179,106,.45) !important;
    background: linear-gradient(180deg,#3f4f72 0%,#2a3550 100%) !important;
    color: #f3f6ff !important;
    font: 600 12px/32px system-ui,sans-serif !important;
    cursor: pointer !important;
    white-space: nowrap !important;
    box-shadow: 0 8px 22px rgba(0,0,0,.35) !important;
  }
  #${TOGGLE_ID}:hover{ filter: brightness(1.08) !important; }
  @media (max-width: 1200px){
    #${TOGGLE_ID}{ right: 12px !important; top: 52px !important; }
  }
  `;
  document.head.appendChild(style);
}

function placeToggle(btn) {
  ensureToggleStyles();
  // Prefer sitting on the action toolbar row next to TE_MAN, but always keep a
  // body-level fixed fallback so Vue/React redraws cannot erase the only entry.
  const nodes = [...document.querySelectorAll("button, [role='button'], a")];
  const labelOf = (n) =>
    `${n.textContent || ""} ${n.getAttribute?.("aria-label") || ""} ${n.title || ""}`;
  const te = nodes.find(
    (n) => n.id !== TOGGLE_ID && labelOf(n).includes("构想台") && !labelOf(n).includes("Ryan")
  );
  const asset = nodes.find((n) => labelOf(n).includes("资产库"));
  const anchor = te || asset;
  if (anchor?.parentElement) {
    // Clone visual alignment: keep fixed, but match anchor vertical center if possible.
    try {
      const rect = anchor.getBoundingClientRect();
      if (rect.top > 0 && rect.height > 0) {
        btn.style.top = `${Math.max(8, Math.round(rect.top + (rect.height - 32) / 2))}px`;
        const right = Math.max(12, Math.round(window.innerWidth - rect.left + 8));
        btn.style.right = `${right}px`;
      }
    } catch (_err) {
      /* keep CSS defaults */
    }
  }
  if (!btn.isConnected) document.body.appendChild(btn);
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
  placeToggle(btn);
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
    const btn = ensureToggle(() => {
      togglePanel();
    });
    // Keep alive against toolbar redraws / SPA updates.
    if (!globalThis.__ryanCwToggleGuard) {
      globalThis.__ryanCwToggleGuard = setInterval(() => {
        const existing = document.getElementById(TOGGLE_ID);
        if (!existing || !existing.isConnected) {
          ensureToggle(() => togglePanel());
        } else {
          placeToggle(existing);
        }
      }, 1500);
    }
    console.info("[Ryan Creative Workspace] toggle ready", btn?.id);
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
