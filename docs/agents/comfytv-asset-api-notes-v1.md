# ComfyTV Asset API 速查（构想台 Bridge 用）

> 供 `Ryan Creative Workspace` / `ComfyTVAssetBridge` 开发快速定位。  
> 主工程仍是 Ryan；ComfyTV 为可选 Asset Provider。  
> 源码根：`X:/ComfyUI-aki-v2/ComfyUI/custom_nodes/ComfyTV`

## 结论

- V1 **优先调用现有 HTTP API**，不必为“列举/引用素材”先改 ComfyTV。
- 资产在 ComfyTV **SQLite DB** 中；Ryan 项目内只存 **AssetRef**，不复制 DB 行、不默认复制大文件。
- 回写资产库（生成图入库）为后续；可复用 `POST /comfytv/assets`。

## 关键路径

| 用途 | 路径 |
|---|---|
| HTTP 路由 | `ComfyTV/api/assets.py` |
| 存储/CRUD | `ComfyTV/storage/assets.py` |
| 前端 hydrate | `ComfyTV/src/stores/assetStore.ts`（`GET /comfytv/assets?category=all`） |
| DB 文件（运行时） | `ComfyUI/user/comfytv/data.db`（表名含 `comfytv_assets`） |
| 媒体 adopt 目录 | `POST /comfytv/assets/adopt` → 扫描 ComfyTV media 目录 |

## HTTP API

前缀均在 ComfyUI 同源下（与前端 `apiFetch` 一致）。

### 读

```http
GET /comfytv/assets?category=all|none|<category_id>&limit=1..500&offset=0
→ { "assets": [ Asset, ... ] }

GET /comfytv/asset_categories
→ { "categories": [ ... ] }
```

### 写（后续回写可用）

```http
POST /comfytv/assets
Body JSON:
  payload_url: string   # required，常为 /view?filename=...&type=output
  media_type: image|video|audio|model  # default image
  name?: string
  category_ids?: number[]
  mime_type?, width?, height?, size_bytes?, source?, metadata?: object
→ { "ok": true, "asset": Asset }

PATCH /comfytv/assets/{id}
DELETE /comfytv/assets/{id}

POST /comfytv/asset_categories   { "name": "..." }
PATCH /comfytv/asset_categories/{id}
DELETE /comfytv/asset_categories/{id}

POST /comfytv/assets/{id}/categories/{cid}
DELETE /comfytv/assets/{id}/categories/{cid}
```

### 扫描入库（不是通用“保存任意图”）

```http
POST /comfytv/assets/adopt
→ 扫描 media 文件夹中尚未登记的媒体，批量 create
```

### 事件

- 广播名：`comfytv-assets`（create / category-* 等）
- 实现：`ComfyTV/api/_common.py` → `broadcast_asset_event`

## Asset JSON 形状

来自 `storage/assets.py` → `_asset_to_dict`：

```json
{
  "id": 1,
  "category_ids": [1, 2],
  "name": "女主定妆",
  "media_type": "image",
  "payload_url": "/view?filename=xxx.png&type=output",
  "mime_type": "image/png",
  "width": 1024,
  "height": 1024,
  "size_bytes": 12345,
  "source": null,
  "metadata": {},
  "created_at": "...",
  "updated_at": "..."
}
```

## Ryan 侧约定（与 CONTEXT 一致）

- Bridge 只依赖 **HTTP**，不 import ComfyTV Python 包（避免硬耦合；ComfyTV 未安装时探测失败并降级）。
- 探测：`GET /comfytv/assets?limit=1` 或 capabilities；失败 → Local upload provider。
- AssetRef 最小字段建议：`provider=comfytv`, `provider_asset_id`, `payload_url` 快照, `media_type`, `display_name`, `semantic_role`, `usage`。
- Agent 编译：图尽力视觉附件；视频元数据+可选关键帧（`cache/`）；音频元数据。
- **不要**把 ComfyTV Project 与 `creative_project_id` 做成同一行；可选 `external_bindings.comfytv_project_id` 仅绑定。

## 相关但非 Asset Library

| API | 说明 |
|---|---|
| `/comfytv/projects` | ComfyTV 自己的 Project，≠ Creative Project |
| `/comfytv/projects/{pid}/outputs` | Stage 输出记录 |
| `/comfytv/resources` | 另一类资源文件（LUT 等），不是侧栏 Asset 主库 |

## 验证线索

- 列表：浏览器或 curl `GET /comfytv/assets?category=all`
- 测试：`ComfyTV/tests/test_assets_api.py`, `test_assets_storage.py`, `test_assets_adopt.py`
