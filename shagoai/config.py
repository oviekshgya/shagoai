import json
from pathlib import Path
from typing import Any


CONFIG_DIR = Path.home() / ".config" / "shagoai"
CONFIG_FILE = CONFIG_DIR / "config.json"


DEFAULT_CONFIG = {
    "api_url": "http://127.0.0.1:8184",
    "token": "",
    "model": "default",
    "guard": "approval required",

    "rpk_enabled": True,
    "rpk_max_tool_chars": 16000,
    "rpk_max_read_file_chars": 24000,
    "rpk_max_command_chars": 14000,
    "rpk_max_search_chars": 12000,
    "rpk_max_diff_chars": 18000,
}


def load_config() -> dict[str, Any]:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG.copy())
        return DEFAULT_CONFIG.copy()

    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        data = {}

    config = DEFAULT_CONFIG.copy()
    config.update(data)
    return config


def save_config(config: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps(config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def set_config_value(key: str, value: Any) -> None:
    config = load_config()
    config[key] = value
    save_config(config)


def get_config_value(key: str, default: Any = None) -> Any:
    config = load_config()
    return config.get(key, default)