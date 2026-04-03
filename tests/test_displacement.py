"""Tests for displacement engine."""

import sys
import os
import numpy as np
import trimesh
from PIL import Image
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.config import DisplacementParams
from src.displacement import (
    load_and_prepare_texture, sample_texture, apply_displacement
)
from src.projection import compute_local_frame, project_planar, normalize_uv


def make_test_mesh():
    """Create a simple flat quad mesh for testing."""
    vertices = np.array([
        [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
        [0.5, 0.5, 0],  # center vertex
    ], dtype=float)
    faces = np.array([
        [0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4],
    ])
    return trimesh.Trimesh(vertices=vertices, faces=faces, process=False)


def make_white_image(size=64):
    """All-white image → maximum displacement."""
    return Image.new('L', (size, size), 255)


def make_black_image(size=64):
    """All-black image → zero displacement."""
    return Image.new('L', (size, size), 0)


def make_gradient_image(size=64):
    """Left-to-right gradient."""
    arr = np.zeros((size, size), dtype=np.uint8)
    for x in range(size):
        arr[:, x] = int(x / (size - 1) * 255)
    return Image.fromarray(arr, mode='L')


class TestTexturePreparation:
    def test_white_image_normalized(self):
        img = make_white_image()
        params = DisplacementParams()
        tex = load_and_prepare_texture(img, params)
        assert tex.shape == (64, 64)
        np.testing.assert_allclose(tex, 1.0, atol=0.01)

    def test_black_image_normalized(self):
        img = make_black_image()
        params = DisplacementParams()
        tex = load_and_prepare_texture(img, params)
        np.testing.assert_allclose(tex, 0.0, atol=0.01)

    def test_invert(self):
        img = make_white_image()
        params = DisplacementParams(invert=True)
        tex = load_and_prepare_texture(img, params)
        np.testing.assert_allclose(tex, 0.0, atol=0.01)

    def test_contrast(self):
        img = make_gradient_image()
        params = DisplacementParams(contrast=2.0)
        tex = load_and_prepare_texture(img, params)
        # Higher contrast should push values further from 0.5
        assert tex.max() >= 0.99
        assert tex.min() <= 0.01

    def test_clamping(self):
        img = make_gradient_image()
        params = DisplacementParams(clamp_min=0.3, clamp_max=0.7)
        tex = load_and_prepare_texture(img, params)
        # After clamping and re-normalization, should span [0, 1]
        assert tex.min() >= 0.0
        assert tex.max() <= 1.0


class TestSampling:
    def test_uniform_sampling(self):
        tex = np.ones((64, 64))
        uv = np.array([[0.0, 0.0], [0.5, 0.5], [1.0, 1.0]])
        vals = sample_texture(tex, uv)
        np.testing.assert_allclose(vals, 1.0, atol=0.01)

    def test_tiling_wrap(self):
        tex = np.ones((64, 64))
        uv = np.array([[1.5, 1.5], [2.0, 2.0], [-0.5, -0.5]])
        vals = sample_texture(tex, uv)
        np.testing.assert_allclose(vals, 1.0, atol=0.01)

    def test_gradient_sampling(self):
        # Horizontal gradient: left=0, right=1
        tex = np.zeros((64, 64))
        for x in range(64):
            tex[:, x] = x / 63.0
        uv = np.array([[0.0, 0.5], [1.0, 0.5]])
        vals = sample_texture(tex, uv)
        assert vals[0] < 0.05  # left edge ~ 0
        assert vals[1] > 0.95  # right edge ~ 1


class TestProjection:
    def test_local_frame_orthogonal(self):
        verts = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=float)
        normals = np.array([[0, 0, 1]], dtype=float)
        center, u, v, n = compute_local_frame(verts, normals)

        # Axes should be orthonormal
        assert abs(np.dot(u, v)) < 1e-10
        assert abs(np.dot(u, n)) < 1e-10
        assert abs(np.dot(v, n)) < 1e-10
        np.testing.assert_allclose(np.linalg.norm(u), 1.0, atol=1e-10)
        np.testing.assert_allclose(np.linalg.norm(v), 1.0, atol=1e-10)

    def test_planar_projection(self):
        center = np.array([0.5, 0.5, 0.0])
        u = np.array([1.0, 0.0, 0.0])
        v = np.array([0.0, 1.0, 0.0])
        verts = np.array([[0, 0, 0], [1, 1, 0]], dtype=float)
        uv = project_planar(verts, center, u, v)
        np.testing.assert_allclose(uv[0], [-0.5, -0.5])
        np.testing.assert_allclose(uv[1], [0.5, 0.5])


class TestDisplacement:
    def test_no_displacement_with_black(self):
        mesh = make_test_mesh()
        original_verts = mesh.vertices.copy()
        img = make_black_image()
        params = DisplacementParams(depth=1.0)
        result = apply_displacement(mesh, np.array([0, 1, 2, 3]), img, params)
        np.testing.assert_allclose(result.vertices, original_verts, atol=1e-10)

    def test_displacement_with_white(self):
        mesh = make_test_mesh()
        original_verts = mesh.vertices.copy()
        img = make_white_image()
        params = DisplacementParams(depth=1.0)
        result = apply_displacement(mesh, np.array([0, 1, 2, 3]), img, params)
        # Vertices should have moved (normals point in Z for flat mesh)
        diff = np.linalg.norm(result.vertices - original_verts, axis=1)
        assert diff.max() > 0.5  # Should have displaced

    def test_depth_scaling(self):
        mesh = make_test_mesh()
        img = make_white_image()

        params1 = DisplacementParams(depth=1.0)
        result1 = apply_displacement(mesh, np.array([0, 1, 2, 3]), img, params1)

        params2 = DisplacementParams(depth=2.0)
        result2 = apply_displacement(mesh, np.array([0, 1, 2, 3]), img, params2)

        diff1 = np.linalg.norm(result1.vertices - mesh.vertices, axis=1).max()
        diff2 = np.linalg.norm(result2.vertices - mesh.vertices, axis=1).max()
        np.testing.assert_allclose(diff2, diff1 * 2, atol=0.1)

    def test_partial_selection(self):
        mesh = make_test_mesh()
        img = make_white_image()
        params = DisplacementParams(depth=1.0)
        # Only select face 0
        result = apply_displacement(mesh, np.array([0]), img, params)
        # Vertices not in face 0 should be unchanged
        face0_verts = set(mesh.faces[0].tolist())
        for i in range(len(mesh.vertices)):
            if i not in face0_verts:
                np.testing.assert_allclose(result.vertices[i], mesh.vertices[i])

    def test_empty_selection_raises(self):
        mesh = make_test_mesh()
        img = make_white_image()
        params = DisplacementParams(depth=1.0)
        with pytest.raises(ValueError):
            apply_displacement(mesh, np.array([], dtype=int), img, params)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
