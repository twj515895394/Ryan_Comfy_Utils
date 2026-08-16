"""cinematic_v1 六阶段注册表与 deliverables 合同。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


PIPELINE_ID = "cinematic_v1"

STAGE_STATUSES = (
    "NOT_STARTED",
    "DRAFT",
    "READY",
    "LOCKED",
    "STALE",
    "ERROR",
)


@dataclass(frozen=True, slots=True)
class DeliverableSpec:
    doc_key: str
    format: str  # "doc" | "items"
    required: bool = False

    def filename(self) -> str:
        if self.format == "items":
            return f"{self.doc_key}.items.md"
        return f"{self.doc_key}.md"


@dataclass(frozen=True, slots=True)
class StageSpec:
    stage_id: str
    display_name: str
    skill_id: str
    order: int
    depends_on: tuple[str, ...] = ()
    optional: bool = False
    deliverables: tuple[DeliverableSpec, ...] = ()
    slash_aliases: tuple[str, ...] = ()

    def required_deliverables(self) -> tuple[DeliverableSpec, ...]:
        return tuple(item for item in self.deliverables if item.required)


_STAGES: tuple[StageSpec, ...] = (
    StageSpec(
        stage_id="creative",
        display_name="创意策划",
        skill_id="creative-story-planner",
        order=10,
        deliverables=(
            DeliverableSpec("concept_image_prompts", "items", required=False),
        ),
        slash_aliases=("creative", "创意", "故事"),
    ),
    StageSpec(
        stage_id="production",
        display_name="美术/资产设计",
        skill_id="production-designer",
        order=20,
        depends_on=("creative",),
        deliverables=(
            DeliverableSpec("image_prompts", "items", required=True),
        ),
        slash_aliases=("production", "美术", "角色"),
    ),
    StageSpec(
        stage_id="script",
        display_name="剧本导演",
        skill_id="script-director",
        order=30,
        depends_on=("creative", "production"),
        deliverables=(),
        slash_aliases=("script", "剧本"),
    ),
    StageSpec(
        stage_id="storyboard",
        display_name="分镜导演",
        skill_id="storyboard-director",
        order=40,
        depends_on=("creative", "production", "script"),
        deliverables=(
            DeliverableSpec("shot_prompts", "items", required=True),
        ),
        slash_aliases=("storyboard", "分镜"),
    ),
    StageSpec(
        stage_id="audio",
        display_name="音频导演",
        skill_id="audio-director",
        order=50,
        depends_on=("script", "storyboard"),
        optional=True,
        deliverables=(
            DeliverableSpec("audio_prompts", "items", required=False),
        ),
        slash_aliases=("audio", "音频"),
    ),
    StageSpec(
        stage_id="video_prompt",
        display_name="视频提示词导演",
        skill_id="video-prompt-director",
        order=60,
        depends_on=("creative", "production", "script", "storyboard", "audio"),
        deliverables=(
            DeliverableSpec("shot_video_prompts", "items", required=True),
        ),
        slash_aliases=("video", "视频提示词", "video_prompt"),
    ),
)


@dataclass(frozen=True, slots=True)
class PipelineSpec:
    pipeline_id: str
    display_name: str
    stages: tuple[StageSpec, ...] = field(default_factory=tuple)

    def stage(self, stage_id: str) -> StageSpec:
        for item in self.stages:
            if item.stage_id == stage_id:
                return item
        raise KeyError(f"unknown stage_id: {stage_id}")

    def stage_ids(self) -> list[str]:
        return [item.stage_id for item in self.stages]

    def dependents_of(self, stage_id: str) -> list[str]:
        return [
            item.stage_id
            for item in self.stages
            if stage_id in item.depends_on
        ]

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "display_name": self.display_name,
            "stages": [
                {
                    "stage_id": s.stage_id,
                    "display_name": s.display_name,
                    "skill_id": s.skill_id,
                    "order": s.order,
                    "depends_on": list(s.depends_on),
                    "optional": s.optional,
                    "deliverables": [
                        {
                            "doc_key": d.doc_key,
                            "format": d.format,
                            "required": d.required,
                            "filename": d.filename(),
                        }
                        for d in s.deliverables
                    ],
                    "slash_aliases": list(s.slash_aliases),
                }
                for s in self.stages
            ],
        }


def load_pipeline(pipeline_id: str = PIPELINE_ID) -> PipelineSpec:
    if pipeline_id != PIPELINE_ID:
        raise KeyError(f"unknown pipeline_id: {pipeline_id}")
    return PipelineSpec(
        pipeline_id=PIPELINE_ID,
        display_name="AI影视创作",
        stages=_STAGES,
    )


def list_stage_skills(pipeline_id: str = PIPELINE_ID) -> list[dict[str, Any]]:
    pipeline = load_pipeline(pipeline_id)
    return [
        {
            "skill_id": stage.skill_id,
            "group": "stage",
            "stage_id": stage.stage_id,
            "order": stage.order,
            "display_name": stage.display_name,
            "slash_aliases": list(stage.slash_aliases),
            "promote_result": True,
        }
        for stage in pipeline.stages
    ]


__all__ = [
    "PIPELINE_ID",
    "STAGE_STATUSES",
    "DeliverableSpec",
    "StageSpec",
    "PipelineSpec",
    "load_pipeline",
    "list_stage_skills",
]
