import os
from typing import Optional
from backend.app.providers.video_gen.base import VideoGenProvider
from backend.app.providers.video_gen.luma_provider import LumaDreamMachineProvider
from backend.app.providers.video_gen.kling_provider import KlingVideoProvider
from backend.app.providers.video_gen.procedural_motion_provider import ProceduralMotionVideoProvider


def get_video_gen_provider(
    preferred: Optional[str] = None,
    luma_api_key: Optional[str] = None,
    kling_api_key: Optional[str] = None
) -> VideoGenProvider:
    """Return the active AI video generation provider based on keys and preferences."""
    if luma_api_key or os.getenv("LUMA_API_KEY"):
        return LumaDreamMachineProvider(api_key=luma_api_key)
    elif kling_api_key or os.getenv("KLING_API_KEY"):
        return KlingVideoProvider(api_key=kling_api_key)
    return ProceduralMotionVideoProvider()
