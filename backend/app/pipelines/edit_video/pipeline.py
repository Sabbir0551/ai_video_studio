import os
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.analysis import AnalysisReport, EditDecision
from backend.app.models.timeline import Timeline
from backend.app.analysis.analyzer import multimodal_analyzer
from backend.app.pipelines.edit_video.validator import cut_validator
from backend.app.pipelines.edit_video.compiler import edl_compiler
from backend.app.timeline.renderer import renderer, RenderQAResult


class AutoEditPipeline:
    """End-to-End pipeline: analyzes raw video, validates cuts, compiles timeline, and renders polished edit."""

    def __init__(self):
        self.analyzer = multimodal_analyzer
        self.validator = cut_validator
        self.compiler = edl_compiler
        self.renderer = renderer

    def edit(
        self,
        video_path: str,
        project_id: str = "edit_proj",
        language: str = "bn",
        goal: str = "talking_head_polish",
        aggressiveness: str = "balanced",
        target_aspect_ratio: str = "16:9",
        enable_punch_zooms: bool = True,
        add_captions: bool = True,
        add_music_bed: bool = True,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        t_start = time.time()
        logger.info(f"Starting Auto-Edit Pipeline for: {video_path} [goal={goal}, aspect={target_aspect_ratio}]")

        proj_dir = settings.data_dir / "projects" / project_id
        proj_dir.mkdir(parents=True, exist_ok=True)

        if not output_path:
            output_path = str(proj_dir / "renders" / f"{project_id}_edited.mp4")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # -------------------------------------------------------------
        # STAGE 1: Multimodal Video Analysis
        # -------------------------------------------------------------
        logger.info("Stage 1/4: Executing Multimodal Analysis...")
        report: AnalysisReport = self.analyzer.analyze(
            video_path=video_path,
            project_id=project_id,
            language=language,
            goal=goal
        )

        # -------------------------------------------------------------
        # STAGE 2: Cut Validation & Continuity Repair
        # -------------------------------------------------------------
        logger.info("Stage 2/4: Validating and repairing cuts against speech rules...")
        valid_cuts: List[EditDecision] = self.validator.validate_and_repair_cuts(
            report=report,
            aggressiveness=aggressiveness
        )

        # -------------------------------------------------------------
        # STAGE 3: EDL to Timeline Compilation
        # -------------------------------------------------------------
        logger.info("Stage 3/4: Compiling EDL to Canonical Timeline...")
        timeline: Timeline = self.compiler.compile(
            original_video_path=video_path,
            report=report,
            validated_cuts=valid_cuts,
            target_aspect_ratio=target_aspect_ratio,
            enable_punch_in_zooms=enable_punch_zooms,
            add_captions=add_captions,
            add_music_bed=add_music_bed
        )

        timeline_path = proj_dir / "timeline" / "timeline_edited.json"
        timeline_path.parent.mkdir(parents=True, exist_ok=True)
        with open(timeline_path, "w", encoding="utf-8") as f:
            f.write(timeline.model_dump_json(indent=2))

        # -------------------------------------------------------------
        # STAGE 4: Final Video Render & QA
        # -------------------------------------------------------------
        logger.info(f"Stage 4/4: Rendering edited video to: {output_path}...")
        qa_result: RenderQAResult = self.renderer.render(
            timeline=timeline,
            output_path=output_path,
            work_dir=str(proj_dir / "temp_render")
        )

        # -------------------------------------------------------------
        # Comparison & Summary
        # -------------------------------------------------------------
        orig_dur = report.duration_seconds
        edited_dur = qa_result.duration
        time_saved = max(0.0, orig_dur - edited_dur)
        percent_saved = (time_saved / orig_dur * 100) if orig_dur > 0 else 0.0

        comparison = {
            "original_duration": round(orig_dur, 2),
            "edited_duration": round(edited_dur, 2),
            "time_saved_seconds": round(time_saved, 2),
            "percent_saved": round(percent_saved, 1),
            "cuts_applied": len(valid_cuts),
            "original_lufs": report.audio.integrated_lufs,
            "edited_lufs": qa_result.integrated_lufs,
            "punch_zooms_enabled": enable_punch_zooms,
            "captions_burned": add_captions,
            "music_bed_added": add_music_bed
        }

        # Save summary JSON
        summary_path = proj_dir / "edit_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(comparison, indent=2))

        total_proc_time = time.time() - t_start
        logger.info(f"Auto-Edit completed in {total_proc_time:.2f}s! Time saved: {time_saved:.2f}s ({percent_saved:.1f}%)")

        return {
            "project_id": project_id,
            "original_video": video_path,
            "edited_video": output_path,
            "timeline_path": str(timeline_path),
            "comparison": comparison,
            "qa": qa_result.to_dict()
        }


auto_edit_pipeline = AutoEditPipeline()
