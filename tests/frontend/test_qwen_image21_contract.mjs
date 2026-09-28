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
  assert.match(source, /const SLOTS_PER_ROW = 4/);
  assert.match(source, /const DEFAULT_VISIBLE_SLOTS = SLOTS_PER_ROW/);
  assert.match(source, /QWEN_NUMERIC_DEFAULTS/);
  assert.match(source, /megapixels: 1\.0/);
  assert.match(source, /resolution: 1024/);
  assert.match(source, /Number\.isInteger\(value\) && value >= 1 && value <= 64/);
  assert.match(source, /value === 0 \|\| value % 32 === 0/);
  assert.match(source, /QWEN_MEGAPIXEL_OPTIONS\.find/);
  assert.match(source, /formatQwenMegapixelOption/);
  assert.match(source, /numeric\.toFixed\(1\)/);
  assert.match(source, /getOptionLabel/);
  assert.match(source, /beforeRegisterNodeDef/);
  assert.doesNotMatch(source, /COUNT_WIDGET|image_slot_count/);
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
  assert.match(source, /ryan_qwen_image_links/);
});

test("Qwen gallery follows the H3-style in-node image workbench layout", () => {
  assert.match(source, /ryan-qwen-image-grid/);
  assert.match(source, /grid-template-columns:repeat\(4/);
  assert.match(source, /max-width:100%/);
  assert.match(source, /padding:0 10px/);
  assert.match(source, /ryan-qwen-image-slot/);
  assert.match(source, /ryan-qwen-image-toggle/);
  assert.match(source, /展开其余/);
  assert.match(source, /点击添加图片/);
  assert.match(source, /node\.removeInput/);
  assert.match(source, /pruneQwenImageInputs/);
  assert.match(source, /patchQwenGraphToPrompt/);
  assert.match(source, /installQwenCanvasBridge/);
  assert.match(source, /ryan-qwen-workbench/);
  assert.match(source, /ryan_qwen_image21_gallery/);
  assert.match(source, /ryan_qwen_image21_prompt_workbench/);
  assert.match(source, /ensureQwenPromptInput/);
  assert.match(source, /qwenPromptGraphPos/);
  assert.match(source, /qwenPromptSlotHit/);
  assert.match(source, /updateQwenPromptConnectionState/);
  assert.match(source, /contentEditable = connected \? "false" : "true"/);
  assert.match(source, /promptInput\.link/);
  assert.doesNotMatch(source, /forceInput/);
  assert.doesNotMatch(source, /promptNode\.inputs\.prompt_text\s*=/);
});

test("Qwen prompt editors expose image mention completion and persist its manifest", () => {
  assert.match(source, /createPromptEditor/);
  assert.match(source, /activeMentionOptions/);
  assert.match(source, /@\(\?:图片\|image\)/);
  assert.match(source, /prompt_mentions/);
  assert.match(source, /assetId/);
});
