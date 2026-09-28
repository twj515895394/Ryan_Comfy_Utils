from .ryan_comfy_utils.nodes.workflow_agent_node import RyanWorkflowAgent
from .ryan_comfy_utils.nodes.creative_text_selector_node import RyanCreativeTextSelector
from .ryan_comfy_utils.workflow_agent import routes as _workflow_agent_routes
from .ryan_comfy_utils.creative_workspace import routes as _creative_workspace_routes

from .ryan_comfy_utils.nodes.acp_nodes import (
    RyanACPImageAnalyzeAgent,
    RyanACPImagePromptAgent,
    RyanACPMiniMaxH3VideoPromptAgent,
    RyanACPUniversalAgent,
    RyanACPVideoPromptAgent,
)
from .ryan_comfy_utils.nodes.llm_nodes import RyanLLMChat, RyanLLMVisionChat
from .ryan_comfy_utils.nodes.file_nodes import RyanFileExporter
from .ryan_comfy_utils.nodes.prompt_nodes import RyanPromptTemplate
from .ryan_comfy_utils.nodes.video_nodes import RyanBatchVideoLoader, RyanVideoFrameSampler, RyanImageBatchSplitter, RyanVideoSceneSplitter
from .ryan_comfy_utils.nodes.image_generator_node import RyanImageGenerator
from .ryan_comfy_utils.nodes.qwen_image21_node import RyanQwenImage21
from .ryan_comfy_utils.nodes.video_generator_node import RyanVideoGenerator
from .ryan_comfy_utils.nodes.smart_filter_node import (
    RyanSmartImageFilter,
    RyanSmartVideoFilter,
    RyanSmartAudioFilter,
    RyanSmartTextFilter,
)

WEB_DIRECTORY = "./ryan_comfy_utils/web"

NODE_CLASS_MAPPINGS = {
    "Ryan ACP Universal Agent": RyanACPUniversalAgent,
    "Ryan ACP Image Prompt Agent": RyanACPImagePromptAgent,
    "Ryan Workflow Agent": RyanWorkflowAgent,
    "Ryan Creative Text Selector": RyanCreativeTextSelector,

    "Ryan ACP Image Analyze Agent": RyanACPImageAnalyzeAgent,
    "Ryan ACP Video Prompt Agent": RyanACPVideoPromptAgent,
    "Ryan ACP MiniMax H3 Video Prompt Agent": RyanACPMiniMaxH3VideoPromptAgent,
    "Ryan LLM Chat": RyanLLMChat,
    "Ryan LLM Vision Chat": RyanLLMVisionChat,
    "Ryan Prompt Template": RyanPromptTemplate,
    "Ryan Batch Video Loader": RyanBatchVideoLoader,
    "Ryan Video Frame Sampler": RyanVideoFrameSampler,
    "Ryan Image Batch Splitter": RyanImageBatchSplitter,
    "Ryan Video Scene Splitter": RyanVideoSceneSplitter,
    "Ryan File Exporter": RyanFileExporter,
    "Ryan Image Generator": RyanImageGenerator,
    "Ryan Qwen Image 2.1": RyanQwenImage21,
    "Ryan Video Generator": RyanVideoGenerator,
    "Ryan Smart Image Filter": RyanSmartImageFilter,
    "Ryan Smart Video Filter": RyanSmartVideoFilter,
    "Ryan Smart Audio Filter": RyanSmartAudioFilter,
    "Ryan Smart Text Filter": RyanSmartTextFilter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Ryan Workflow Agent": "Ryan Workflow Agent",
    "Ryan Creative Text Selector": "Ryan Creative Text Selector",

    "Ryan ACP Universal Agent": "Ryan ACP Universal Agent",
    "Ryan ACP Image Prompt Agent": "Ryan Image Prompt Agent",
    "Ryan ACP Image Analyze Agent": "Ryan Image Analyze Agent",
    "Ryan ACP Video Prompt Agent": "Ryan Video Prompt Agent",
    "Ryan ACP MiniMax H3 Video Prompt Agent": "Ryan MiniMax H3 Video Prompt Agent",
    "Ryan LLM Chat": "Ryan LLM Chat",
    "Ryan LLM Vision Chat": "Ryan LLM Vision Chat",
    "Ryan Prompt Template": "Ryan Prompt Template",
    "Ryan Batch Video Loader": "Ryan Batch Video Loader",
    "Ryan Video Frame Sampler": "Ryan Video Frame Sampler",
    "Ryan Image Batch Splitter": "Ryan Image Batch Splitter",
    "Ryan Video Scene Splitter": "Ryan Video Scene Splitter",
    "Ryan File Exporter": "Ryan File Exporter",
    "Ryan Image Generator": "Ryan Image Generator",
    "Ryan Qwen Image 2.1": "Ryan Qwen Image 2.1",
    "Ryan Video Generator": "Ryan Video Generator",
    "Ryan Smart Image Filter": "Ryan Smart Image Filter",
    "Ryan Smart Video Filter": "Ryan Smart Video Filter",
    "Ryan Smart Audio Filter": "Ryan Smart Audio Filter",
    "Ryan Smart Text Filter": "Ryan Smart Text Filter",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

import sys

def _safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        try:
            sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))
        except Exception:
            pass

_safe_print("\n" + "=" * 60)
_safe_print("Ryan_Comfy_Utils custom nodes loaded")
_safe_print("-" * 60)
for node_id in sorted(NODE_CLASS_MAPPINGS.keys()):
    display_name = NODE_DISPLAY_NAME_MAPPINGS.get(node_id, node_id)
    _safe_print(f"  * {display_name}")
_safe_print("=" * 60 + "\n")
