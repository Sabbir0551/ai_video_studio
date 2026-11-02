from backend.app.core.config import settings


def test_settings_initialization():
    assert settings.app_name == "AI Video Studio"
    assert settings.default_lufs_target == -14.0
    assert settings.default_video_fps == 30
    settings.init_directories()
    assert settings.data_dir.exists()
    assert settings.fonts_dir.exists()

