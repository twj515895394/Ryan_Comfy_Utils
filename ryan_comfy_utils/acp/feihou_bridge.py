"""FeiHou-Easy-H3 桥接模块。

暴露 ``run_h3_agent()`` 供 FeiHou 插件的提示词优化流程调用。
该函数封装了完整的 ACP 执行管线：
1. 从 FeiHou API 配置动态构建 runner_profile
2. 格式化 FeiHou 上下文为 ACP user context
3. 解析双 Skill manifest (video-prompt-skill + minimax-h3-video-prompt)
4. 调用 execute_text_session 完成推理
5. 返回优化后的 H3 prompt
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .contracts import load_manifest
from .runtime import execute_text_session, map_result_fields
from .skill_loader import resolve_skill_directory, resolve_skill_root

_PACKAGE_ROOT = Path(__file__).resolve().parent
_DEFAULT_MANIFEST_PATH = _PACKAGE_ROOT / "fixtures" / "manifests" / "feihou_h3_agent.json"
_DEFAULT_SINGLE_SKILL_MANIFEST_PATH = _PACKAGE_ROOT / "fixtures" / "manifests" / "minimax_h3_video_prompt_agent.json"
_DEFAULT_SKILL_ROOT = _PACKAGE_ROOT / "fixtures" / "skills"


# ---------------------------------------------------------------------------
# FeiHou mode → Ryan H3 mode 映射
# ---------------------------------------------------------------------------

_FEIHOU_MODE_MAP: dict[str, str] = {
    # FeiHou 前端 mode 值
    "image": "T2VA",
    "reference": "Ref2VA",
    # 直接传入的 H3 模式名（来自 FeiHou 的更新版本）
    "T2VA": "T2VA",
    "I2VA": "I2VA",
    "FL2VA": "FL2VA",
    "L2VA": "L2VA",
    "Ref2VA": "Ref2VA",
    # 中文模式名（来自 Ryan 节点）
    "纯文生": "T2VA",
    "普通图生": "Ref2VA",
    "首帧生成": "I2VA",
    "首尾帧": "FL2VA",
    "尾帧生成": "L2VA",
    "全能参考": "Ref2VA",
    "视频编辑": "Ref2VA",
    "视频续接": "Ref2VA",
}


# ---------------------------------------------------------------------------
# Runner profile 构建：将 FeiHou 的 API 配置转为 ACP runner_profile
# ---------------------------------------------------------------------------

def _build_runner_profile(
    *,
    api_url: str,
    api_key: str,
    api_format: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    top_p: float = 0.9,
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    """从 FeiHou 的 API 配置构建 pi_cli runner_profile。

    pi CLI 通过环境变量接收 API 配置。
    """
    env: dict[str, str] = {}

    # pi CLI 使用环境变量传递 API 配置
    if api_key:
        env["ANTHROPIC_API_KEY"] = api_key
    if api_url:
        env["ANTHROPIC_BASE_URL"] = api_url

    return {
        "runner": "pi_cli",
        "command": ["pi", "-p"],
        "mode": "text",
        "no_context_files": True,
        "use_skill_flag": True,
        "tool_policy": "full",
        "workspace_root": "output/acp_workspace",
        "timeout_seconds": timeout_seconds,
        "environment": env,
        # 非 profile 标准字段，供桥接层读取
        "_feihou_api": {
            "api_url": api_url,
            "api_key": api_key,
            "api_format": api_format,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
        },
    }


# ---------------------------------------------------------------------------
# 用户上下文构建：将 FeiHou 的模式/素材/时长/画幅格式化为 user context
# ---------------------------------------------------------------------------

def _build_feihou_context(
    *,
    generation_mode: str,
    task_relation: str,
    media_resources: list[dict[str, str]],
    duration_seconds: float,
    aspect_ratio: str,
    ref_image_short_edge: int,
) -> str:
    """格式化 FeiHou 上下文为 ACP user context 字符串。"""
    h3_mode = _FEIHOU_MODE_MAP.get(generation_mode, "T2VA")
    lines: list[str] = [
        f"基础生成模式: {h3_mode}",
        f"用户界面模式: {generation_mode}",
        f"附加任务关系: {task_relation or '无'}",
        f"目标时长: {duration_seconds:.1f} 秒",
    ]
    if aspect_ratio:
        lines.append(f"目标画幅: {aspect_ratio}")
    if ref_image_short_edge:
        lines.append(f"参考图短边: {ref_image_short_edge}px")

    # 素材清单
    lines.append("素材清单:")
    if media_resources:
        for res in media_resources:
            res_type = res.get("type", "unknown")
            path = res.get("path", "")
            role = res.get("role", "")
            tag = res.get("tag", "")
            desc = f"  - [{res_type}] {path}"
            if role:
                desc += f" (角色: {role})"
            if tag:
                desc += f" (标签: {tag})"
            lines.append(desc)
    else:
        lines.append("  - 无（纯文本生成场景）")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def run_h3_agent(
    *,
    user_prompt: str,
    generation_mode: str = "T2VA",
    task_relation: str = "无",
    media_resources: list[dict[str, str]] | None = None,
    duration_seconds: float = 10.0,
    aspect_ratio: str = "",
    ref_image_short_edge: int = 480,
    # LLM API 配置
    api_url: str,
    api_key: str,
    api_format: str = "openai",
    model: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    top_p: float = 0.9,
    timeout_seconds: int = 300,
    use_dual_skill: bool = True,
    # 可选覆盖
    manifest_path: str = "",
    skill_root: str = "",
    workspace_root: str = "",
    session_id: str = "session_feihou_h3",
) -> str:
    """执行 ACP H3 Agent 并返回优化后的 H3 prompt。

    Parameters
    ----------
    user_prompt : str
        用户原始 prompt。
    generation_mode : str
        FeiHou 的生成模式（"image"/"reference"/H3 模式名/中文模式名）。
    task_relation : str
        附加任务关系（无/Video Editing/Video Continuation/...）。
    media_resources : list
        素材列表，每项 {"type": "image"/"video"/"audio", "path": "...", "role": "...", "tag": "..."}.
    duration_seconds : float
        目标时长。
    aspect_ratio : str
        目标画幅。
    ref_image_short_edge : int
        参考图短边像素。
    api_url, api_key, api_format, model : str
        LLM API 配置。
    temperature, max_tokens, top_p : float/int
        LLM 推理参数。
    timeout_seconds : int
        ACP session 超时。
    use_dual_skill : bool
        True 使用双 Skill manifest（video-prompt-skill + minimax-h3-video-prompt），
        False 使用原始单 Skill manifest（仅 minimax-h3-video-prompt，与原 H3 Agent 节点一致）。
    manifest_path : str
        可选，覆盖默认 manifest 路径。

    Returns
    -------
    str
        优化后的 H3 prompt 文本。

    Raises
    ------
    RuntimeError
        ACP 执行失败。
    ValueError
        配置不完整。
    """
    if not user_prompt.strip():
        raise ValueError("提示词不能为空")
    if not api_url.strip():
        raise ValueError("API URL 不能为空")
    if not model.strip():
        raise ValueError("模型名称不能为空")
    if api_format != "ollama" and not api_key.strip():
        raise ValueError("API Key 不能为空")

    # 1. 加载 manifest（单/双 Skill 由 use_dual_skill 决定）
    if manifest_path.strip():
        m_path = Path(manifest_path)
    elif use_dual_skill:
        m_path = _DEFAULT_MANIFEST_PATH
    else:
        m_path = _DEFAULT_SINGLE_SKILL_MANIFEST_PATH
    manifest = load_manifest(m_path)

    # 2. 解析 Skill 目录
    s_root = resolve_skill_root(skill_root)
    primary_skill_id = manifest["skill_id"]
    adapter_skill_id = manifest.get("adapter_skill_id", "")

    primary_skill_dir = resolve_skill_directory(s_root, primary_skill_id)
    # 仅双 Skill 模式注入 adapter 目录；单 Skill manifest 无 adapter 字段
    adapter_skill_dir = (
        resolve_skill_directory(s_root, adapter_skill_id)
        if use_dual_skill and adapter_skill_id
        else None
    )

    # 3. 构建 runner_profile
    profile = _build_runner_profile(
        api_url=api_url,
        api_key=api_key,
        api_format=api_format,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        timeout_seconds=timeout_seconds,
    )

    # 4. 构建 user context
    feihou_context = _build_feihou_context(
        generation_mode=generation_mode,
        task_relation=task_relation,
        media_resources=media_resources or [],
        duration_seconds=duration_seconds,
        aspect_ratio=aspect_ratio,
        ref_image_short_edge=ref_image_short_edge,
    )
    merged_text = f"{user_prompt.strip()}\n\n{feihou_context}"

    # 5. 收集媒体路径
    image_paths: list[str] = []
    file_paths: list[str] = []
    for res in (media_resources or []):
        path = res.get("path", "")
        if not path:
            continue
        res_type = res.get("type", "")
        if res_type == "image":
            image_paths.append(path)
        elif res_type in {"video", "audio"}:
            file_paths.append(path)

    # 6. 准备 workspace
    ws_root = Path(workspace_root) if workspace_root.strip() else Path(profile["workspace_root"])

    # 7. 执行 ACP session（渲染前由 execute_text_session 注入 adapter 目录）
    result = execute_text_session(
        workspace_root=ws_root,
        session_id=session_id,
        skill_root=s_root,
        skill_id=primary_skill_id,
        context_template=manifest["context_template"],
        user_text=merged_text,
        runner_profile=profile,
        image_inputs=image_paths,
        file_inputs=file_paths,
        adapter_skill_directory=str(adapter_skill_dir) if adapter_skill_dir else None,
    )

    # 9. 提取结果
    mapped = map_result_fields(result, manifest["result_mapping"])
    response_text = str(mapped.get("response_text", ""))

    if not response_text.strip():
        raise RuntimeError("ACP Agent 返回了空结果")

    return response_text
