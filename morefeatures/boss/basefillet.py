# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The base fillet, rounded once on the template: where the boss and its gussets meet the face they
# stand on, and where the gussets' flat sides meet the boss, all in one fillet. Separate fillets
# fail when their radii are equal, because each would roll into the other's rounded corner.

import math

import FreeCAD as App
import Part

from morefeatures import fillet
from morefeatures.boss import geometry

EDGE_MATCH_TOLERANCE = 1e-4
SLAB_MARGIN = 1.0


def filletBase(template: Part.Shape, gussetCount: int, radius: float) -> Part.Shape:
    """The template filleted as if standing on an endless face in z = 0, so the fillet comes along
    wherever the template is placed, and nothing standing next to a boss keeps it from fitting."""
    slab = _buildSlab(template, radius)
    standing = template.fuse(slab)
    footprint = geometry.findFootprintWire(template)
    baseEdges = [edge for edge in standing.Edges if _isOnFootprint(standing, edge, footprint)]
    gussetEdges = [edge for edge in standing.Edges if _isGussetToBossEdge(standing, edge)]
    if len(gussetEdges) != 2 * gussetCount:
        raise ValueError(
            "Found {0} gusset-to-boss edges instead of {1}; the gussets do not meet the boss cleanly.".format(
                len(gussetEdges), 2 * gussetCount
            )
        )
    filleted = fillet.makeCheckedFillet(standing, radius, baseEdges + gussetEdges, "base")
    return filleted.cut(_enlarged(slab))


def _buildSlab(template: Part.Shape, radius: float) -> Part.Shape:
    reach = radius + SLAB_MARGIN
    box = template.BoundBox
    return Part.makeBox(
        box.XLength + 2.0 * reach,
        box.YLength + 2.0 * reach,
        reach,
        App.Vector(box.XMin - reach, box.YMin - reach, -reach),
    )


def _enlarged(slab: Part.Shape) -> Part.Shape:
    """Reaching past the slab on every side but its top, so the cut shares only that face with it."""
    box = slab.BoundBox
    return Part.makeBox(
        box.XLength + 2.0 * SLAB_MARGIN,
        box.YLength + 2.0 * SLAB_MARGIN,
        box.ZLength + SLAB_MARGIN,
        App.Vector(box.XMin - SLAB_MARGIN, box.YMin - SLAB_MARGIN, box.ZMin - SLAB_MARGIN),
    )


def _isOnFootprint(standing: Part.Shape, edge: Part.Edge, footprint: Part.Wire) -> bool:
    """On the outline where the template meets the slab's top face."""
    isInSketchPlane = abs(edge.BoundBox.ZMin) < EDGE_MATCH_TOLERANCE and abs(edge.BoundBox.ZMax) < EDGE_MATCH_TOLERANCE
    return (
        isInSketchPlane
        and any(_isSlabTop(face) for face in standing.ancestorsOfType(edge, Part.Face))
        and footprint.distToShape(Part.Vertex(_midpoint(edge)))[0] < EDGE_MATCH_TOLERANCE
    )


def _isGussetToBossEdge(standing: Part.Shape, edge: Part.Edge) -> bool:
    """Where a gusset's drafted flat side meets the boss's round wall."""
    faces = standing.ancestorsOfType(edge, Part.Face)
    return len(faces) == 2 and any(_isBossWall(face) for face in faces) and any(_isGussetSide(face) for face in faces)


def _isSlabTop(face: Part.Face) -> bool:
    if not isinstance(face.Surface, Part.Plane):
        return False
    uMin, uMax, vMin, vMax = face.ParameterRange
    isFacingUp = face.normalAt(uMin, vMin).dot(geometry.LOCAL_AXIS) > 1.0 - EDGE_MATCH_TOLERANCE
    return isFacingUp and abs(face.Surface.Position.z) < EDGE_MATCH_TOLERANCE


def _isBossWall(face: Part.Face) -> bool:
    surface = face.Surface
    if not isinstance(surface, (Part.Cone, Part.Cylinder)) or not _isAlongAxis(surface.Axis):
        return False
    return math.hypot(surface.Center.x, surface.Center.y) < EDGE_MATCH_TOLERANCE


def _isGussetSide(face: Part.Face) -> bool:
    return isinstance(face.Surface, Part.Plane) and not _isAlongAxis(face.Surface.Axis)


def _isAlongAxis(direction: App.Vector) -> bool:
    alignment = abs(App.Vector(direction).normalize().dot(geometry.LOCAL_AXIS))
    return math.isclose(alignment, 1.0, abs_tol=EDGE_MATCH_TOLERANCE)


def _midpoint(edge: Part.Edge) -> App.Vector:
    return edge.valueAt((edge.FirstParameter + edge.LastParameter) / 2.0)
