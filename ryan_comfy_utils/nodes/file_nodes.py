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
    DESCRIPTION = "文件导出节点。将输入的文本内容写入本地指定子目录下的文件（支持 txt、md、json 格式），可自动追加时间戳。"

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