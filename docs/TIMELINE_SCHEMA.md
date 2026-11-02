# Timeline JSON Schema Specification

The `Timeline` schema is the single source of truth between the AI decision generators and the media composition engine.

## Schema Architecture

```
Timeline
├── canvas: Resolution, Aspect Ratio, Frame Rate
├── audio: Sample Rate, Channels, Target LUFS, True Peak
├── tracks: Array of Track
│   ├── track_type: video | image | voice | music | sfx | captions | overlays
│   └── clips: Array of Clip
│       ├── id: string
│       ├── source_path: string
│       ├── source_in: float (seconds)
│       ├── source_out: float (seconds)
│       ├── timeline_start: float (seconds)
│       ├── timeline_end: float (seconds)
│       ├── speed: float
│       ├── volume: float
│       ├── transform: Crop, Scale, Position, KenBurns
│       ├── transition_in: Dissolve, Wipe, Slide, Fade, Cut
│       └── transition_out: Dissolve, Wipe, Slide, Fade, Cut
├── captions: Array of CaptionItem (word-level or line-level)
└── metadata: Project ID, Render Preset, Creation Timestamp
```

## Sample JSON Instance

```json
{
  "version": "1.0",
  "project_id": "proj_demo_01",
  "canvas": {
    "width": 1920,
    "height": 1080,
    "aspect_ratio": "16:9",
    "fps": 30
  },
  "audio": {
    "sample_rate": 48000,
    "channels": 2,
    "target_lufs": -14.0,
    "true_peak": -1.0
  },
  "tracks": [
    {
      "id": "track_video_main",
      "name": "Main Visuals",
      "track_type": "image",
      "z_index": 0,
      "clips": [
        {
          "id": "clip_01",
          "source_path": "assets/sample_scene.jpg",
          "source_in": 0.0,
          "source_out": 4.5,
          "timeline_start": 0.0,
          "timeline_end": 4.5,
          "transform": {
            "ken_burns": {
              "start_scale": 1.0,
              "end_scale": 1.08,
              "pan_x": 0.02,
              "pan_y": 0.0
            }
          },
          "transition_out": {
            "type": "fade",
            "duration": 0.5
          }
        }
      ]
    },
    {
      "id": "track_voice_narration",
      "name": "Narration Voice",
      "track_type": "voice",
      "z_index": 1,
      "clips": [
        {
          "id": "clip_voice_01",
          "source_path": "data/projects/proj_demo_01/audio/scene_01.mp3",
          "source_in": 0.0,
          "source_out": 4.5,
          "timeline_start": 0.0,
          "timeline_end": 4.5,
          "volume": 1.0
        }
      ]
    },
    {
      "id": "track_bg_music",
      "name": "Background Music",
      "track_type": "music",
      "z_index": 2,
      "clips": [
        {
          "id": "clip_music_01",
          "source_path": "assets/audio/ambient_track.mp3",
          "source_in": 0.0,
          "source_out": 4.5,
          "timeline_start": 0.0,
          "timeline_end": 4.5,
          "volume": 0.15,
          "sidechain_ducking": {
            "source_track_id": "track_voice_narration",
            "threshold_db": -24.0,
            "reduction_db": -12.0,
            "attack_ms": 20.0,
            "release_ms": 300.0
          }
        }
      ]
    }
  ],
  "captions": [
    {
      "id": "cap_01",
      "start": 0.2,
      "end": 2.1,
      "text": "স্বাগতম আমাদের ভিডিও স্টুডিওতে",
      "words": [
        {"word": "স্বাগতম", "start": 0.2, "end": 0.8},
        {"word": "আমাদের", "start": 0.85, "end": 1.3},
        {"word": "ভিডিও", "start": 1.35, "end": 1.7},
        {"word": "স্টুডিওতে", "start": 1.75, "end": 2.1}
      ],
      "style": "tiktok_highlight"
    }
  ]
}
```
