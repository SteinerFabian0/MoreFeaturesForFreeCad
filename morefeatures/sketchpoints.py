# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The point markers of a driving sketch: every point is one instance location.
# Instances are keyed by geometry id, not geometry index: the index of every later
# element shifts when one is deleted, the id stays with its point for good.

from dataclasses import dataclass

import Part
from FreeCAD import Vector

SKETCH_NORMAL = Vector(0.0, 0.0, 1.0)


@dataclass(frozen=True)
class SketchPoint:
    geometryId: int
    geometryIndex: int
    localPosition: Vector
    position: Vector


def readSketchPoints(sketch) -> list:
    placement = sketch.getGlobalPlacement()
    points = []
    for geometryIndex, geometry in enumerate(sketch.Geometry):
        if isinstance(geometry, Part.Point):
            localPosition = Vector(geometry.X, geometry.Y, geometry.Z)
            points.append(
                SketchPoint(
                    sketch.getGeometryId(geometryIndex),
                    geometryIndex,
                    localPosition,
                    placement.multVec(localPosition),
                )
            )
    return points


def hasPoints(sketch) -> bool:
    return any(isinstance(geometry, Part.Point) for geometry in sketch.Geometry)


def findPointNearest(sketch, points: list, position: Vector, maximumDistance: float):
    """Matches a click anywhere above or below a point, e.g. on top of its boss, by
    comparing positions projected onto the sketch plane."""
    projected = _projectOntoSketchPlane(sketch, position)
    nearest = min(points, key=lambda point: (point.position - projected).Length, default=None)
    if nearest is None or (nearest.position - projected).Length > maximumDistance:
        return None
    return nearest


def _projectOntoSketchPlane(sketch, position: Vector) -> Vector:
    placement = sketch.getGlobalPlacement()
    normal = placement.Rotation.multVec(SKETCH_NORMAL)
    return position - normal * (position - placement.Base).dot(normal)
