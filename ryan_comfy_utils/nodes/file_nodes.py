from ..acp.file_exporter import write_text_export


class RyanFileExporter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"default": "", "multiline": True}),
                "output_subdir": ("STRING", {"default": "ryan_acp_exports/manual"}),
                "filename": ("STRING", {"default": ""}),
                "extension": (["txt", "md", "json"], {"default": "md"}),
                "append_timestamp": ("BOOLEAN", {"default": True}),
                "overwrite": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("file_path", "file_text")
    FUNCTION = "run"
    CATEGORY = "Ryan Utils / File"

    def run(self, text, output_subdir, filename, extension, append_timestamp, overwrite):
        path = write_text_export(
            text=text,
            output_subdir=output_subdir,
            filename=filename,
            extension=extension,
            append_timestamp=append_timestamp,
            overwrite=overwrite,
        )
        return path, text