"""
Dock widget for the TOFPA plugin.

Provides the UI panel (surface parameters, obstacle analysis, export options)
and emits ``calculateClicked`` when the user initiates a calculation.
"""
import logging
import os

from qgis.PyQt import uic
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import QDockWidget, QScrollArea
from .utils.compat import (
    FIELD_INT, FIELD_DOUBLE,
    WKB_LINE_GEOM, WKB_POINT_GEOM, WKB_POLYGON_GEOM,
    LAYER_FILTER_VECTOR,
)

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'tofpa_panel_base.ui'))

logger = logging.getLogger('TOFPA.ui')

# Applied once at widget construction; avoids per-widget setStyleSheet calls (QGIS theme safe)
_TOFPA_STYLE = """
QGroupBox {
    font-weight: bold;
    border: 1px solid #aaaaaa;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 4px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
}
QPushButton#calculateButton {
    background-color: #2c7bb6;
    color: white;
    border-radius: 3px;
    padding: 4px 12px;
    font-weight: bold;
}
QPushButton#calculateButton:hover {
    background-color: #1a5f8e;
}
QPushButton#calculateButton:disabled {
    background-color: #888888;
    color: #cccccc;
}
QPushButton#cancelButton {
    padding: 4px 12px;
}
QDoubleSpinBox[invalid="true"] {
    background-color: #ffcccc;
    border: 1px solid #cc0000;
}
"""


class TofpaDockWidget(QDockWidget, FORM_CLASS):
    closingPlugin = pyqtSignal()
    calculateClicked = pyqtSignal()
    closeClicked = pyqtSignal()

    def __init__(self, iface, parent=None):
        super(TofpaDockWidget, self).__init__(parent)
        self.iface = iface
        self.setupUi(self)

        # Wrap in QScrollArea so the panel survives small / high-DPI screens
        scroll = QScrollArea()
        scroll.setObjectName("tofpaScrollArea")
        scroll.setWidgetResizable(True)
        from qgis.PyQt.QtCore import Qt
        _policy = (
            getattr(Qt.ScrollBarPolicy, "ScrollBarAlwaysOff", None)  # Qt6 / QGIS 4
            or getattr(Qt, "ScrollBarAlwaysOff", None)               # Qt5 / QGIS 3
        )
        if _policy is not None:
            scroll.setHorizontalScrollBarPolicy(_policy)
        scroll.setWidget(self.dockWidgetContents)
        self.setWidget(scroll)

        self.setStyleSheet(_TOFPA_STYLE)

        self.runwayLayerCombo.setFilters(LAYER_FILTER_VECTOR)
        self.runwayLayerCombo.setExceptedLayerList([])
        self.thresholdLayerCombo.setFilters(LAYER_FILTER_VECTOR)
        self.thresholdLayerCombo.setExceptedLayerList([])
        self.obstaclesLayerCombo.setFilters(LAYER_FILTER_VECTOR)
        self.obstaclesLayerCombo.setExceptedLayerList([])

        try:
            self._apply_geometry_filters()
        except Exception:
            logger.debug("Geometry filter application skipped (QGIS not ready)", exc_info=True)

        try:
            from qgis.core import QgsProject
            QgsProject.instance().layersAdded.connect(self._on_layers_changed)
            QgsProject.instance().layersRemoved.connect(self._on_layers_changed)
        except Exception:
            logger.debug("QGIS layers signal connection failed - running outside QGIS", exc_info=True)

        self.obstaclesLayerCombo.layerChanged.connect(self._update_obstacle_fields)
        self.includeObstaclesCheckBox.toggled.connect(self._toggle_obstacles_group)

        self.initialWidthSpin.setValue(180.0)
        self.maxWidthSpin.setValue(1800.0)
        self.clearwayLengthSpin.setValue(0.0)
        self.initialElevationSpin.setValue(0.0)
        self.endElevationSpin.setValue(0.0)
        self.exportToKmzCheckBox.setChecked(False)
        self.exportToAixmCheckBox.setChecked(False)
        self.useSelectedFeatureCheckBox.setChecked(True)
        self.directionCombo.setCurrentIndex(0)

        self.includeObstaclesCheckBox.setChecked(False)
        self.obstacleBufferSpin.setValue(10.0)
        self.minObstacleHeightSpin.setValue(5.0)
        self.enableShadowAnalysisCheckBox.setChecked(False)
        self.shadowToleranceSpin.setValue(5.0)

        self.enableShadowAnalysisCheckBox.toggled.connect(self._toggle_shadow_controls)
        self._toggle_obstacles_group(False)
        self._toggle_shadow_controls(False)

        self.initialWidthSpin.valueChanged.connect(self._validate_widths)
        self.maxWidthSpin.valueChanged.connect(self._validate_widths)
        self.endElevationSpin.valueChanged.connect(self._validate_elevations)
        self.initialElevationSpin.valueChanged.connect(self._validate_elevations)

        self.calculateButton.clicked.connect(self.on_calculate_clicked)
        self.cancelButton.clicked.connect(self.on_close_clicked)

    def _apply_geometry_filters(self):
        from qgis.core import QgsProject

        all_layers = QgsProject.instance().mapLayers().values()
        vector_layers = [layer for layer in all_layers if hasattr(layer, 'geometryType')]

        non_line_layers = []
        non_point_layers = []
        non_obstacle_layers = []

        for layer in vector_layers:
            try:
                geom_type = layer.geometryType()
                if geom_type != WKB_LINE_GEOM:
                    non_line_layers.append(layer)
                if geom_type != WKB_POINT_GEOM:
                    non_point_layers.append(layer)
                if geom_type not in [WKB_POINT_GEOM, WKB_POLYGON_GEOM]:
                    non_obstacle_layers.append(layer)
            except Exception:
                logger.debug("Could not determine geometry type, excluding layer from all combos", exc_info=True)
                non_line_layers.append(layer)
                non_point_layers.append(layer)
                non_obstacle_layers.append(layer)

        self.runwayLayerCombo.setExceptedLayerList(non_line_layers)
        self.thresholdLayerCombo.setExceptedLayerList(non_point_layers)
        self.obstaclesLayerCombo.setExceptedLayerList(non_obstacle_layers)

    def _on_layers_changed(self):
        try:
            self._apply_geometry_filters()
            self._update_obstacle_fields()
        except Exception:
            logger.debug("Geometry filter application failed", exc_info=True)

    def _update_obstacle_fields(self):
        try:
            self.obstacleHeightFieldCombo.clear()

            layer = self.obstaclesLayerCombo.currentLayer()
            if layer:
                numeric_field_names: list[str] = []
                for field in layer.fields():
                    if field.type() in [FIELD_INT, FIELD_DOUBLE]:
                        self.obstacleHeightFieldCombo.addItem(field.name())
                        numeric_field_names.append(field.name().lower())

                for default_name in ['height', 'elevation', 'elev', 'z', 'alt', 'altitude']:
                    if default_name in numeric_field_names:
                        self.obstacleHeightFieldCombo.setCurrentIndex(
                            numeric_field_names.index(default_name)
                        )
                        break
        except Exception:
            logger.debug("Obstacle height field update failed", exc_info=True)

    def _validate_elevations(self) -> None:
        """Warn when DER elevation is 0 and THR elevation is non-zero — likely an unfilled field."""
        try:
            der = self.endElevationSpin.value()
            thr = self.initialElevationSpin.value()
            suspicious = (der == 0.0 and abs(thr) > 1.0)
            self.endElevationSpin.setProperty("invalid", suspicious)
            self.endElevationSpin.style().unpolish(self.endElevationSpin)
            self.endElevationSpin.style().polish(self.endElevationSpin)
            if suspicious:
                self.endElevationSpin.setToolTip(
                    "\u26a0 DER Elevation is 0 while THR Elevation is non-zero. "
                    "Please verify \u2014 the TOFPA surface will start at sea level."
                )
            else:
                self.endElevationSpin.setToolTip(
                    "Elevation at the Departure End of the Runway (ZE). "
                    "The TOFPA OCS surface starts from this elevation and climbs at 1.2\u2009%\u2009\u2014 ICAO Doc 8168 Vol I \u00a73.1.3."
                )
        except Exception:
            logger.debug("Elevation validation failed", exc_info=True)

    def _validate_widths(self):
        """Block calculation when max width < initial width and highlight both spinboxes."""
        try:
            invalid = self.maxWidthSpin.value() < self.initialWidthSpin.value()
            for spin in (self.maxWidthSpin, self.initialWidthSpin):
                spin.setProperty("invalid", invalid)
                spin.style().unpolish(spin)
                spin.style().polish(spin)
            self.calculateButton.setEnabled(not invalid)
            self.maxWidthSpin.setToolTip(
                "Maximum width must be \u2265 initial width" if invalid
                else "Maximum width of the TOFPA surface at the end of the climb. Typical: 1800 m"
            )
        except Exception:
            logger.debug("Width validation failed", exc_info=True)

    def _toggle_obstacles_group(self, enabled):
        try:
            self.obstaclesGroup.setEnabled(enabled)
            if not enabled:
                # Layer selection is intentionally preserved — get_parameters() ignores
                # obstacles_layer_id when include_obstacles is False.
                self.enableShadowAnalysisCheckBox.setChecked(False)
            self._toggle_shadow_controls(self.enableShadowAnalysisCheckBox.isChecked())
        except Exception:
            logger.debug("Toggle obstacles group failed", exc_info=True)

    def _toggle_shadow_controls(self, enabled):
        try:
            obstacles_enabled = self.includeObstaclesCheckBox.isChecked()
            final_enabled = enabled and obstacles_enabled

            self.shadowToleranceLabel.setEnabled(final_enabled)
            self.shadowToleranceSpin.setEnabled(final_enabled)

            if not obstacles_enabled:
                self.enableShadowAnalysisCheckBox.setEnabled(False)
                self.enableShadowAnalysisCheckBox.setChecked(False)
            else:
                self.enableShadowAnalysisCheckBox.setEnabled(True)
        except Exception:
            logger.debug("Toggle shadow controls failed", exc_info=True)

    def on_calculate_clicked(self):
        self.calculateClicked.emit()

    def on_close_clicked(self):
        self.closeClicked.emit()

    def get_parameters(self) -> dict:
        """Return all UI values as a flat dict consumed by TofpaParams.from_dict()."""
        # index 0 → start-to-end (s=0); index 1 → end-to-start (s=-1)
        direction_value = 0 if self.directionCombo.currentIndex() == 0 else -1

        return {
            'width_tofpa': self.initialWidthSpin.value(),
            'max_width_tofpa': self.maxWidthSpin.value(),
            'cwy_length': self.clearwayLengthSpin.value(),
            'z0': self.initialElevationSpin.value(),
            'ze': self.endElevationSpin.value(),
            's': direction_value,
            'runway_layer_id': self.runwayLayerCombo.currentLayer().id() if self.runwayLayerCombo.currentLayer() else None,
            'threshold_layer_id': self.thresholdLayerCombo.currentLayer().id() if self.thresholdLayerCombo.currentLayer() else None,
            'use_selected_feature': self.useSelectedFeatureCheckBox.isChecked(),
            'export_kmz': self.exportToKmzCheckBox.isChecked(),
            'export_aixm': self.exportToAixmCheckBox.isChecked(),
            'include_obstacles': self.includeObstaclesCheckBox.isChecked(),
            'obstacles_layer_id': self.obstaclesLayerCombo.currentLayer().id() if self.obstaclesLayerCombo.currentLayer() and self.includeObstaclesCheckBox.isChecked() else None,
            'obstacle_height_field': self.obstacleHeightFieldCombo.currentText() if self.includeObstaclesCheckBox.isChecked() else None,
            'obstacle_buffer': self.obstacleBufferSpin.value(),
            'min_obstacle_height': self.minObstacleHeightSpin.value(),
            'enable_shadow_analysis': self.enableShadowAnalysisCheckBox.isChecked() and self.includeObstaclesCheckBox.isChecked(),
            'shadow_tolerance': self.shadowToleranceSpin.value(),
            'contour_interval_m': int(round(self.contourIntervalSpin.value())),
        }

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()
