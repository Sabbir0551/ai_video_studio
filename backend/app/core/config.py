import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # General
    app_name: str = "AI Video Studio"
    studio_env: str = "development"
    debug: bool = True
    studio_host: str = "0.0.0.0"
    studio_port: int = 8000

    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent.parent.parent
    data_dir: Path = Path("data")
    assets_dir: Path = Path("assets")
    fonts_dir: Path = Path("assets/fonts")

    # Defaults
    default_lufs_target: float = -14.0
    default_true_peak_target: float = -1.0
    default_video_fps: int = 30
    default_resolution: str = "1920x1080"

    # Database & Queue
    database_url: str = "sqlite:///data/studio.db"
    redis_url: Optional[str] = None
    use_in_process_queue: bool = True

    # Bangla Typography
    bangla_default_font: str = "Noto Sans Bengali"
    default_font_path: str = "assets/fonts/NotoSansBengali-VariableFont.ttf"

    # Providers
    default_tts_provider: str = "edge-tts"
    default_llm_provider: str = "mock"
    default_asr_provider: str = "faster-whisper"

    # API Keys (Optional)
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None
    azure_speech_key: Optional[str] = None
    azure_speech_region: Optional[str] = None
    pexels_api_key: Optional[str] = None
    unsplash_access_key: Optional[str] = None
    pixabay_api_key: Optional[str] = None

    # Budget Limits (USD)
    job_max_budget_usd: float = 5.0
    monthly_max_budget_usd: float = 50.0

    def init_directories(self) -> None:
        """Create standard studio directory trees."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "projects").mkdir(parents=True, exist_ok=True)
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.fonts_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
