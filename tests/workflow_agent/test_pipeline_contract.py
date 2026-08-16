import unittest

from ryan_comfy_utils.workflow_agent.artifacts import RyanArtifactBundle
from ryan_comfy_utils.workflow_agent.context_select import render_context_view
from ryan_comfy_utils.workflow_agent.models import RyanContext, RyanContextEntry

class TestWorkflowAgentPipelineContract(unittest.TestCase):
    """用最小六阶段数据验证依据与可连接 Prompt 的边界。"""

    def _entry(self, index, agent_uid, kind, artifact_type, title, summary, handoff, locks, outputs):
        return RyanContextEntry(
            entry_id=f"entry_{index:02d}",
            workflow_id="wf_pipeline",
            source_agent_uid=agent_uid,
            source_agent_name=title,
            skill_id=agent_uid,
            kind=kind,
            revision=1,
            title=title,
            summary=summary,
            content=f"# {title}\n\n{summary}\n\n下游交接：{handoff}",
            created_at=f"2026-08-12T10:0{index}:00Z",
            metadata={
                "artifact_bundle": {
                    "artifact_type": artifact_type,
                    "schema_version": 2,
                    "content": {"summary": summary, "handoff": handoff, "locks": locks},
                    "outputs": outputs,
                    "shots": [],
                }
            },
        )

    def _context(self):
        return RyanContext(
            workflow_id="wf_pipeline",
            entries=[
                self._entry(
                    1,
                    "agent_creative",
                    "creative.story",
                    "creative_story",
                    "创意策划",
                    "CHAR_001 的目标是守住夜市摊位。",
                    "交给美术与剧本，保留 CHAR_001 的动机。",
                    ["CHAR_001", "BEAT_001"],
                    [],
                ),
                self._entry(
                    2,
                    "agent_design",
                    "production.design",
                    "production_design",
                    "美术设计",
                    "CHAR_001 穿旧帆布围裙，夜市使用冷暖对撞灯光。",
                    "交给分镜，锁定角色识别与 SCENE_001 空间。",
                    ["CHAR_001", "SCENE_001"],
                    [
                        {
                            "output_id": "CHAR_001_REFERENCE",
                            "kind": "image_prompt",
                            "label": "CHAR_001 角色参考图",
                            "purpose": "character_sheet",
                            "target_ids": ["CHAR_001"],
                            "text": "中文角色参考图：正面、侧面、背面与三种表情，保留旧帆布围裙和红色围巾。",
                            "priority": 20,
                        }
                    ],
                ),
                self._entry(
                    3,
                    "agent_script",
                    "script.direction",
                    "script_direction",
                    "剧本导演",
                    "BEAT_001 在 SCENE_001 完成误会与反应。",
                    "交给分镜，保留 Blocking 与表演连续性。",
                    ["SCENE_001", "BEAT_001"],
                    [],
                ),
                self._entry(
                    4,
                    "agent_storyboard",
                    "storyboard.plan",
                    "storyboard_plan",
                    "分镜导演",
                    "SHOT_001 到 SHOT_002 组成 SEG_001，首尾状态连续。",
                    "交给音频与视频，保留 SHOT_001 的起始站位。",
                    ["SHOT_001", "SEG_001"],
                    [
                        {
                            "output_id": "SHOT_001_KEYFRAME",
                            "kind": "keyframe_prompt",
                            "label": "SHOT_001 首帧",
                            "purpose": "start_frame",
                            "target_ids": ["SHOT_001"],
                            "text": "中文关键帧 Prompt：CHAR_001 位于摊位左侧，镜头保留夜市纵深与冷暖灯光。",
                            "priority": 20,
                        }
                    ],
                ),
                self._entry(
                    5,
                    "agent_audio",
                    "audio.design",
                    "audio_design",
                    "音频导演",
                    "SEG_001 以短促拟音推动误会后的停顿。",
                    "交给视频，明确 BGM、Foley-SFX、Ambience、Silence。",
                    ["SEG_001"],
                    [
                        {
                            "output_id": "SEG_001_FOLEY",
                            "kind": "audio_prompt",
                            "label": "SEG_001 拟音",
                            "purpose": "foley",
                            "target_ids": ["SEG_001"],
                            "text": "中文音频 Prompt：帆布袋摩擦、金属夹轻响，误会揭示前留出半秒静默。",
                            "priority": 20,
                        }
                    ],
                ),
                self._entry(
                    6,
                    "agent_video",
                    "video.prompts",
                    "video_prompts",
                    "视频提示词导演",
                    "SEG_001 按 SHOT_001 的 Blocking 完成误会与反应。",
                    "交给视频生成节点，逐 Segment 执行，不改变首尾状态。",
                    ["SEG_001"],
                    [
                        {
                            "output_id": "SEG_001_VIDEO",
                            "kind": "video_prompt",
                            "label": "SEG_001 视频 Prompt",
                            "purpose": "segment_execution",
                            "target_ids": ["SEG_001"],
                            "text": "中文视频 Prompt：先保持站位，再完成递袋、停顿、抬眼反应；镜头轻微推进。audio_sync：帆布袋摩擦与金属夹轻响跟随递袋，误会揭示前保留半秒静默。",
                            "priority": 10,
                        },
                        {
                            "output_id": "SEG_002_VIDEO",
                            "kind": "video_prompt",
                            "label": "SEG_002 视频 Prompt",
                            "purpose": "segment_execution",
                            "target_ids": ["SEG_002"],
                            "text": "不应被 SEG_001 选择带出。",
                            "priority": 20,
                        },
                    ],
                ),
            ],
        )

    def test_summary_transmits_locks_and_handoff_but_not_prompt_text(self):
        result = render_context_view(self._context(), ["*"])
        self.assertIn("CHAR_001", result)
        self.assertIn("交给视频", result)
        self.assertNotIn("中文角色参考图：", result)
        self.assertNotIn("中文视频 Prompt：", result)

    def test_bundle_outputs_keep_target_ids_for_downstream_tools(self):
        context = self._context()
        production = next(e for e in context.entries if e.kind == "production.design")
        bundle = RyanArtifactBundle.from_dict(production.metadata["artifact_bundle"])
        image = next(o for o in bundle.outputs if "CHAR_001" in (o.target_ids or []))
        self.assertIn("角色参考图", image.text)
        video_entry = next(e for e in context.entries if e.kind == "video.prompts")
        video_bundle = RyanArtifactBundle.from_dict(video_entry.metadata["artifact_bundle"])
        video = next(o for o in video_bundle.outputs if "SEG_001" in (o.target_ids or []))
        self.assertIn("audio_sync", video.text)
        other = next(o for o in video_bundle.outputs if "SEG_002" in (o.target_ids or []))
        self.assertIn("不应被 SEG_001", other.text)

    def test_script_stage_has_no_connectable_prompt_outputs(self):
        context = self._context()
        script = next(e for e in context.entries if e.kind == "script.direction")
        bundle = RyanArtifactBundle.from_dict(script.metadata["artifact_bundle"])
        self.assertEqual(bundle.outputs, [])


if __name__ == "__main__":
    unittest.main()
