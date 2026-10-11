# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The holes of a hexagonal pattern that fit inside a sketch's perimeter, and the material each one
# removes from the part: from the sketch plane on until the hole first comes out of the part.

import math
from dataclasses import dataclass

import Part
from FreeCAD import Vector

from morefeatures.holefill.parameters import HoleFillParameters

SKETCH_NORMAL = Vector(0.0, 0.0, 1.0)
CUT_OVERSHOOT = 0.1
SKETCH_PLANE_TOLERANCE = 1e-4
ARC_JOIN = 0
BOUNDING_BOX_CORNER_COUNT = 8
# Each hole costs two booleans; this many already take tens of seconds.
MAX_HOLE_COUNT = 10000


@dataclass(frozen=True)
class HoleCuts:
    material: Part.Shape
    holeCount: int


def buildHoleCuts(sketch, partShape: Part.Shape, parameters: HoleFillParameters) -> HoleCuts:
    if parameters.pitch <= parameters.holeDiameter:
        raise ValueError("The pitch must be larger than the hole diameter, or the holes run into each other.")
    holeCentres = _hexagonalHoleCentres(_localPerimeter(sketch), parameters)
    localCutDirection = SKETCH_NORMAL if parameters.isReversed else -SKETCH_NORMAL
    holeTools = _holeTools(holeCentres, localCutDirection, partShape, sketch.Placement, parameters)
    cutDirection = sketch.Placement.Rotation.multVec(localCutDirection)
    material = [
        piece
        for piece in partShape.common(holeTools).Solids
        if _startsAtSketchPlane(piece, sketch.Placement.Base, cutDirection)
    ]
    if not material:
        raise ValueError("No hole reaches the part. Draw the perimeter on the part's face, or tick Reversed.")
    return HoleCuts(Part.makeCompound(material), len(holeCentres))


def _localPerimeter(sketch) -> Part.Face:
    wires = sketch.Shape.Wires
    if len(wires) != 1 or not wires[0].isClosed():
        raise ValueError("The sketch must hold exactly one closed perimeter.")
    return Part.Face(wires[0].transformed(sketch.Placement.inverse().toMatrix()))


def _hexagonalHoleCentres(perimeter: Part.Face, parameters: HoleFillParameters) -> list:
    """One hole on the perimeter's centre of area, rows along the sketch's X axis; only holes that fit
    inside the perimeter whole."""
    centreRegion = _centreRegion(perimeter, parameters.holeRadius)
    estimatedHoleCount = centreRegion.Area / (parameters.pitch * parameters.rowSpacing)
    if estimatedHoleCount > MAX_HOLE_COUNT:
        raise ValueError(
            "About {0} holes would be cut, more than the {1} this feature takes. Use a larger pitch.".format(
                int(estimatedHoleCount), MAX_HOLE_COUNT
            )
        )
    gridOrigin = perimeter.CenterOfMass
    bounds = centreRegion.BoundBox
    holeCentres = []
    for row in _indexRange(bounds.YMin - gridOrigin.y, bounds.YMax - gridOrigin.y, parameters.rowSpacing):
        rowShift = 0.5 * (row % 2)
        for column in _indexRange(bounds.XMin - gridOrigin.x, bounds.XMax - gridOrigin.x, parameters.pitch):
            centre = gridOrigin + Vector((column + rowShift) * parameters.pitch, row * parameters.rowSpacing, 0.0)
            if _isInside(centreRegion, centre):
                holeCentres.append(centre)
    if not holeCentres:
        raise ValueError("No hole fits inside the perimeter.")
    return holeCentres


def _centreRegion(perimeter: Part.Face, holeRadius: float) -> Part.Shape:
    """Where a hole's centre may lie for the whole hole to fit inside the perimeter."""
    try:
        return perimeter.makeOffset2D(-holeRadius, ARC_JOIN)
    except (RuntimeError, ValueError) as error:
        raise ValueError("No hole fits inside the perimeter.") from error


def _indexRange(lowest: float, highest: float, spacing: float) -> range:
    # One extra index on each side covers the half-pitch shift of every other row.
    return range(math.floor(lowest / spacing) - 1, math.ceil(highest / spacing) + 2)


def _isInside(region: Part.Shape, point: Vector) -> bool:
    return any(face.isInside(point, 0.0, True) for face in region.Faces)


def _holeTools(
    holeCentres: list, localCutDirection: Vector, partShape: Part.Shape, placement, parameters: HoleFillParameters
) -> Part.Shape:
    """Each hole runs from the sketch plane on through all of the part, in the Body's frame."""
    toPartsFarEnd = max(
        placement.inverse().multVec(partShape.BoundBox.getPoint(index)).dot(localCutDirection)
        for index in range(BOUNDING_BOX_CORNER_COUNT)
    )
    length = max(toPartsFarEnd, 0.0) + CUT_OVERSHOOT
    holeTool = Part.makeCylinder(parameters.holeRadius, length, Vector(), localCutDirection)
    localTools = Part.makeCompound([holeTool.translated(centre) for centre in holeCentres])
    return localTools.transformed(placement.toMatrix())


def _startsAtSketchPlane(piece: Part.Shape, sketchOrigin: Vector, cutDirection: Vector) -> bool:
    """A piece of a hole that starts beyond the sketch plane lies past where the hole came out of the part."""
    return min((vertex.Point - sketchOrigin).dot(cutDirection) for vertex in piece.Vertexes) <= SKETCH_PLANE_TOLERANCE
