from __future__ import annotations

from ..core.image_utils import resize_max_side
from ..core.local_multimodal_runtime import (
    LocalMultimodalRuntime,
    find_llama_server,
    list_local_model_choices,
    list_mmproj_choices,
    resolve_mmproj_path,
    resolve_model_path,
)
from .comfy_image_inputs import build_image_slot_input_types, flatten_slot_tensors_to_pil, slots_from_explicit_args


def _release_comfy_models(enabled: bool) -> None:
    if not enabled:
        return
    try:
        import comfy.model_management as model_management

        unload = getattr(model_management, "unload_all_models", None)
        if callable(unload):
            unload()
        empty_cache = getattr(model_management, "soft_empty_cache", None)
        if callable(empty_cache):
            empty_cache()
    except Exception as exc:
        print(f"[Ryan Local Multimodal] Unable to release ComfyUI models before load: {exc}")


class RyanLocalMultimodalChat:
    def __init__(self):
        self.runtime = LocalMultimodalRuntime()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "backend": (["auto", "transformers", "llama.cpp (GGUF + mmproj)"], {"default": "auto"}),
                "model": (list_local_model_choices(),),
                "mmproj": (list_mmproj_choices(), {"default": "auto"}),
                "model_path_override": ("STRING", {"default": ""}),
                "mmproj_path_override": ("STRING", {"default": ""}),
                "system_prompt": ("STRING", {"default": "", "multiline": True}),
                "user_prompt": ("STRING", {"default": "Describe the image in detail.", "multiline": True}),
                "keep_model_loaded": ("BOOLEAN", {"default": False}),
                "unload_comfy_models_before_load": ("BOOLEAN", {"default": True}),
                "max_images": ("INT", {"default": 10, "min": 1, "max": 10, "step": 1}),
                "image_max_side": ("INT", {"default": 1536, "min": 0, "max": 8192, "step": 64}),
                "temperature": ("FLOAT", {"default": 0.2, "min": 0.0, "max": 2.0, "step": 0.01}),
                "top_p": ("FLOAT", {"default": 0.95, "min": 0.0, "max": 1.0, "step": 0.01}),
                "max_new_tokens": ("INT", {"default": 2048, "min": 1, "max": 131072, "step": 1}),
                "seed": ("INT", {"default": -1, "min": -1, "max": 0x7FFFFFFFFFFFFFFF}),
                "transformers_dtype": (["auto", "bfloat16", "float16", "float32"], {"default": "auto"}),
                "transformers_quantization": (["none", "4bit", "8bit"], {"default": "none"}),
                "transformers_attention": (["auto", "eager", "sdpa", "flash_attention_2"], {"default": "auto"}),
                "trust_remote_code": ("BOOLEAN", {"default": False}),
                "llama_server_path": ("STRING", {"default": ""}),
                "context_size": ("INT", {"default": 8192, "min": 0, "max": 1048576, "step": 256}),
                "gpu_layers": ("STRING", {"default": "auto"}),
                "threads": ("INT", {"default": 0, "min": 0, "max": 256, "step": 1}),
                "mmproj_offload": ("BOOLEAN", {"default": True}),
                "startup_timeout_seconds": ("INT", {"default": 300, "min": 10, "max": 1800, "step": 10}),
                "request_timeout_seconds": ("INT", {"default": 600, "min": 30, "max": 7200, "step": 10}),
            },
            "optional": build_image_slot_input_types(include_paths=False, default_slot_count=2),
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("response_text", "backend_used", "resolved_model_path", "runtime_info_json")
    FUNCTION = "run"
    CATEGORY = "Ryan Utils / LLM"

    def run(
        self,
        backend,
        model,
        mmproj,
        model_path_override,
        mmproj_path_override,
        system_prompt,
        user_prompt,
        keep_model_loaded,
        unload_comfy_models_before_load,
        max_images,
        image_max_side,
        temperature,
        top_p,
        max_new_tokens,
        seed,
        transformers_dtype,
        transformers_quantization,
        transformers_attention,
        trust_remote_code,
        llama_server_path,
        context_size,
        gpu_layers,
        threads,
        mmproj_offload,
        startup_timeout_seconds,
        request_timeout_seconds,
        image_slot_count=2,
        image_01=None,
        image_02=None,
        image_03=None,
        image_04=None,
        image_05=None,
        image_06=None,
        image_07=None,
        image_08=None,
        image_09=None,
        image_10=None,
    ):
        detected_backend, model_path = resolve_model_path(model, model_path_override)
        requested_backend = {
            "auto": detected_backend,
            "transformers": "transformers",
            "llama.cpp (GGUF + mmproj)": "llama_cpp",
        }[backend]
        if requested_backend == "transformers" and not model_path.is_dir():
            raise ValueError("Transformers backend requires a local model directory containing config.json")
        if requested_backend == "llama_cpp" and model_path.suffix.lower() != ".gguf":
            raise ValueError("llama.cpp backend requires a .gguf model file")

        slots = slots_from_explicit_args(
            image_slot_count,
            image_01=image_01,
            image_02=image_02,
            image_03=image_03,
            image_04=image_04,
            image_05=image_05,
            image_06=image_06,
            image_07=image_07,
            image_08=image_08,
            image_09=image_09,
            image_10=image_10,
        )
        images = flatten_slot_tensors_to_pil(slots, max_total=int(max_images or 10))
        images = [resize_max_side(image, int(image_max_side)) for image in images]
        _release_comfy_models(bool(unload_comfy_models_before_load))

        if requested_backend == "transformers":
            text, info = self.runtime.run_transformers(
                model_path=model_path,
                images=images,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                top_p=top_p,
                max_new_tokens=max_new_tokens,
                seed=seed,
                dtype_name=transformers_dtype,
                quantization=transformers_quantization,
                attention=transformers_attention,
                trust_remote_code=trust_remote_code,
                keep_model_loaded=keep_model_loaded,
            )
            backend_used = "transformers"
        else:
            mmproj_path = resolve_mmproj_path(
                mmproj,
                mmproj_path_override,
                model_path,
                required=bool(images),
            )
            server_path = find_llama_server(llama_server_path)
            text, info = self.runtime.run_llama_cpp(
                server_path=server_path,
                model_path=model_path,
                mmproj_path=mmproj_path,
                images=images,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                top_p=top_p,
                max_new_tokens=max_new_tokens,
                seed=seed,
                context_size=context_size,
                gpu_layers=gpu_layers,
                threads=threads,
                mmproj_offload=mmproj_offload,
                startup_timeout_seconds=startup_timeout_seconds,
                request_timeout_seconds=request_timeout_seconds,
                keep_model_loaded=keep_model_loaded,
            )
            backend_used = "llama_cpp_server"

        return (text, backend_used, str(model_path), self.runtime.info_json(info))
