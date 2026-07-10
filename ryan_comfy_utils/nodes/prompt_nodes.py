from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


def _list_templates(source="built_in", prompt_dir=""):
    directory = PROMPTS_DIR if source == "built_in" else Path(prompt_dir).expanduser()
    if not directory.exists() or not directory.is_dir():
        return ["video_frame_analysis.md"]
    files = [p.name for p in directory.iterdir() if p.is_file() and p.suffix.lower() in {".txt", ".md", ".json"}]
    return sorted(files) or ["video_frame_analysis.md"]


def _read_template(source, prompt_dir, template_name):
    directory = PROMPTS_DIR if source == "built_in" else Path(prompt_dir).expanduser()
    path = directory / template_name
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")



TEMPLATE_SOURCE_MAP = {
    "内置模板": "built_in",
    "自定义目录": "custom_dir",
}


class RyanPromptTemplate:
    @classmethod
    def INPUT_TYPES(cls):
        templates = _list_templates("built_in", "")
        return {
            "required": {
                "template_source": (["内置模板", "自定义目录"], {"default": "内置模板"}),
                "prompt_dir": ("STRING", {"default": ""}),
                "template_name": (templates,),
                "user_prompt": ("STRING", {"default": "", "multiline": True}),
                "append_user_prompt": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("final_prompt", "template_text")
    FUNCTION = "run"
    CATEGORY = "Ryan Utils / Prompt"

    def run(self, template_source, prompt_dir, template_name, user_prompt, append_user_prompt):
        source = TEMPLATE_SOURCE_MAP.get(template_source, "built_in")
        template_text = _read_template(source, prompt_dir, template_name)
        final_prompt = template_text
        if append_user_prompt and user_prompt and user_prompt.strip():
            final_prompt = final_prompt.rstrip() + "\n\n" + user_prompt.strip()
        return (final_prompt, template_text)
