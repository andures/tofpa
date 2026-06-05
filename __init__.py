# -*- coding: utf-8 -*-
"""TOFPA — Take-Off Flight Path Analysis QGIS plugin."""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """QGIS plugin entry point."""
    from .tofpa import TOFPA
    return TOFPA(iface)