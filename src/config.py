"""Application configuration and persistence."""

import json
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict

from .paths import config_file, library_dir, textures_dir, user_data_dir

# These module-level constants are used throughout the app.
# In source mode they resolve to the project root subfolders.
# In frozen/.exe mode they resolve to %APPDATA%/TextureSTLTool subfolders.
APP_DIR = user_data_dir()
CONFIG_FILE = config_file()
LIBRARY_DIR = library_dir()
TEXTURES_DIR = textures_dir()


@dataclass
class DisplacementParams:
    """Parameters for texture displacement."""
    depth: float = 0.5            # mm
    tile_x: float = 1.0
    tile_y: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    invert: bool = False
    smooth_kernel: int = 0        # Gaussian blur kernel size (0 = off)
    contrast: float = 1.0         # 0.5 - 2.0
    clamp_min: float = 0.0
    clamp_max: float = 1.0
    mode: str = "positive"        # "positive" or "centered"
    subdivision: int = 0          # 0, 1, 2, 3


class AppConfig:
    """Manages app settings and recent files."""

    def __init__(self):
        self.recent_files: list[str] = []
        self.last_import_dir: str = ""
        self.last_export_dir: str = ""
        self.window_geometry: dict = {}
        self._load()

    def _load(self):
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text())
                self.recent_files = data.get("recent_files", [])
                self.last_import_dir = data.get("last_import_dir", "")
                self.last_export_dir = data.get("last_export_dir", "")
                self.window_geometry = data.get("window_geometry", {})
            except (json.JSONDecodeError, KeyError):
                pass

    def save(self):
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "recent_files": self.recent_files[:20],
            "last_import_dir": self.last_import_dir,
            "last_export_dir": self.last_export_dir,
            "window_geometry": self.window_geometry,
        }
        CONFIG_FILE.write_text(json.dumps(data, indent=2))

    def add_recent_file(self, path: str):
        path = str(Path(path).resolve())
        if path in self.recent_files:
            self.recent_files.remove(path)
        self.recent_files.insert(0, path)
        self.recent_files = self.recent_files[:20]
        self.save()
