# -*- coding: utf-8 -*-
"""
Pure-Python contour geometry for the TOFPA AOC Type A climb surface.

No QGIS dependency — safe to import in unit tests without a QGIS context.
All distances and elevations in metres.

The surface has two width zones:
  - Expanding  [0, distance_to_max_width]:  half-width grows linearly.
  - Constant   [distance_to_max_width, surface_length]: max half-width fixed.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor, radians, sin, cos
from typing import List


@dataclass(frozen=True)
class ContourSpec:
    """Single contour line defined by its elevation (m MSL), axis distance (m), and half-width (m)."""

    elevation: float
    distance_from_origin: float
    half_width: float


def contour_elevations(z_start: float, z_end: float, interval: int) -> List[float]:
    """Return integer-multiple elevation levels in the half-open interval (z_start, z_end].

    z_start is excluded because the surface polygon already starts at that elevation.
    Returns an empty list when interval <= 0 or z_end <= z_start.

    >>> contour_elevations(21.7, 81.7, 10)
    [30.0, 40.0, 50.0, 60.0, 70.0, 80.0]
    >>> contour_elevations(0.0, 10.0, 10)
    [10.0]
    """
    if interval <= 0 or z_end <= z_start:
        return []
    # Add a small epsilon so z_start is strictly excluded when it falls exactly
    # on an interval boundary (contract: open at z_start, closed at z_end).
    first = int(ceil(z_start / interval + 1e-9)) * interval
    last = int(floor(z_end / interval)) * interval
    return [float(v) for v in range(first, last + 1, interval)]


def contour_specs_for_linear_section(
    z_section_start: float,
    z_section_end: float,
    slope: float,
    d_offset: float,
    near_half_width: float,
    divergence_ratio: float,
    elevations: List[float],
) -> List[ContourSpec]:
    """Compute ContourSpecs for a linearly sloped trapezoidal section.

    Half-width at global distance d:  near_half_width + d * divergence_ratio
    """
    if slope <= 0:
        return []

    specs: List[ContourSpec] = []
    for z_c in elevations:
        if not (z_section_start - 1e-9 < z_c <= z_section_end + 1e-9):
            continue
        d_in_section = (z_c - z_section_start) / slope
        d_from_origin = d_offset + d_in_section
        half_w = near_half_width + d_from_origin * divergence_ratio
        specs.append(ContourSpec(
            elevation=z_c,
            distance_from_origin=d_from_origin,
            half_width=half_w,
        ))
    return specs


def contour_specs_for_takeoff(
    z_start: float,
    slope_ratio: float,
    distance_to_max_width: float,
    surface_length: float,
    near_half_width: float,
    max_half_width: float,
    divergence_ratio: float,
    elevations: List[float],
) -> List[ContourSpec]:
    """Compute ContourSpecs for the full TOFPA AOC Type A Climb Surface.

    Elevation: z(d) = z_start + d * slope_ratio
    Width zones:
      [0, distance_to_max_width]  → half_width grows with divergence_ratio
      (distance_to_max_width, …]  → half_width fixed at max_half_width
    """
    if slope_ratio <= 0:
        return []

    z_end = z_start + surface_length * slope_ratio
    specs: List[ContourSpec] = []

    for z_c in elevations:
        if not (z_start - 1e-9 < z_c <= z_end + 1e-9):
            continue
        d = (z_c - z_start) / slope_ratio
        if d > surface_length + 1e-6:
            continue
        if d <= distance_to_max_width:
            half_w = near_half_width + d * divergence_ratio
        else:
            half_w = max_half_width
        specs.append(ContourSpec(
            elevation=z_c,
            distance_from_origin=d,
            half_width=half_w,
        ))
    return specs


def distance_along_axis(obstacle_pt, der_pt, azimuth_deg: float) -> float:
    """Signed projection of obstacle_pt onto the takeoff axis from der_pt (metres)."""
    az = radians(azimuth_deg)
    dx = obstacle_pt.x() - der_pt.x()
    dy = obstacle_pt.y() - der_pt.y()
    return dx * sin(az) + dy * cos(az)


def ocs_elevation_at_distance(d: float, z_der: float, climb_gradient: float) -> float:
    """OCS elevation (m MSL) at distance d from the DER. Returns z_der for d < 0."""
    if d < 0:
        return z_der
    return z_der + d * climb_gradient
