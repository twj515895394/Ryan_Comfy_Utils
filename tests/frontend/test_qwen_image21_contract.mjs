import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

const source = await readFile(
  new URL("../../ryan_comfy_utils/web/ryan_qwen_image21.js", import.meta.url),
  "utf8",
);

test("Qwen Image 2.1 frontend owns a sixteen-slot node extension", () => {
  assert.match(source, /const NODE_NAME = "Ryan Qwen Image 2\.1"/);
  assert.match(source, /const MAX_SLOTS = 16/);
  assert.match(source, /beforeRegisterNodeDef/);
  assert.match(source, /image_slot_count/);
});

test("Qwen gallery uses ComfyUI upload metadata and persists stable assets", () => {
  assert.match(source, /fetchApi\("\/upload\/image"/);
  assert.match(source, /form\.append\("image"/);
  assert.match(source, /asset_id/);
  assert.match(source, /gallery_manifest/);
  assert.match(source, /annotatedPathFromUpload/);
});

test("Qwen gallery supports sorting, deletion, and external input visibility", () => {
  assert.match(source, /draggable = true/);
  assert.match(source, /swapGalleryItems/);
  assert.match(source, /remove\.addEventListener/);
  assert.match(source, /link != null/);
  assert.match(source, /externallyConnected/);
  assert.match(source, /_ryanQwenAllInputs/);
});
