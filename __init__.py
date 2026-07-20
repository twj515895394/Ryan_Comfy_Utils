from .ryan_comfy_utils.nodes.llm_nodes import RyanLLMChat, RyanLLMVisionChat
from .ryan_comfy_utils.nodes.local_multimodal_nodes import RyanLocalMultimodalChat
from .ryan_comfy_utils.nodes.acp_nodes import (
    RyanACPImageAnalyzeAgent,
    RyanACPImagePromptAgent,
    RyanACPUniversalAgent,
    RyanACPVideoPromptAgent,
)
from .ryan_comfy_utils.nodes.file_nodes import RyanFileExporter
from .ryan_comfy_utils.nodes.prompt_nodes import RyanPromptTemplate
from .ryan_comfy_utils.nodes.video_nodes import RyanBatchVideoLoader, RyanVideoFrameSampler, RyanImageBatchSplitter, RyanVideoSceneSplitter

WEB_DIRECTORY = "./ryan_comfy_utils/web"

NODE_CLASS_MAPPINGS = {
    "Ryan ACP Universal Agent": RyanACPUniversalAgent,
    "Ryan ACP Image Prompt Agent": RyanACPImagePromptAgent,
    "Ryan ACP Image Analyze Agent": RyanACPImageAnalyzeAgent,
    "Ryan ACP Video Prompt Agent": RyanACPVideoPromptAgent,
    "Ryan LLM Chat": RyanLLMChat,
    "Ryan LLM Vision Chat": RyanLLMVisionChat,
    "Ryan Local Multimodal Chat": RyanLocalMultimodalChat,
    "Ryan Prompt Template": RyanPromptTemplate,
    "Ryan Batch Video Loader": RyanBatchVideoLoader,
    "Ryan Video Frame Sampler": RyanVideoFrameSampler,
    "Ryan Image Batch Splitter": RyanImageBatchSplitter,
    "Ryan Video Scene Splitter": RyanVideoSceneSplitter,
    "Ryan File Exporter": RyanFileExporter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Ryan ACP Universal Agent": "Ryan ACP Universal Agent",
    "Ryan ACP Image Prompt Agent": "Ryan Image Prompt Agent",
    "Ryan ACP Image Analyze Agent": "Ryan Image Analyze Agent",
    "Ryan ACP Video Prompt Agent": "Ryan Video Prompt Agent",
    "Ryan LLM Chat": "Ryan LLM Chat",
    "Ryan LLM Vision Chat": "Ryan LLM Vision Chat",
    "Ryan Local Multimodal Chat": "Ryan Local Multimodal Chat",
    "Ryan Prompt Template": "Ryan Prompt Template",
    "Ryan Batch Video Loader": "Ryan Batch Video Loader",
    "Ryan Video Frame Sampler": "Ryan Video Frame Sampler",
    "Ryan Image Batch Splitter": "Ryan Image Batch Splitter",
    "Ryan Video Scene Splitter": "Ryan Video Scene Splitter",
    "Ryan File Exporter": "Ryan File Exporter",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

# === 节点加载醒目提示（便于确认是否成功加载）===
print("\n" + "=" * 60)
print("🚀 Ryan_Comfy_Utils 自定义节点包加载完成")
print("-" * 60)
for node_id in sorted(NODE_CLASS_MAPPINGS.keys()):
    display_name = NODE_DISPLAY_NAME_MAPPINGS.get(node_id, node_id)
    print(f"  ✓ {display_name}")
print("=" * 60 + "\n")
