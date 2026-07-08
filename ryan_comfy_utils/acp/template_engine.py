def render_context_template(template: str, payload: dict) -> str:
    replacements = {
        "{skill_directory}": payload["skill"]["directory"],
        "{input.text}": payload["input"]["text"],
        "{input.images}": "\n".join(payload["input"].get("images", [])),
        "{input.files}": "\n".join(payload["input"].get("files", [])),
    }
    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace(key, value)
    return rendered
