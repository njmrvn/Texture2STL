"""Centralized path resolution for both source and PyInstaller-frozen modes.

When running from source:
    All paths resolve relative to the project root (parent of src/).

When running as a frozen .exe:
    - Read-only bundled assets (sample textures, initial library) come from sys._MEIPASS
    - Writable user data (config, library, user textures) goes to %APPDATA%/TextureSTLTool

This module MUST be imported before any path constants are used elsewhere.
"""

import os
import sys
import shutil
from pathlib import Path


def is_frozen() -> bool:
    """Check if running inside a PyInstaller bundle."""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def bundle_dir() -> Path:
    """Root directory for read-only bundled assets.

    - Frozen: sys._MEIPASS (temp extraction folder)
    - Source: project root (parent of src/)
    """
    if is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent.resolve()


def user_data_dir() -> Path:
    """Root directory for writable user data.

    - Frozen: %APPDATA%/TextureSTLTool  (Windows)
              ~/Library/Application Support/TextureSTLTool  (macOS)
              ~/.local/share/TextureSTLTool  (Linux)
    - Source: project root (same as bundle_dir for development convenience)
    """
    if is_frozen():
        if sys.platform == 'win32':
            base = Path(os.environ.get('APPDATA',
                                       Path.home() / 'AppData' / 'Roaming'))
        elif sys.platform == 'darwin':
            base = Path.home() / 'Library' / 'Application Support'
        else:
            base = Path(os.environ.get('XDG_DATA_HOME',
                                       Path.home() / '.local' / 'share'))
        return base / 'TextureSTLTool'
    return Path(__file__).parent.parent.resolve()


# ---------------------------------------------------------------------------
# Derived path accessors
# ---------------------------------------------------------------------------

def config_file() -> Path:
    """Path to settings.json (writable)."""
    return user_data_dir() / 'config' / 'settings.json'


def library_dir() -> Path:
    """Path to library/ folder (writable)."""
    return user_data_dir() / 'library'


def textures_dir() -> Path:
    """Path to textures/ folder (writable — user imports go here)."""
    return user_data_dir() / 'textures'


def bundled_textures_dir() -> Path:
    """Path to the read-only sample textures shipped inside the bundle."""
    return bundle_dir() / 'textures'


def bundled_library_dir() -> Path:
    """Path to the read-only seed library.json inside the bundle."""
    return bundle_dir() / 'library'


# ---------------------------------------------------------------------------
# First-run initialization
# ---------------------------------------------------------------------------

def initialize_user_data():
    """Seed user data directory from bundled assets on first run.

    Called once at startup.  In source mode this is a no-op because the
    writable and bundled directories are the same folder.
    """
    if not is_frozen():
        return  # source mode — paths already point to project root

    ud = user_data_dir()
    ud.mkdir(parents=True, exist_ok=True)

    # --- Seed textures/ ---
    tex_dst = textures_dir()
    if not tex_dst.exists():
        tex_src = bundled_textures_dir()
        if tex_src.exists() and any(tex_src.iterdir()):
            shutil.copytree(tex_src, tex_dst)
        else:
            tex_dst.mkdir(parents=True, exist_ok=True)

    # --- Seed library/ ---
    lib_dst = library_dir()
    if not lib_dst.exists():
        lib_src = bundled_library_dir()
        if lib_src.exists() and any(lib_src.iterdir()):
            shutil.copytree(lib_src, lib_dst)
        else:
            lib_dst.mkdir(parents=True, exist_ok=True)
            (lib_dst / 'library.json').write_text('{"textures": []}')

    # --- Ensure config directory ---
    config_file().parent.mkdir(parents=True, exist_ok=True)
