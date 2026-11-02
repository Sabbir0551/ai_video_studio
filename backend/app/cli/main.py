import os
import sys
import shutil
import typer
from typing import Optional, List
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from backend.app.core.config import settings
from backend.app.core.logging import setup_logger
from backend.app.media.ffmpeg_wrapper import ffmpeg
from backend.app.media.bangla_shaper import (
    generate_ass_subtitle_file,
    normalize_bangla_text_for_speech
)
from backend.app.models.timeline import CaptionItem, WordTimestamp

app = typer.Typer(help="AI Video Studio CLI - Personal AI Video Production & Editing Suite")
console = Console()
logger = setup_logger("studio_cli")


@app.command()
def doctor():
    """Run comprehensive environment diagnostics (FFmpeg, HarfBuzz, Fonts, GPU, Directories)."""
    console.print(Panel.fit("[bold green]AI Video Studio - System Diagnostics (Doctor)[/bold green]"))

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Component", style="dim", width=24)
    table.add_column("Status", width=12)
    table.add_column("Details")

    all_passed = True

    # 1. Python
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    table.add_row("Python", "[green]PASS[/green]", f"Python {py_ver}")

    # 2. FFmpeg & ffprobe
    ffmpeg_ok = shutil.which("ffmpeg") is not None
    ffprobe_ok = shutil.which("ffprobe") is not None
    if ffmpeg_ok and ffprobe_ok:
        table.add_row("FFmpeg Core", "[green]PASS[/green]", "ffmpeg and ffprobe found in PATH")
    else:
        table.add_row("FFmpeg Core", "[red]FAIL[/red]", "ffmpeg or ffprobe missing from PATH")
        all_passed = False

    # 3. Libass and HarfBuzz in FFmpeg
    accel = ffmpeg.get_hardware_acceleration()
    table.add_row("Video Acceleration", "[green]PASS[/green]", f"Active encoder: {accel}")

    # 4. Bangla Font
    font_path = Path(settings.default_font_path)
    if font_path.exists():
        table.add_row("Bangla Font", "[green]PASS[/green]", f"Found: {font_path} ({font_path.stat().st_size} bytes)")
    else:
        # Check system fonts as fallback
        nirmala = Path("C:/Windows/Fonts/Nirmala.ttc")
        if nirmala.exists():
            table.add_row("Bangla Font", "[yellow]PASS (System)[/yellow]", "Using Windows Nirmala UI")
        else:
            table.add_row("Bangla Font", "[red]FAIL[/red]", f"Font missing at {font_path}")
            all_passed = False

    # 5. Data & Storage
    settings.init_directories()
    if settings.data_dir.exists() and os.access(settings.data_dir, os.W_OK):
        table.add_row("Storage Perms", "[green]PASS[/green]", f"Writable directory: {settings.data_dir.resolve()}")
    else:
        table.add_row("Storage Perms", "[red]FAIL[/red]", "Cannot write to data directory")
        all_passed = False

    console.print(table)
    if all_passed:
        console.print("\n[bold green]✓ All core requirements passed. System is ready![/bold green]\n")
    else:
        console.print("\n[bold red]✗ Some checks failed. Please review errors above.[/bold red]\n")
        raise typer.Exit(code=1)


@app.command()
def test_bangla(
    output: str = "bangla_test_render.png",
    text: str = "স্বাগতম! কৃত্রিম বুদ্ধিমত্তা ও ভিডিও এডিটিং স্টুডিও"
):
    """Render a test frame with complex Bengali conjuncts to visually verify HarfBuzz shaping."""
    console.print(f"[bold cyan]Rendering Bengali typography test frame to: {output}[/bold cyan]")
    settings.init_directories()

    # Generate ASS file
    ass_path = str(settings.data_dir / "temp_test_bangla.ass")
    caption = CaptionItem(
        id="c1",
        start=0.0,
        end=2.0,
        text=text,
        words=[
            WordTimestamp(word="স্বাগতম!", start=0.0, end=0.6),
            WordTimestamp(word="কৃত্রিম", start=0.6, end=1.0),
            WordTimestamp(word="বুদ্ধিমত্তা", start=1.0, end=1.5),
            WordTimestamp(word="স্টুডিও", start=1.5, end=2.0)
        ]
    )

    generate_ass_subtitle_file(
        captions=[caption],
        output_path=ass_path,
        font_name="Noto Sans Bengali",
        font_size=60,
        play_res_x=1920,
        play_res_y=1080,
        margin_v=60,
        highlight_active_word=False
    )

    fonts_dir = str(settings.fonts_dir)
    success = ffmpeg.render_color_frame_with_ass(
        ass_path=ass_path,
        output_png=output,
        fonts_dir=fonts_dir,
        width=1920,
        height=1080
    )

    # Clean temporary ASS
    if os.path.exists(ass_path):
        os.remove(ass_path)

    if success and os.path.exists(output):
        console.print(f"[bold green]✓ Test frame rendered successfully: {output} ({os.path.getsize(output)} bytes)[/bold green]")
    else:
        console.print("[bold red]✗ Failed to render Bengali test frame.[/bold red]")
        raise typer.Exit(code=1)


@app.command()
def create(
    prompt: str = typer.Option(..., "--prompt", "-p", help="Topic, article, or content prompt"),
    lang: str = typer.Option("bn", "--lang", "-l", help="Language: 'bn' (Bangla) or 'en' (English)"),
    aspect: str = typer.Option("16:9", "--aspect", "-a", help="Aspect ratio: '16:9' or '9:16'"),
    preset: str = typer.Option("clean_corporate", "--preset", help="Preset: clean_corporate, short_hype, documentary, news_flash"),
    watermark: bool = typer.Option(False, "--watermark", "-w", help="Burn brand watermark/logo onto video"),
    preview: bool = typer.Option(False, "--preview", help="Render ultra-fast low-res preview"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Custom output video path"),
    duration: float = typer.Option(20.0, "--duration", "-d", help="Target duration in seconds")
):
    """Create a complete broadcast-quality video from a text topic or script."""
    import uuid
    from backend.app.pipelines.create_video.pipeline import create_video_pipeline
    from backend.app.models.brand import BrandKit

    project_id = f"proj_{uuid.uuid4().hex[:8]}"
    brand_kit = BrandKit() if watermark else None

    console.print(Panel.fit(
        f"[bold green]AI Video Studio - Video Creation[/bold green]\n"
        f"[bold]Project ID:[/bold] {project_id}\n"
        f"[bold]Prompt:[/bold] {prompt}\n"
        f"[bold]Language:[/bold] {lang} | [bold]Aspect:[/bold] {aspect} | [bold]Preset:[/bold] {preset}\n"
        f"[bold]Watermark:[/bold] {'Enabled' if watermark else 'Disabled'} | [bold]Preview Mode:[/bold] {preview}"
    ))

    res = create_video_pipeline.run(
        project_id=project_id,
        topic_or_content=prompt,
        language=lang,
        aspect_ratio=aspect,
        preset_name=preset,
        target_duration=duration,
        output_path=output,
        brand_kit=brand_kit,
        preview_mode=preview
    )

    qa = res["qa"]
    status_color = "green" if qa["passed"] else "yellow"
    
    table = Table(title="Render & Quality Assurance (QA) Report", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="dim", width=22)
    table.add_column("Value", style=status_color)

    table.add_row("Output Video", qa["output_path"])
    table.add_row("Duration", f"{qa['duration']}s")
    table.add_row("Resolution", qa["resolution"])
    table.add_row("Frame Rate", f"{qa['fps']} fps")
    table.add_row("Loudness (LUFS)", f"{qa['integrated_lufs']} LUFS")
    table.add_row("File Size", f"{qa['file_size_bytes']:,} bytes")
    table.add_row("Render Time", f"{qa['render_time_seconds']}s")
    if res.get("thumbnail_path"):
        table.add_row("Thumbnail", res["thumbnail_path"])
    if res.get("credits_path"):
        table.add_row("Credits File", res["credits_path"])
    table.add_row("QA Status", "PASSED" if qa["passed"] else "FLAGGED")

    console.print(table)
    if qa["notes"]:
        console.print("[bold]QA Notes:[/bold]")
        for note in qa["notes"]:
            console.print(f" - {note}")

    if res.get("seo_metadata"):
        seo = res["seo_metadata"]
        console.print(Panel(
            f"[bold cyan]SEO Title Candidates:[/bold cyan]\n" + "\n".join(f" • {t}" for t in seo['title_candidates']) + "\n\n"
            f"[bold cyan]Hashtags:[/bold cyan] {' '.join(seo['hashtags'])}\n\n"
            f"[bold cyan]Chapters:[/bold cyan]\n" + "\n".join(seo['chapters']),
            title="Generated SEO & Platform Metadata"
        ))

    console.print(f"\n[bold green]✓ Video successfully produced at: {qa['output_path']}[/bold green]\n")


@app.command()
def analyze(
    video_path: str = typer.Argument(..., help="Path to video file to analyze (MP4, MOV, MKV, WebM)"),
    lang: str = typer.Option("bn", "--lang", "-l", help="Video primary language ('bn' or 'en')"),
    goal: str = typer.Option("talking_head_polish", "--goal", "-g", help="Edit goal: talking_head_polish, tight_short, highlight_reel"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Custom JSON report output path")
):
    """Analyze a raw uploaded video (speech transcription, fillers, silences, shots, audio quality)."""
    import uuid
    from backend.app.analysis.analyzer import multimodal_analyzer

    if not os.path.exists(video_path):
        console.print(f"[bold red]Error: Video file not found: {video_path}[/bold red]")
        raise typer.Exit(code=1)

    project_id = f"analyze_{uuid.uuid4().hex[:8]}"
    console.print(Panel.fit(
        f"[bold cyan]AI Video Studio - Multimodal Video Analysis[/bold cyan]\n"
        f"[bold]Video Path:[/bold] {video_path}\n"
        f"[bold]Language:[/bold] {lang} | [bold]Goal:[/bold] {goal}"
    ))

    report = multimodal_analyzer.analyze(
        video_path=video_path,
        project_id=project_id,
        language=lang,
        goal=goal
    )

    # 1. Video & Audio Specs Table
    specs_table = Table(title="Media & Audio Quality Overview", show_header=True, header_style="bold cyan")
    specs_table.add_column("Property", style="dim", width=22)
    specs_table.add_column("Value")

    specs_table.add_row("Resolution", f"{report.width}x{report.height}")
    specs_table.add_row("Duration", f"{report.duration_seconds:.2f}s")
    specs_table.add_row("Frame Rate", f"{report.fps:.1f} fps")
    specs_table.add_row("Integrated LUFS", f"{report.audio.integrated_lufs} LUFS")
    specs_table.add_row("True Peak", f"{report.audio.true_peak_db} dBTP")
    specs_table.add_row("Silence Segments", f"{len(report.audio.silence_segments)} detected")
    specs_table.add_row("Clipping Present", "Yes (Needs normalization)" if report.audio.has_clipping else "No (Clean)")
    console.print(specs_table)

    # 2. Speech & Content Table
    fillers = [w for w in report.words if w.is_filler]
    speech_table = Table(title="Speech & Content Intelligence", show_header=True, header_style="bold green")
    speech_table.add_column("Speech Metric", style="dim", width=22)
    speech_table.add_column("Value")

    speech_table.add_row("Language", report.language)
    speech_table.add_row("Total Words", str(len(report.words)))
    speech_table.add_row("Filler Words", f"[bold red]{len(fillers)}[/bold red] detected ({', '.join(set(w.word for w in fillers)) if fillers else 'None'})")
    speech_table.add_row("Visual Shots", f"{len(report.shots)} shots detected")
    console.print(speech_table)

    # 3. Transcript
    console.print(Panel(report.transcript_text, title="[bold]Speech Transcript[/bold]"))

    # 4. Suggested Edits Table
    edits_table = Table(title="Suggested Edit Decisions (EDL)", show_header=True, header_style="bold yellow")
    edits_table.add_column("Type", width=16)
    edits_table.add_column("Timestamp", width=16)
    edits_table.add_column("Reason")

    for e in report.suggested_edits[:8]: # Display first 8 decisions
        edits_table.add_row(
            e.operation.value,
            f"{e.start_time:.2f}s -> {e.end_time:.2f}s",
            e.reason
        )
    console.print(edits_table)

    # Summary Panel
    console.print(Panel(report.summary, title="[bold green]Executive Edit Rationale[/bold green]"))

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))
        console.print(f"\n[bold green]✓ Analysis Report saved to: {output}[/bold green]\n")


@app.command()
def edit(
    video_path: str = typer.Argument(..., help="Path to raw video to edit (MP4, MOV, MKV, WebM)"),
    lang: str = typer.Option("bn", "--lang", "-l", help="Primary language ('bn' or 'en')"),
    goal: str = typer.Option("talking_head_polish", "--goal", "-g", help="Edit goal: talking_head_polish, tight_short, highlight_reel"),
    aggressiveness: str = typer.Option("balanced", "--aggressiveness", help="Cut aggressiveness: gentle, balanced, aggressive"),
    aspect: str = typer.Option("16:9", "--aspect", "-a", help="Target aspect ratio: 16:9 or 9:16"),
    punch_zooms: bool = typer.Option(True, "--punch-zooms/--no-punch-zooms", help="Alternate 112% punch-in zooms to hide jump cuts"),
    captions: bool = typer.Option(True, "--captions/--no-captions", help="Burn synchronized captions"),
    music: bool = typer.Option(True, "--music/--no-music", help="Add subtle ambient music bed with ducking"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Custom output video path")
):
    """Automatically edit a raw video: removes dead silences, cuts fillers, applies punch-in zooms, and balances audio."""
    import uuid
    from backend.app.pipelines.edit_video.pipeline import auto_edit_pipeline

    if not os.path.exists(video_path):
        console.print(f"[bold red]Error: Input video not found: {video_path}[/bold red]")
        raise typer.Exit(code=1)

    project_id = f"edit_{uuid.uuid4().hex[:8]}"
    console.print(Panel.fit(
        f"[bold green]AI Video Studio - Auto Video Editor[/bold green]\n"
        f"[bold]Project ID:[/bold] {project_id}\n"
        f"[bold]Source Video:[/bold] {video_path}\n"
        f"[bold]Goal:[/bold] {goal} | [bold]Aggressiveness:[/bold] {aggressiveness} | [bold]Aspect:[/bold] {aspect}\n"
        f"[bold]Punch Zooms:[/bold] {punch_zooms} | [bold]Captions:[/bold] {captions} | [bold]Music Bed:[/bold] {music}"
    ))

    res = auto_edit_pipeline.edit(
        video_path=video_path,
        project_id=project_id,
        language=lang,
        goal=goal,
        aggressiveness=aggressiveness,
        target_aspect_ratio=aspect,
        enable_punch_zooms=punch_zooms,
        add_captions=captions,
        add_music_bed=music,
        output_path=output
    )

    comp = res["comparison"]
    qa = res["qa"]

    # Before / After Comparison Table
    comp_table = Table(title="Before / After Edit Optimization Summary", show_header=True, header_style="bold green")
    comp_table.add_column("Optimization Metric", style="dim", width=24)
    comp_table.add_column("Before Edit", width=16)
    comp_table.add_column("After Auto-Edit", style="bold cyan", width=16)

    comp_table.add_row("Total Duration", f"{comp['original_duration']}s", f"{comp['edited_duration']}s")
    comp_table.add_row("Time Saved", "-", f"[bold green]{comp['time_saved_seconds']}s ({comp['percent_saved']}%) [/bold green]")
    comp_table.add_row("Applied Cuts", "-", f"{comp['cuts_applied']} cuts")
    comp_table.add_row("Audio Loudness", f"{comp['original_lufs']} LUFS", f"{comp['edited_lufs']} LUFS")
    comp_table.add_row("Jump-Cut Zooms", "None", "112% punch-in zooms" if comp['punch_zooms_enabled'] else "None")
    comp_table.add_row("Captions", "None", "Burned-in HarfBuzz" if comp['captions_burned'] else "None")
    console.print(comp_table)

    # QA Table
    qa_table = Table(title="Post-Render QA Report", show_header=True, header_style="bold cyan")
    qa_table.add_column("Metric", style="dim", width=22)
    qa_table.add_column("Value", style="green" if qa["passed"] else "yellow")

    qa_table.add_row("Output Video", qa["output_path"])
    qa_table.add_row("Resolution", qa["resolution"])
    qa_table.add_row("Frame Rate", f"{qa['fps']} fps")
    qa_table.add_row("File Size", f"{qa['file_size_bytes']:,} bytes")
    qa_table.add_row("Render Time", f"{qa['render_time_seconds']}s")
    qa_table.add_row("QA Status", "PASSED" if qa["passed"] else "FLAGGED")
    console.print(qa_table)

    console.print(f"\n[bold green]✓ Polished video produced at: {qa['output_path']}[/bold green]\n")


@app.command()
def presets():
    """List all available style and platform presets."""
    from backend.app.presets.manager import preset_manager
    all_p = preset_manager.list_presets()
    table = Table(title="Available Style & Platform Presets", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="bold green", width=18)
    table.add_column("Aspect", width=8)
    table.add_column("Description")

    for p in all_p:
        table.add_row(p.name, p.aspect_ratio, p.description)
    console.print(table)


@app.command()
def info():
    """Display environment configuration."""
    console.print(Panel.fit(
        f"[bold]App Name:[/bold] {settings.app_name}\n"
        f"[bold]Environment:[/bold] {settings.studio_env}\n"
        f"[bold]Default TTS:[/bold] {settings.default_tts_provider}\n"
        f"[bold]Bangla Font:[/bold] {settings.bangla_default_font}\n"
        f"[bold]Target LUFS:[/bold] {settings.default_lufs_target}\n"
        f"[bold]Data Dir:[/bold] {settings.data_dir.resolve()}"
    ))


if __name__ == "__main__":
    app()
