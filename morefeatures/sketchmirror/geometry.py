# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# Mirrored copies of sketch geometry, and which point of a copy mirrors which point of its original.

import math
from dataclasses import dataclass
from typing import Optional

import Part
from FreeCAD import Vector

SKETCH_NORMAL = Vector(0.0, 0.0, 1.0)
START = 1
END = 2
CENTRE = 3
ON_LINE_TOLERANCE = 1e-6
ARC_CENTRE_NUDGE = 1e-6


@dataclass(frozen=True)
class MirrorLine:
    point: Vector
    unitNormal: Vector

    def reflect(self, position: Vector) -> Vector:
        return position - self.unitNormal * (2.0 * self._signedDistanceTo(position))

    def isOnLine(self, position: Vector) -> bool:
        return abs(self._signedDistanceTo(position)) < ON_LINE_TOLERANCE

    def _signedDistanceTo(self, position: Vector) -> float:
        return (position - self.point).dot(self.unitNormal)


@dataclass(frozen=True)
class MirroredGeometry:
    geometry: object
    # (point position on the original, point position on the copy): the pairs that mirror each other.
    matchingPositions: tuple
    # Symmetric points leave a circle's radius free.
    hasEqualRadius: bool


def mirrorLineAlong(line: Part.LineSegment) -> MirrorLine:
    direction = line.EndPoint - line.StartPoint
    direction.normalize()
    return MirrorLine(Vector(line.StartPoint), SKETCH_NORMAL.cross(direction))


def mirrorGeometry(geometry, mirrorLine: MirrorLine) -> Optional[MirroredGeometry]:
    """None for geometry types that are not mirrored yet."""
    if isinstance(geometry, Part.Point):
        mirroredPoint = mirrorLine.reflect(Vector(geometry.X, geometry.Y, geometry.Z))
        return MirroredGeometry(Part.Point(mirroredPoint), ((START, START),), False)
    if isinstance(geometry, Part.LineSegment):
        mirroredLine = Part.LineSegment(mirrorLine.reflect(geometry.StartPoint), mirrorLine.reflect(geometry.EndPoint))
        return MirroredGeometry(mirroredLine, ((START, START), (END, END)), False)
    if isinstance(geometry, Part.ArcOfCircle):
        return _mirrorArc(geometry, mirrorLine)
    if isinstance(geometry, Part.Circle):
        mirroredCircle = Part.Circle(mirrorLine.reflect(geometry.Center), SKETCH_NORMAL, geometry.Radius)
        return MirroredGeometry(mirroredCircle, ((CENTRE, CENTRE),), True)
    return None


def _mirrorArc(arc: Part.ArcOfCircle, mirrorLine: MirrorLine) -> MirroredGeometry:
    # Sketch arcs always run counterclockwise, and mirroring reverses the direction, so the
    # copy starts where the original ends.
    startPoint = mirrorLine.reflect(arc.EndPoint)
    endPoint = mirrorLine.reflect(arc.StartPoint)
    chordBisector = SKETCH_NORMAL.cross(endPoint - startPoint)
    chordBisector.normalize()
    # On an exact copy of a half circle, e.g. a slot end, the centre sits on the chord, where the
    # equal radius constraint has no slope along the bisector: the solver's Jacobian turns singular
    # and flags a constraint as redundant (FreeCAD nudges its own mirrored arcs for the same
    # reason, issue #13551). Off by a hair, the constraint stays independent, and the solver
    # never pulls it back exactly, since the radius error left is far below its tolerance.
    centre = mirrorLine.reflect(arc.Center) + chordBisector * ARC_CENTRE_NUDGE
    startAngle = _angleAround(centre, startPoint)
    endAngle = _angleAround(centre, endPoint)
    if endAngle <= startAngle:
        endAngle += 2.0 * math.pi
    circle = Part.Circle(centre, SKETCH_NORMAL, (startPoint - centre).Length)
    return MirroredGeometry(Part.ArcOfCircle(circle, startAngle, endAngle), ((START, END), (END, START)), True)


def _angleAround(centre: Vector, position: Vector) -> float:
    return math.atan2(position.y - centre.y, position.x - centre.x)
