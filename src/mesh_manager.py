"""Mesh loading, manipulation, and export using trimesh."""

import numpy as np
import trimesh
import pyvista as pv
from pathlib import Path
from dataclasses import dataclass


@dataclass
class MeshStats:
    triangle_count: int
    vertex_count: int
    bbox_min: np.ndarray
    bbox_max: np.ndarray
    bbox_size: np.ndarray
    is_watertight: bool


class MeshManager:
    """Handles mesh I/O, conversion, and modification."""

    def __init__(self):
        self.mesh: trimesh.Trimesh | None = None
        self.original_mesh: trimesh.Trimesh | None = None
        self.file_path: str | None = None

    def load_stl(self, path: str) -> trimesh.Trimesh:
        """Load an STL file and store as the current mesh."""
        mesh = trimesh.load(path, force='mesh')
        if not isinstance(mesh, trimesh.Trimesh):
            raise ValueError(f"Failed to load as a single mesh: {path}")
        self.mesh = mesh
        self.original_mesh = mesh.copy()
        self.file_path = path
        return mesh

    def get_stats(self) -> MeshStats | None:
        if self.mesh is None:
            return None
        bounds = self.mesh.bounds
        return MeshStats(
            triangle_count=len(self.mesh.faces),
            vertex_count=len(self.mesh.vertices),
            bbox_min=bounds[0],
            bbox_max=bounds[1],
            bbox_size=bounds[1] - bounds[0],
            is_watertight=self.mesh.is_watertight,
        )

    def to_pyvista(self, mesh: trimesh.Trimesh | None = None) -> pv.PolyData:
        """Convert trimesh to PyVista PolyData."""
        m = mesh if mesh is not None else self.mesh
        if m is None:
            raise ValueError("No mesh loaded")
        faces = np.column_stack([
            np.full(len(m.faces), 3, dtype=np.int64),
            m.faces.astype(np.int64)
        ]).ravel()
        return pv.PolyData(m.vertices.copy(), faces)

    def subdivide(self, mesh: trimesh.Trimesh, iterations: int = 1) -> trimesh.Trimesh:
        """Subdivide mesh using loop subdivision."""
        result = mesh.copy()
        for _ in range(iterations):
            result = result.subdivide()
        return result

    def subdivide_selected(self, selected_faces: np.ndarray, iterations: int = 1) -> tuple[trimesh.Trimesh, np.ndarray]:
        """Subdivide only the region around selected faces.

        For simplicity in MVP, this subdivides the entire mesh but returns
        updated face indices for the selected region.
        """
        if self.mesh is None:
            raise ValueError("No mesh loaded")

        mesh = self.mesh.copy()
        # Track which original faces were selected
        n_original = len(mesh.faces)
        is_selected = np.zeros(n_original, dtype=bool)
        is_selected[selected_faces] = True

        for _ in range(iterations):
            new_mesh = mesh.subdivide()
            # Each original face produces 4 sub-faces in loop subdivision
            new_selected = np.zeros(len(new_mesh.faces), dtype=bool)
            for i in range(len(is_selected)):
                if is_selected[i]:
                    # In trimesh subdivide, each face becomes 4 faces
                    base = i * 4
                    new_selected[base:base + 4] = True
            mesh = new_mesh
            is_selected = new_selected

        new_face_indices = np.where(is_selected)[0]
        return mesh, new_face_indices

    def export_stl(self, path: str, mesh: trimesh.Trimesh | None = None):
        """Export mesh as STL."""
        m = mesh if mesh is not None else self.mesh
        if m is None:
            raise ValueError("No mesh to export")
        m.export(path, file_type='stl')

    def reset_to_original(self):
        """Reset mesh to the originally loaded state."""
        if self.original_mesh is not None:
            self.mesh = self.original_mesh.copy()
            return self.mesh
        return None

    def update_mesh(self, new_mesh: trimesh.Trimesh):
        """Replace the current mesh with a modified version."""
        self.mesh = new_mesh
