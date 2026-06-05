"""
Compatibility shim for QGIS 3.x (PyQt5) and QGIS 4.0 (PyQt6).

QGIS 4.0 introduced three breaking changes relevant here:
  - QVariant removed → replaced by QMetaType.Type
  - Enum scoping: QgsWkbTypes.PolygonGeometry → QgsWkbTypes.GeometryType.PolygonGeometry
  - QgsMapLayerProxyModel.VectorLayer → QgsMapLayerProxyModel.Filter.VectorLayer

Constants exported from this module work on both Qt versions; the correct
variant is selected at import time via try/except on AttributeError.
"""

from __future__ import annotations

# Field type constants: QVariant (PyQt5) → QMetaType.Type (PyQt6)
try:
    from qgis.PyQt.QtCore import QMetaType  # PyQt6 / Qt 6

    FIELD_INT: int = QMetaType.Type.Int       # type: ignore[attr-defined]
    FIELD_DOUBLE: int = QMetaType.Type.Double  # type: ignore[attr-defined]
    FIELD_STRING: int = QMetaType.Type.QString  # type: ignore[attr-defined]
except (ImportError, AttributeError):
    from qgis.PyQt.QtCore import QVariant  # type: ignore[attr-defined]  # PyQt5 / Qt 5

    FIELD_INT: int = QVariant.Int      # type: ignore[assignment]
    FIELD_DOUBLE: int = QVariant.Double  # type: ignore[assignment]
    FIELD_STRING: int = QVariant.String  # type: ignore[assignment]

# WKB geometry type constants and layer filter: unscoped (PyQt5) → scoped enums (PyQt6)
from qgis.core import QgsWkbTypes, QgsMapLayerProxyModel  # noqa: E402
from qgis.PyQt.QtCore import Qt  # noqa: E402

try:
    WKB_POLYGON_GEOM: int = QgsWkbTypes.GeometryType.PolygonGeometry  # type: ignore[attr-defined]
    WKB_LINE_GEOM: int = QgsWkbTypes.GeometryType.LineGeometry        # type: ignore[attr-defined]
    WKB_POINT_GEOM: int = QgsWkbTypes.GeometryType.PointGeometry      # type: ignore[attr-defined]
    LAYER_FILTER_VECTOR: int = QgsMapLayerProxyModel.Filter.VectorLayer  # type: ignore[attr-defined]
except AttributeError:
    WKB_POLYGON_GEOM: int = QgsWkbTypes.PolygonGeometry         # type: ignore[assignment, attr-defined]
    WKB_LINE_GEOM: int = QgsWkbTypes.LineGeometry               # type: ignore[assignment, attr-defined]
    WKB_POINT_GEOM: int = QgsWkbTypes.PointGeometry             # type: ignore[assignment, attr-defined]
    LAYER_FILTER_VECTOR: int = QgsMapLayerProxyModel.VectorLayer  # type: ignore[assignment, attr-defined]

# Qt dock area flag: unscoped (PyQt5) → DockWidgetArea enum (PyQt6)
try:
    DOCK_RIGHT = Qt.DockWidgetArea.RightDockWidgetArea  # type: ignore[attr-defined]
except AttributeError:
    DOCK_RIGHT = Qt.RightDockWidgetArea  # type: ignore[attr-defined]

__all__ = [
    "FIELD_INT",
    "FIELD_DOUBLE",
    "FIELD_STRING",
    "WKB_POLYGON_GEOM",
    "WKB_LINE_GEOM",
    "WKB_POINT_GEOM",
    "LAYER_FILTER_VECTOR",
    "DOCK_RIGHT",
]
