"""Tests for texture loading and library management."""

import sys
import os
import json
import tempfile
import shutil
from pathlib import Path
from PIL import Image
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.texture_manager import TextureManager, TextureEntry
from src.config import AppConfig, TEXTURES_DIR, LIBRARY_DIR


class TestTextureEntry:
    def test_roundtrip(self):
        entry = TextureEntry("Test", "test.png", "abc123")
        d = entry.to_dict()
        restored = TextureEntry.from_dict(d)
        assert restored.name == "Test"
        assert restored.filename == "test.png"
        assert restored.id == "abc123"

    def test_path(self):
        entry = TextureEntry("Test", "test.png")
        assert entry.path == TEXTURES_DIR / "test.png"


class TestTextureManager:
    @pytest.fixture
    def temp_env(self, tmp_path):
        """Set up temporary texture and library directories."""
        import src.config as cfg
        orig_tex = cfg.TEXTURES_DIR
        orig_lib = cfg.LIBRARY_DIR
        cfg.TEXTURES_DIR = tmp_path / "textures"
        cfg.LIBRARY_DIR = tmp_path / "library"
        cfg.TEXTURES_DIR.mkdir()
        cfg.LIBRARY_DIR.mkdir()

        # Also patch the module reference in texture_manager
        import src.texture_manager as tm
        tm.TEXTURES_DIR = cfg.TEXTURES_DIR
        tm.LIBRARY_DIR = cfg.LIBRARY_DIR

        yield tmp_path

        cfg.TEXTURES_DIR = orig_tex
        cfg.LIBRARY_DIR = orig_lib
        tm.TEXTURES_DIR = orig_tex
        tm.LIBRARY_DIR = orig_lib

    def test_import_texture(self, temp_env):
        # Create a test image
        img_path = temp_env / "test_input.png"
        Image.new('L', (32, 32), 128).save(img_path)

        config = AppConfig()
        mgr = TextureManager(config)
        entry = mgr.import_texture(str(img_path), "My Texture")

        assert entry.name == "My Texture"
        assert entry.path.exists()
        assert len(mgr.entries) == 1

    def test_remove_texture(self, temp_env):
        img_path = temp_env / "test_input.png"
        Image.new('L', (32, 32), 128).save(img_path)

        config = AppConfig()
        mgr = TextureManager(config)
        entry = mgr.import_texture(str(img_path), "To Delete")

        assert entry.path.exists()
        mgr.remove_texture(entry)
        assert not entry.path.exists()
        assert len(mgr.entries) == 0

    def test_load_image(self, temp_env):
        img_path = temp_env / "test.png"
        Image.new('RGB', (64, 64), (100, 150, 200)).save(img_path)

        config = AppConfig()
        mgr = TextureManager(config)
        img = mgr.load_image(str(img_path))

        assert img is not None
        assert img.size == (64, 64)
        assert mgr.current_image is not None

    def test_library_persistence(self, temp_env):
        img_path = temp_env / "persist.png"
        Image.new('L', (32, 32), 64).save(img_path)

        config = AppConfig()
        mgr1 = TextureManager(config)
        mgr1.import_texture(str(img_path), "Persistent")

        # Create new manager - should load from disk
        mgr2 = TextureManager(config)
        assert len(mgr2.entries) == 1
        assert mgr2.entries[0].name == "Persistent"

    def test_thumbnail(self, temp_env):
        img_path = temp_env / "thumb.png"
        Image.new('L', (256, 256), 200).save(img_path)

        config = AppConfig()
        mgr = TextureManager(config)
        entry = mgr.import_texture(str(img_path), "Thumb Test")

        thumb = mgr.get_thumbnail(entry, 64)
        assert thumb is not None
        assert max(thumb.size) <= 64


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
