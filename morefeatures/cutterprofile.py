# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The silhouette of a cutter with a ball, flat or corner radius tip whose flanks taper outward
# above the tip. The ribs are swept with it, and a boss gusset is the ball cutter's silhouette.

import math
from dataclasses import dataclass
from typing import Callable

import Part
from FreeCAD import Vector

POINT_TOLERANCE = 1e-9

# Maps a profile point (across the axis, height relative to the tip) into 3D.
ProfilePointMapper = Callable[[float, float], Vector]


@dataclass(frozen=True)
class CutterTip:
    roundRadius: float
    # Distance of the round's centre from the axis: 0 for a ball, the flat's half-width otherwise.
    roundCentreRadius: float
    # Per side, from the axis, in radians.
    taper: float

    @property
    def tangentDepth(self) -> float:
        """How far below the tip the round runs into the tapered flank."""
        return self.roundRadius * (1.0 - math.sin(self.taper))

    def radiusBelowTip(self, depth: float) -> float:
        if depth <= self.tangentDepth:
            return self.roundCentreRadius + math.sqrt(self.roundRadius**2 - (self.roundRadius - depth) ** 2)
        flankStartRadius = self.roundCentreRadius + self.roundRadius * math.cos(self.taper)
        return flankStartRadius + (depth - self.tangentDepth) * math.tan(self.taper)


def buildProfileWire(tip: CutterTip, depth: float, toPoint: ProfilePointMapper) -> Part.Wire:
    """Both flanks, tip on height 0, closed straight across at height -depth."""
    top, *rightSide = _buildRightOutline(tip, depth)
    tipCentre, *_, topEnd = top
    # One edge across the tip rather than a pair meeting on the axis.
    wholeTop = (_mirrored(topEnd), tipCentre, topEnd) if len(top) == 3 else (_mirrored(topEnd), topEnd)
    footRight = rightSide[-1][-1] if rightSide else topEnd
    leftSide = [tuple(_mirrored(point) for point in reversed(segment)) for segment in reversed(rightSide)]
    return _toWire([wholeTop] + rightSide + [(footRight, _mirrored(footRight))] + leftSide, toPoint)


def buildHalfProfileWire(tip: CutterTip, depth: float, toPoint: ProfilePointMapper) -> Part.Wire:
    """The side at positive across only, closed along the axis: revolved, it is the cutter."""
    outline = _buildRightOutline(tip, depth)
    footRight = outline[-1][-1]
    footOnAxis = (0.0, -depth)
    return _toWire(outline + [(footRight, footOnAxis), (footOnAxis, (0.0, 0.0))], toPoint)


def _buildRightOutline(tip: CutterTip, depth: float) -> list:
    """Segments from the tip centre out to the foot: 2 points for a line, 3 for an arc through
    its middle point."""
    hasFlat = tip.roundCentreRadius > POINT_TOLERANCE
    hasRound = tip.roundRadius > POINT_TOLERANCE
    if not hasFlat and not hasRound:
        raise ValueError("The cutter tip has no size.")
    flatEnd = (tip.roundCentreRadius, 0.0)
    outline = [((0.0, 0.0), flatEnd)] if hasFlat else []
    roundEnd = flatEnd
    if hasRound:
        roundEndAngle = _roundAngleAtDepth(tip, min(depth, tip.tangentDepth))
        roundEnd = _pointOnRound(tip, roundEndAngle)
        outline.append((flatEnd, _pointOnRound(tip, roundEndAngle / 2.0), roundEnd))
    if depth > tip.tangentDepth + POINT_TOLERANCE:
        outline.append((roundEnd, (tip.radiusBelowTip(depth), -depth)))
    return outline


def _roundAngleAtDepth(tip: CutterTip, depth: float) -> float:
    """Measured at the round's centre, from straight up."""
    return math.acos((tip.roundRadius - depth) / tip.roundRadius)


def _pointOnRound(tip: CutterTip, angle: float) -> tuple:
    return (
        tip.roundCentreRadius + tip.roundRadius * math.sin(angle),
        -tip.roundRadius + tip.roundRadius * math.cos(angle),
    )


def _mirrored(point: tuple) -> tuple:
    return (-point[0], point[1])


def _toWire(segments: list, toPoint: ProfilePointMapper) -> Part.Wire:
    return Part.Wire([_toEdge([toPoint(*point) for point in segment]) for segment in segments])


def _toEdge(points: list) -> Part.Edge:
    if len(points) == 3:
        return Part.Arc(*points).toShape()
    return Part.LineSegment(*points).toShape()
