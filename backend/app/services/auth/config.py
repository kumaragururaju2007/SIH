from pathlib import Path
from typing import Any, Dict
import yaml


def load_auth_config() -> Dict[str, Any]:
    """Load configuration from configs/authentication/auth_config.yaml."""
    backend_dir = Path(__file__).resolve().parent.parent.parent
    candidates = [
        backend_dir / "configs" / "authentication" / "auth_config.yaml",
        backend_dir.parent / "configs" / "authentication" / "auth_config.yaml",
        Path("configs/authentication/auth_config.yaml").resolve(),
    ]
    for c in candidates:
        if c.exists():
            with open(c, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    return {}
