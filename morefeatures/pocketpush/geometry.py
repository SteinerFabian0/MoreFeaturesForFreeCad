# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The cavities pushed into the part through each closed outline of the sketch, and the drafted walls
# that wrap them, in the Body's frame.

import math
from dataclasses import dataclass
from typing import Callable

import Part
from FreeCAD import Vector

from morefeatures import fillet
from morefeatures.pocketpush.parameters import PocketPushParameters

JOIN_INTERSECTION = 2
AREA_TOLERANCE = 1e-6
DIRECTION_TOLERANCE = 1e-9
# Faces meeting at less than this many radians count as tangent, so their edge is no corner.
TANGENT_ANGLE_TOLERANCE = 1e-3
CONCAVITY_PROBE_DISTANCE = 1e-3
SHRINKS_AWAY_MESSAGE = (
    "A rounded corner, a short edge or the whole outline shrinks away when drafted or offset by the side "
    "wall. Use a gentler draft, a thinner side wall or larger radii in the sketch."
)

OutlineAtHeight = Callable[[float], Part.Wire]


@dataclass(frozen=True)
class PushedPockets:
    walls: Part.Shape
    cavities: Part.Shape


@dataclass(frozen=True)
class CornerRadii:
    """Of the edges along the pull direction, by whether the solid is convex or concave there."""

    convex: float
    concave: float


def buildPushedPockets(
    sketchShape: Part.Shape, sketchNormal: Vector, parameters: PocketPushParameters
) -> PushedPockets:
    outlines = _closedOutlines(sketchShape)
    pushDirection = sketchNormal if parameters.isReversed else -sketchNormal
    draftSlope = math.tan(math.radians(parameters.draftAngle))
    walls = []
    cavities = []
    for outline in outlines:
        cavityOutline = _draftedOutline(outline, draftSlope)
        wallOutline = _grownOutline(cavityOutline, parameters.sideWallOffset)
        cavity = _draftedSolid(cavityOutline, parameters.cavityDepth, pushDirection)
        wall = _draftedSolid(wallOutline, parameters.outerHeight, pushDirection)
        cavities.append(_roundedCavity(cavity, pushDirection, parameters))
        walls.append(_roundedWalls(wall, pushDirection, parameters))
    return PushedPockets(_fused(walls), Part.makeCompound(cavities))


def _closedOutlines(sketchShape: Part.Shape) -> list:
    if not sketchShape.Wires:
        raise ValueError("The sketch has no outline.")
    if any(not wire.isClosed() for wire in sketchShape.Wires):
        raise ValueError("The sketch may only hold closed outlines.")
    faces = [Part.Face(wire) for wire in sketchShape.Wires]
    for index, face in enumerate(faces):
        if any(face.common(otherFace).Area > AREA_TOLERANCE for otherFace in faces[index + 1:]):
            raise ValueError("The sketch's outlines may not overlap or lie inside one another.")
    return [face.OuterWire for face in faces]


def _draftedOutline(outline: Part.Wire, draftSlope: float) -> OutlineAtHeight:
    return lambda height: _offsetOutline(outline, -height * draftSlope)


def _grownOutline(outlineAtHeight: OutlineAtHeight, distance: float) -> OutlineAtHeight:
    return lambda height: _offsetOutline(outlineAtHeight(height), distance)


def _offsetOutline(outline: Part.Wire, distance: float) -> Part.Wire:
    if distance == 0.0:
        return outline
    # Sharp corners stay sharp, so the walls' corners can be rounded by fillets coaxial with the cavity's.
    try:
        return Part.Face(outline).makeOffset2D(distance, JOIN_INTERSECTION).OuterWire
    except (RuntimeError, ValueError) as error:
        raise ValueError(SHRINKS_AWAY_MESSAGE) from error


def _draftedSolid(outlineAtHeight: OutlineAtHeight, height: float, pushDirection: Vector) -> Part.Solid:
    bottom = outlineAtHeight(0.0)
    top = outlineAtHeight(height).translated(pushDirection * height)
    # The ruled loft pairs the two outlines edge by edge, so an edge that shrank away would twist it.
    if len(top.Edges) != len(bottom.Edges):
        raise ValueError(SHRINKS_AWAY_MESSAGE)
    solid = Part.makeLoft([bottom, top], True, True)
    if not solid.isValid():
        raise ValueError("The drafted walls could not be built for this outline.")
    return solid


def _roundedCavity(cavity: Part.Solid, pushDirection: Vector, parameters: PocketPushParameters) -> Part.Shape:
    radii = CornerRadii(convex=parameters.innerCornerRadius, concave=parameters.outerCornerRadius)
    return _filletCorners(cavity, pushDirection, radii, "inner corner")


def _roundedWalls(walls: Part.Solid, pushDirection: Vector, parameters: PocketPushParameters) -> Part.Shape:
    # Each wall corner fillet shares its axis with the cavity's, so the wall keeps its thickness round it.
    radii = CornerRadii(convex=parameters.outerCornerRadius, concave=parameters.innerCornerRadius)
    rounded = _filletCorners(walls, pushDirection, radii, "outer corner")
    topRadius = parameters.topFilletRadiusInEffect
    if topRadius <= 0.0:
        return rounded
    topEdges = _topFace(rounded, pushDirection).Edges
    return fillet.makeCheckedFillet(rounded, topRadius, topEdges, "top surface")


def _filletCorners(solid: Part.Shape, pushDirection: Vector, radii: CornerRadii, filletName: str) -> Part.Shape:
    for isConcave, radius in ((False, radii.convex), (True, radii.concave)):
        corners = [edge for edge in _cornerEdges(solid, pushDirection) if _isConcave(solid, edge) == isConcave]
        if radius > 0.0 and corners:
            solid = fillet.makeCheckedFillet(solid, radius, corners, filletName)
    return solid


def _cornerEdges(solid: Part.Shape, pushDirection: Vector) -> list:
    capEdgeHashes = {edge.hashCode() for face in _capFaces(solid, pushDirection) for edge in face.Edges}
    return [edge for edge in solid.Edges if edge.hashCode() not in capEdgeHashes and _isSharp(solid, edge)]


def _isSharp(solid: Part.Shape, edge: Part.Edge) -> bool:
    normals = _faceNormalsAtMidpoint(solid, edge)
    return len(normals) == 2 and normals[0].getAngle(normals[1]) > TANGENT_ANGLE_TOLERANCE


def _isConcave(solid: Part.Shape, edge: Part.Edge) -> bool:
    # Stepping off the edge along the difference of its faces' outward normals lands outside a convex
    # corner but inside a concave one, whose material wraps round both sides.
    firstNormal, secondNormal = _faceNormalsAtMidpoint(solid, edge)
    probeDirection = firstNormal - secondNormal
    probeDirection.normalize()
    probe = _midpoint(edge) + probeDirection * CONCAVITY_PROBE_DISTANCE
    return solid.isInside(probe, 0.0, True)


def _faceNormalsAtMidpoint(solid: Part.Shape, edge: Part.Edge) -> list:
    midpoint = _midpoint(edge)
    faces = solid.ancestorsOfType(edge, Part.Face)
    return [face.normalAt(*face.Surface.parameter(midpoint)) for face in faces]


def _midpoint(edge: Part.Edge) -> Vector:
    return edge.valueAt((edge.FirstParameter + edge.LastParameter) / 2.0)


def _capFaces(solid: Part.Shape, pushDirection: Vector) -> list:
    return [
        face
        for face in solid.Faces
        if isinstance(face.Surface, Part.Plane)
        and abs(abs(face.normalAt(0.0, 0.0).dot(pushDirection)) - 1.0) < DIRECTION_TOLERANCE
    ]


def _topFace(solid: Part.Shape, pushDirection: Vector) -> Part.Face:
    return max(_capFaces(solid, pushDirection), key=lambda face: face.CenterOfMass.dot(pushDirection))


def _fused(solids: list) -> Part.Shape:
    return solids[0].multiFuse(solids[1:]) if len(solids) > 1 else solids[0]
