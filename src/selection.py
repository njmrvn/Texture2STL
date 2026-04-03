"""Mesh face selection tools."""

import numpy as np
import trimesh
from collections import deque


class SelectionManager:
    """Manages face selection state and provides selection algorithms."""

    def __init__(self):
        self.selected_faces: set[int] = set()
        self._face_adjacency: np.ndarray | None = None
        self._mesh: trimesh.Trimesh | None = None

    def set_mesh(self, mesh: trimesh.Trimesh):
        """Set the working mesh and precompute adjacency."""
        self._mesh = mesh
        self._face_adjacency = None  # Lazy compute

    @property
    def face_adjacency(self) -> np.ndarray:
        if self._face_adjacency is None and self._mesh is not None:
            self._face_adjacency = self._mesh.face_adjacency
        return self._face_adjacency

    def clear(self):
        self.selected_faces.clear()

    def select_face(self, face_id: int):
        """Toggle a single face selection."""
        if face_id in self.selected_faces:
            self.selected_faces.discard(face_id)
        else:
            self.selected_faces.add(face_id)

    def add_face(self, face_id: int):
        self.selected_faces.add(face_id)

    def remove_face(self, face_id: int):
        self.selected_faces.discard(face_id)

    def select_connected_region(self, seed_face: int, angle_threshold: float = 30.0):
        """Flood-fill select faces connected to seed_face within angle threshold.

        Args:
            seed_face: starting face index
            angle_threshold: max angle (degrees) between adjacent face normals
        """
        if self._mesh is None:
            return

        mesh = self._mesh
        threshold_rad = np.radians(angle_threshold)
        cos_threshold = np.cos(threshold_rad)

        # Build adjacency dict for fast lookup
        adj = self._build_adjacency_dict()

        seed_normal = mesh.face_normals[seed_face]
        visited = set()
        queue = deque([seed_face])

        while queue:
            face = queue.popleft()
            if face in visited:
                continue
            visited.add(face)

            face_normal = mesh.face_normals[face]
            cos_angle = np.dot(face_normal, seed_normal)

            if cos_angle >= cos_threshold:
                self.selected_faces.add(face)
                for neighbor in adj.get(face, []):
                    if neighbor not in visited:
                        queue.append(neighbor)

    def select_by_normal(self, reference_normal: np.ndarray, angle_threshold: float = 30.0):
        """Select all faces whose normal is within angle_threshold of reference_normal."""
        if self._mesh is None:
            return

        cos_threshold = np.cos(np.radians(angle_threshold))
        dots = np.dot(self._mesh.face_normals, reference_normal)
        matching = np.where(dots >= cos_threshold)[0]
        self.selected_faces.update(matching.tolist())

    def select_all(self):
        """Select all faces."""
        if self._mesh is not None:
            self.selected_faces = set(range(len(self._mesh.faces)))

    def invert_selection(self):
        """Invert the current selection."""
        if self._mesh is not None:
            all_faces = set(range(len(self._mesh.faces)))
            self.selected_faces = all_faces - self.selected_faces

    def get_selected_array(self) -> np.ndarray:
        """Return sorted numpy array of selected face indices."""
        return np.array(sorted(self.selected_faces), dtype=int)

    def get_selection_mask(self, n_faces: int) -> np.ndarray:
        """Return boolean mask of selected faces."""
        mask = np.zeros(n_faces, dtype=bool)
        for f in self.selected_faces:
            if f < n_faces:
                mask[f] = True
        return mask

    def _build_adjacency_dict(self) -> dict[int, list[int]]:
        """Build face adjacency dictionary from trimesh face_adjacency."""
        adj: dict[int, list[int]] = {}
        for a, b in self.face_adjacency:
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)
        return adj

    @property
    def count(self) -> int:
        return len(self.selected_faces)
