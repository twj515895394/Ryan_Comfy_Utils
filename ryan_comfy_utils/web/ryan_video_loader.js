import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

function findWidget(node, name) {
  return node.widgets?.find((w) => w.name === name);
}

function addButton(node, label, delta) {
  node.addWidget("button", label, null, () => {
    const indexWidget = findWidget(node, "index");
    if (!indexWidget) return;
    const current = Number(indexWidget.value || 0);
    const next = Math.max(0, current + delta);
    indexWidget.value = next;
    indexWidget.callback?.(next);
    app.graph.setDirtyCanvas(true, true);
  });
}

function addBrowseButton(node) {
  node.addWidget("button", "选择文件夹...", null, async () => {
    try {
      const response = await fetch("/ryan_comfy_utils/select_dir", {
        method: "POST",
      });
      if (response.ok) {
        const data = await response.json();
        if (data.dir) {
          const dirWidget = findWidget(node, "video_dir");
          if (dirWidget) {
            dirWidget.value = data.dir;
            dirWidget.callback?.(data.dir);
            app.graph.setDirtyCanvas(true, true);
          }
        }
      }
    } catch (e) {
      console.error("Failed to select directory:", e);
    }
  });
}

function addRefreshButton(node) {
  node.addWidget("button", "刷新视频信息", null, () => {
    refreshVideoInfo(node);
  });
}

async function refreshVideoInfo(node) {
  const dirWidget = findWidget(node, "video_dir");
  const indexWidget = findWidget(node, "index");
  const recursiveWidget = findWidget(node, "recursive");
  const extWidget = findWidget(node, "extensions");
  const sortWidget = findWidget(node, "sort_mode");

  if (!dirWidget || !indexWidget) return;

  const payload = {
    video_dir: dirWidget.value,
    index: Number(indexWidget.value || 0),
    recursive: recursiveWidget ? !!recursiveWidget.value : false,
    extensions: extWidget ? extWidget.value : "mp4,mov,mkv,webm,avi",
    sort_mode: sortWidget ? sortWidget.value : "filename_asc"
  };

  try {
    const response = await fetch("/ryan_comfy_utils/get_video_info", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    if (response.ok) {
      const data = await response.json();
      if (data.error) {
        console.warn("Get video info error:", data.error);
        if (node.warningEl) {
          node.warningEl.style.display = "flex";
          node.warningText.innerText = `目录中未找到支持的视频文件。`;
        }
        if (node.videoEl) {
          node.videoEl.src = "";
        }
        return;
      }

      // 1. 更新视频预览播放器
      const ext = data.filename.split('.').pop().toLowerCase();
      const unsupportedExts = ['mov', 'mkv', 'avi'];
      
      if (node.warningEl) {
        if (unsupportedExts.includes(ext)) {
          node.warningEl.style.display = "flex";
          node.warningText.innerText = `视频格式为 .${ext}，浏览器无法直接预览播放，但后台节点可以正常读取处理。`;
        } else {
          node.warningEl.style.display = "none";
        }
      }

      const url = api.apiURL(`/ryan_comfy_utils/view_video?path=${encodeURIComponent(data.video_path)}&t=${Date.now()}`);
      if (node.videoEl && node.videoEl.src !== url) {
        node.videoEl.src = url;
        node.videoEl.load();
        node.videoEl.play().catch(e => {
          console.log("Autoplay preview failed:", e);
        });
      }

      // 2. 动态更新参数 Label，显示实际的视频属性（格式形如: 参数名 (当前视频对应属性)）
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

      const idxWidget = findWidget(node, "index");
      if (idxWidget) {
        idxWidget.label = `index (file: ${data.filename})`;
      }
      
      app.graph.setDirtyCanvas(true, true);
    }
  } catch (e) {
    console.error("Error fetching video info:", e);
  }
}

function setupWidgetCallbacks(node) {
  const widgetsToWatch = ["video_dir", "index", "recursive", "extensions", "sort_mode"];
  widgetsToWatch.forEach(name => {
    const w = findWidget(node, name);
    if (w) {
      const orig = w.callback;
      w.callback = function(value) {
        const res = orig ? orig.apply(this, arguments) : value;
        refreshVideoInfo(node);
        return res;
      };
    }
  });
}

app.registerExtension({
  name: "RyanComfyUtils.VideoLoaderNavigation",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "Ryan Batch Video Loader") return;

    const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      originalOnNodeCreated?.apply(this, arguments);

      addBrowseButton(this);
      addButton(this, "Previous Video", -1);
      addButton(this, "Next Video", 1);
      addRefreshButton(this);

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
        refreshVideoInfo(this);
      }, 200);

      // 自动计算并更新节点尺寸，防止视频容器和上面的其他输入框重叠
      this.size = this.computeSize();
    };

    const originalConfigure = nodeType.prototype.configure;
    nodeType.prototype.configure = function () {
      const r = originalConfigure?.apply(this, arguments);
      this.size = this.computeSize();
      refreshVideoInfo(this);
      return r;
    };

    const originalOnExecuted = nodeType.prototype.onExecuted;
    nodeType.prototype.onExecuted = function (message) {
      originalOnExecuted?.apply(this, arguments);
      // 后台执行完毕后也会触发一次信息同步，确保最新状态一致
      refreshVideoInfo(this);
    };
  },
});
