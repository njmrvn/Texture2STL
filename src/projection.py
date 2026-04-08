"""UV projection methods for mapping textures onto mesh surfaces.

Supported projection modes:
    - planar       : Flat projection onto a best-fit plane (default)
    - cylindrical  : Wraps texture around an axis fitted to the region
    - box          : Triplanar — each vertex uses the axis-aligned plane
                     perpendicular to its dominant normal direction
    - auto         : Heuristically picks one of the above based on region
                     curvature (good for curved surfaces)
"""

import numpy as np


# ============================================================================
# Planar projection (the original)
# ============================================================================

def compute_local_frame(vertices: np.ndarray, face_normals: np.ndarray):
    """Compute a local coordinate frame for a planar mesh region."""
    center = vertices.mean(axis=0)

    normal = face_normals.mean(axis=0)
    norm = np.linalg.norm(normal)
    if norm < 1e-10:
        normal = np.array([0.0, 0.0, 1.0])
    else:
        normal = normal / norm

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
    """Project 3D vertices onto a local 2D plane."""
    relative = vertices - center
    u = np.dot(relative, axis_u)
    v = np.dot(relative, axis_v)
    return np.column_stack([u, v])


def normalize_uv(uv: np.ndarray) -> np.ndarray:
    """Normalize UV coordinates to [0, 1] range based on bounding box."""
    uv_min = uv.min(axis=0)
    uv_max = uv.max(axis=0)
    uv_range = uv_max - uv_min
    uv_range[uv_range < 1e-10] = 1.0
    return (uv - uv_min) / uv_range


def apply_tiling_offset(uv: np.ndarray, tile_x: float, tile_y: float,
                        offset_x: float, offset_y: float) -> np.ndarray:
    """Apply tiling and offset to UV coordinates."""
    result = uv.copy()
    result[:, 0] = result[:, 0] * tile_x + offset_x
    result[:, 1] = result[:, 1] * tile_y + offset_y
    return result


# ============================================================================
# Cylindrical projection
# ============================================================================

def fit_cylinder_axis(vertices: np.ndarray, normals: np.ndarray) -> np.ndarray:
    """Estimate the axis of a cylindrical surface from vertex normals.

    For a perfect cylinder, all surface normals are perpendicular to the axis.
    The axis direction is therefore the eigenvector of the normal covariance
    matrix corresponding to the SMALLEST eigenvalue (the direction in which
    the normals vary least).
    """
    if len(normals) < 3:
        # Fall back to face-averaged normal direction
        return np.array([0.0, 0.0, 1.0])

    n_centered = normals - normals.mean(axis=0)
    cov = np.cov(n_centered.T)

    try:
        eigvals, eigvecs = np.linalg.eigh(cov)
    except np.linalg.LinAlgError:
        return np.array([0.0, 0.0, 1.0])

    # eigh returns eigenvalues in ascending order; the smallest is at index 0
    axis = eigvecs[:, 0]
    norm = np.linalg.norm(axis)
    if norm < 1e-10:
        return np.array([0.0, 0.0, 1.0])
    return axis / norm


def project_cylindrical(vertices: np.ndarray,
                        axis_origin: np.ndarray,
                        axis_direction: np.ndarray) -> np.ndarray:
    """Project vertices onto a cylinder.

    Args:
        vertices: (N, 3) point coordinates
        axis_origin: (3,) point on the cylinder axis
        axis_direction: (3,) unit vector along the axis

    Returns:
        (N, 2) UV coordinates: U is angle around axis [0,1], V is height
    """
    direction = np.asarray(axis_direction, dtype=float)
    direction = direction / np.linalg.norm(direction)

    rel = vertices - axis_origin

    # Height along axis
    h = np.dot(rel, direction)

    # Component perpendicular to axis
    perp = rel - h[:, np.newaxis] * direction

    # Build two perpendicular reference axes for angle measurement
    ref = np.array([1.0, 0.0, 0.0])
    if abs(np.dot(direction, ref)) > 0.9:
        ref = np.array([0.0, 1.0, 0.0])
    u_axis = np.cross(direction, ref)
    u_axis /= np.linalg.norm(u_axis)
    v_axis = np.cross(direction, u_axis)

    x = np.dot(perp, u_axis)
    y = np.dot(perp, v_axis)
    angle = np.arctan2(y, x)            # -pi to +pi
    u = (angle + np.pi) / (2 * np.pi)   # 0 to 1

    return np.column_stack([u, h])


# ============================================================================
# Box / triplanar projection
# ============================================================================

def project_box(vertices: np.ndarray, vertex_normals: np.ndarray) -> np.ndarray:
    """Triplanar (box) projection.

    Each vertex is projected onto the axis-aligned plane perpendicular to
    its dominant normal direction.  Works well for cube-like or boxy meshes
    where different regions face different cardinal directions.
    """
    abs_n = np.abs(vertex_normals)
    dominant = np.argmax(abs_n, axis=1)  # 0=X, 1=Y, 2=Z

    uv = np.zeros((len(vertices), 2), dtype=float)

    mask_x = dominant == 0
    uv[mask_x, 0] = vertices[mask_x, 1]
    uv[mask_x, 1] = vertices[mask_x, 2]

    mask_y = dominant == 1
    uv[mask_y, 0] = vertices[mask_y, 0]
    uv[mask_y, 1] = vertices[mask_y, 2]

    mask_z = dominant == 2
    uv[mask_z, 0] = vertices[mask_z, 0]
    uv[mask_z, 1] = vertices[mask_z, 1]

    return uv


# ============================================================================
# Curved-surface auto-detection
# ============================================================================

def detect_surface_type(vertices: np.ndarray, normals: np.ndarray) -> str:
    """Heuristically classify a region as planar, cylindrical, or box.

    Uses PCA on the vertex normals:
        - All eigenvalues tiny  → planar (normals don't vary)
        - One large eigenvalue  → cylindrical (normals rotate around an axis)
        - Multiple large        → box / general (normals point many directions)
    """
    if len(vertices) < 4 or len(normals) < 4:
        return 'planar'

    n_centered = normals - normals.mean(axis=0)
    try:
        cov = np.cov(n_centered.T)
        eigvals = np.sort(np.linalg.eigvalsh(cov))[::-1]  # descending
    except np.linalg.LinAlgError:
        return 'planar'

    total = float(eigvals.sum())
    if total < 1e-8:
        return 'planar'

    e0, e1, e2 = (eigvals / total).tolist()

    # Almost no variation in normals → flat surface
    if e0 < 0.05:
        return 'planar'
    # One dominant eigenvalue, others small → cylindrical curve
    if e0 > 0.65 and e1 < 0.30:
        return 'cylindrical'
    # Otherwise treat as box / general curved surface
    return 'box'


# ============================================================================
# UV rotation (used by both preview and displacement)
# ============================================================================

def rotate_uv(uv: np.ndarray, degrees: float) -> np.ndarray:
    """Rotate UV coordinates around (0.5, 0.5) by the given angle in degrees.

    Works with tiling because rotation is applied before the fractional
    wrap used during sampling.
    """
    if abs(degrees) < 1e-6:
        return uv
    theta = np.radians(degrees)
    c, s = np.cos(theta), np.sin(theta)
    centered = uv - 0.5
    rotated = np.column_stack([
        c * centered[:, 0] - s * centered[:, 1],
        s * centered[:, 0] + c * centered[:, 1],
    ])
    return rotated + 0.5


# ============================================================================
# Whole-mesh UV generation (used by the texture-preview view mode)
# ============================================================================

def generate_mesh_uv(vertices: np.ndarray,
                     vertex_normals: np.ndarray,
                     mode: str = "planar",
                     tile_x: float = 1.0,
                     tile_y: float = 1.0,
                     rotation_deg: float = 0.0) -> np.ndarray:
    """Generate per-vertex (u, v) coordinates for an entire mesh.

    Used for the real-time texture preview overlay. The selected `mode`
    controls which projection is used. 'auto' picks planar/cylindrical/box
    based on the distribution of vertex normals.
    """
    verts = np.asarray(vertices, dtype=float)
    normals = np.asarray(vertex_normals, dtype=float)

    effective_mode = mode
    if mode == "auto":
        effective_mode = detect_surface_type(verts, normals)

    if effective_mode == "cylindrical":
        axis = fit_cylinder_axis(verts, normals)
        origin = verts.mean(axis=0)
        uv = project_cylindrical(verts, origin, axis)
        # project_cylindrical returns (u in [0,1], height) — normalize v
        v = uv[:, 1]
        v_min, v_max = float(v.min()), float(v.max())
        if v_max - v_min > 1e-10:
            v = (v - v_min) / (v_max - v_min)
        else:
            v = np.zeros_like(v)
        uv = np.column_stack([uv[:, 0], v])
    elif effective_mode == "box":
        uv = project_box(verts, normals)
        uv = normalize_uv(uv)
    else:  # planar
        # Use global best-fit plane from averaged vertex normals
        center, axis_u, axis_v, _ = compute_local_frame(verts, normals)
        uv = project_planar(verts, center, axis_u, axis_v)
        uv = normalize_uv(uv)

    uv = rotate_uv(uv, rotation_deg)
    uv = uv * np.array([tile_x, tile_y])
    return uv

