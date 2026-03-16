import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
TRANSCRIPT_DIR = DATA_DIR / "transcripciones"
SUMMARY_DIR = DATA_DIR / "summary"
SETTINGS_FILE = DATA_DIR / "settings.json"

DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)
TRANSCRIPT_DIR.mkdir(exist_ok=True)
SUMMARY_DIR.mkdir(exist_ok=True)

EXTENSIONES_PERMITIDAS = {".mp4", ".mp3", ".m4a", ".wav", ".mov", ".mkv", ".webm"}

ALL_WHISPER_MODELS = ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3", "large-v3-turbo"]


def get_installed_models() -> list[dict]:
    """Return locally installed whisper models + the API option."""
    whisper_cache = Path.home() / ".cache" / "whisper"
    installed = []
    for model_name in ALL_WHISPER_MODELS:
        model_file = whisper_cache / f"{model_name}.pt"
        if model_file.exists():
            installed.append({"id": model_name, "label": model_name, "type": "local"})
    # Always include the OpenAI Whisper API option
    installed.append({"id": "whisper-api", "label": "Whisper API (OpenAI)", "type": "api"})
    return installed


# Keep backward compat: flat list of valid model ids
AVAILABLE_MODELS = [m for m in ALL_WHISPER_MODELS] + ["whisper-api"]
AVAILABLE_LANGUAGES = {
    "es": "Español", "en": "English", "fr": "Français", "de": "Deutsch",
    "pt": "Português", "it": "Italiano", "ja": "日本語", "zh": "中文",
    "ko": "한국어", "ru": "Русский", "ar": "العربية", "auto": "Auto-detectar",
}


def load_settings() -> dict:
    defaults = {
        "model": os.environ.get("WHISPER_MODEL", "large-v3-turbo"),
        "language": os.environ.get("WHISPER_LANGUAGE", "es"),
        "ollama_url": "http://localhost:11434",
        "ollama_model": "llama3.2",
        "ai_provider": "ollama",
        "gemini_api_key": "",
        "gemini_model": "gemini-2.5-pro",
        "openai_api_key": "",
    }
    if SETTINGS_FILE.exists():
        try:
            saved = json.loads(SETTINGS_FILE.read_text())
            defaults.update(saved)
        except Exception:
            pass
    # API keys: env vars take priority, never store in settings.json
    if os.environ.get("GEMINI_API_KEY"):
        defaults["gemini_api_key"] = os.environ["GEMINI_API_KEY"]
    if os.environ.get("OPENAI_API_KEY"):
        defaults["openai_api_key"] = os.environ["OPENAI_API_KEY"]
    return defaults


def save_settings(data: dict):
    # Don't persist API keys in settings.json — they belong in .env
    safe = {k: v for k, v in data.items() if k not in ("gemini_api_key", "openai_api_key")}
    SETTINGS_FILE.write_text(json.dumps(safe, indent=2))
