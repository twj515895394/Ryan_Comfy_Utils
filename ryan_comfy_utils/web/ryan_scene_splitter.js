import { app } from "../../../scripts/app.js";

function findWidget(node, name) {
  return node.widgets?.find((w) => w.name === name);
}

function addVideoFilePickerButton(node) {
  node.addWidget("button", "选择视频文件...", null, async () => {
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
}

function resetVideoInfoLabels(node) {
  const forceRateWidget = findWidget(node, "force_rate");
  if (forceRateWidget) forceRateWidget.label = "force_rate";
  const customWidthWidget = findWidget(node, "custom_width");
  if (customWidthWidget) customWidthWidget.label = "custom_width";
  const customHeightWidget = findWidget(node, "custom_height");
  if (customHeightWidget) customHeightWidget.label = "custom_height";
  const frameLoadCapWidget = findWidget(node, "frame_load_cap");
  if (frameLoadCapWidget) frameLoadCapWidget.label = "frame_load_cap";
}

async function updateVideoInfoLabels(node, path) {
  if (!path) return;
  try {
    const response = await fetch("/ryan_comfy_utils/get_single_video_info", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ video_path: path }),
    });
    if (response.ok) {
      const data = await response.json();
      
      const forceRateWidget = findWidget(node, "force_rate");
      if (forceRateWidget) {
        forceRateWidget.label = `force_rate (fps: ${data.fps ? data.fps.toFixed(1) : 'unknown'})`;
      }
      
      const customWidthWidget = findWidget(node, "custom_width");
      if (customWidthWidget) {
        customWidthWidget.label = `custom_width (orig: ${data.width || 'unknown'})`;
      }
      
      const customHeightWidget = findWidget(node, "custom_height");
      if (customHeightWidget) {
        customHeightWidget.label = `custom_height (orig: ${data.height || 'unknown'})`;
      }
      
      const frameLoadCapWidget = findWidget(node, "frame_load_cap");
      if (frameLoadCapWidget) {
        frameLoadCapWidget.label = `frame_load_cap (total: ${data.total_frames || 'unknown'})`;
      }
      
      app.graph.setDirtyCanvas(true, true);
    }
  } catch (e) {
    console.error("Error fetching single video info:", e);
  }
}

function sanitizeWidgetValues(node) {
  if (!node.widgets) return;
  node.widgets.forEach(w => {
    if (w.name === "custom_width" || w.name === "custom_height" || w.name === "frame_load_cap" || w.name === "skip_first_frames" || w.name === "select_every_nth") {
      const val = Number(w.value);
      if (isNaN(val) || w.value === undefined || w.value === null) {
        w.value = w.options?.default ?? 0;
      } else {
        w.value = val;
      }
    }
    if (w.name === "force_rate" || w.name === "threshold" || w.name === "min_scene_len" || w.name === "merge_min_duration") {
      const val = Number(w.value);
      if (isNaN(val) || w.value === undefined || w.value === null) {
        w.value = w.options?.default ?? 0.0;
      } else {
        w.value = val;
      }
    }
  });
}

function refreshVideoPreview(node) {
  const pathWidget = findWidget(node, "video_path");
  if (!pathWidget || !node.videoEl) return;
  const path = pathWidget.value;
  if (!path) {
    node.videoEl.src = "";
    if (node.warningEl) node.warningEl.style.display = "none";
    resetVideoInfoLabels(node);
    return;
  }

  const ext = path.split('.').pop().toLowerCase();
  const unsupportedExts = ['mov', 'mkv', 'avi'];
  
  if (node.warningEl) {
    if (unsupportedExts.includes(ext)) {
      node.warningEl.style.display = "flex";
      node.warningText.innerText = `视频格式为 .${ext}，浏览器无法直接预览播放，但后台节点可以正常读取处理。`;
    } else {
      node.warningEl.style.display = "none";
    }
  }

  const url = `/ryan_comfy_utils/view_video?path=${encodeURIComponent(path)}&t=${Date.now()}`;
  if (node.videoEl.src !== url) {
    node.videoEl.src = url;
    node.videoEl.load();
    node.videoEl.play().catch(e => {
      console.log("Autoplay preview failed:", e);
    });
  }

  updateVideoInfoLabels(node, path);
}

function setupWidgetCallbacks(node) {
  const w = findWidget(node, "video_path");
  if (w) {
    const orig = w.callback;
    w.callback = function(value) {
      const res = orig ? orig.apply(this, arguments) : value;
      refreshVideoPreview(node);
      return res;
    };
  }
}

app.registerExtension({
  name: "Ryan.SceneSplitter",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "Ryan Video Scene Splitter") return;

    const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      originalOnNodeCreated?.apply(this, arguments);

      addVideoFilePickerButton(this);

      // 创建容器 DOM 元素
      const container = document.createElement("div");
      container.style.width = "100%";
      container.style.height = "180px";
      container.style.position = "relative";
      container.style.backgroundColor = "#000";

      // 创建预览视频播放器 DOM 元素
      const videoEl = document.createElement("video");
      videoEl.controls = true;
      videoEl.autoplay = true;
      videoEl.loop = true;
      videoEl.muted = true;
      videoEl.style.width = "100%";
      videoEl.style.height = "100%";
      videoEl.style.objectFit = "contain";

      // 创建格式不支持或播放失败提示层
      const warningEl = document.createElement("div");
      warningEl.style.position = "absolute";
      warningEl.style.top = "0";
      warningEl.style.left = "0";
      warningEl.style.width = "100%";
      warningEl.style.height = "100%";
      warningEl.style.display = "none";
      warningEl.style.flexDirection = "column";
      warningEl.style.alignItems = "center";
      warningEl.style.justifyContent = "center";
      warningEl.style.backgroundColor = "rgba(0, 0, 0, 0.85)";
      warningEl.style.color = "#ccc";
      warningEl.style.fontSize = "12px";
      warningEl.style.padding = "10px";
      warningEl.style.textAlign = "center";
      warningEl.style.pointerEvents = "none";

      const warningText = document.createElement("span");
      warningText.innerText = "此视频格式（如 .mov / .mkv / .avi）浏览器无法直接预览，但后台节点可以正常读取处理。";
      warningEl.appendChild(warningText);

      container.appendChild(videoEl);
      container.appendChild(warningEl);

      videoEl.onerror = () => {
        if (videoEl.src) {
          warningEl.style.display = "flex";
          warningText.innerText = "视频播放失败。浏览器可能不支持此编码/格式（如 H.265/HEVC、.mov、.mkv 等），但后台节点仍能正常读取处理。";
        }
      };

      // 用 addDOMWidget 渲染到节点底部
      const videoWidget = this.addDOMWidget("video_preview", "video", container, {
        serialize: false,
        getValue() {
          return videoEl.src;
        },
        setValue(v) {
          videoEl.src = v;
        }
      });

      videoWidget.computeSize = function (width) {
        return [width || 350, 180];
      };

      this.videoEl = videoEl;
      this.warningEl = warningEl;
      this.warningText = warningText;
      this.videoWidget = videoWidget;

      // 绑定参数变化回调
      setupWidgetCallbacks(this);

      // 延时初次获取属性
      setTimeout(() => {
        refreshVideoPreview(this);
      }, 200);

      // 自动计算并更新节点尺寸
      sanitizeWidgetValues(this);
      this.size = this.computeSize();
    };

    const originalConfigure = nodeType.prototype.configure;
    nodeType.prototype.configure = function (info) {
      if (info && info.widgets_values) {
        // Old nodes have fewer widgets than new nodes
        // (the old widgets array had 10 items, the new one has 16 items)
        if (info.widgets_values.length < 14) {
          const oldValues = info.widgets_values;
          const newValues = [];
          
          // 1. Copy the first 8 original widgets
          for (let i = 0; i < Math.min(8, oldValues.length); i++) {
            newValues.push(oldValues[i]);
          }
          // 2. Insert defaults for the 6 new parameters
          newValues.push(0.0); // force_rate
          newValues.push(0);   // custom_width
          newValues.push(0);   // custom_height
          newValues.push(0);   // frame_load_cap
          newValues.push(0);   // skip_first_frames
          newValues.push(1);   // select_every_nth
          
          // 3. Add button value (index 14)
          newValues.push(null);
          
          // 4. Add video_preview value (index 15)
          if (oldValues.length > 9) {
            newValues.push(oldValues[9]);
          } else if (oldValues.length > 8) {
            newValues.push(oldValues[8]);
          } else {
            newValues.push(null);
          }
          
          info.widgets_values = newValues;
        }
      }
      const r = originalConfigure?.apply(this, arguments);
      sanitizeWidgetValues(this);
      this.size = this.computeSize();
      refreshVideoPreview(this);
      return r;
    };
  },
});
