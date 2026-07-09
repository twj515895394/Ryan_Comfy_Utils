"""将 runner profile 中的 command 占位符展开为可执行 argv。"""

from __future__ import annotations


def expand_cli_command(command: list, replacements: dict[str, str]) -> list[str]:
    """对 command 每个参数做字面量占位符替换。

    仅替换完整占位符子串（如 ``{context_file}``），不经 shell。
    无占位符时原样返回字符串列表。
    """
    if not command:
        raise ValueError("runner command must be a non-empty list")

    expanded: list[str] = []
    for part in command:
        text = str(part)
        for key, value in replacements.items():
            text = text.replace(key, value)
        expanded.append(text)
    return expanded
