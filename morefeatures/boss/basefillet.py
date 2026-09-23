# The base fillet, rounded on the fused part: where each placed boss and its gussets meet the face
# they stand on, and where the gussets' flat sides meet the boss, all in one fillet. Separate
# fillets fail when their radii are equal, because each would roll into the other's rounded corner.

import math

import FreeCAD as App
import Part

from morefeatures.boss import geometry

EDGE_MATCH_TOLERANCE = 1e-4


def filletBossBases(
    shape: Part.Shape, template: Part.Shape, placements: list, gussetCount: int, radius: float
) -> Part.Shape:
    footprint = geometry.findFootprintWire(template)
    baseEdges = []
    gussetEdges = []
    for placement in placements:
        axis = placement.Rotation.multVec(geometry.LOCAL_AXIS)
        searchBox = template.BoundBox.transformed(placement.toMatrix())
        searchBox.enlarge(EDGE_MATCH_TOLERANCE)
        candidates = [edge for edge in shape.Edges if searchBox.isInside(edge.BoundBox)]
        placedFootprint = footprint.transformed(placement.toMatrix())
        baseEdges += _findBaseEdges(shape, candidates, placedFootprint, placement.Base, axis)
        instanceGussetEdges = _findGussetToBossEdges(shape, candidates, placement.Base, axis)
        if len(instanceGussetEdges) != 2 * gussetCount:
            raise ValueError(
                "Found {0} gusset-to-boss edges instead of {1}; the gussets do not meet the boss cleanly.".format(
                    len(instanceGussetEdges), 2 * gussetCount
                )
            )
        gussetEdges += instanceGussetEdges
    if not baseEdges:
        raise ValueError("No boss stands on a face of the part; draw the sketch on the face the bosses grow from.")
    return geometry.makeCheckedFillet(shape, radius, _withoutDuplicates(baseEdges + gussetEdges), "base")


def _findBaseEdges(
    shape: Part.Shape, candidates: list, footprint: Part.Wire, origin: App.Vector, axis: App.Vector
) -> list:
    """Edges of the footprint outline that border the part's face the boss stands on."""
    return [
        edge
        for edge in candidates
        if any(_isMountingFace(face, origin, axis) for face in shape.ancestorsOfType(edge, Part.Face))
        and footprint.distToShape(Part.Vertex(_midpoint(edge)))[0] < EDGE_MATCH_TOLERANCE
    ]


def _findGussetToBossEdges(shape: Part.Shape, candidates: list, origin: App.Vector, axis: App.Vector) -> list:
    """Edges where a gusset's drafted flat side meets the boss's round wall."""
    edges = []
    for edge in candidates:
        faces = shape.ancestorsOfType(edge, Part.Face)
        if (
            len(faces) == 2
            and any(_isBossWall(face, origin, axis) for face in faces)
            and any(_isGussetSide(face, axis) for face in faces)
        ):
            edges.append(edge)
    return edges


def _isMountingFace(face: Part.Face, origin: App.Vector, axis: App.Vector) -> bool:
    if not isinstance(face.Surface, Part.Plane):
        return False
    uMin, uMax, vMin, vMax = face.ParameterRange
    # Facing along the boss axis; a boss overhanging the part keeps its own bottom face, which faces away.
    isFacingUp = face.normalAt(uMin, vMin).dot(axis) > 1.0 - EDGE_MATCH_TOLERANCE
    isInSketchPlane = abs((face.Surface.Position - origin).dot(axis)) < EDGE_MATCH_TOLERANCE
    return isFacingUp and isInSketchPlane


def _isBossWall(face: Part.Face, origin: App.Vector, axis: App.Vector) -> bool:
    surface = face.Surface
    if not isinstance(surface, (Part.Cone, Part.Cylinder)) or not _isParallel(surface.Axis, axis):
        return False
    offset = surface.Center - origin
    return (offset - axis * offset.dot(axis)).Length < EDGE_MATCH_TOLERANCE


def _isGussetSide(face: Part.Face, axis: App.Vector) -> bool:
    return isinstance(face.Surface, Part.Plane) and not _isParallel(face.Surface.Axis, axis)


def _isParallel(direction: App.Vector, other: App.Vector) -> bool:
    return math.isclose(abs(App.Vector(direction).normalize().dot(other)), 1.0, abs_tol=EDGE_MATCH_TOLERANCE)


def _midpoint(edge: Part.Edge) -> App.Vector:
    return edge.valueAt((edge.FirstParameter + edge.LastParameter) / 2.0)


def _withoutDuplicates(edges: list) -> list:
    unique = []
    for edge in edges:
        if not any(edge.isSame(kept) for kept in unique):
            unique.append(edge)
    return unique
