"""UV projection methods for mapping textures onto mesh surfaces."""

import numpy as np


def compute_local_frame(vertices: np.ndarray, face_normals: np.ndarray):
    """Compute a local coordinate frame for a mesh region.

    Returns:
        center: centroid of the region
        axis_u: local X axis (tangent)
        axis_v: local Y axis (tangent)
        normal: average face normal (local Z)
    """
    center = vertices.mean(axis=0)

    # Average normal weighted by... just average for now
    normal = face_normals.mean(axis=0)
    norm = np.linalg.norm(normal)
    if norm < 1e-10:
        normal = np.array([0.0, 0.0, 1.0])
    else:
        normal = normal / norm

    # Find a tangent vector not parallel to normal
    ref = np.array([1.0, 0.0, 0.0])
    if abs(np.dot(normal, ref)) > 0.9:
        ref = np.array([0.0, 1.0, 0.0])

    axis_u = np.cross(normal, ref)
    axis_u /= np.linalg.norm(axis_u)
    axis_v = np.cross(normal, axis_u)
    axis_v /= np.linalg.norm(axis_v)

    return center, axis_u, axis_v, normal


def project_planar(vertices: np.ndarray, center: np.ndarray,
                   axis_u: np.ndarray, axis_v: np.ndarray) -> np.ndarray:
    """Project 3D vertices onto a local 2D plane.

    Returns:
        uv: (N, 2) array of local 2D coordinates
    """
    relative = vertices - center
    u = np.dot(relative, axis_u)
    v = np.dot(relative, axis_v)
    return np.column_stack([u, v])


def normalize_uv(uv: np.ndarray) -> np.ndarray:
    """Normalize UV coordinates to [0, 1] range based on bounding box."""
    uv_min = uv.min(axis=0)
    uv_max = uv.max(axis=0)
    uv_range = uv_max - uv_min
    # Avoid division by zero
    uv_range[uv_range < 1e-10] = 1.0
    return (uv - uv_min) / uv_range


def apply_tiling_offset(uv: np.ndarray, tile_x: float, tile_y: float,
                        offset_x: float, offset_y: float) -> np.ndarray:
    """Apply tiling and offset to UV coordinates."""
    result = uv.copy()
    result[:, 0] = result[:, 0] * tile_x + offset_x
    result[:, 1] = result[:, 1] * tile_y + offset_y
    return result


# Future: cylindrical projection
def project_cylindrical(vertices: np.ndarray, center: np.ndarray,
                        axis: np.ndarray, radius: float) -> np.ndarray:
    """Placeholder for cylindrical projection. Not yet implemented."""
    raise NotImplementedError("Cylindrical projection coming in a future version.")


# Future: box projection
def project_box(vertices: np.ndarray, center: np.ndarray) -> np.ndarray:
    """Placeholder for box projection. Not yet implemented."""
    raise NotImplementedError("Box projection coming in a future version.")
