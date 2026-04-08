"""Main application window - assembles all panels and manages workflow."""

import copy
from collections import deque
import numpy as np
from pathlib import Path
from PIL import Image

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QScrollArea,
    QSplitter, QFileDialog, QMessageBox, QMenuBar, QStatusBar,
    QSizePolicy,
)

from .config import AppConfig, DisplacementParams
from .mesh_manager import MeshManager
from .selection import SelectionManager
from .texture_manager import TextureManager
from .viewport import ViewportWidget
from .displacement import apply_displacement
from .workers import DisplacementWorker, ExportWorker
from .panels import ImportPanel, TexturePanel, ParametersPanel, SelectionPanel, ActionPanel


class MainWindow(QMainWindow):
    """Main application window for Texture STL Tool."""

    def __init__(self, config: AppConfig, tex_manager: TextureManager):
        super().__init__()
        self.config = config
        self.tex_manager = tex_manager
        self.mesh_mgr = MeshManager()
        self.selection = SelectionManager()

        self._current_texture: Image.Image | None = None
        self._preview_mesh = None
        self._displacement_worker: DisplacementWorker | None = None
        self._selection_type = "Single Face"
        self._undo_stack: deque = deque(maxlen=10)
        self._sel_undo_stack: deque = deque(maxlen=100)
        self._brush_stroke_active: bool = False
        self._brush_add_mode: bool = True
        self._view_mode: str = "shaded"
        self._tile_enabled: bool = True

        self.setWindowTitle("Texture STL Tool")
        self.setMinimumSize(1200, 700)
        self._restore_geometry()
        self._build_ui()
        self._build_menu()
        self._connect_signals()

        # Ctrl+Z → undo last applied displacement
        self._undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        self._undo_shortcut.activated.connect(self._on_undo)

        self.statusBar().showMessage("Ready. Import an STL file to begin.")

    def _restore_geometry(self):
        geo = self.config.window_geometry
        if geo:
            self.setGeometry(geo.get("x", 100), geo.get("y", 100),
                             geo.get("w", 1200), geo.get("h", 800))

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- Left panel (scrollable) ---
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setMaximumWidth(300)
        left_scroll.setMinimumWidth(220)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.import_panel = ImportPanel()
        left_layout.addWidget(self.import_panel)

        self.texture_panel = TexturePanel(self.tex_manager)
        left_layout.addWidget(self.texture_panel)

        self.params_panel = ParametersPanel()
        left_layout.addWidget(self.params_panel)

        left_layout.addStretch()
        left_scroll.setWidget(left_widget)
        splitter.addWidget(left_scroll)

        # --- Center: 3D viewport ---
        self.viewport = ViewportWidget()
        self.viewport.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        splitter.addWidget(self.viewport)

        # --- Right panel (scrollable) ---
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_scroll.setMaximumWidth(280)
        right_scroll.setMinimumWidth(200)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.selection_panel = SelectionPanel()
        right_layout.addWidget(self.selection_panel)

        self.action_panel = ActionPanel()
        right_layout.addWidget(self.action_panel)

        right_layout.addStretch()
        right_scroll.setWidget(right_widget)
        splitter.addWidget(right_scroll)

        # Set splitter proportions
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)

        main_layout.addWidget(splitter)

    def _build_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        file_menu.addAction("Import STL...", self._on_import_menu)
        file_menu.addAction("Export STL...", self._on_export)
        file_menu.addSeparator()

        # Recent files
        self._recent_menu = file_menu.addMenu("Recent Files")
        self._update_recent_menu()

        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)

        view_menu = menubar.addMenu("View")
        view_menu.addAction("Fit View", self.viewport.fit_view)
        view_menu.addAction("Toggle Wireframe", self.viewport.toggle_wireframe)
        view_menu.addAction("Reset to Original", self._on_reset)

        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About", self._on_about)

    def _update_recent_menu(self):
        self._recent_menu.clear()
        for path in self.config.recent_files[:10]:
            name = Path(path).name
            self._recent_menu.addAction(name, lambda p=path: self._load_stl(p))

    def _connect_signals(self):
        # Import
        self.import_panel.import_requested.connect(self._load_stl)
        self.import_panel.reset_requested.connect(self._on_reset)

        # Texture
        self.texture_panel.texture_selected.connect(self._on_texture_selected)

        # Selection
        self.selection_panel.selection_mode_changed.connect(self._on_selection_mode)
        self.selection_panel.selection_type_changed.connect(self._on_selection_type)
        self.selection_panel.clear_selection.connect(self._on_clear_selection)
        self.selection_panel.select_all.connect(self._on_select_all)
        self.selection_panel.invert_selection.connect(self._on_invert_selection)
        self.selection_panel.brush_radius_changed.connect(self._on_brush_radius)
        self.selection_panel.brush_add_changed.connect(self._on_brush_add)

        # Viewport picking
        self.viewport.face_picked.connect(self._on_face_picked)
        self.viewport.face_brushed.connect(self._on_face_brushed)
        self.viewport.brush_painted.connect(self._on_brush_painted)
        self.viewport.brush_stroke_ended.connect(self._on_brush_stroke_ended)

        # View mode + texture preview
        self.action_panel.view_mode_changed.connect(self._on_view_mode_changed)
        self.action_panel.tile_texture_changed.connect(self._on_tile_toggled)
        self.params_panel.params_changed.connect(self._on_params_changed)

        # Actions
        self.action_panel.preview_requested.connect(self._on_preview)
        self.action_panel.apply_requested.connect(self._on_apply)
        self.action_panel.export_requested.connect(self._on_export)
        self.action_panel.wireframe_toggled.connect(self.viewport.toggle_wireframe)
        self.action_panel.fit_view_requested.connect(self.viewport.fit_view)

    # --- Mesh loading ---

    def _on_import_menu(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open STL File", self.config.last_import_dir,
            "STL Files (*.stl);;All Files (*)"
        )
        if path:
            self._load_stl(path)

    def _load_stl(self, path: str):
        try:
            self.mesh_mgr.load_stl(path)
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to load STL:\n{e}")
            return

        self.config.add_recent_file(path)
        self.config.last_import_dir = str(Path(path).parent)
        self.config.save()
        self._update_recent_menu()

        # Update selection manager
        self.selection.set_mesh(self.mesh_mgr.mesh)
        self.selection.clear()

        # Any prior undo snapshots reference the old mesh — drop them
        self._undo_stack.clear()
        self._sel_undo_stack.clear()

        # Display
        polydata = self.mesh_mgr.to_pyvista()
        self.viewport.display_mesh(polydata)

        # Update panels
        self.import_panel.update_info(self.mesh_mgr.get_stats())
        self.action_panel.set_mesh_loaded(True)
        self._update_action_readiness()
        self.selection_panel.update_count(0)

        self.statusBar().showMessage(f"Loaded: {Path(path).name}")

    def _on_reset(self):
        mesh = self.mesh_mgr.reset_to_original()
        if mesh is None:
            return
        self.selection.set_mesh(mesh)
        self.selection.clear()
        self._undo_stack.clear()
        self._sel_undo_stack.clear()
        polydata = self.mesh_mgr.to_pyvista()
        self.viewport.display_mesh(polydata)
        self.import_panel.update_info(self.mesh_mgr.get_stats())
        self.selection_panel.update_count(0)
        self._preview_mesh = None
        self.statusBar().showMessage("Reset to original mesh.")

    # --- Texture ---

    def _on_texture_selected(self, img: Image.Image):
        self._current_texture = img
        self._update_action_readiness()
        self.statusBar().showMessage("Texture loaded.")

    # --- Selection ---

    def _on_selection_mode(self, enabled: bool):
        self.viewport.selection_mode = enabled
        status = "Selection mode ON - click faces to select" if enabled else "Selection mode OFF"
        self.statusBar().showMessage(status)

    def _on_selection_type(self, sel_type: str):
        self._selection_type = sel_type
        self.viewport.brush_mode = (sel_type == "Brush")

    def _on_face_brushed(self, face_id: int):
        if self.mesh_mgr.mesh is None:
            return
        # One undo entry per stroke, not per painted face
        if not self._brush_stroke_active:
            self._push_sel_undo()
            self._brush_stroke_active = True
        self.selection.add_face(face_id)
        self._refresh_selection_display()

    def _on_face_picked(self, face_id: int):
        if self.mesh_mgr.mesh is None:
            return

        self._push_sel_undo()
        if self._selection_type == "Single Face":
            self.selection.select_face(face_id)
        elif self._selection_type == "Connected Region":
            threshold = self.selection_panel.spin_angle.value()
            self.selection.select_connected_region(face_id, threshold)
        elif self._selection_type == "By Normal":
            threshold = self.selection_panel.spin_angle.value()
            normal = self.mesh_mgr.mesh.face_normals[face_id]
            self.selection.select_by_normal(normal, threshold)

        self._refresh_selection_display()

    def _on_brush_stroke_ended(self):
        self._brush_stroke_active = False

    def _on_brush_radius(self, r: float):
        self.viewport.brush_radius = r

    def _on_brush_add(self, add: bool):
        self._brush_add_mode = add

    def _on_brush_painted(self, world_point, radius: float):
        if self.mesh_mgr.mesh is None:
            return
        if not self._brush_stroke_active:
            self._push_sel_undo()
            self._brush_stroke_active = True
        self.selection.brush_select(world_point, radius,
                                    add=self._brush_add_mode)
        self._refresh_selection_display()

    def _on_view_mode_changed(self, mode: str):
        self._view_mode = mode
        self._refresh_view()

    def _on_tile_toggled(self, enabled: bool):
        self._tile_enabled = bool(enabled)
        if self._view_mode == "texture":
            self._refresh_view()

    def _on_params_changed(self):
        # Live update the texture preview if that view is active
        if self._view_mode == "texture":
            self._refresh_view()

    def _refresh_view(self):
        """Redraw the viewport according to the active view mode."""
        if self.mesh_mgr.mesh is None:
            return
        polydata = self.mesh_mgr.to_pyvista()

        if self._view_mode == "texture" and self._current_texture is not None:
            params = self.params_panel.get_params()
            self.viewport.display_texture_preview(
                polydata,
                self._current_texture,
                mode=params.projection_mode,
                tile_x=params.tile_x,
                tile_y=params.tile_y,
                rotation=params.rotation,
                tile_enabled=self._tile_enabled,
                reset_camera=False,
            )
        elif self._view_mode == "displacement" and self._preview_mesh is not None:
            displaced = self.mesh_mgr.to_pyvista(self._preview_mesh)
            self.viewport.display_preview(polydata, displaced)
        else:
            n_faces = len(self.mesh_mgr.mesh.faces)
            mask = self.selection.get_selection_mask(n_faces)
            self.viewport.display_mesh(polydata, mask, reset_camera=False)

    def _on_clear_selection(self):
        self._push_sel_undo()
        self.selection.clear()
        self._refresh_selection_display()

    def _on_select_all(self):
        self._push_sel_undo()
        self.selection.select_all()
        self._refresh_selection_display()

    def _on_invert_selection(self):
        self._push_sel_undo()
        self.selection.invert_selection()
        self._refresh_selection_display()

    def _refresh_selection_display(self):
        if self.mesh_mgr.mesh is None:
            return
        n_faces = len(self.mesh_mgr.mesh.faces)
        mask = self.selection.get_selection_mask(n_faces)

        # Update selection highlight in place — preserves camera
        self.viewport.update_selection_display(mask)

        self.selection_panel.update_count(self.selection.count)
        self._update_action_readiness()

    # --- Displacement ---

    def _update_action_readiness(self):
        ready = (
            self.mesh_mgr.mesh is not None
            and self.selection.count > 0
            and self._current_texture is not None
        )
        self.action_panel.set_ready_for_displacement(ready)

    def _on_preview(self):
        if not self._can_displace():
            return

        params = self.params_panel.get_params()
        selected = self.selection.get_selected_array()

        self.action_panel.set_status("Computing preview...")
        self.action_panel.show_progress(0)

        self._displacement_worker = DisplacementWorker(
            self.mesh_mgr.mesh, selected, self._current_texture, params
        )
        self._displacement_worker.progress.connect(self.action_panel.show_progress)
        self._displacement_worker.finished.connect(self._on_preview_done)
        self._displacement_worker.error.connect(self._on_displacement_error)
        self._displacement_worker.start()

    def _on_preview_done(self, result_mesh):
        self._preview_mesh = result_mesh
        displaced_pd = self.mesh_mgr.to_pyvista(result_mesh)
        original_pd = self.mesh_mgr.to_pyvista()
        self.viewport.display_preview(original_pd, displaced_pd)

        stats_msg = f"Preview: {len(result_mesh.faces):,} triangles, {len(result_mesh.vertices):,} vertices"
        self.action_panel.set_status(stats_msg)
        self.action_panel.hide_progress()
        self.statusBar().showMessage("Preview ready. Click 'Apply' to commit changes.")

    def _push_undo(self):
        if self.mesh_mgr.mesh is not None:
            self._undo_stack.append(self.mesh_mgr.mesh.copy())

    def _push_sel_undo(self):
        self._sel_undo_stack.append(set(self.selection.selected_faces))

    def _on_undo(self):
        # Selection undo takes priority over mesh undo
        if self._sel_undo_stack:
            prev_sel = self._sel_undo_stack.pop()
            self.selection.selected_faces = prev_sel
            self._refresh_selection_display()
            self.statusBar().showMessage("Undo: selection reverted.")
            return
        if not self._undo_stack:
            self.statusBar().showMessage("Nothing to undo.")
            return
        prev = self._undo_stack.pop()
        self.mesh_mgr.update_mesh(prev)
        self.selection.set_mesh(prev)
        self.selection.clear()
        self._sel_undo_stack.clear()
        self._preview_mesh = None
        polydata = self.mesh_mgr.to_pyvista()
        self.viewport.display_mesh(polydata, reset_camera=False)
        self.import_panel.update_info(self.mesh_mgr.get_stats())
        self.selection_panel.update_count(0)
        self.statusBar().showMessage("Undo: reverted last change.")

    def _on_apply(self):
        if self._preview_mesh is not None:
            # Commit the previewed changes
            self._push_undo()
            self.mesh_mgr.update_mesh(self._preview_mesh)
            self.selection.set_mesh(self._preview_mesh)
            self.selection.clear()
            self._sel_undo_stack.clear()
            self._preview_mesh = None

            polydata = self.mesh_mgr.to_pyvista()
            self.viewport.display_mesh(polydata)
            self.import_panel.update_info(self.mesh_mgr.get_stats())
            self.selection_panel.update_count(0)
            self.action_panel.set_status("Changes applied.")
            self.statusBar().showMessage("Displacement applied to mesh.")
        else:
            # No preview - run displacement and apply directly
            if not self._can_displace():
                return

            params = self.params_panel.get_params()
            selected = self.selection.get_selected_array()

            self._push_undo()
            self.action_panel.set_status("Applying displacement...")
            self.action_panel.show_progress(0)

            self._displacement_worker = DisplacementWorker(
                self.mesh_mgr.mesh, selected, self._current_texture, params
            )
            self._displacement_worker.progress.connect(self.action_panel.show_progress)
            self._displacement_worker.finished.connect(self._on_apply_done)
            self._displacement_worker.error.connect(self._on_displacement_error)
            self._displacement_worker.start()

    def _on_apply_done(self, result_mesh):
        self.mesh_mgr.update_mesh(result_mesh)
        self.selection.set_mesh(result_mesh)
        self.selection.clear()
        # Selection snapshots from the previous mesh no longer match
        self._sel_undo_stack.clear()

        polydata = self.mesh_mgr.to_pyvista()
        self.viewport.display_mesh(polydata)
        self.import_panel.update_info(self.mesh_mgr.get_stats())
        self.selection_panel.update_count(0)
        self.action_panel.hide_progress()
        self.action_panel.set_status("Displacement applied.")
        self.statusBar().showMessage("Displacement committed to mesh.")

    def _on_displacement_error(self, error_msg: str):
        self.action_panel.hide_progress()
        self.action_panel.set_status(f"Error: {error_msg}")
        QMessageBox.critical(self, "Displacement Error", error_msg)

    def _can_displace(self) -> bool:
        if self.mesh_mgr.mesh is None:
            QMessageBox.warning(self, "No Mesh", "Please import an STL file first.")
            return False
        if self.selection.count == 0:
            QMessageBox.warning(self, "No Selection", "Please select faces on the mesh first.")
            return False
        if self._current_texture is None:
            QMessageBox.warning(self, "No Texture", "Please load a texture image first.")
            return False
        return True

    # --- Export ---

    def _on_export(self):
        if self.mesh_mgr.mesh is None:
            QMessageBox.warning(self, "No Mesh", "No mesh to export.")
            return

        # Warn if high triangle count
        stats = self.mesh_mgr.get_stats()
        if stats and stats.triangle_count > 1_000_000:
            reply = QMessageBox.question(
                self, "Large Mesh",
                f"The mesh has {stats.triangle_count:,} triangles.\n"
                "Export may produce a large file. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return

        default_name = ""
        if self.mesh_mgr.file_path:
            p = Path(self.mesh_mgr.file_path)
            default_name = str(p.parent / f"{p.stem}_textured.stl")

        path, _ = QFileDialog.getSaveFileName(
            self, "Export STL", default_name or self.config.last_export_dir,
            "STL Files (*.stl);;All Files (*)"
        )
        if not path:
            return

        self.config.last_export_dir = str(Path(path).parent)
        self.config.save()

        try:
            self.action_panel.set_status("Exporting...")
            export_mesh = self._preview_mesh if self._preview_mesh else self.mesh_mgr.mesh
            self.mesh_mgr.export_stl(path, export_mesh)
            self.action_panel.set_status(f"Exported to {Path(path).name}")
            self.statusBar().showMessage(f"Exported: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export:\n{e}")

    # --- Misc ---

    def _on_about(self):
        QMessageBox.about(
            self, "About Texture STL Tool",
            "Texture STL Tool v1.0\n\n"
            "Apply grayscale textures as real geometric displacement\n"
            "to STL meshes for 3D printing and manufacturing.\n\n"
            "The exported STL contains the texture permanently\n"
            "embedded in the mesh geometry."
        )

    def closeEvent(self, event):
        geo = self.geometry()
        self.config.window_geometry = {
            "x": geo.x(), "y": geo.y(),
            "w": geo.width(), "h": geo.height()
        }
        self.config.save()
        self.viewport.close()
        super().closeEvent(event)
