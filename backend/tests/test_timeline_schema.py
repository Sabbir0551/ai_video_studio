import pytest
from backend.app.models.timeline import (
    Timeline,
    Track,
    Clip,
    TrackType,
    AspectRatio,
    CaptionItem,
    WordTimestamp,
    SidechainDucking,
    Transform,
    KenBurnsEffect
)


def test_timeline_validation():
    tl = Timeline(
        project_id="test_proj_1",
        tracks=[
            Track(
                id="t_video",
                name="Visual Track",
                track_type=TrackType.IMAGE,
                clips=[
                    Clip(
                        id="c1",
                        source_path="assets/sample.jpg",
                        source_in=0.0,
                        source_out=5.0,
                        timeline_start=0.0,
                        timeline_end=5.0,
                        transform=Transform(
                            ken_burns=KenBurnsEffect(start_scale=1.0, end_scale=1.1, pan_x=0.05)
                        )
                    )
                ]
            ),
            Track(
                id="t_music",
                name="Background Music",
                track_type=TrackType.MUSIC,
                clips=[
                    Clip(
                        id="c_m1",
                        source_path="assets/audio/bg.mp3",
                        source_in=0.0,
                        source_out=5.0,
                        timeline_start=0.0,
                        timeline_end=5.0,
                        sidechain_ducking=SidechainDucking(source_track_id="t_voice")
                    )
                ]
            )
        ],
        captions=[
            CaptionItem(
                id="cap1",
                start=0.5,
                end=4.0,
                text="স্বাগতম আমাদের ভিডিও স্টুডিওতে",
                words=[
                    WordTimestamp(word="স্বাগতম", start=0.5, end=1.5),
                    WordTimestamp(word="আমাদের", start=1.5, end=2.5),
                    WordTimestamp(word="স্টুডিওতে", start=2.5, end=4.0)
                ]
            )
        ]
    )

    assert tl.total_duration() == 5.0
    assert tl.canvas.aspect_ratio == AspectRatio.HORIZONTAL_16_9
    assert len(tl.tracks) == 2
    assert len(tl.captions) == 1


def test_invalid_clip_timestamps_raise_error():
    with pytest.raises(ValueError):
        # timeline_end must be greater than timeline_start
        Clip(
            id="bad_clip",
            source_path="dummy.mp4",
            source_in=0.0,
            source_out=5.0,
            timeline_start=4.0,
            timeline_end=3.0
        )
