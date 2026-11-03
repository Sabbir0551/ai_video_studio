import os
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from backend.app.core.logging import logger
from backend.app.core.config import settings
from backend.app.core.db import db
from backend.app.models.job import Job, StageRecord, StageStatus
from backend.app.models.timeline import (
    Timeline,
    CanvasConfig,
    AudioConfig,
    Track,
    Clip,
    TrackType,
    CaptionItem,
    WordTimestamp,
    SidechainDucking,
    Transform,
    KenBurnsEffect
)
from backend.app.providers.base import LLMProvider, TTSProvider, ScriptResult
from backend.app.providers.llm.smart_script_engine import SmartScriptEngine
from backend.app.providers.llm.mock_llm_provider import MockLLMProvider
from backend.app.providers.tts.edge_tts_provider import EdgeTTSProvider
from backend.app.providers.tts.mock_tts_provider import MockTTSProvider
from backend.app.providers.image.base import ImageGenProvider
from backend.app.providers.image.generative_image_provider import GenerativeImageProvider
from backend.app.providers.image.mock_image_provider import MockImageGenProvider
from backend.app.providers.video_gen.base import VideoGenProvider
from backend.app.providers.video_gen.procedural_motion_provider import ProceduralMotionVideoProvider
from backend.app.providers.video_gen.manager import get_video_gen_provider
from backend.app.presets.manager import preset_manager
from backend.app.models.brand import BrandKit
from backend.app.core.cost_tracker import CostAndAttributionTracker, CostItem, AttributionRecord
from backend.app.media.thumbnail import thumbnail_generator
from backend.app.timeline.renderer import renderer, RenderQAResult


class CreateVideoPipeline:
    """End-to-End Pipeline converting text/topic into a fully rendered, broadcast-quality video."""

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        tts_provider: Optional[TTSProvider] = None,
        image_provider: Optional[ImageGenProvider] = None,
        video_gen_provider: Optional[VideoGenProvider] = None
    ):
        self.llm = llm_provider or SmartScriptEngine()
        self.tts = tts_provider or EdgeTTSProvider()
        self.image_gen = image_provider or GenerativeImageProvider()
        self.video_gen = video_gen_provider or ProceduralMotionVideoProvider()

    def run(
        self,
        project_id: str,
        topic_or_content: str,
        language: str = "bn",
        aspect_ratio: str = "16:9",
        preset_name: str = "clean_corporate",
        target_duration: float = 30.0,
        user_images: Optional[List[str]] = None,
        output_path: Optional[str] = None,
        brand_kit: Optional[BrandKit] = None,
        preview_mode: bool = False,
        generate_thumbnail: bool = True,
        enable_video_motion: bool = True,
        luma_api_key: Optional[str] = None,
        kling_api_key: Optional[str] = None,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute the end-to-end creation pipeline synchronously."""
        return asyncio.run(self.run_async(
            project_id=project_id,
            topic_or_content=topic_or_content,
            language=language,
            aspect_ratio=aspect_ratio,
            preset_name=preset_name,
            target_duration=target_duration,
            user_images=user_images,
            output_path=output_path,
            brand_kit=brand_kit,
            preview_mode=preview_mode,
            generate_thumbnail=generate_thumbnail,
            enable_video_motion=enable_video_motion,
            luma_api_key=luma_api_key,
            kling_api_key=kling_api_key,
            job_id=job_id
        ))

    async def run_async(
        self,
        project_id: str,
        topic_or_content: str,
        language: str = "bn",
        aspect_ratio: str = "16:9",
        preset_name: str = "clean_corporate",
        target_duration: float = 30.0,
        user_images: Optional[List[str]] = None,
        output_path: Optional[str] = None,
        brand_kit: Optional[BrandKit] = None,
        preview_mode: bool = False,
        generate_thumbnail: bool = True,
        enable_video_motion: bool = True,
        luma_api_key: Optional[str] = None,
        kling_api_key: Optional[str] = None,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        settings.init_directories()
        proj_dir = settings.data_dir / "projects" / project_id
        proj_dir.mkdir(parents=True, exist_ok=True)
        audio_dir = proj_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        img_dir = proj_dir / "images"
        img_dir.mkdir(parents=True, exist_ok=True)

        cost_tracker = CostAndAttributionTracker()
        preset = preset_manager.get_preset(preset_name)

        if not output_path:
            out_name = f"{project_id}_preview.mp4" if preview_mode else f"{project_id}_final.mp4"
            output_path = str(proj_dir / "renders" / out_name)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Starting Text-to-Video pipeline for '{project_id}' "
            f"[lang={language}, preset={preset.name}, aspect={aspect_ratio}, preview={preview_mode}]"
        )

        # -------------------------------------------------------------
        # STAGE 1: Script & Storyboard Generation
        # -------------------------------------------------------------
        t0 = time.time()
        logger.info("Stage 1/5: Generating script & storyboard...")
        script: ScriptResult = await self.llm.generate_script(
            topic_or_content=topic_or_content,
            language=language,
            target_duration=target_duration
        )
        cost_tracker.record_cost(CostItem(
            service="llm",
            provider=self.llm.name,
            units=script.estimated_word_count,
            unit_name="words",
            cost_usd=script.cost_usd
        ))
        logger.info(f"Script generated with {len(script.scenes)} scenes in {time.time()-t0:.2f}s")

        # In preview mode, restrict to first 3 scenes for ultra-fast iteration
        if preview_mode and len(script.scenes) > 3:
            logger.info("Preview mode active: restricting render to first 3 scenes for fast turnaround.")
            script.scenes = script.scenes[:3]

        # -------------------------------------------------------------
        # STAGE 2: Voiceover Synthesis (TTS) & Word-level Alignment
        # -------------------------------------------------------------
        t0 = time.time()
        logger.info(f"Stage 2/5: Synthesizing voiceover via {self.tts.name}...")
        scene_audio_results = []
        all_captions: List[CaptionItem] = []
        total_chars = 0

        current_timeline_time = 0.0
        for idx, scene in enumerate(script.scenes):
            scene_audio_path = str(audio_dir / f"scene_{idx+1:02d}.mp3")
            total_chars += len(scene.narration)
            tts_res = await self.tts.synthesize(
                text=scene.narration,
                output_path=scene_audio_path,
                language=language,
                content_hint=topic_or_content
            )
            scene_audio_results.append((scene_audio_path, tts_res.duration_seconds))

            # Build caption item for this scene with adjusted timeline offsets
            scene_start = current_timeline_time
            scene_end = current_timeline_time + tts_res.duration_seconds

            adjusted_words = []
            for w in tts_res.word_timestamps:
                adjusted_words.append(WordTimestamp(
                    word=w.word,
                    start=round(scene_start + w.start, 3),
                    end=round(scene_start + w.end, 3)
                ))

            all_captions.append(CaptionItem(
                id=f"cap_scene_{idx+1}",
                start=round(scene_start, 3),
                end=round(scene_end, 3),
                text=scene.narration,
                words=adjusted_words,
                style="tiktok_highlight" if preset.caption.highlight_active_word else "classic"
            ))
            current_timeline_time = scene_end

        total_audio_duration = current_timeline_time
        cost_tracker.record_cost(CostItem(
            service="tts",
            provider=self.tts.name,
            units=total_chars,
            unit_name="characters",
            cost_usd=0.0
        ))
        logger.info(f"Synthesized voiceover across {len(script.scenes)} scenes (total: {total_audio_duration:.2f}s) in {time.time()-t0:.2f}s")

        # -------------------------------------------------------------
        # STAGE 3: Visual Sourcing & Generation
        # -------------------------------------------------------------
        logger.info("Stage 3/5: Sourcing scene visuals...")
        chosen_visuals = []
        user_imgs = [p for p in (user_images or []) if os.path.exists(p)]
        width, height = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)

        for idx, scene in enumerate(script.scenes):
            if idx < len(user_imgs):
                chosen_visuals.append(user_imgs[idx])
                cost_tracker.record_attribution(AttributionRecord(
                    asset_name=Path(user_imgs[idx]).name,
                    asset_type="image",
                    source_url_or_provider="User Upload",
                    license_type="Proprietary User Asset",
                    attribution_text="Supplied by creator."
                ))
            else:
                sc_img_path = str(img_dir / f"scene_{idx+1:02d}_visual.png")
                gen_res = await self.image_gen.generate_or_source_image(
                    query_or_prompt=scene.visual_intent,
                    output_path=sc_img_path,
                    width=width,
                    height=height,
                    scene_number=idx + 1
                )

                if enable_video_motion:
                    motion_vid_path = str(img_dir / f"scene_{idx+1:02d}_motion.mp4")
                    scene_dur = scene_audio_results[idx][1] if idx < len(scene_audio_results) else 5.0
                    video_provider = get_video_gen_provider(
                        luma_api_key=luma_api_key,
                        kling_api_key=kling_api_key
                    )
                    motion_res = await video_provider.animate_image_to_video(
                        image_path=gen_res.image_path,
                        motion_prompt=scene.visual_intent,
                        duration=max(3.0, scene_dur),
                        output_path=motion_vid_path,
                        aspect_ratio=aspect_ratio,
                        width=width,
                        height=height
                    )
                    chosen_visuals.append(motion_res.video_path)
                    cost_tracker.record_cost(CostItem(
                        service="video_gen",
                        provider=motion_res.provider_name,
                        units=round(motion_res.duration_seconds, 1),
                        unit_name="seconds",
                        cost_usd=motion_res.cost_usd
                    ))
                else:
                    chosen_visuals.append(gen_res.image_path)

                cost_tracker.record_attribution(AttributionRecord(
                    asset_name=f"Scene {idx+1} Graphic",
                    asset_type="video" if enable_video_motion else "image",
                    source_url_or_provider=gen_res.provider_name,
                    license_type=gen_res.license_type,
                    attribution_text=gen_res.attribution or ""
                ))

        # -------------------------------------------------------------
        # STAGE 4: Timeline Compilation
        # -------------------------------------------------------------
        logger.info("Stage 4/5: Compiling Canonical Timeline with preset styling...")

        # Build Visual Track
        visual_clips = []
        scene_start_marker = 0.0
        for idx, (audio_p, dur) in enumerate(scene_audio_results):
            chosen_media = chosen_visuals[idx % len(chosen_visuals)]
            is_vid = any(chosen_media.lower().endswith(ext) for ext in [".mp4", ".mov", ".mkv"])
            kb = None
            if not is_vid and preset.visual.ken_burns_enabled:
                kb = KenBurnsEffect(
                    start_scale=1.0,
                    end_scale=1.08,
                    pan_x=0.02 if idx % 2 == 0 else -0.02
                )

            visual_clips.append(Clip(
                id=f"vis_clip_{idx+1}",
                source_path=chosen_media,
                source_in=0.0,
                source_out=dur,
                timeline_start=scene_start_marker,
                timeline_end=scene_start_marker + dur,
                transform=Transform(ken_burns=kb) if kb else None
            ))
            scene_start_marker += dur

        has_videos = any(c.source_path.lower().endswith((".mp4", ".mov", ".mkv")) for c in visual_clips)
        visual_track = Track(
            id="track_visual_main",
            name="Main Storyboard Visuals",
            track_type=TrackType.VIDEO if has_videos else TrackType.IMAGE,
            z_index=0,
            clips=visual_clips
        )

        # Build Voice Track
        voice_clips = []
        voice_start_marker = 0.0
        for idx, (audio_p, dur) in enumerate(scene_audio_results):
            voice_clips.append(Clip(
                id=f"voice_clip_{idx+1}",
                source_path=audio_p,
                source_in=0.0,
                source_out=dur,
                timeline_start=voice_start_marker,
                timeline_end=voice_start_marker + dur,
                volume=1.0
            ))
            voice_start_marker += dur

        voice_track = Track(
            id="track_voice_narration",
            name="Voiceover Narration",
            track_type=TrackType.VOICE,
            z_index=1,
            clips=voice_clips
        )

        # Build Background Music Track with Sidechain Ducking
        nursery_music = str(settings.assets_dir / "audio" / "nursery_music.mp3")
        ambient_music = str(settings.assets_dir / "audio" / "ambient_music.mp3")
        is_toddler_or_cartoon = any(w in topic_or_content.lower() for w in ["toddler", "cartoon", "baby", "children", "nursery", "kids", "buli", "lullaby"])
        music_file = nursery_music if (is_toddler_or_cartoon and os.path.exists(nursery_music)) else ambient_music
        music_track_clips = []
        if os.path.exists(music_file):
            music_track_clips.append(Clip(
                id="music_bed_01",
                source_path=music_file,
                source_in=0.0,
                source_out=total_audio_duration,
                timeline_start=0.0,
                timeline_end=total_audio_duration,
                volume=preset.audio.music_volume,
                sidechain_ducking=SidechainDucking(
                    source_track_id="track_voice_narration",
                    threshold_db=preset.audio.music_ducking_threshold_db,
                    reduction_db=preset.audio.music_ducking_reduction_db
                )
            ))

        music_track = Track(
            id="track_bg_music",
            name="Ambient Music Bed",
            track_type=TrackType.MUSIC,
            z_index=2,
            clips=music_track_clips
        )

        tracks_list = [visual_track, voice_track, music_track]

        # Add optional Transition SFX Track
        sfx_whoosh = str(settings.assets_dir / "audio" / "sfx" / "whoosh.mp3")
        if os.path.exists(sfx_whoosh) and len(script.scenes) > 1 and preset.name in ("short_hype", "news_flash"):
            sfx_clips = []
            cur_t = 0.0
            for idx, (audio_p, dur) in enumerate(scene_audio_results[:-1]):
                cur_t += dur
                sfx_clips.append(Clip(
                    id=f"sfx_whoosh_{idx+1}",
                    source_path=sfx_whoosh,
                    source_in=0.0,
                    source_out=0.4,
                    timeline_start=max(0.0, cur_t - 0.2),
                    timeline_end=cur_t + 0.2,
                    volume=0.5
                ))
            if sfx_clips:
                tracks_list.append(Track(
                    id="track_sfx",
                    name="Transition SFX",
                    track_type=TrackType.SFX,
                    z_index=3,
                    clips=sfx_clips
                ))

        timeline = Timeline(
            project_id=project_id,
            canvas=CanvasConfig(
                width=width,
                height=height,
                aspect_ratio=aspect_ratio,
                fps=preset.fps
            ),
            audio=AudioConfig(
                sample_rate=48000,
                channels=2,
                target_lufs=preset.audio.target_lufs,
                true_peak=preset.audio.true_peak
            ),
            tracks=tracks_list,
            captions=all_captions,
            metadata={
                "topic": topic_or_content,
                "language": language,
                "preset": preset.name,
                "script_title": script.title
            }
        )

        # Save compiled timeline JSON
        timeline_json_path = proj_dir / "timeline" / "timeline.json"
        timeline_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(timeline_json_path, "w", encoding="utf-8") as f:
            f.write(timeline.model_dump_json(indent=2))

        # -------------------------------------------------------------
        # STAGE 5: Rendering & Automated Post-Render QA
        # -------------------------------------------------------------
        logger.info(f"Stage 5/5: Rendering video to: {output_path}")
        qa_result: RenderQAResult = renderer.render(
            timeline=timeline,
            output_path=output_path,
            work_dir=str(proj_dir / "temp_render"),
            brand_kit=brand_kit,
            preview_mode=preview_mode
        )

        # -------------------------------------------------------------
        # POST-PROCESSING: Thumbnail, SEO Metadata, Credits & Attributions
        # -------------------------------------------------------------
        thumb_path = None
        seo_meta = None
        if generate_thumbnail and os.path.exists(output_path):
            thumb_path = str(proj_dir / "renders" / f"{project_id}_thumb.jpg")
            thumbnail_generator.generate_thumbnail(
                video_path=output_path,
                title_text=script.title,
                output_image_path=thumb_path,
                timestamp_seconds=min(1.0, total_audio_duration * 0.25)
            )
            seo_meta = thumbnail_generator.generate_seo_metadata(
                timeline=timeline,
                topic=topic_or_content,
                language=language
            )

        credits_path = str(proj_dir / "credits.txt")
        cost_tracker.export_credits_file(credits_path)

        return {
            "project_id": project_id,
            "script": script.model_dump(),
            "timeline_path": str(timeline_json_path),
            "output_path": output_path,
            "thumbnail_path": thumb_path,
            "seo_metadata": seo_meta,
            "credits_path": credits_path,
            "total_cost_usd": cost_tracker.total_cost_usd(),
            "qa": qa_result.to_dict()
        }


create_video_pipeline = CreateVideoPipeline()
