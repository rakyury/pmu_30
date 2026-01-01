"""
Logic Engine - Lookup Tables

2D and 3D lookup tables with linear/bilinear interpolation.
"""

from dataclasses import dataclass, field
from typing import List, Optional


TABLE_2D_MAX_POINTS = 16
TABLE_3D_MAX_X = 8
TABLE_3D_MAX_Y = 8


@dataclass
class Table2D:
    """2D lookup table with interpolation"""
    x_values: List[int] = field(default_factory=list)
    y_values: List[int] = field(default_factory=list)

    @property
    def size(self) -> int:
        return min(len(self.x_values), len(self.y_values))


@dataclass
class Table3D:
    """3D lookup table with bilinear interpolation"""
    x_values: List[int] = field(default_factory=list)
    y_values: List[int] = field(default_factory=list)
    z_values: List[List[int]] = field(default_factory=list)  # z[y][x]

    @property
    def x_size(self) -> int:
        return len(self.x_values)

    @property
    def y_size(self) -> int:
        return len(self.y_values)


def _find_index(values: List[int], x: int) -> tuple[int, int]:
    """
    Binary search to find indices for interpolation.
    Returns (lower_index, upper_index).
    """
    n = len(values)
    if n == 0:
        return 0, 0

    if x <= values[0]:
        return 0, 0
    if x >= values[n - 1]:
        return n - 1, n - 1

    # Binary search
    low = 0
    high = n - 1

    while high - low > 1:
        mid = (low + high) // 2
        if values[mid] <= x:
            low = mid
        else:
            high = mid

    return low, high


def _interpolate(x: int, x0: int, x1: int, y0: int, y1: int) -> int:
    """Linear interpolation with integer math"""
    if x1 == x0:
        return y0

    # Use 64-bit intermediate to prevent overflow
    dx = x1 - x0
    dy = y1 - y0
    result = y0 + (x - x0) * dy // dx

    return result


def table2d_lookup(table: Table2D, x: int) -> int:
    """
    Lookup value in 2D table with linear interpolation.

    Args:
        table: 2D lookup table
        x: Input value

    Returns:
        Interpolated output value
    """
    n = table.size
    if n == 0:
        return 0
    if n == 1:
        return table.y_values[0]

    i0, i1 = _find_index(table.x_values, x)

    if i0 == i1:
        return table.y_values[i0]

    return _interpolate(
        x,
        table.x_values[i0], table.x_values[i1],
        table.y_values[i0], table.y_values[i1]
    )


def table3d_lookup(table: Table3D, x: int, y: int) -> int:
    """
    Lookup value in 3D table with bilinear interpolation.

    Args:
        table: 3D lookup table
        x: X input value
        y: Y input value

    Returns:
        Interpolated output value
    """
    nx = table.x_size
    ny = table.y_size

    if nx == 0 or ny == 0 or not table.z_values:
        return 0

    # Find x indices
    xi0, xi1 = _find_index(table.x_values, x)

    # Find y indices
    yi0, yi1 = _find_index(table.y_values, y)

    # Get corner values
    try:
        z00 = table.z_values[yi0][xi0]
        z01 = table.z_values[yi0][xi1] if xi1 < nx else z00
        z10 = table.z_values[yi1][xi0] if yi1 < ny else z00
        z11 = table.z_values[yi1][xi1] if (xi1 < nx and yi1 < ny) else z00
    except IndexError:
        return 0

    # Bilinear interpolation
    if xi0 == xi1:
        # Only Y interpolation needed
        if yi0 == yi1:
            return z00
        return _interpolate(y, table.y_values[yi0], table.y_values[yi1], z00, z10)

    if yi0 == yi1:
        # Only X interpolation needed
        return _interpolate(x, table.x_values[xi0], table.x_values[xi1], z00, z01)

    # Full bilinear interpolation
    # Interpolate along X for both Y rows
    zx0 = _interpolate(x, table.x_values[xi0], table.x_values[xi1], z00, z01)
    zx1 = _interpolate(x, table.x_values[xi0], table.x_values[xi1], z10, z11)

    # Interpolate along Y
    return _interpolate(y, table.y_values[yi0], table.y_values[yi1], zx0, zx1)


def table2d_from_points(points: List[tuple[int, int]]) -> Table2D:
    """Create 2D table from list of (x, y) points"""
    points = sorted(points, key=lambda p: p[0])
    return Table2D(
        x_values=[p[0] for p in points],
        y_values=[p[1] for p in points]
    )
