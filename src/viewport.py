"""3D viewport widget using PyVista and VTK for mesh visualization and picking."""

import numpy as np
import pyvista as pv
import trimesh
import vtk
from PySide6.QtCore import Signal, Qt, QEvent
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget, QVBoxLayout
from pyvistaqt import QtInteractor


class ViewportWidget(QWidget):
    """3D viewport with mesh display and face picking."""

    face_picked = Signal(int)  # Emitted when a face is clicked in selection mode
    face_brushed = Signal(int)  # Emitted per face as the user drags in brush mode
    brush_painted = Signal(object, float)  # world point (np.ndarray(3,)), radius
    brush_stroke_ended = Signal()  # Emitted when user releases mouse after a brush stroke

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selection_mode = False
        self._brush_mode = False
        self._painting = False
        self._mesh_actor = None
        self._selection_actor = None
        self._current_polydata: pv.PolyData | None = None
        self._wireframe_visible = False
        self._brush_radius = 5.0  # world units
        self._view_mode = "shaded"  # "shaded" | "texture" | "displacement"
        self._texture_image = None  # PIL.Image for preview
        self._texture_params = None  # dict(mode, tile_x, tile_y, rot, tile_enabled)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.plotter = QtInteractor(self)
        layout.addWidget(self.plotter.interactor)

        # Configure plotter
        self.plotter.set_background('#2b2b2b')
        self.plotter.add_axes()
        self.plotter.enable_anti_aliasing('ssaa')

        # Set up cell picker
        self._picker = vtk.vtkCellPicker()
        self._picker.SetTolerance(0.005)

        # Add VTK-level observers (used for non-brush face picking)
        self.plotter.interactor.AddObserver(
            vtk.vtkCommand.LeftButtonPressEvent, self._on_left_press, 100.0
        )
        self.plotter.interactor.AddObserver(
            vtk.vtkCommand.LeftButtonReleaseEvent, self._on_left_release, 100.0
        )
        self.plotter.interactor.AddObserver(
            vtk.vtkCommand.MouseMoveEvent, self._on_mouse_move, 100.0
        )

        # Qt-level event filter — authoritative source of mouse button state.
        # The VTK bridge occasionally drops release events, so we use Qt's own
        # press / move / release events to drive brush painting.
        self.plotter.interactor.installEventFilter(self)

    @property
    def selection_mode(self) -> bool:
        return self._selection_mode

    @selection_mode.setter
    def selection_mode(self, enabled: bool):
        self._selection_mode = enabled
        from PySide6.QtGui import QCursor
        if enabled:
            self.plotter.interactor.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        else:
            self.plotter.interactor.unsetCursor()

    @property
    def brush_mode(self) -> bool:
        return self._brush_mode

    @brush_mode.setter
    def brush_mode(self, enabled: bool):
        self._brush_mode = enabled

    @property
    def brush_radius(self) -> float:
        return self._brush_radius

    @brush_radius.setter
    def brush_radius(self, r: float):
        self._brush_radius = float(max(0.0, r))

    def _pick_world_point(self):
        """Return the world-space (x,y,z) under the cursor, or None."""
        pos = self.plotter.interactor.GetEventPosition()
        if self._picker.Pick(pos[0], pos[1], 0, self.plotter.renderer):
            return np.array(self._picker.GetPickPosition(), dtype=float)
        return None

    def _pick_cell(self):
        pos = self.plotter.interactor.GetEventPosition()
        self._picker.Pick(pos[0], pos[1], 0, self.plotter.renderer)
        return self._picker.GetCellId()

    def _left_button_held(self) -> bool:
        """Authoritative check: is Qt actually reporting the left button down?"""
        return bool(QGuiApplication.mouseButtons() & Qt.MouseButton.LeftButton)

    def _on_left_press(self, obj, event):
        """Handle left click - pick cell in non-brush selection modes only.

        Brush mode is fully handled by the Qt eventFilter below so that mouse
        release is detected reliably.
        """
        if not self._selection_mode or self._brush_mode:
            return  # Brush handled by Qt filter; non-selection: let VTK orbit

        cell_id = self._pick_cell()
        if cell_id >= 0:
            self.face_picked.emit(cell_id)
            getattr(obj, "SetAbortFlag", lambda _x: None)(1)

    def _on_mouse_move(self, obj, event):
        # Safety net: if for any reason _painting is set but the button isn't
        # actually held, force-stop the stroke. Brush painting itself is driven
        # by Qt events, not this observer.
        if self._painting and not self._left_button_held():
            self._painting = False
            self.brush_stroke_ended.emit()

    def _on_left_release(self, obj, event):
        if self._painting:
            self._painting = False
            self.brush_stroke_ended.emit()
            getattr(obj, "SetAbortFlag", lambda _x: None)(1)

    # ------------------------------------------------------------------
    # Qt-level event filter — drives the brush so release is reliable
    # ------------------------------------------------------------------
    def eventFilter(self, watched, event):
        if watched is not self.plotter.interactor:
            return super().eventFilter(watched, event)

        if not (self._selection_mode and self._brush_mode):
            return False  # Pass-through: allow VTK orbit / zoom / etc.

        etype = event.type()

        if etype == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self._painting = True
                pt = self._pick_world_point()
                if pt is not None:
                    self.brush_painted.emit(pt, self._brush_radius)
                return True  # Consume so VTK doesn't start orbit on LMB
            # Right/middle buttons fall through → VTK handles orbit/pan
            return False

        if etype == QEvent.Type.MouseMove:
            # Only paint while LMB is genuinely held. Hover = nothing.
            if self._painting and self._left_button_held():
                pt = self._pick_world_point()
                if pt is not None:
                    self.brush_painted.emit(pt, self._brush_radius)
                return True
            # If we thought we were painting but button was released elsewhere,
            # stop immediately.
            if self._painting and not self._left_button_held():
                self._painting = False
                self.brush_stroke_ended.emit()
            return False  # Let VTK handle hover / right-drag orbit

        if etype == QEvent.Type.MouseButtonRelease:
            if event.button() == Qt.MouseButton.LeftButton and self._painting:
                self._painting = False
                self.brush_stroke_ended.emit()
                return True
            return False

        if etype in (QEvent.Type.Leave, QEvent.Type.FocusOut):
            # Cursor left the widget — abort any in-progress stroke
            if self._painting:
                self._painting = False
                self.brush_stroke_ended.emit()
            return False

        return False

    def display_mesh(self, polydata: pv.PolyData, selection_mask: np.ndarray | None = None,
                     reset_camera: bool = True):
        """Display a mesh in the viewport.

        Args:
            polydata: PyVista PolyData to display
            selection_mask: boolean array, True for selected faces
        """
        self._current_polydata = polydata
        self.plotter.clear()
        self.plotter.add_axes()

        if selection_mask is not None and len(selection_mask) == polydata.n_cells:
            # Color by selection
            colors = np.where(selection_mask, 1.0, 0.0)
            polydata.cell_data['selection'] = colors
            self._mesh_actor = self.plotter.add_mesh(
                polydata,
                scalars='selection',
                cmap=['#b0b0b0', '#ff4444'],
                show_edges=self._wireframe_visible,
                clim=[0, 1],
                show_scalar_bar=False,
                name='main_mesh',
            )
        else:
            self._mesh_actor = self.plotter.add_mesh(
                polydata,
                color='#b0b0b0',
                show_edges=self._wireframe_visible,
                name='main_mesh',
            )

        if reset_camera:
            self.plotter.reset_camera()

    def update_selection_display(self, selection_mask: np.ndarray):
        """Update selection highlighting without resetting camera."""
        if self._current_polydata is None:
            return

        polydata = self._current_polydata
        # Guard against stale masks (e.g. after a mesh change / undo)
        if len(selection_mask) != polydata.n_cells:
            return
        colors = np.where(selection_mask, 1.0, 0.0)
        polydata.cell_data['selection'] = colors

        # In-place scalar update — preserves camera
        self.plotter.remove_actor('main_mesh', reset_camera=False)
        self._mesh_actor = self.plotter.add_mesh(
            polydata,
            scalars='selection',
            cmap=['#b0b0b0', '#ff4444'],
            show_edges=self._wireframe_visible,
            clim=[0, 1],
            show_scalar_bar=False,
            name='main_mesh',
            reset_camera=False,
        )
        self.plotter.render()

    def display_preview(self, original: pv.PolyData, displaced: pv.PolyData,
                        selection_mask: np.ndarray | None = None):
        """Display displaced mesh alongside or replacing original."""
        self.plotter.clear()
        self.plotter.add_axes()

        # Show displaced mesh
        self._current_polydata = displaced
        self._mesh_actor = self.plotter.add_mesh(
            displaced,
            color='#90c0f0',
            show_edges=self._wireframe_visible,
            name='main_mesh',
        )
        self.plotter.reset_camera()

    def display_texture_preview(self, polydata: pv.PolyData, pil_image,
                                 mode: str = "planar",
                                 tile_x: float = 1.0, tile_y: float = 1.0,
                                 rotation: float = 0.0,
                                 tile_enabled: bool = True,
                                 reset_camera: bool = False):
        """Overlay the texture onto the mesh using computed UVs.

        This renders the mesh with the texture sampled from PIL image,
        giving a live 2D texture preview *on* the mesh surface.
        """
        from .projection import generate_mesh_uv

        self._current_polydata = polydata
        self._texture_image = pil_image
        self._texture_params = dict(mode=mode, tile_x=tile_x, tile_y=tile_y,
                                    rotation=rotation, tile_enabled=tile_enabled)

        # Compute per-vertex UVs using the mesh's own vertices/normals
        verts = np.asarray(polydata.points)
        if 'Normals' in polydata.point_data.keys():
            normals = np.asarray(polydata.point_data['Normals'])
        else:
            polydata.compute_normals(inplace=True, point_normals=True,
                                      cell_normals=False)
            normals = np.asarray(polydata.point_data['Normals'])

        uv = generate_mesh_uv(verts, normals, mode=mode,
                              tile_x=tile_x, tile_y=tile_y,
                              rotation_deg=rotation)
        polydata.active_texture_coordinates = uv.astype(np.float32)

        # Build a VTK texture from the PIL image
        img = pil_image.convert('RGB')
        arr = np.asarray(img)
        tex = pv.numpy_to_texture(arr)
        try:
            tex.repeat = bool(tile_enabled)
        except Exception:
            pass

        self.plotter.remove_actor('main_mesh', reset_camera=False)
        self._mesh_actor = self.plotter.add_mesh(
            polydata,
            texture=tex,
            show_edges=self._wireframe_visible,
            name='main_mesh',
            reset_camera=reset_camera,
        )
        if reset_camera:
            self.plotter.reset_camera()
        self.plotter.render()

    def set_view_mode(self, mode: str):
        """Switch between 'shaded', 'texture', 'displacement' views."""
        self._view_mode = mode

    def toggle_wireframe(self) -> bool:
        """Toggle wireframe overlay. Returns new state."""
        self._wireframe_visible = not self._wireframe_visible
        if self._current_polydata is not None:
            # Re-display with new edge visibility
            if 'selection' in self._current_polydata.cell_data:
                mask = self._current_polydata.cell_data['selection'] > 0.5
                self.display_mesh(self._current_polydata, mask)
            else:
                self.display_mesh(self._current_polydata)
        return self._wireframe_visible

    def fit_view(self):
        """Reset camera to fit the entire mesh."""
        self.plotter.reset_camera()

    def clear_display(self):
        """Remove all actors."""
        self.plotter.clear()
        self.plotter.add_axes()
        self._current_polydata = None
        self._mesh_actor = None

    def close(self):
        self.plotter.close()
