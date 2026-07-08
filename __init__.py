from .ryan_comfy_utils.nodes.llm_nodes import RyanLLMChat, RyanLLMVisionChat
from .ryan_comfy_utils.nodes.prompt_nodes import RyanPromptTemplate
from .ryan_comfy_utils.nodes.video_nodes import RyanBatchVideoLoader, RyanVideoFrameSampler

WEB_DIRECTORY = "./ryan_comfy_utils/web"

NODE_CLASS_MAPPINGS = {
    "Ryan LLM Chat": RyanLLMChat,
    "Ryan LLM Vision Chat": RyanLLMVisionChat,
    "Ryan Prompt Template": RyanPromptTemplate,
    "Ryan Batch Video Loader": RyanBatchVideoLoader,
    "Ryan Video Frame Sampler": RyanVideoFrameSampler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Ryan LLM Chat": "Ryan LLM Chat",
    "Ryan LLM Vision Chat": "Ryan LLM Vision Chat",
    "Ryan Prompt Template": "Ryan Prompt Template",
    "Ryan Batch Video Loader": "Ryan Batch Video Loader",
    "Ryan Video Frame Sampler": "Ryan Video Frame Sampler",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
