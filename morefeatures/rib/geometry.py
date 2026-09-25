# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The volume the cutter sweeps along the path edges, in the Body's frame. Each edge is swept by
# the cutter's whole profile. Where paths end, meet or cross, a wedge of the revolved cutter closes
# the gap on the outside of a turn. With a crossing fillet the cutter also runs along an arc from
# path to path in every inside corner, as a mould maker rounds the corner of the steel between two
# cavities, and clears what steel that arc would leave standing in a sharp corner.

import math
from dataclasses import dataclass

import Part
from FreeCAD import Vector

from morefeatures import cutterprofile
from morefeatures.rib.parameters import RibParameters

POINT_TOLERANCE = 1e-6
ANGLE_TOLERANCE = 1e-9
# How far a fillet arc cuts into each path, as a fraction of the fillet radius, instead of touching
# it; 0.01 leaves a kink of about 8 degrees where the fillet meets the rib. Exactly tangent, a ball
# cutter's sweeps touch along a whole cross-section and fail to fuse. Near-touching sweeps still fuse
# wrongly now and then, so each overlap in turn is tried until one works.
FILLET_ARC_OVERLAPS = (0.01, 0.005, 0.02, 0.0025)
# A fused result is only trusted if no more than this fraction of any fillet sweep is missing from it.
MISSING_VOLUME_TOLERANCE = 1e-4


@dataclass(frozen=True)
class RibCutter:
    tip: cutterprofile.CutterTip
    ribHeight: float
    # The sketch normal: the cutter's axis, pointing from the sketch plane towards the tip.
    axis: Vector

    @property
    def baseRadius(self) -> float:
        return self.tip.radiusBelowTip(self.ribHeight)

    def profileFace(self, position: Vector, across: Vector) -> Part.Face:
        return Part.Face(cutterprofile.buildProfileWire(self.tip, self.ribHeight, self._mapper(position, across)))

    def halfProfileFace(self, position: Vector, across: Vector) -> Part.Face:
        return Part.Face(cutterprofile.buildHalfProfileWire(self.tip, self.ribHeight, self._mapper(position, across)))

    def _mapper(self, position: Vector, across: Vector) -> cutterprofile.ProfilePointMapper:
        tipPosition = position + self.axis * self.ribHeight
        return lambda acrossDistance, height: tipPosition + across * acrossDistance + self.axis * height


@dataclass(frozen=True)
class LeavingPath:
    edge: Part.Edge
    direction: Vector


@dataclass(frozen=True)
class Corner:
    """Between two paths leaving a junction; second lies angle counterclockwise from first."""

    position: Vector
    first: LeavingPath
    second: LeavingPath
    angle: float


@dataclass(frozen=True)
class CornerFillet:
    """The arc runs counterclockwise about its centre from start to end, from path to path."""

    centre: Vector
    start: Vector
    end: Vector
    # From the corner to the arc; only where the arc alone would leave steel standing down to the base.
    clearingPass: object


def buildRibs(pathEdges: list, sketchNormal: Vector, parameters: RibParameters) -> Part.Shape:
    if not pathEdges:
        raise ValueError("The path sketch has no lines.")
    cutter = RibCutter(parameters.cutterTip, parameters.ribHeight, Vector(sketchNormal).normalize())
    corners = [corner for position in _findJunctions(pathEdges) for corner in _cornersAt(position, pathEdges, cutter)]
    pathPieces = [_sweepEdge(edge, cutter) for edge in pathEdges]
    pathPieces += [_buildWedge(corner, cutter) for corner in corners if corner.angle > math.pi + ANGLE_TOLERANCE]
    sharpRibs = _fuse(pathPieces)
    if not _isPlausibleUnion(sharpRibs, pathPieces):
        raise ValueError("The ribs could not be built along this path sketch.")
    filletRadius = parameters.crossingFilletRadius
    if filletRadius <= 0.0:
        return sharpRibs
    for overlap in FILLET_ARC_OVERLAPS:
        fillets = _planCornerFillets(corners, cutter, filletRadius, overlap)
        filletPieces = [piece for fillet in fillets for piece in _sweepCornerFillet(fillet, cutter)]
        ribs = _fuse([sharpRibs] + filletPieces)
        if _isPlausibleUnion(ribs, [sharpRibs] + filletPieces) and _containsAll(ribs, filletPieces):
            return ribs
    raise ValueError(
        "The rib crossings fillet radius {0} mm could not be built; a slightly different radius usually works.".format(
            filletRadius
        )
    )


def _fuse(pieces: list) -> Part.Shape:
    first, *others = pieces
    fused = first.fuse(others) if others else first
    return fused.removeSplitter()


def _containsAll(union: Part.Shape, pieces: list) -> bool:
    """Catches a boolean that silently drops a piece, which no volume bound can."""
    return all(piece.cut(union).Volume <= MISSING_VOLUME_TOLERANCE * piece.Volume for piece in pieces)


def _isPlausibleUnion(union: Part.Shape, pieces: list) -> bool:
    """A broken boolean can still pass as valid, but not with a volume no union could have."""
    volumes = [piece.Volume for piece in pieces]
    tolerance = POINT_TOLERANCE * sum(volumes)
    return union.isValid() and max(volumes) - tolerance <= union.Volume <= sum(volumes) + tolerance


def _sweepEdge(edge: Part.Edge, cutter: RibCutter) -> Part.Shape:
    start = edge.valueAt(edge.FirstParameter)
    if isinstance(edge.Curve, Part.Line):
        direction = edge.valueAt(edge.LastParameter) - start
        return cutter.profileFace(start, _unit(direction.cross(cutter.axis))).extrude(direction)
    if isinstance(edge.Curve, Part.Circle):
        circle = edge.Curve
        if circle.Radius <= cutter.baseRadius + POINT_TOLERANCE:
            raise ValueError(
                "An arc of radius {0:.2f} mm is tighter than half the rib width at its base ({1:.2f} mm).".format(
                    circle.Radius, cutter.baseRadius
                )
            )
        sweptAngle = math.degrees(edge.LastParameter - edge.FirstParameter)
        return cutter.profileFace(start, _unit(start - circle.Center)).revolve(circle.Center, circle.Axis, sweptAngle)
    raise ValueError("The path sketch may only hold lines and arcs, not a {0}.".format(type(edge.Curve).__name__))


def _buildWedge(corner: Corner, cutter: RibCutter) -> Part.Shape:
    """Each path's sweep covers the half of the cutter it leaves into; the rest of an outside
    corner wider than half a turn is filled by this wedge of the revolved cutter."""
    startAcross = _rotated(corner.first.direction, cutter.axis, math.pi / 2.0)
    wedgeAngle = math.degrees(corner.angle - math.pi)
    return cutter.halfProfileFace(corner.position, startAcross).revolve(corner.position, cutter.axis, wedgeAngle)


def _planCornerFillets(corners: list, cutter: RibCutter, filletRadius: float, overlap: float) -> list:
    insideCorners = [corner for corner in corners if ANGLE_TOLERANCE < corner.angle < math.pi - ANGLE_TOLERANCE]
    return [_planCornerFillet(corner, cutter, filletRadius, overlap) for corner in insideCorners]


def _planCornerFillet(corner: Corner, cutter: RibCutter, filletRadius: float, overlap: float) -> CornerFillet:
    # Wide enough that the rib's own surface is rounded with the fillet radius at its base.
    pathRadius = filletRadius + cutter.baseRadius
    centre = _findFilletCentre(corner, cutter.axis, pathRadius - overlap * filletRadius)
    filletCircle = Part.Circle(centre, cutter.axis, pathRadius)
    firstEnd, secondEnd = (
        _findArcEnd(filletCircle, path.edge, corner.position) for path in (corner.first, corner.second)
    )
    if firstEnd is None or secondEnd is None:
        raise ValueError(
            "The rib crossings fillet radius {0} mm does not fit: a path meeting another one is too short.".format(
                filletRadius
            )
        )
    # Measured along the corner's bisector, down at the base where the cutter is widest.
    reachedAlongPaths = cutter.baseRadius / math.sin(corner.angle / 2.0)
    reachedFromArc = (centre - corner.position).Length - pathRadius - cutter.baseRadius
    if reachedFromArc * math.sin(corner.angle / 2.0) > 2.0 * cutter.baseRadius:
        raise ValueError(
            "The rib crossings fillet radius {0} mm is too large for a corner this sharp.".format(filletRadius)
        )
    clearingPass = None
    if reachedFromArc > reachedAlongPaths:
        arcPointNearestCorner = centre + _unit(corner.position - centre) * pathRadius
        clearingPass = Part.LineSegment(corner.position, arcPointNearestCorner).toShape()
    # Seen from the centre, the corner's second path lies clockwise of its first.
    return CornerFillet(centre, secondEnd, firstEnd, clearingPass)


def _findArcEnd(filletCircle: Part.Circle, edge: Part.Edge, cornerPosition: Vector):
    """Where the fillet circle crosses the path nearest the corner; None if not on the edge."""
    crossings = [Vector(point.X, point.Y, point.Z) for point in filletCircle.intersectCC(edge.Curve)]
    onEdge = [point for point in crossings if _isOnEdge(edge, point)]
    return min(onEdge, key=lambda point: (point - cornerPosition).Length, default=None)


def _sweepCornerFillet(fillet: CornerFillet, cutter: RibCutter) -> list:
    sweptAngle = _angleAbout(cutter.axis, fillet.start - fillet.centre, fillet.end - fillet.centre)
    arcSweep = cutter.profileFace(fillet.start, _unit(fillet.start - fillet.centre)).revolve(
        fillet.centre, cutter.axis, math.degrees(sweptAngle)
    )
    if fillet.clearingPass is None:
        return [arcSweep]
    return [arcSweep, _sweepEdge(fillet.clearingPass, cutter)]


def _findFilletCentre(corner: Corner, axis: Vector, centreDistance: float) -> Vector:
    """Where the two paths, each offset into the corner by the centre distance, cross nearest to it."""
    firstOffset = _offsetCurve(
        corner.first, corner.position, _rotated(corner.first.direction, axis, math.pi / 2.0), centreDistance
    )
    secondOffset = _offsetCurve(
        corner.second, corner.position, _rotated(corner.second.direction, axis, -math.pi / 2.0), centreDistance
    )
    crossings = [Vector(point.X, point.Y, point.Z) for point in firstOffset.intersectCC(secondOffset)]
    inCorner = [
        point
        for point in crossings
        if 0.0 < _angleAbout(axis, corner.first.direction, point - corner.position) < corner.angle
    ]
    if not inCorner:
        raise ValueError("The rib crossings fillet does not fit into a corner where ribs meet.")
    return min(inCorner, key=lambda point: (point - corner.position).Length)


def _offsetCurve(leavingPath: LeavingPath, position: Vector, towardsCorner: Vector, distance: float):
    curve = leavingPath.edge.Curve
    if isinstance(curve, Part.Circle):
        isTowardsCentre = towardsCorner.dot(position - curve.Center) < 0.0
        offsetRadius = curve.Radius - distance if isTowardsCentre else curve.Radius + distance
        if offsetRadius <= POINT_TOLERANCE:
            raise ValueError("The rib crossings fillet does not fit inside an arc of the path.")
        return Part.Circle(curve.Center, curve.Axis, offsetRadius)
    offsetPosition = position + towardsCorner * distance
    return Part.Line(offsetPosition, offsetPosition + leavingPath.direction)


def _cornersAt(position: Vector, pathEdges: list, cutter: RibCutter) -> list:
    leavingPaths = _leavingPathsAt(position, pathEdges)
    reference = leavingPaths[0].direction
    angledPaths = sorted(
        ((_angleAbout(cutter.axis, reference, path.direction), path) for path in leavingPaths), key=lambda pair: pair[0]
    )
    # The last corner closes the full turn back to the first path.
    nextAngledPaths = angledPaths[1:] + [(angledPaths[0][0] + 2.0 * math.pi, angledPaths[0][1])]
    return [
        Corner(position, first, second, secondAngle - firstAngle)
        for (firstAngle, first), (secondAngle, second) in zip(angledPaths, nextAngledPaths)
    ]


def _findJunctions(pathEdges: list) -> list:
    """Every point where a path ends, meets another or crosses it."""
    candidates = [end for edge in pathEdges for end in _edgeEnds(edge)]
    for index, edge in enumerate(pathEdges):
        for other in pathEdges[index + 1 :]:
            candidates += _crossings(edge, other)
    junctions = []
    for candidate in candidates:
        if not any(_isSamePosition(candidate, junction) for junction in junctions):
            junctions.append(candidate)
    return junctions


def _crossings(edge: Part.Edge, other: Part.Edge) -> list:
    try:
        points = edge.Curve.intersectCC(other.Curve)
    except RuntimeError:
        # Overlapping collinear paths have no single crossing point.
        return []
    crossings = [Vector(point.X, point.Y, point.Z) for point in points if isinstance(point, Part.Point)]
    return [point for point in crossings if _isOnEdge(edge, point) and _isOnEdge(other, point)]


def _leavingPathsAt(position: Vector, pathEdges: list) -> list:
    """An edge ending at the position leaves it one way, one running on through it both ways."""
    leavingPaths = []
    for edge in pathEdges:
        first = edge.FirstParameter
        last = edge.LastParameter
        if not edge.isClosed() and _isSamePosition(edge.valueAt(first), position):
            leavingPaths.append(LeavingPath(edge, _tangentAt(edge, first)))
        elif not edge.isClosed() and _isSamePosition(edge.valueAt(last), position):
            leavingPaths.append(LeavingPath(edge, -_tangentAt(edge, last)))
        elif _isOnEdge(edge, position):
            tangent = _tangentAt(edge, edge.Curve.parameter(position))
            leavingPaths += [LeavingPath(edge, tangent), LeavingPath(edge, -tangent)]
    return leavingPaths


def _edgeEnds(edge: Part.Edge) -> list:
    if edge.isClosed():
        return []
    return [edge.valueAt(edge.FirstParameter), edge.valueAt(edge.LastParameter)]


def _isOnEdge(edge: Part.Edge, position: Vector) -> bool:
    return edge.distToShape(Part.Vertex(position))[0] < POINT_TOLERANCE


def _tangentAt(edge: Part.Edge, parameter: float) -> Vector:
    """Along increasing parameter, whichever way the edge is oriented."""
    if isinstance(edge.Curve, Part.Circle):
        circle = edge.Curve
        return _unit(circle.Axis.cross(edge.Curve.value(parameter) - circle.Center))
    return _unit(edge.valueAt(edge.LastParameter) - edge.valueAt(edge.FirstParameter))


def _angleAbout(axis: Vector, reference: Vector, direction: Vector) -> float:
    return math.atan2(axis.cross(reference).dot(direction), reference.dot(direction)) % (2.0 * math.pi)


def _rotated(direction: Vector, axis: Vector, angle: float) -> Vector:
    return direction * math.cos(angle) + axis.cross(direction) * math.sin(angle)


def _isSamePosition(position: Vector, other: Vector) -> bool:
    return (position - other).Length < POINT_TOLERANCE


def _unit(vector: Vector) -> Vector:
    return Vector(vector).normalize()
