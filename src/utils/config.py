"""Config loader and shared utilities."""
import yaml
import logging
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent

def load_config(path: str | Path = None) -> dict:
    path = path or ROOT / "config.yaml"
    with open(path) as f:
        return yaml.safe_load(f)

def get_logger(name: str) -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    return logging.getLogger(name)
