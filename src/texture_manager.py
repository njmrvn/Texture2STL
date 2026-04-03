"""Texture library management - loading, storing, and organizing textures."""

import json
import shutil
import uuid
from pathlib import Path
from PIL import Image
import numpy as np

from .config import AppConfig, LIBRARY_DIR, TEXTURES_DIR


class TextureEntry:
    """A single texture in the library."""

    def __init__(self, name: str, filename: str, tex_id: str = ""):
        self.name = name
        self.filename = filename
        self.id = tex_id or str(uuid.uuid4())[:8]

    @property
    def path(self) -> Path:
        return TEXTURES_DIR / self.filename

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "filename": self.filename}

    @classmethod
    def from_dict(cls, d: dict) -> "TextureEntry":
        return cls(d["name"], d["filename"], d.get("id", ""))


class TextureManager:
    """Manages the local texture library."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.entries: list[TextureEntry] = []
        self.current_image: Image.Image | None = None
        self.current_entry: TextureEntry | None = None
        self._load_library()

    def _library_file(self) -> Path:
        return LIBRARY_DIR / "library.json"

    def _load_library(self):
        path = self._library_file()
        if path.exists():
            try:
                data = json.loads(path.read_text())
                self.entries = [TextureEntry.from_dict(t) for t in data.get("textures", [])]
            except (json.JSONDecodeError, KeyError):
                self.entries = []

    def _save_library(self):
        LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
        data = {"textures": [e.to_dict() for e in self.entries]}
        self._library_file().write_text(json.dumps(data, indent=2))

    def import_texture(self, source_path: str, name: str = "") -> TextureEntry:
        """Import an image file into the texture library."""
        src = Path(source_path)
        if not src.exists():
            raise FileNotFoundError(f"Texture file not found: {source_path}")

        if not name:
            name = src.stem

        # Copy to textures directory with unique name
        TEXTURES_DIR.mkdir(parents=True, exist_ok=True)
        dest_name = f"{uuid.uuid4().hex[:8]}_{src.name}"
        dest = TEXTURES_DIR / dest_name
        shutil.copy2(src, dest)

        entry = TextureEntry(name, dest_name)
        self.entries.append(entry)
        self._save_library()
        return entry

    def remove_texture(self, entry: TextureEntry):
        """Remove a texture from the library."""
        if entry.path.exists():
            entry.path.unlink()
        self.entries = [e for e in self.entries if e.id != entry.id]
        self._save_library()

    def load_image(self, path: str | Path) -> Image.Image:
        """Load an image and set as current texture."""
        img = Image.open(path)
        self.current_image = img
        return img

    def load_entry(self, entry: TextureEntry) -> Image.Image:
        """Load a library texture entry."""
        self.current_entry = entry
        return self.load_image(entry.path)

    def get_thumbnail(self, entry: TextureEntry, size: int = 64) -> Image.Image | None:
        """Get a thumbnail for a library entry."""
        if not entry.path.exists():
            return None
        img = Image.open(entry.path)
        img.thumbnail((size, size))
        return img

    def ensure_sample_textures(self):
        """Generate sample textures if the library is empty."""
        if self.entries:
            return

        TEXTURES_DIR.mkdir(parents=True, exist_ok=True)

        # Checkerboard
        self._generate_checkerboard("checkerboard.png", 256, 16)
        self._generate_diamond_plate("diamond_plate.png", 256)
        self._generate_noise("noise_fine.png", 256, scale=4)
        self._generate_waves("waves.png", 256)
        self._generate_brick("brick.png", 256)

    def _generate_checkerboard(self, filename: str, size: int, squares: int):
        arr = np.zeros((size, size), dtype=np.uint8)
        sq = size // squares
        for i in range(squares):
            for j in range(squares):
                if (i + j) % 2 == 0:
                    arr[i * sq:(i + 1) * sq, j * sq:(j + 1) * sq] = 255
        self._save_generated(arr, filename, "Checkerboard")

    def _generate_diamond_plate(self, filename: str, size: int):
        arr = np.zeros((size, size), dtype=np.uint8)
        for y in range(size):
            for x in range(size):
                # Diamond pattern
                dx = (x % 32) - 16
                dy = (y % 32) - 16
                d = abs(dx) + abs(dy)
                arr[y, x] = max(0, 255 - d * 16)
        self._save_generated(arr, filename, "Diamond Plate")

    def _generate_noise(self, filename: str, size: int, scale: int):
        from scipy.ndimage import zoom
        small = np.random.randint(0, 256, (size // scale, size // scale), dtype=np.uint8)
        arr = zoom(small, scale, order=1).astype(np.uint8)[:size, :size]
        self._save_generated(arr, filename, "Fine Noise")

    def _generate_waves(self, filename: str, size: int):
        x = np.linspace(0, 4 * np.pi, size)
        y = np.linspace(0, 4 * np.pi, size)
        xx, yy = np.meshgrid(x, y)
        arr = ((np.sin(xx) * np.sin(yy) + 1) / 2 * 255).astype(np.uint8)
        self._save_generated(arr, filename, "Sine Waves")

    def _generate_brick(self, filename: str, size: int):
        arr = np.full((size, size), 200, dtype=np.uint8)
        brick_h, brick_w = 24, 48
        mortar = 3
        for row in range(0, size, brick_h):
            # Horizontal mortar line
            arr[row:row + mortar, :] = 40
            offset = (brick_w // 2) if (row // brick_h) % 2 else 0
            for col in range(-offset, size, brick_w):
                c = col % size if col >= 0 else col + size
                arr[row:row + brick_h, c:c + mortar] = 40
        self._save_generated(arr, filename, "Brick")

    def _save_generated(self, arr: np.ndarray, filename: str, name: str):
        path = TEXTURES_DIR / filename
        Image.fromarray(arr, mode='L').save(path)
        entry = TextureEntry(name, filename)
        self.entries.append(entry)
        self._save_library()
