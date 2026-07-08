import base64
import io
from typing import List

import numpy as np
import torch
from PIL import Image


def tensor_batch_to_pil(images) -> List[Image.Image]:
    if images is None:
        return []

    if not isinstance(images, torch.Tensor):
        raise TypeError("images must be a torch.Tensor in ComfyUI IMAGE format")

    if images.ndim == 3:
        images = images.unsqueeze(0)

    if images.ndim != 4:
        raise ValueError(f"Invalid IMAGE tensor shape: {tuple(images.shape)}")

    pil_images = []
    for img in images:
        arr = img.detach().cpu().numpy()
        arr = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
        pil_images.append(Image.fromarray(arr))
    return pil_images


def pil_to_tensor_batch(pil_images: List[Image.Image]):
    if not pil_images:
        return torch.zeros((0, 64, 64, 3), dtype=torch.float32)

    tensors = []
    base_size = pil_images[0].size
    for img in pil_images:
        if img.size != base_size:
            img = img.resize(base_size, Image.LANCZOS)
        arr = np.asarray(img.convert("RGB")).astype(np.float32) / 255.0
        tensors.append(torch.from_numpy(arr))
    return torch.stack(tensors, dim=0)


def resize_max_side(img: Image.Image, max_side: int) -> Image.Image:
    max_side = int(max_side or 0)
    if max_side <= 0:
        return img

    width, height = img.size
    current_max = max(width, height)
    if current_max <= max_side:
        return img

    scale = max_side / float(current_max)
    new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    return img.resize(new_size, Image.LANCZOS)


def pil_to_data_url(img: Image.Image, image_format: str = "jpeg", jpeg_quality: int = 85) -> str:
    fmt = (image_format or "jpeg").lower()
    buffer = io.BytesIO()

    if fmt == "png":
        img.save(buffer, format="PNG")
        mime = "image/png"
    else:
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        img.save(buffer, format="JPEG", quality=int(jpeg_quality), optimize=True)
        mime = "image/jpeg"

    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"
