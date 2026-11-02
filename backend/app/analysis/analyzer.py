import os
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.analysis import AnalysisReport, EditDecision, EditOperationType
from backend.app.analysis.ingest import video_ingestor, IngestResult
from backend.app.analysis.speech_analyzer import speech_analyzer
from backend.app.analysis.audio_analyzer import audio_quality_analyzer
from backend.app.analysis.visual_analyzer import visual_scene_analyzer
from backend.app.providers.asr.base import ASRProvider
from backend.app.providers.asr.mock_asr_provider import MockASRProvider


class MultimodalVideoAnalyzer:
    """End-to-End Multimodal Video Analyzer synthesizing Speech, Vision, and Audio into an AnalysisReport."""

    def __init__(self, asr_provider: Optional[ASRProvider] = None):
        self.asr = asr_provider or MockASRProvider()
        self.ingestor = video_ingestor
        self.speech_analyzer = speech_analyzer
        self.audio_analyzer = audio_quality_analyzer
        self.visual_analyzer = visual_scene_analyzer

    def analyze(
        self,
        video_path: str,
        project_id: str = "analyze_proj",
        language: str = "bn",
        goal: str = "talking_head_polish"
    ) -> AnalysisReport:
        return asyncio.run(self.analyze_async(
            video_path=video_path,
            project_id=project_id,
            language=language,
            goal=goal
        ))

    async def analyze_async(
        self,
        video_path: str,
        project_id: str = "analyze_proj",
        language: str = "bn",
        goal: str = "talking_head_polish"
    ) -> AnalysisReport:
        t_start = time.time()
        logger.info(f"Initiating Multimodal Analysis for '{video_path}' [goal={goal}]")

        work_dir = settings.data_dir / "projects" / project_id / "analysis"
        work_dir.mkdir(parents=True, exist_ok=True)
        keyframes_dir = str(work_dir / "keyframes")

        # 1. Ingestion and Proxy Normalization
        ingest_res: IngestResult = self.ingestor.ingest(video_path, str(work_dir))

        # 2. Audio Quality Analysis (Silences, LUFS, Clipping)
        audio_stats = self.audio_analyzer.analyze_audio(ingest_res.audio_wav_path)

        # 3. Speech Transcription & Word Analysis
        asr_res = await self.asr.transcribe(ingest_res.audio_wav_path, language=language)
        detailed_words, speech_edits, wpm = self.speech_analyzer.analyze_words(
            words=asr_res.words,
            language=language
        )

        # 4. Visual Structure (Shot Boundaries, Keyframes, Quality)
        shots = self.visual_analyzer.analyze_scenes(
            video_path=ingest_res.proxy_video_path,
            keyframes_dir=keyframes_dir,
            fps=ingest_res.fps,
            total_duration=ingest_res.duration
        )

        # 5. Synthesize Suggested Edits and Punch-in Zooms
        all_edits: List[EditDecision] = []
        all_edits.extend(speech_edits)

        # Add Punch-in Zooms (112% crop) after each cut to smooth jump cuts
        sorted_cuts = sorted(all_edits, key=lambda x: x.start_time)
        zoom_state = False
        for idx, cut in enumerate(sorted_cuts):
            zoom_state = not zoom_state
            if zoom_state:
                all_edits.append(EditDecision(
                    id=f"edit_zoom_{idx+1}",
                    operation=EditOperationType.PUNCH_IN_ZOOM,
                    start_time=cut.end_time,
                    end_time=cut.end_time + 4.0, # Hold zoom for 4 seconds
                    reason="Subtle 112% punch-in zoom to seamlessly hide jump cut",
                    confidence=0.90,
                    accepted=True,
                    extra_params={"scale": 1.12}
                ))

        # 6. Calculate Savings & Build Summary
        total_cut_duration = sum((e.end_time - e.start_time) for e in all_edits if "cut" in e.operation.value)
        estimated_new_duration = max(1.0, ingest_res.duration - total_cut_duration)

        summary = (
            f"Video Analysis Summary:\n"
            f" • Original Duration: {ingest_res.duration:.2f}s | Resolution: {ingest_res.width}x{ingest_res.height}\n"
            f" • Speaking Pace: {wpm} words/min across {len(detailed_words)} words\n"
            f" • Detected Issues: {len([w for w in detailed_words if w.is_filler])} filler words, "
            f"{len(audio_stats.silence_segments)} dead silences\n"
            f" • Audio Loudness: {audio_stats.integrated_lufs} LUFS (Target: -14.0 LUFS)\n"
            f" • Visual Shots: {len(shots)} scene boundaries identified\n"
            f" • Edit Rationale: Removing silences & fillers will save ~{total_cut_duration:.2f}s "
            f"(new estimated duration: {estimated_new_duration:.2f}s)."
        )

        report = AnalysisReport(
            video_path=video_path,
            duration_seconds=ingest_res.duration,
            width=ingest_res.width,
            height=ingest_res.height,
            fps=ingest_res.fps,
            language=language,
            transcript_text=asr_res.transcript_text,
            words=detailed_words,
            shots=shots,
            audio=audio_stats,
            summary=summary,
            suggested_edits=all_edits
        )

        # 7. Save JSON Report and Human-Readable Markdown
        report_json_path = work_dir / "analysis_report.json"
        with open(report_json_path, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))

        summary_md_path = work_dir / "analysis_summary.md"
        with open(summary_md_path, "w", encoding="utf-8") as f:
            f.write(f"# Analysis Report: {Path(video_path).name}\n\n{summary}\n\n## Transcript\n> {asr_res.transcript_text}\n")

        logger.info(f"Analysis completed in {time.time()-t_start:.2f}s. Report saved to: {report_json_path}")
        return report


multimodal_analyzer = MultimodalVideoAnalyzer()
