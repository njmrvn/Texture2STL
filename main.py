"""Texture STL Tool - Desktop application for applying geometric texture displacement to STL meshes."""

import os
import sys

# Set Qt binding before any Qt imports
os.environ['QT_API'] = 'pyside6'

# --- PyInstaller frozen-app bootstrap ---
# When running as a packaged .exe, seed writable user data from bundled assets
# BEFORE any module touches config/library/texture paths.
from src.paths import initialize_user_data
initialize_user_data()

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from src.app import MainWindow
from src.config import AppConfig
from src.texture_manager import TextureManager
from src.paths import bundle_dir


def _create_mutex():
    """Create a named mutex so the Inno Setup installer can detect a running instance.

    Only relevant on Windows.  Silently ignored on other platforms or if
    the Win32 API is unavailable.
    """
    if sys.platform != 'win32':
        return None
    try:
        import ctypes
        return ctypes.windll.kernel32.CreateMutexW(None, False, "TextureSTLToolMutex")
    except Exception:
        return None


def main():
    mutex_handle = _create_mutex()

    app = QApplication(sys.argv)
    app.setApplicationName("Texture STL Tool")
    app.setOrganizationName("TextureSTLTool")

    # Set application icon if present
    icon_path = bundle_dir() / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Initialize config and ensure texture library has samples
    config = AppConfig()
    tex_manager = TextureManager(config)
    tex_manager.ensure_sample_textures()

    window = MainWindow(config, tex_manager)
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
