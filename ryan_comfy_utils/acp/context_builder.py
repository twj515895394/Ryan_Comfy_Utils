from pathlib import Path


def build_context_payload(
    skill_id: str,
    skill_directory: Path,
    user_text: str,
    image_paths: list[str],
    file_paths: list[str],
    workspace_info: dict,
) -> dict:
    return {
        "skill": {
            "id": skill_id,
            "directory": str(skill_directory),
        },
        "input": {
            "text": user_text,
            "images": image_paths,
            "files": file_paths,
        },
        "workspace": workspace_info,
    }
