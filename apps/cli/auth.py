from __future__ import annotations

import json
from pathlib import Path

import platformdirs

CREDENTIALS_PATH = Path(platformdirs.user_config_dir("argus")) / "credentials.json"


def save_token(token: str) -> None:
    CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_PATH.write_text(json.dumps({"token": token}))


def load_token() -> str | None:
    if not CREDENTIALS_PATH.exists():
        return None
    try:
        return json.loads(CREDENTIALS_PATH.read_text()).get("token")
    except (json.JSONDecodeError, OSError):
        return None


def clear_token() -> None:
    CREDENTIALS_PATH.unlink(missing_ok=True)
