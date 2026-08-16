export const WORKFLOW_AGENT_CSS = `
.ryan-agent-dock {
  --ryan-panel-width: 480px;
  --ryan-bg-panel: var(--comfy-menu-bg, #17191e);
  --ryan-bg-elevated: var(--comfy-input-bg, #20242b);
  --ryan-bg-input: #121419;
  --ryan-border: color-mix(in srgb, var(--fg-color, #e9edf2) 12%, transparent);
  --ryan-border-strong: color-mix(in srgb, var(--fg-color, #e9edf2) 24%, transparent);
  --ryan-text-primary: var(--fg-color, #f2f4f7);
  --ryan-text-secondary: color-mix(in srgb, var(--fg-color, #f2f4f7) 64%, transparent);
  --ryan-accent: #8d9cff;
  --ryan-accent-strong: #b9c0ff;
  --ryan-success: #78d6a0;
  --ryan-warning: #e8b86a;
  --ryan-error: #ef8a8a;
  position: fixed;
  z-index: 10010;
  top: 0;
  right: 0;
  bottom: 0;
  width: var(--ryan-panel-width);
  min-width: 380px;
  max-width: 55vw;
  box-sizing: border-box;
  color: var(--ryan-text-primary);
  font: 13px/1.5 Inter, ui-sans-serif, system-ui, -apple-system, sans-serif;
  pointer-events: none;
}
.ryan-agent-dock.is-open { pointer-events: none; }
.ryan-agent-panel {
  position: absolute;
  inset: 12px 12px 12px 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  pointer-events: auto;
  background: color-mix(in srgb, var(--ryan-bg-panel) 96%, #08090c);
  border: 1px solid var(--ryan-border-strong);
  border-radius: 16px;
  box-shadow: -16px 0 48px rgba(0, 0, 0, .32), 0 12px 34px rgba(0, 0, 0, .22);
  backdrop-filter: blur(16px);
}
.ryan-agent-dock__resize {
  position: absolute;
  z-index: 2;
  top: 24px;
  bottom: 24px;
  left: -4px;
  width: 9px;
  cursor: ew-resize;
  pointer-events: auto;
}
.ryan-agent-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 20px 16px;
  border-bottom: 1px solid var(--ryan-border);
  background: linear-gradient(180deg, rgba(255,255,255,.035), transparent);
}
.ryan-agent-header__name { margin: 0; font-size: 17px; line-height: 1.2; letter-spacing: -.01em; }
.ryan-agent-header__skill { margin: 5px 0 7px; color: var(--ryan-text-secondary); font: 11px/1.2 ui-monospace, SFMono-Regular, monospace; }
.ryan-agent-header__status { color: var(--ryan-accent-strong); font-size: 11px; }
.ryan-panel-close { border: 0; background: transparent; color: var(--ryan-text-secondary); font-size: 24px; line-height: 1; cursor: pointer; padding: 0 2px; }
.ryan-panel-close:hover { color: var(--ryan-text-primary); }
.ryan-context-inspector { border-bottom: 1px solid var(--ryan-border); }
.ryan-context-bar { width: 100%; padding: 11px 20px; border: 0; color: var(--ryan-text-secondary); background: transparent; text-align: left; cursor: pointer; font-size: 11px; }
.ryan-context-bar:hover { color: var(--ryan-text-primary); background: rgba(255,255,255,.025); }
.ryan-context-details { max-height: 280px; overflow: auto; padding: 0 14px 12px; }
.ryan-context-entry { margin: 6px 0; overflow: hidden; border: 1px solid var(--ryan-border); border-radius: 9px; background: rgba(255,255,255,.025); }
.ryan-context-entry__summary { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; padding: 9px 11px; cursor: pointer; list-style: none; }
.ryan-context-entry__summary::-webkit-details-marker { display: none; }
.ryan-context-entry__agent { font-size: 12px; }
.ryan-context-entry__meta, .ryan-context-entry__source { color: var(--ryan-text-secondary); font-size: 10px; }
.ryan-context-entry__body { padding: 0 11px 11px; }
.ryan-context-entry__summary-text { margin: 4px 0 8px; color: var(--ryan-text-secondary); }
.ryan-context-entry__source, .ryan-context-entry__assets { margin: 6px 0 0; }
.ryan-context-entry__content { max-height: 160px; overflow: auto; margin: 10px 0 0; padding: 9px; white-space: pre-wrap; border-radius: 6px; background: var(--ryan-bg-input); color: var(--ryan-text-secondary); font: 11px/1.5 ui-monospace, monospace; }
.ryan-context-empty { margin: 3px 6px; color: var(--ryan-text-secondary); }
.ryan-context-assets { padding: 8px 4px 0; }
.ryan-context-assets__title { margin: 0 0 7px; font-size: 11px; }
.ryan-asset-chip { display: inline-flex; margin: 0 5px 5px 0; padding: 4px 7px; border: 1px solid var(--ryan-border); border-radius: 8px; color: var(--ryan-text-secondary); font-size: 10px; }
.ryan-context-artifacts { margin-top: 11px; padding-top: 9px; border-top: 1px solid var(--ryan-border); }
.ryan-context-artifacts__title { margin: 0 0 7px; font-size: 11px; }
.ryan-artifact-copy { display: block; width: 100%; margin: 4px 0; padding: 6px 8px; overflow: hidden; border: 1px solid var(--ryan-border); border-radius: 7px; color: var(--ryan-text-secondary); background: rgba(255,255,255,.025); cursor: pointer; text-align: left; text-overflow: ellipsis; white-space: nowrap; font: inherit; font-size: 10px; }
.ryan-artifact-copy:hover { border-color: var(--ryan-accent); color: var(--ryan-text-primary); background: rgba(255,255,255,.05); }
.ryan-artifact-selector__advanced { margin-top: 6px; }
.ryan-artifact-selector__empty { color: var(--ryan-text-secondary); font-size: 10px; }
.ryan-artifact-selector__error { color: var(--ryan-error); font-size: 10px; }
.ryan-message-list { position: relative; flex: 1 1 auto; min-height: 120px; overflow: auto; padding: 20px; scroll-behavior: smooth; }
.ryan-message-list__busy { position: absolute; inset: 0; z-index: 2; display: grid; place-content: center; justify-items: center; gap: 10px; padding: 20px; color: var(--ryan-text-primary); background: rgba(8, 9, 12, .72); opacity: 0; visibility: hidden; pointer-events: none; transition: opacity .16s ease, visibility .16s ease; }
.ryan-message-list__busy.is-visible { opacity: 1; visibility: visible; pointer-events: auto; }
.ryan-message-list__busy-spinner { width: 28px; height: 28px; box-sizing: border-box; border: 3px solid color-mix(in srgb, var(--ryan-text-primary) 22%, transparent); border-top-color: var(--ryan-accent-strong); border-radius: 50%; animation: ryan-message-list-spin .8s linear infinite; }
.ryan-message-list__busy-text { font-size: 12px; }
.ryan-message { max-width: 94%; margin: 0 0 18px; }
.ryan-message--user { margin-left: auto; max-width: 86%; }
.ryan-message__header { margin-bottom: 5px; color: var(--ryan-text-secondary); font-size: 10px; letter-spacing: .04em; text-transform: uppercase; }
.ryan-message--user .ryan-message__header { text-align: right; }
.ryan-message__body { color: var(--ryan-text-primary); }
.ryan-message--user .ryan-message__body { padding: 10px 12px; border: 1px solid color-mix(in srgb, var(--ryan-accent) 30%, transparent); border-radius: 12px 4px 12px 12px; background: color-mix(in srgb, var(--ryan-accent) 11%, transparent); }
.ryan-message--system .ryan-message__body { padding: 9px 11px; border-left: 2px solid var(--ryan-accent); color: var(--ryan-text-secondary); background: rgba(255,255,255,.025); }
.ryan-message__error { margin-top: 7px; color: var(--ryan-error); font-size: 11px; }
.ryan-markdown-paragraph { margin: 0 0 10px; white-space: pre-wrap; overflow-wrap: anywhere; }
.ryan-markdown-heading { margin: 18px 0 8px; font-size: 15px; line-height: 1.3; }
.ryan-markdown-list { margin: 0 0 10px; padding-left: 20px; }
.ryan-markdown-list li { margin: 4px 0; }
.ryan-markdown-code { overflow: auto; margin: 10px 0; padding: 12px; border: 1px solid var(--ryan-border); border-radius: 8px; background: var(--ryan-bg-input); color: #c9d0e1; font: 11px/1.6 ui-monospace, monospace; white-space: pre; }
.ryan-markdown-spacer { height: 4px; }
.ryan-message-empty { display: grid; place-items: center; min-height: 180px; padding: 30px; color: var(--ryan-text-secondary); text-align: center; }
.ryan-message-empty h3 { margin: 10px 0 4px; color: var(--ryan-text-primary); font-size: 15px; }
.ryan-message-empty p { max-width: 260px; margin: 0; font-size: 12px; }
.ryan-message-empty__icon { display: grid; place-items: center; width: 34px; height: 34px; border: 1px solid color-mix(in srgb, var(--ryan-accent) 42%, transparent); border-radius: 50%; color: var(--ryan-accent-strong); }
.ryan-commit-bar { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 12px 16px; border-top: 1px solid var(--ryan-border); border-bottom: 1px solid var(--ryan-border); background: rgba(255,255,255,.025); }
.ryan-commit-bar.is-dirty { border-left: 3px solid var(--ryan-warning); }
.ryan-commit-bar__copy { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.ryan-commit-bar__title { font-size: 11px; }
.ryan-commit-bar__detail { color: var(--ryan-text-secondary); font-size: 10px; }
.ryan-commit-bar__actions { display: flex; flex-shrink: 0; gap: 6px; }
.ryan-button { padding: 7px 9px; border: 1px solid var(--ryan-border-strong); border-radius: 8px; cursor: pointer; font: inherit; font-size: 11px; transition: transform .16s ease, opacity .16s ease, background .16s ease; }
.ryan-button:disabled { cursor: not-allowed; opacity: .56; }
.ryan-button--quiet { color: var(--ryan-text-secondary); background: transparent; }
.ryan-button--accent { border-color: transparent; color: #151721; background: var(--ryan-accent-strong); font-weight: 600; }
.ryan-button--accent.is-loading { color: var(--ryan-text-primary); background: var(--ryan-border-strong); animation: ryan-commit-pulse 1.1s ease-in-out infinite; }
.ryan-commit-bar.is-committing { border-left: 3px solid var(--ryan-accent-strong); }
.ryan-commit-preview { position: absolute; right: 18px; bottom: 184px; z-index: 3; width: min(300px, calc(100% - 36px)); padding: 13px; border: 1px solid var(--ryan-border-strong); border-radius: 10px; background: var(--ryan-bg-elevated); box-shadow: 0 10px 30px rgba(0,0,0,.3); }
.ryan-commit-preview p { margin: 5px 0 0; color: var(--ryan-text-secondary); font-size: 11px; }
.ryan-attachment-tray { padding: 10px 16px 0; }
.ryan-attachment-controls { display: flex; gap: 6px; }
.ryan-attachment-button { padding: 5px 7px; border: 1px solid var(--ryan-border); border-radius: 7px; color: var(--ryan-text-secondary); background: transparent; cursor: pointer; font: inherit; font-size: 10px; }
.ryan-attachment-button:hover:not(:disabled) { border-color: var(--ryan-accent); color: var(--ryan-text-primary); }
.ryan-attachment-button:disabled { cursor: not-allowed; opacity: .35; }
.ryan-attachment-cards { display: flex; flex-wrap: wrap; gap: 5px; padding-top: 7px; }
.ryan-attachment-card { display: inline-flex; align-items: center; max-width: 100%; gap: 5px; padding: 4px 6px; border: 1px solid var(--ryan-border); border-radius: 8px; background: rgba(255,255,255,.03); font-size: 10px; }
.ryan-attachment-card__name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ryan-attachment-card__remove { border: 0; color: var(--ryan-text-secondary); background: transparent; cursor: pointer; font-size: 14px; line-height: 1; }
.ryan-composer { position: relative; margin: 10px 16px 16px; padding: 10px 10px 8px; border: 1px solid var(--ryan-border-strong); border-radius: 14px; background: var(--ryan-bg-input); }
.ryan-composer__tools { min-height: 4px; }
.ryan-composer__input { display: block; width: calc(100% - 38px); max-height: 180px; min-height: 42px; resize: none; overflow: auto; border: 0; outline: 0; color: var(--ryan-text-primary); background: transparent; font: inherit; line-height: 1.5; }
.ryan-composer__input::placeholder { color: color-mix(in srgb, var(--ryan-text-secondary) 76%, transparent); }
.ryan-composer__hint { display: block; margin-top: 6px; color: var(--ryan-text-secondary); font-size: 10px; }
.ryan-send-button { position: absolute; right: 10px; bottom: 10px; width: 28px; height: 28px; border: 0; border-radius: 9px; color: #151721; background: var(--ryan-accent-strong); cursor: pointer; font-size: 17px; line-height: 1; transition: transform .16s ease, background .16s ease, opacity .16s ease; }
.ryan-send-button.is-stop { color: #fff; background: var(--ryan-error); font-size: 11px; }
.ryan-send-button.is-busy:not(.is-stop) { color: var(--ryan-text-primary); background: var(--ryan-border-strong); animation: ryan-send-pulse 1.1s ease-in-out infinite; }
.ryan-send-button.is-stop { animation: ryan-stop-pulse 1.1s ease-in-out infinite; }
.ryan-send-button:disabled { cursor: not-allowed; opacity: .72; }
@keyframes ryan-commit-pulse { 50% { transform: translateY(-1px); opacity: .72; } }
@keyframes ryan-send-pulse { 50% { transform: scale(.92); opacity: .72; } }
@keyframes ryan-stop-pulse { 50% { box-shadow: 0 0 0 4px color-mix(in srgb, var(--ryan-error) 18%, transparent); } }
@keyframes ryan-pending-dots { from { width: 0; } to { width: 1.2em; } }
@keyframes ryan-message-list-spin { to { transform: rotate(360deg); } }
.ryan-toast { position: absolute; z-index: 4; right: 16px; bottom: 12px; max-width: calc(100% - 32px); padding: 9px 12px; border: 1px solid var(--ryan-border-strong); border-radius: 9px; background: var(--ryan-bg-elevated); box-shadow: 0 8px 22px rgba(0,0,0,.3); font-size: 11px; }
.ryan-toast--error { border-color: color-mix(in srgb, var(--ryan-error) 55%, transparent); color: var(--ryan-error); }
@media (max-width: 900px) {
  .ryan-agent-dock { min-width: min(380px, 100vw); max-width: 100vw; }
  .ryan-agent-panel { inset: 0; border-radius: 0; }
}
`;

export function installStyles() {
  if (document.getElementById("ryan-workflow-agent-styles")) return;
  const style = document.createElement("style");
  style.id = "ryan-workflow-agent-styles";
  style.textContent = WORKFLOW_AGENT_CSS;
  document.head.append(style);
}
