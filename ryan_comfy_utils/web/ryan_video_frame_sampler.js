import { app } from "../../../scripts/app.js";

const SAMPLER_MAPPINGS = {
  "head_tail": "首尾与均匀采样",
  "uniform": "完全均匀采样",
  "interval": "固定间隔采样",
  "custom_indexes": "自定义帧索引",
  "scene_first_frame": "分镜首帧采样",
  "preview_only": "仅预览不保存",
  "save_to_output": "保存至 output 目录"
};

function findWidget(node, name) {
  return node.widgets?.find((w) => w.name === name);
}

function toggleWidget(node, name, show, defaultType) {
  const w = node.widgets?.find((w) => w.name === name);
  if (!w) return;
  if (show) {
    if (w.type === "hidden") {
      w.type = w.origType || defaultType;
      delete w.origType;
    }
  } else {
    if (w.type !== "hidden") {
      w.origType = w.type;
      w.type = "hidden";
    }
  }
}

function updateWidgetsVisibility(node) {
  const sampleModeWidget = findWidget(node, "sample_mode");
  if (!sampleModeWidget) return;

  const isSceneMode = sampleModeWidget.value === "分镜首帧采样";

  toggleWidget(node, "video_path", isSceneMode, "text");
  toggleWidget(node, "select_video_file_btn", isSceneMode, "button");
  toggleWidget(node, "scene_detector", isSceneMode, "combo");
  toggleWidget(node, "scene_threshold", isSceneMode, "number");
  toggleWidget(node, "scene_min_len", isSceneMode, "number");
  toggleWidget(node, "scene_merge_min", isSceneMode, "number");

  toggleWidget(node, "frame_count", !isSceneMode, "number");
  toggleWidget(node, "frame_interval", !isSceneMode, "number");
  toggleWidget(node, "custom_indexes", !isSceneMode, "text");

  node.setSize?.(node.computeSize?.());
  if (node.graph) {
    node.graph.setDirtyCanvas(true, true);
  }
}

function setupVideoFrameSamplerUI(node) {
  // Add picker button if it doesn't exist
  let pickerBtn = node.widgets?.find((w) => w.name === "select_video_file_btn");
  if (!pickerBtn) {
    pickerBtn = node.addWidget("button", "选择视频文件...", null, async () => {
      try {
        const response = await fetch("/ryan_comfy_utils/select_video_file", {
          method: "POST",
        });
        if (response.ok) {
          const data = await response.json();
          if (data.path) {
            const pathWidget = findWidget(node, "video_path");
            if (pathWidget) {
              pathWidget.value = data.path;
              pathWidget.callback?.(data.path);
              app.graph.setDirtyCanvas(true, true);
            }
          }
        }
      } catch (e) {
        console.error("Failed to select video file:", e);
      }
    });
    pickerBtn.name = "select_video_file_btn";
  }

  const sampleModeWidget = findWidget(node, "sample_mode");
  if (sampleModeWidget) {
    const originalCallback = sampleModeWidget.callback;
    sampleModeWidget.callback = function (value) {
      const r = originalCallback?.apply(this, arguments);
      updateWidgetsVisibility(node);
      return r;
    };
  }

  updateWidgetsVisibility(node);
}

app.registerExtension({
  name: "RyanComfyUtils.VideoFrameSampler",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "Ryan Video Frame Sampler") return;

    const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const r = originalOnNodeCreated?.apply(this, arguments);
      setupVideoFrameSamplerUI(this);
      return r;
    };

    const originalConfigure = nodeType.prototype.configure;
    nodeType.prototype.configure = function (info) {
      if (info?.widgets_values) {
        info.widgets_values = info.widgets_values.map(val => {
          if (typeof val === "string" && SAMPLER_MAPPINGS[val]) {
            return SAMPLER_MAPPINGS[val];
          }
          return val;
        });
      }
      const r = originalConfigure?.apply(this, arguments);
      updateWidgetsVisibility(this);
      return r;
    };
  },
});
