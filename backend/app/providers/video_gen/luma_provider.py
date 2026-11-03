import os
import time
import httpx
import asyncio
from pathlib import Path
from typing import Optional
from backend.app.core.logging import logger
from backend.app.providers.video_gen.base import VideoGenProvider, VideoGenResult
from backend.app.providers.video_gen.procedural_motion_provider import ProceduralMotionVideoProvider


class LumaDreamMachineProvider(VideoGenProvider):
    """
    Luma Dream Machine AI Video Provider.
    Generates realistic 3D CGI and Pixar-grade character animation video clips via Luma API.
    Gracefully falls back to ProceduralMotionVideoProvider if no API key is provided or request fails.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("LUMA_API_KEY")
        self._fallback = ProceduralMotionVideoProvider()

    @property
    def name(self) -> str:
        return "luma-dream-machine"

    async def animate_image_to_video(
        self,
        image_path: str,
        motion_prompt: str,
        duration: float = 5.0,
        output_path: str = "motion_clip.mp4",
        aspect_ratio: str = "16:9",
        width: int = 1920,
        height: int = 1080
    ) -> VideoGenResult:
        if not self.api_key or len(self.api_key) < 10:
            logger.info("No LUMA_API_KEY provided; routing motion rendering to Procedural Motion Engine.")
            return await self._fallback.animate_image_to_video(
                image_path=image_path,
                motion_prompt=motion_prompt,
                duration=duration,
                output_path=output_path,
                aspect_ratio=aspect_ratio,
                width=width,
                height=height
            )

        try:
            logger.info(f"Submitting Image-to-Video generation to Luma Dream Machine: '{motion_prompt[:60]}...'")
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "prompt": motion_prompt,
                "aspect_ratio": "16:9" if width >= height else "9:16",
                "loop": False
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(
                    "https://api.lumalabs.ai/dream-machine/v1/generations",
                    json=payload,
                    headers=headers
                )
                if res.status_code in (200, 201):
                    gen_data = res.json()
                    gen_id = gen_data.get("id")
                    
                    # Poll for completion (up to 120s)
                    poll_url = f"https://api.lumalabs.ai/dream-machine/v1/generations/{gen_id}"
                    for _ in range(24):
                        await asyncio.sleep(5)
                        poll_res = await client.get(poll_url, headers=headers)
                        if poll_res.status_code == 200:
                            state = poll_res.json()
                            if state.get("state") == "completed":
                                video_url = state.get("assets", {}).get("video")
                                if video_url:
                                    dl_res = await client.get(video_url)
                                    with open(output_path, "wb") as f:
                                        f.write(dl_res.content)
                                    logger.info(f"Downloaded Luma 3D motion clip -> {output_path}")
                                    return VideoGenResult(
                                        video_path=output_path,
                                        duration_seconds=duration,
                                        width=width,
                                        height=height,
                                        provider_name=self.name,
                                        cost_usd=0.25
                                    )
                            elif state.get("state") == "failed":
                                logger.warning(f"Luma generation failed: {state.get('failure_reason')}")
                                break
        except Exception as e:
            logger.warning(f"Luma Dream Machine API call encountered an error: {e}")

        # Fallback if cloud job failed
        return await self._fallback.animate_image_to_video(
            image_path=image_path,
            motion_prompt=motion_prompt,
            duration=duration,
            output_path=output_path,
            aspect_ratio=aspect_ratio,
            width=width,
            height=height
        )

