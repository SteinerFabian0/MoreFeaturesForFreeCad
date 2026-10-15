# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The silhouette of a cutter with a ball, flat or corner radius tip whose flanks taper outward
# above the tip, optionally flaring out into a concave fillet at its foot. The ribs are swept with
# it, and a boss gusset is the ball cutter's silhouette.

import math
from dataclasses import dataclass
from typing import Callable

import Part
from FreeCAD import Vector

POINT_TOLERANCE = 1e-9
# The foot fillet's circle dips this fraction of its radius below the foot, so it meets the face the
# cutter's foot stands on at about 8 degrees and its knife-edged end lies inside that face's part.
# Exactly tangent, that end lies on the face itself and fuses wrongly now and then.
FOOT_FILLET_SINK = 0.01

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


def footReach(tip: CutterTip, depth: float, footFilletRadius: float) -> float:
    """How far the profile reaches out from the axis at its foot, foot fillet included."""
    footDepth = _footDepth(depth, footFilletRadius)
    return tip.radiusBelowTip(footDepth) + footFilletRadius * (1.0 - math.sin(tip.taper)) / math.cos(tip.taper)


def buildProfileWire(
    tip: CutterTip, depth: float, toPoint: ProfilePointMapper, footFilletRadius: float = 0.0
) -> Part.Wire:
    """Both flanks, tip on height 0, closed straight across at height -depth. A foot fillet
    rounds each flank into a face at height -depth, sinking the foot a little below it."""
    top, *rightSide = _buildRightOutline(tip, depth, footFilletRadius)
    tipCentre, *_, topEnd = top
    # One edge across the tip rather than a pair meeting on the axis.
    wholeTop = (_mirrored(topEnd), tipCentre, topEnd) if len(top) == 3 else (_mirrored(topEnd), topEnd)
    footRight = rightSide[-1][-1] if rightSide else topEnd
    leftSide = [tuple(_mirrored(point) for point in reversed(segment)) for segment in reversed(rightSide)]
    return _toWire([wholeTop] + rightSide + [(footRight, _mirrored(footRight))] + leftSide, toPoint)


def buildHalfProfileWire(
    tip: CutterTip, depth: float, toPoint: ProfilePointMapper, footFilletRadius: float = 0.0
) -> Part.Wire:
    """The side at positive across only, closed along the axis: revolved, it is the cutter."""
    outline = _buildRightOutline(tip, depth, footFilletRadius)
    footRight = outline[-1][-1]
    footOnAxis = (0.0, footRight[1])
    return _toWire(outline + [(footRight, footOnAxis), (footOnAxis, (0.0, 0.0))], toPoint)


def _buildRightOutline(tip: CutterTip, depth: float, footFilletRadius: float) -> list:
    """Segments from the tip centre out to the foot: 2 points for a line, 3 for an arc through
    its middle point."""
    hasFlat = tip.roundCentreRadius > POINT_TOLERANCE
    hasRound = tip.roundRadius > POINT_TOLERANCE
    hasFootFillet = footFilletRadius > POINT_TOLERANCE
    if not hasFlat and not hasRound:
        raise ValueError("The cutter tip has no size.")
    footDepth = _footDepth(depth, footFilletRadius)
    flankDepth = footDepth - footFilletRadius * (1.0 - math.sin(tip.taper))
    if hasFootFillet and flankDepth <= tip.tangentDepth + POINT_TOLERANCE:
        raise ValueError("The base fillet radius {0} mm does not fit below the rounded tip.".format(footFilletRadius))
    flatEnd = (tip.roundCentreRadius, 0.0)
    outline = [((0.0, 0.0), flatEnd)] if hasFlat else []
    roundEnd = flatEnd
    if hasRound:
        roundEndAngle = _roundAngleAtDepth(tip, min(flankDepth, tip.tangentDepth))
        roundEnd = _pointOnRound(tip, roundEndAngle)
        outline.append((flatEnd, _pointOnRound(tip, roundEndAngle / 2.0), roundEnd))
    flankEnd = (tip.radiusBelowTip(flankDepth), -flankDepth)
    if flankDepth > tip.tangentDepth + POINT_TOLERANCE:
        outline.append((roundEnd, flankEnd))
    if hasFootFillet:
        outline.append(_buildFootFillet(tip, flankEnd, footDepth, footFilletRadius))
    return outline


def _footDepth(depth: float, footFilletRadius: float) -> float:
    return depth + footFilletRadius * FOOT_FILLET_SINK


def _buildFootFillet(tip: CutterTip, flankEnd: tuple, footDepth: float, radius: float) -> tuple:
    """Concave, from the flank down to the foot line at height -footDepth, tangent to both."""
    centre = (flankEnd[0] + radius * math.cos(tip.taper), -footDepth + radius)
    towardsMiddle = (-math.cos(tip.taper), -(1.0 + math.sin(tip.taper)))
    middleScale = radius / math.hypot(*towardsMiddle)
    middle = (centre[0] + towardsMiddle[0] * middleScale, centre[1] + towardsMiddle[1] * middleScale)
    return (flankEnd, middle, (centre[0], -footDepth))


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
