# Known Issues and Workarounds

## 1. Windows Console UTF-8 Output
- **Issue**: Standard Windows Command Prompt / PowerShell may default to non-UTF-8 codepages (e.g., cp1252), causing `UnicodeEncodeError` when printing Bengali characters directly to stdout.
- **Remediation**: AI Video Studio automatically enforces `sys.stdout.reconfigure(encoding='utf-8')` on startup. CLI commands use `rich` with UTF-8 encoding enabled.

## 2. FFmpeg Filter Path Escaping on Windows
- **Issue**: In FFmpeg complex filter chains (`-vf`), unescaped drive letters (e.g. `C:/`) cause FFmpeg filter parser syntax errors because `:` is treated as an option separator.
- **Remediation**: The internal `ffmpeg_wrapper` automatically normalizes paths: Windows paths inside filter descriptions are converted to forward slashes with escaped colons (`C\\:/...`) or wrapped in single quotes.

## 3. Native GPU Acceleration Availability
- **Issue**: System environments without dedicated NVIDIA GPU or CUDA drivers fall back to CPU encoding (`libx264`).
- **Remediation**: The media engine queries FFmpeg encoders dynamically. If `h264_nvenc` or `h264_d3d11va` is absent, it falls back smoothly to multi-threaded CPU `libx264` with preset `fast`/`medium` and `crf=21`.

## 4. Complex Bangla Conjuncts on Non-HarfBuzz Renderers
- **Issue**: Naive character-by-character canvas drawing breaks Bengali vowel signs (`ি-কার`, `ে-কার`) and conjuncts (`ক্ষ`, `জ্ঞ`, `ব্র`).
- **Remediation**: All subtitle and text graphics are rendered exclusively via HarfBuzz-enabled pipelines: FFmpeg's `libass` (which invokes HarfBuzz + FriBidi) with bundled `Noto Sans Bengali`, or Chromium-based Remotion rendering.
