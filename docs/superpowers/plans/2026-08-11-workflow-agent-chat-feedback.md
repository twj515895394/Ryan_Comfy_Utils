# Workflow Agent Chat Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Agent Chat clearly distinguish accepted, running, stopped, and failed requests while clearing submitted input and synchronizing the node status.

**Architecture:** Keep the existing `AgentPanel -> AgentStateStore -> PanelManager -> node_extension` state path. Represent failures as persisted chat records, render an execution overlay inside the message list, and derive node status text from the same state event without changing Pi RPC or HTTP contracts.

**Tech Stack:** Vanilla ES modules, DOM/CSS, existing Python `unittest` suite, Node syntax checks.

---

### Task 1: Make chat request state observable

**Files:**
- Modify: `ryan_comfy_utils/web/workflow_agent/agent_panel.js:128-245`
- Modify: `ryan_comfy_utils/web/workflow_agent/message_list.js:36-96`

- [ ] **Step 1: Preserve the submitted user message and clear only composer state**

  In `send()`, keep the existing user message in `messages`, set `composerDraft: ""` before the request, and on failure do not restore `composerDraft: submittedMessage`.

- [ ] **Step 2: Represent a failed request as a visible message**

  In the `catch` branch, pass a patch to `setError()` containing the messages without the pending assistant record plus a system error record:

  ```js
  {
    role: "system",
    content: "执行失败",
    error: messageText,
    requestId,
    messageId,
  }
  ```

  Keep `status: "error"` and the original user message. The composer remains empty.

- [ ] **Step 3: Make the status label explicit**

  Update `statusLabel()` so `error` and `stopped` take precedence over draft/commit labels:

  ```js
  if (state.status === "error") return "● 执行失败";
  if (state.status === "stopped") return "● 已停止";
  if (state.status === "submitting") return "● 正在连接 Pi…";
  if (state.status === "generating") return "● Pi 正在思考…";
  ```

- [ ] **Step 4: Render pending and error records without losing the error text**

  In `message_list.js`, retain the existing pending placeholder and render `message.error` in a dedicated error element after the message body. Do not remove the user message when the request fails.

- [ ] **Step 5: Run syntax validation**

  Run:

  ```bash
  rtk node --check ryan_comfy_utils/web/workflow_agent/agent_panel.js
  rtk node --check ryan_comfy_utils/web/workflow_agent/message_list.js
  ```

  Expected: both commands exit successfully.

### Task 2: Add an execution overlay to the message area

**Files:**
- Modify: `ryan_comfy_utils/web/workflow_agent/message_list.js:53-76`
- Modify: `ryan_comfy_utils/web/workflow_agent/agent_panel.js:128-143`
- Modify: `ryan_comfy_utils/web/workflow_agent/styles.js:84-142`

- [ ] **Step 1: Add a message-list busy layer**

  Add `this.busyLayer` to `MessageList`, with a spinner, text element, and `aria-live="polite"`. Mount it inside the message list root and expose:

  ```js
  setBusy(busy, status = "generating")
  ```

  Text mapping:

  ```js
  submitting -> "正在连接 Pi…"
  generating -> "Pi 正在思考…"
  ```

- [ ] **Step 2: Drive the overlay from panel state**

  In `AgentPanel.renderState()`, call:

  ```js
  this.messages.setBusy(["submitting", "generating"].includes(state.status), state.status);
  ```

  Keep the composer disabled during these states and leave the stop button available during `generating`.

- [ ] **Step 3: Add visible overlay styles**

  Add styles for `.ryan-message-list__busy`, `.ryan-message-list__busy.is-visible`, and a spinner animation. The overlay must cover only the message list, use a translucent panel background, and have a z-index above message content.

- [ ] **Step 4: Run syntax validation**

  Run:

  ```bash
  rtk node --check ryan_comfy_utils/web/workflow_agent/message_list.js
  rtk node --check ryan_comfy_utils/web/workflow_agent/agent_panel.js
  ```

  Expected: both commands exit successfully.

### Task 3: Synchronize node status text and error styling

**Files:**
- Modify: `ryan_comfy_utils/web/workflow_agent/node_extension.js:245-276`
- Modify: `ryan_comfy_utils/web/workflow_agent/panel_manager.js:60-67`
- Modify: `ryan_comfy_utils/web/workflow_agent/styles.js:1-142`

- [ ] **Step 1: Preserve error state in the existing state event**

  Keep the current `onState -> publishState -> ryan-workflow-agent-state` path and ensure the node receives `status` and `error` fields from the panel state.

- [ ] **Step 2: Prioritize runtime statuses in node drawing**

  Update the node status derivation to use this order:

  ```js
  const status = state.status === "error" ? "Error" :
    state.status === "submitting" ? "Sending…" :
    state.status === "generating" ? "Generating…" :
    state.status === "stopped" ? "Stopped" :
    state.upstreamChanged ? "Upstream changed" :
    revision > 0 ? `Committed v${revision}` :
    state.draft ? "Discussing" : "Not started";
  ```

  Use the existing error color for `error`, accent color for active execution, and warning color for upstream changes.

- [ ] **Step 3: Show a short node error detail without exposing a large payload**

  When `state.status === "error"`, set the node tooltip/title or draw a short error marker from `state.error`, truncated to a safe visual length. Do not log or render full Context contents.

- [ ] **Step 4: Run syntax validation**

  Run:

  ```bash
  rtk node --check ryan_comfy_utils/web/workflow_agent/node_extension.js
  rtk node --check ryan_comfy_utils/web/workflow_agent/panel_manager.js
  ```

  Expected: both commands exit successfully.

### Task 4: Add regression coverage and run the suite

**Files:**
- Modify: `tests/nodes/test_workflow_agent_node.py` only if node output behavior changes; otherwise no new backend test file.
- Test manually: AgentPanel state transitions through existing browser-independent DOM seams are not currently covered by a JS test runner.

- [ ] **Step 1: Confirm backend contracts remain unchanged**

  Run:

  ```bash
  rtk python -m unittest tests.nodes.test_workflow_agent_node tests.workflow_agent.test_context tests.workflow_agent.test_chat_commit tests.workflow_agent.test_routes -v
  ```

  Expected: all tests pass; no Pi or API contract changes are required.

- [ ] **Step 2: Run all changed JavaScript syntax checks**

  Run:

  ```bash
  rtk node --check ryan_comfy_utils/web/workflow_agent/agent_panel.js
  rtk node --check ryan_comfy_utils/web/workflow_agent/message_list.js
  rtk node --check ryan_comfy_utils/web/workflow_agent/node_extension.js
  rtk node --check ryan_comfy_utils/web/workflow_agent/panel_manager.js
  rtk node --check ryan_comfy_utils/web/workflow_agent/styles.js
  ```

  Expected: all commands pass.

- [ ] **Step 3: Manually verify the observable paths**

  In the running ComfyUI UI verify:

  1. Send a message: input clears immediately and a user record remains.
  2. During request: message area shows the overlay and the header/node show `正在连接 Pi…` or `Pi 正在思考…`.
  3. Successful response: pending record becomes the assistant response and overlay disappears.
  4. Failed response: user record remains, red `执行失败` record appears with the error, input stays empty, and node shows `Error`.
  5. Stop: overlay disappears, status shows `已停止`, and the generated draft remains available for Commit.
