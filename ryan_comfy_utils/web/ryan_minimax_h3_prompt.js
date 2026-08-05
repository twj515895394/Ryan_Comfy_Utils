import { app } from "../../../scripts/app.js";

const MAX_IMAGE_SLOTS = 9;
const MAX_VIDEO_SLOTS = 3;
const MAX_AUDIO_SLOTS = 3;

function findWidget(node, name) {
  return node.widgets?.find((w) => w.name === name);
}

function setWidgetVisibility(widget, visible) {
  if (!widget) return;
  if (visible) {
    if (widget.origType !== undefined) {
      widget.type = widget.origType;
    }
  } else {
    if (widget.origType === undefined) {
      widget.origType = widget.type;
    }
    widget.type = "hidden";
  }
}

function applyH3SlotVisibility(node, imgCount, vidCount, audCount) {
  const nImg = Math.max(0, Math.min(MAX_IMAGE_SLOTS, Number(imgCount) || 0));
  const nVid = Math.max(0, Math.min(MAX_VIDEO_SLOTS, Number(vidCount) || 0));
  const nAud = Math.max(0, Math.min(MAX_AUDIO_SLOTS, Number(audCount) || 0));

  // 1. 初始化全部 inputs 备份
  if (!node._all_inputs) {
    node._all_inputs = [...(node.inputs || [])];
  }

  // 2. 断开即将隐藏槽位上的连线
  for (let i = 1; i <= MAX_IMAGE_SLOTS; i++) {
    if (i > nImg) {
      const name = `image_${String(i).padStart(2, "0")}`;
      const inp = node._all_inputs.find((item) => item.name === name);
      if (inp) {
        const curIdx = node.inputs?.indexOf(inp);
        if (curIdx !== undefined && curIdx !== -1 && node.inputs[curIdx].link !== null) {
          node.disconnectInput(curIdx);
        }
      }
    }
  }
  for (let i = 1; i <= MAX_VIDEO_SLOTS; i++) {
    if (i > nVid) {
      const name = `video_${String(i).padStart(2, "0")}`;
      const inp = node._all_inputs.find((item) => item.name === name);
      if (inp) {
        const curIdx = node.inputs?.indexOf(inp);
        if (curIdx !== undefined && curIdx !== -1 && node.inputs[curIdx].link !== null) {
          node.disconnectInput(curIdx);
        }
      }
    }
  }
  for (let i = 1; i <= MAX_AUDIO_SLOTS; i++) {
    if (i > nAud) {
      const name = `audio_${String(i).padStart(2, "0")}`;
      const inp = node._all_inputs.find((item) => item.name === name);
      if (inp) {
        const curIdx = node.inputs?.indexOf(inp);
        if (curIdx !== undefined && curIdx !== -1 && node.inputs[curIdx].link !== null) {
          node.disconnectInput(curIdx);
        }
      }
    }
  }

  // 3. 过滤构建新的 inputs 数组
  const newInputs = [];
  for (const input of node._all_inputs) {
    const imgMatch = input.name.match(/^image_(\d+)$/);
    const vidMatch = input.name.match(/^video_(\d+)$/);
    const audMatch = input.name.match(/^audio_(\d+)$/);

    if (imgMatch) {
      const idx = parseInt(imgMatch[1], 10);
      if (idx <= nImg) newInputs.push(input);
    } else if (vidMatch) {
      const idx = parseInt(vidMatch[1], 10);
      if (idx <= nVid) newInputs.push(input);
    } else if (audMatch) {
      const idx = parseInt(audMatch[1], 10);
      if (idx <= nAud) newInputs.push(input);
    } else {
      newInputs.push(input);
    }
  }

  node.inputs = newInputs;

  // 同步 Widget 值
  const imgW = findWidget(node, "image_slot_count");
  if (imgW) imgW.value = nImg;
  const vidW = findWidget(node, "video_slot_count");
  if (vidW) vidW.value = nVid;
  const audW = findWidget(node, "audio_slot_count");
  if (audW) audW.value = nAud;

  node.setSize?.(node.computeSize?.());
  app.graph?.setDirtyCanvas(true, true);
}

function applyModeUI(node) {
  const modeWidget = findWidget(node, "generation_mode");
  if (!modeWidget) return;

  const mode = modeWidget.value || "纯文生";

  const imgCountWidget = findWidget(node, "image_slot_count");
  const vidCountWidget = findWidget(node, "video_slot_count");
  const audCountWidget = findWidget(node, "audio_slot_count");

  const videoStartWidget = findWidget(node, "video_start_frame");
  const videoCountWidget = findWidget(node, "video_frame_count");
  const updateBtn = node.widgets?.find((w) => w.name === "Update" || w.label === "Update");

  switch (mode) {
    case "纯文生":
    default:
      setWidgetVisibility(imgCountWidget, false);
      setWidgetVisibility(vidCountWidget, false);
      setWidgetVisibility(audCountWidget, false);
      setWidgetVisibility(videoStartWidget, false);
      setWidgetVisibility(videoCountWidget, false);
      setWidgetVisibility(updateBtn, false);
      applyH3SlotVisibility(node, 0, 0, 0);
      break;

    case "普通图生":
      setWidgetVisibility(imgCountWidget, true);
      setWidgetVisibility(vidCountWidget, false);
      setWidgetVisibility(audCountWidget, false);
      setWidgetVisibility(videoStartWidget, false);
      setWidgetVisibility(videoCountWidget, false);
      setWidgetVisibility(updateBtn, true);
      applyH3SlotVisibility(node, imgCountWidget?.value || 2, 0, 0);
      break;

    case "首尾帧":
      setWidgetVisibility(imgCountWidget, true);
      setWidgetVisibility(vidCountWidget, false);
      setWidgetVisibility(audCountWidget, false);
      setWidgetVisibility(videoStartWidget, false);
      setWidgetVisibility(videoCountWidget, false);
      setWidgetVisibility(updateBtn, true);
      if (imgCountWidget) imgCountWidget.value = 2; // 锁定 2 帧
      applyH3SlotVisibility(node, 2, 0, 0);
      break;

    case "全能参考":
      setWidgetVisibility(imgCountWidget, true);
      setWidgetVisibility(vidCountWidget, true);
      setWidgetVisibility(audCountWidget, true);
      setWidgetVisibility(videoStartWidget, true);
      setWidgetVisibility(videoCountWidget, true);
      setWidgetVisibility(updateBtn, true);
      applyH3SlotVisibility(
        node,
        imgCountWidget?.value || 2,
        vidCountWidget?.value || 1,
        audCountWidget?.value || 1
      );
      break;

    case "视频编辑":
      setWidgetVisibility(imgCountWidget, true);
      setWidgetVisibility(vidCountWidget, true);
      setWidgetVisibility(audCountWidget, false);
      setWidgetVisibility(videoStartWidget, true);
      setWidgetVisibility(videoCountWidget, true);
      setWidgetVisibility(updateBtn, true);
      applyH3SlotVisibility(
        node,
        imgCountWidget?.value || 2,
        vidCountWidget?.value || 1,
        0
      );
      break;
  }
}

function setupH3UI(node) {
  if (!node._all_inputs) {
    node._all_inputs = [...(node.inputs || [])];
  }

  // 避免重复添加 Update 按钮
  let updateBtn = node.widgets?.find((w) => w.name === "Update" || w.label === "Update");
  if (!updateBtn) {
    node.addWidget("button", "Update", null, () => {
      const imgCount = findWidget(node, "image_slot_count")?.value || 2;
      const vidCount = findWidget(node, "video_slot_count")?.value || 0;
      const audCount = findWidget(node, "audio_slot_count")?.value || 0;
      applyH3SlotVisibility(node, imgCount, vidCount, audCount);
    });
  }

  applyModeUI(node);
}

app.registerExtension({
  name: "RyanComfyUtils.MiniMaxH3PromptModeUI",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "Ryan ACP MiniMax H3 Video Prompt Agent") return;

    const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      originalOnNodeCreated?.apply(this, arguments);

      const modeWidget = findWidget(this, "generation_mode");
      if (modeWidget) {
        const origCallback = modeWidget.callback;
        modeWidget.callback = (val) => {
          origCallback?.(val);
          applyModeUI(this);
        };
      }

      setupH3UI(this);
    };

    const originalConfigure = nodeType.prototype.configure;
    nodeType.prototype.configure = function (info) {
      if (this._all_inputs) {
        this.inputs = [...this._all_inputs];
      }

      const r = originalConfigure?.apply(this, arguments);

      if (this.inputs && this._all_inputs) {
        for (const input of this.inputs) {
          const backupInput = this._all_inputs.find((inp) => inp.name === input.name);
          if (backupInput) {
            backupInput.link = input.link;
          }
        }
      }

      if (!this._all_inputs) {
        this._all_inputs = [...(this.inputs || [])];
      }

      setupH3UI(this);
      return r;
    };
  },
});
