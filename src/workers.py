"""Background worker threads for heavy operations."""

import trimesh
import numpy as np
from PIL import Image
from PySide6.QtCore import QThread, Signal

from .config import DisplacementParams
from .displacement import apply_displacement
from .mesh_manager import MeshManager


class DisplacementWorker(QThread):
    """Runs displacement in a background thread."""

    finished = Signal(object)  # trimesh.Trimesh
    error = Signal(str)
    progress = Signal(int)  # 0-100

    def __init__(self, mesh: trimesh.Trimesh, selected_faces: np.ndarray,
                 texture_image: Image.Image, params: DisplacementParams):
        super().__init__()
        self.mesh = mesh.copy()
        self.selected_faces = selected_faces.copy()
        self.texture_image = texture_image.copy()
        self.params = params

    def run(self):
        try:
            self.progress.emit(10)
            # Subdivide if requested
            if self.params.subdivision > 0:
                self.progress.emit(20)
                mesh_mgr = MeshManager()
                mesh_mgr.mesh = self.mesh
                self.mesh, self.selected_faces = mesh_mgr.subdivide_selected(
                    self.selected_faces, self.params.subdivision
                )
                self.progress.emit(50)

            result = apply_displacement(
                self.mesh, self.selected_faces,
                self.texture_image, self.params
            )
            self.progress.emit(100)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ExportWorker(QThread):
    """Exports mesh in a background thread."""

    finished = Signal(str)  # output path
    error = Signal(str)

    def __init__(self, mesh: trimesh.Trimesh, path: str):
        super().__init__()
        self.mesh = mesh
        self.path = path

    def run(self):
        try:
            self.mesh.export(self.path, file_type='stl')
            self.finished.emit(self.path)
        except Exception as e:
            self.error.emit(str(e))


class SubdivisionWorker(QThread):
    """Subdivides mesh in a background thread."""

    finished = Signal(object, object)  # (mesh, new_selected_faces)
    error = Signal(str)
    progress = Signal(int)

    def __init__(self, mesh: trimesh.Trimesh, selected_faces: np.ndarray, iterations: int):
        super().__init__()
        self.mesh = mesh.copy()
        self.selected_faces = selected_faces.copy()
        self.iterations = iterations

    def run(self):
        try:
            self.progress.emit(10)
            mesh_mgr = MeshManager()
            mesh_mgr.mesh = self.mesh
            result_mesh, new_faces = mesh_mgr.subdivide_selected(
                self.selected_faces, self.iterations
            )
            self.progress.emit(100)
            self.finished.emit(result_mesh, new_faces)
        except Exception as e:
            self.error.emit(str(e))
