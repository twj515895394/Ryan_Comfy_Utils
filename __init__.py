from .ryan_comfy_utils.nodes.llm_nodes import RyanLLMChat, RyanLLMVisionChat
from .ryan_comfy_utils.nodes.acp_nodes import (
    RyanACPImageAnalyzeAgent,
    RyanACPImagePromptAgent,
    RyanACPUniversalAgent,
    RyanACPVideoPromptAgent,
)
from .ryan_comfy_utils.nodes.prompt_nodes import RyanPromptTemplate
from .ryan_comfy_utils.nodes.video_nodes import RyanBatchVideoLoader, RyanVideoFrameSampler

WEB_DIRECTORY = "./ryan_comfy_utils/web"

NODE_CLASS_MAPPINGS = {
    "Ryan ACP Universal Agent": RyanACPUniversalAgent,
    "Ryan ACP Image Prompt Agent": RyanACPImagePromptAgent,
    "Ryan ACP Image Analyze Agent": RyanACPImageAnalyzeAgent,
    "Ryan ACP Video Prompt Agent": RyanACPVideoPromptAgent,
    "Ryan LLM Chat": RyanLLMChat,
    "Ryan LLM Vision Chat": RyanLLMVisionChat,
    "Ryan Prompt Template": RyanPromptTemplate,
    "Ryan Batch Video Loader": RyanBatchVideoLoader,
    "Ryan Video Frame Sampler": RyanVideoFrameSampler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Ryan ACP Universal Agent": "Ryan ACP Universal Agent",
    "Ryan ACP Image Prompt Agent": "Ryan Image Prompt Agent",
    "Ryan ACP Image Analyze Agent": "Ryan Image Analyze Agent",
    "Ryan ACP Video Prompt Agent": "Ryan Video Prompt Agent",
    "Ryan LLM Chat": "Ryan LLM Chat",
    "Ryan LLM Vision Chat": "Ryan LLM Vision Chat",
    "Ryan Prompt Template": "Ryan Prompt Template",
    "Ryan Batch Video Loader": "Ryan Batch Video Loader",
    "Ryan Video Frame Sampler": "Ryan Video Frame Sampler",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]