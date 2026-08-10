"""Ryan Smart Input Filter — 自动检测占位符文件并输出 null。

4 个过滤节点（Image / Video / Audio / Text），每个最多 9 个动态输入/输出。
通过 ComfyUI 的 PROMPT hidden input 回溯上游节点图，自动检测占位符文件名
（默认 example / default），对应输出返回 None（null），实现"不传递数据"效果。
"""

from __future__ import annotations

import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# AnyType — 通配类型，匹配任何 ComfyUI 类型
# ---------------------------------------------------------------------------
class _AnyType(str):
    """A string subclass that equals any other type, used as ComfyUI '*' wildcard."""

    def __eq__(self, _):
        return True

    def __ne__(self, _):
        return False

    def __hash__(self):
        return hash("*")


ANY = _AnyType("*")

MAX_SLOTS = 9
DEFAULT_PLACEHOLDERS = "example,default"

# 常见 Load 节点中包含文件名的 widget 名称
_FILENAME_WIDGETS = frozenset({
    "image", "video", "audio", "file", "filename",
    "path", "file_path", "audio_file", "video_path",
})


# ---------------------------------------------------------------------------
# 通过 PROMPT 回溯上游文件名
# ---------------------------------------------------------------------------
def _find_filename_in_node(prompt: dict, node_id: str) -> str | None:
    """检查节点的 widget 值中是否含有文件名。"""
    node = prompt.get(str(node_id))
    if not node:
        return None
    inputs = node.get("inputs", {})

    # 优先检查已知的文件名 widget
    for wname in _FILENAME_WIDGETS:
        val = inputs.get(wname)
        if isinstance(val, str) and val.strip():
            return val.strip()

    # 回退：任何包含点号的短字符串（大概率是文件名）
    for val in inputs.values():
        if isinstance(val, str) and "." in val and len(val) < 300:
            return val.strip()

    return None


def _trace_upstream_filename(
    prompt: dict,
    node_id: str,
    input_name: str,
    *,
    depth: int = 5,
) -> str | None:
    """递归回溯上游节点，查找源文件名。

    从当前节点 node_id 的 input_name 出发，沿连线向上游追溯，
    直到找到一个包含文件名 widget 的节点（通常是 LoadImage、LoadVideo 等）。
    """
    if depth <= 0 or not prompt:
        return None

    node = prompt.get(str(node_id))
    if not node:
        return None

    connection = node.get("inputs", {}).get(input_name)

    # 如果输入值本身就是字符串（widget 直接值而非连线）
    if isinstance(connection, str) and connection.strip():
        return connection.strip()

    # 不是连线引用 [node_id, output_index]
    if not isinstance(connection, list) or len(connection) < 2:
        return None

    source_id = str(connection[0])

    # 检查上游节点是否有文件名 widget
    filename = _find_filename_in_node(prompt, source_id)
    if filename:
        return filename

    # 继续向更上游追溯
    source_node = prompt.get(source_id)
    if not source_node:
        return None
    for key, val in source_node.get("inputs", {}).items():
        if isinstance(val, list) and len(val) >= 2:
            result = _trace_upstream_filename(
                prompt, source_id, key, depth=depth - 1,
            )
            if result:
                return result

    return None


def _is_placeholder(filename: str, placeholders: set[str]) -> bool:
    """判断文件名的 stem（不含后缀）是否匹配占位符列表。"""
    try:
        stem = Path(filename).stem.lower().strip()
        return stem in placeholders
    except Exception:
        return False


# ---------------------------------------------------------------------------
# 槽位命名
# ---------------------------------------------------------------------------
def _in_name(i: int) -> str:
    return f"in_{i:02d}"


def _out_name(i: int) -> str:
    return f"out_{i:02d}"


# ---------------------------------------------------------------------------
# 安全打印
# ---------------------------------------------------------------------------
def _log(msg: str) -> None:
    try:
        print(f"[RyanSmartFilter] {msg}")
    except UnicodeEncodeError:
        try:
            sys.stdout.buffer.write(
                (f"[RyanSmartFilter] {msg}\n").encode("utf-8", errors="replace")
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 节点类工厂
# ---------------------------------------------------------------------------
def _create_filter_class(
    group_name: str,
    data_type,
    default_visible: int,
):
    """为指定数据类型创建一个 Smart Filter 节点类。"""

    slot_type = data_type  # 闭包捕获

    class _FilterNode:
        @classmethod
        def INPUT_TYPES(cls):
            optional: dict = {
                "placeholder_names": (
                    "STRING",
                    {"default": DEFAULT_PLACEHOLDERS, "multiline": False},
                ),
            }
            for i in range(1, MAX_SLOTS + 1):
                optional[_in_name(i)] = (slot_type,)
            return {
                "required": {},
                "optional": optional,
                "hidden": {
                    "prompt": "PROMPT",
                    "unique_id": "UNIQUE_ID",
                },
            }

        RETURN_TYPES = tuple(slot_type for _ in range(MAX_SLOTS))
        RETURN_NAMES = tuple(_out_name(i) for i in range(1, MAX_SLOTS + 1))

        FUNCTION = "filter_inputs"
        CATEGORY = "Ryan Utils / Filter"
        OUTPUT_NODE = False
        DESCRIPTION = (
            f"智能 {group_name.upper()} 过滤/转接节点。"
            f"自动回溯上游节点，检测占位符文件（默认 example / default），"
            f"匹配时该路输出 null。固定提供 {MAX_SLOTS} 个槽位，保持工作流连线索引稳定。"
        )

        # 前端 JS 需要的元信息
        _GROUP_NAME = group_name
        _DEFAULT_VISIBLE = default_visible

        def filter_inputs(
            self,
            placeholder_names: str = DEFAULT_PLACEHOLDERS,
            prompt=None,
            unique_id=None,
            **kwargs,
        ):
            placeholders: set[str] = {
                n.strip().lower()
                for n in placeholder_names.split(",")
                if n.strip()
            }
            results: list = []
            connected_slots: list[int] = []
            valid_slots: list[int] = []
            invalid_slots: list[int] = []

            for i in range(1, MAX_SLOTS + 1):
                name = _in_name(i)
                value = kwargs.get(name)
                connection = (
                    prompt.get(str(unique_id), {}).get("inputs", {}).get(name)
                    if prompt and unique_id
                    else None
                )
                is_connected = value is not None or (
                    isinstance(connection, list) and len(connection) >= 2
                )
                if not is_connected:
                    results.append(None)
                    continue
                connected_slots.append(i)

                invalid_reason = None
                if value is None:
                    invalid_reason = "connected input resolved to None"
                elif isinstance(value, str) and _is_placeholder(value, placeholders):
                    invalid_reason = f"placeholder value '{value}'"
                elif prompt and unique_id:
                    upstream_file = _trace_upstream_filename(
                        prompt, str(unique_id), name,
                    )
                    if upstream_file and _is_placeholder(
                        upstream_file, placeholders
                    ):
                        invalid_reason = f"placeholder source '{upstream_file}'"

                if invalid_reason:
                    invalid_slots.append(i)
                    _log(
                        f"[{group_name}] slot {i} -> null "
                        f"({invalid_reason})"
                    )
                    results.append(None)
                    continue

                valid_slots.append(i)
                results.append(value)

            _log(
                f"[{group_name}] node={unique_id or 'unknown'} "
                f"connected={len(connected_slots)} "
                f"valid_outputs={len(valid_slots)} "
                f"null_outputs={len(invalid_slots)} "
                f"connected_slots={connected_slots or '-'} "
                f"valid_slots={valid_slots or '-'} "
                f"null_slots={invalid_slots or '-'}"
            )
            return tuple(results)

    # 设置类名（便于调试和 ComfyUI 内部识别）
    cls_name = f"RyanSmart{group_name.title()}Filter"
    _FilterNode.__name__ = cls_name
    _FilterNode.__qualname__ = cls_name
    return _FilterNode


# ---------------------------------------------------------------------------
# 创建 4 个过滤节点类
# ---------------------------------------------------------------------------
RyanSmartImageFilter = _create_filter_class("image", "IMAGE", 5)
RyanSmartVideoFilter = _create_filter_class("video", ANY, 1)
RyanSmartAudioFilter = _create_filter_class("audio", ANY, 1)
RyanSmartTextFilter = _create_filter_class("text", "STRING", 1)
