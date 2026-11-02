import json
from pathlib import Path
from typing import Dict, List, Optional
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.preset import Preset, CaptionPreset, AudioPreset, VisualPreset


class PresetManager:
    def __init__(self, presets_dir: Optional[Path] = None):
        self.presets_dir = presets_dir or (settings.assets_dir / "presets")
        self._cache: Dict[str, Preset] = {}
        self.reload()

    def reload(self) -> None:
        self._cache.clear()
        if not self.presets_dir.exists():
            return
        for file in self.presets_dir.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    preset = Preset(**data)
                    self._cache[preset.name] = preset
            except Exception as e:
                logger.warning(f"Failed to load preset {file.name}: {e}")

    def list_presets(self) -> List[Preset]:
        return list(self._cache.values())

    def get_preset(self, name: str) -> Preset:
        if name in self._cache:
            return self._cache[name]
        logger.warning(f"Preset '{name}' not found. Falling back to default 'clean_corporate'.")
        return self._cache.get("clean_corporate", Preset(
            name="default",
            description="Default preset",
            aspect_ratio="16:9",
            fps=30
        ))


preset_manager = PresetManager()
