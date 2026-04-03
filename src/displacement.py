"""Core displacement engine - applies texture as geometric height map to mesh."""

import numpy as np
import trimesh
from PIL import Image, ImageFilter
from scipy.ndimage import gaussian_filter

from .projection import compute_local_frame, project_planar, normalize_uv, apply_tiling_offset
from .config import DisplacementParams


def load_and_prepare_texture(image: Image.Image, params: DisplacementParams) -> np.ndarray:
    """Convert image to processed grayscale array ready for sampling.

    Returns:
        2D numpy array of floats in [0, 1]
    """
    gray = image.convert('L')
    arr = np.array(gray, dtype=np.float64) / 255.0

    # Apply contrast
    if params.contrast != 1.0:
        arr = np.clip((arr - 0.5) * params.contrast + 0.5, 0.0, 1.0)

    # Apply smoothing
    if params.smooth_kernel > 0:
        arr = gaussian_filter(arr, sigma=params.smooth_kernel)

    # Invert
    if params.invert:
        arr = 1.0 - arr

    # Clamp
    arr = np.clip(arr, params.clamp_min, params.clamp_max)

    # Re-normalize clamped range to [0, 1]
    val_range = params.clamp_max - params.clamp_min
    if val_range > 1e-10:
        arr = (arr - params.clamp_min) / val_range
    else:
        arr[:] = 0.0

    return arr


def sample_texture(texture: np.ndarray, uv: np.ndarray) -> np.ndarray:
    """Sample grayscale values from texture at UV coordinates using bilinear interpolation.

    Args:
        texture: 2D array (H, W) of float values in [0, 1]
        uv: (N, 2) array of UV coordinates (may be outside [0,1] for tiling)

    Returns:
        (N,) array of sampled values in [0, 1]
    """
    h, w = texture.shape

    # Tile: wrap UVs to [0, 1]
    u = np.mod(uv[:, 0], 1.0)
    v = np.mod(uv[:, 1], 1.0)

    # Convert to pixel coordinates
    px = u * (w - 1)
    py = (1.0 - v) * (h - 1)  # Flip V so bottom-left is origin

    # Bilinear interpolation
    x0 = np.floor(px).astype(int)
    y0 = np.floor(py).astype(int)
    x1 = np.minimum(x0 + 1, w - 1)
    y1 = np.minimum(y0 + 1, h - 1)

    # Clamp to valid range
    x0 = np.clip(x0, 0, w - 1)
    y0 = np.clip(y0, 0, h - 1)

    fx = px - np.floor(px)
    fy = py - np.floor(py)

    val = (texture[y0, x0] * (1 - fx) * (1 - fy) +
           texture[y0, x1] * fx * (1 - fy) +
           texture[y1, x0] * (1 - fx) * fy +
           texture[y1, x1] * fx * fy)

    return val


def compute_vertex_normals_for_selection(mesh: trimesh.Trimesh,
                                          vertex_indices: np.ndarray) -> np.ndarray:
    """Compute vertex normals for selected vertices.

    Uses trimesh's built-in vertex normals.
    """
    return mesh.vertex_normals[vertex_indices].copy()


def apply_displacement(mesh: trimesh.Trimesh, selected_faces: np.ndarray,
                       texture_image: Image.Image,
                       params: DisplacementParams) -> trimesh.Trimesh:
    """Apply texture displacement to selected mesh region.

    This is the core algorithm:
    1. Get unique vertices from selected faces
    2. Compute local coordinate frame from the selected region
    3. Project vertices to local 2D (planar projection)
    4. Normalize and apply tiling/offset to get UVs
    5. Sample grayscale values from texture
    6. Displace vertices along their normals

    Returns:
        New mesh with displaced vertices
    """
    if len(selected_faces) == 0:
        raise ValueError("No faces selected for displacement.")

    # Prepare texture
    texture = load_and_prepare_texture(texture_image, params)

    # Get unique vertex indices from selected faces
    selected_verts = np.unique(mesh.faces[selected_faces].ravel())

    # Get positions and normals
    positions = mesh.vertices[selected_verts]
    normals = compute_vertex_normals_for_selection(mesh, selected_verts)

    # Compute local frame from selected region
    face_normals = mesh.face_normals[selected_faces]
    center, axis_u, axis_v, _ = compute_local_frame(positions, face_normals)

    # Project to local 2D
    local_uv = project_planar(positions, center, axis_u, axis_v)

    # Normalize to [0, 1]
    uv = normalize_uv(local_uv)

    # Apply tiling and offset
    uv = apply_tiling_offset(uv, params.tile_x, params.tile_y,
                             params.offset_x, params.offset_y)

    # Sample texture values
    values = sample_texture(texture, uv)

    # Compute displacement based on mode
    if params.mode == "centered":
        displacement = (values - 0.5) * 2.0 * params.depth
    else:  # positive
        displacement = values * params.depth

    # Apply displacement: new_pos = old_pos + normal * displacement
    new_vertices = mesh.vertices.copy()
    new_vertices[selected_verts] += normals * displacement[:, np.newaxis]

    # Build new mesh
    result = trimesh.Trimesh(
        vertices=new_vertices,
        faces=mesh.faces.copy(),
        process=False
    )

    # Recompute normals
    result.fix_normals()

    return result
