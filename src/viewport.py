"""3D viewport widget using PyVista and VTK for mesh visualization and picking."""

import numpy as np
import pyvista as pv
import trimesh
import vtk
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout
from pyvistaqt import QtInteractor


class ViewportWidget(QWidget):
    """3D viewport with mesh display and face picking."""

    face_picked = Signal(int)  # Emitted when a face is clicked in selection mode

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selection_mode = False
        self._mesh_actor = None
        self._selection_actor = None
        self._current_polydata: pv.PolyData | None = None
        self._wireframe_visible = False

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

        # Add click observer
        self.plotter.interactor.AddObserver(
            vtk.vtkCommand.LeftButtonPressEvent, self._on_left_press, 100.0
        )

    @property
    def selection_mode(self) -> bool:
        return self._selection_mode

    @selection_mode.setter
    def selection_mode(self, enabled: bool):
        self._selection_mode = enabled
        if enabled:
            self.plotter.interactor.SetCursor(Qt.CrossCursor.value
                                               if hasattr(Qt.CrossCursor, 'value')
                                               else 2)
        else:
            self.plotter.interactor.SetCursor(0)

    def _on_left_press(self, obj, event):
        """Handle left click - pick cell if in selection mode."""
        if not self._selection_mode:
            return  # Let VTK handle it normally

        click_pos = self.plotter.interactor.GetEventPosition()
        self._picker.Pick(click_pos[0], click_pos[1], 0, self.plotter.renderer)
        cell_id = self._picker.GetCellId()

        if cell_id >= 0:
            self.face_picked.emit(cell_id)
            # Consume the event to prevent orbit in selection mode
            obj.SetAbortFlag(1)

    def display_mesh(self, polydata: pv.PolyData, selection_mask: np.ndarray | None = None):
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

        self.plotter.reset_camera()

    def update_selection_display(self, selection_mask: np.ndarray):
        """Update selection highlighting without resetting camera."""
        if self._current_polydata is None:
            return

        polydata = self._current_polydata
        colors = np.where(selection_mask, 1.0, 0.0)
        polydata.cell_data['selection'] = colors

        self.plotter.remove_actor('main_mesh')
        self._mesh_actor = self.plotter.add_mesh(
            polydata,
            scalars='selection',
            cmap=['#b0b0b0', '#ff4444'],
            show_edges=self._wireframe_visible,
            clim=[0, 1],
            show_scalar_bar=False,
            name='main_mesh',
        )

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
