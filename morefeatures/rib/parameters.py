# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The rib wizard's inputs: the mould maker's cutter the ribs are "machined" with, and the field
# schema the task panel and the feature's properties are built from.

import math
from dataclasses import asdict, dataclass, fields

from morefeatures.schema import ANGLE, CHOICE, LENGTH, ParameterField

TIP_BALL = "Ball"
TIP_FLAT = "Flat"
TIP_CORNER_RADIUS = "Corner radius"
TIP_SHAPES = (TIP_BALL, TIP_FLAT, TIP_CORNER_RADIUS)

MAX_TAPER_ANGLE = 45.0

TIP_GROUP = "Tip"
TAPER_GROUP = "Taper"
RIB_GROUP = "Rib"


@dataclass
class RibParameters:
    tipShape: str = TIP_BALL
    ballRadius: float = 0.5
    tipDiameter: float = 1.0
    cornerRadius: float = 0.25
    taperAngle: float = 1.0
    ribHeight: float = 5.0
    crossingFilletRadius: float = 0.0

    @property
    def maxCornerRadius(self) -> float:
        return self.tipDiameter / 2.0

    @property
    def baseWidth(self) -> float:
        return 2.0 * self._cutterRadiusBelowTip(self.ribHeight)

    def _cutterRadiusBelowTip(self, depth: float) -> float:
        taper = math.radians(self.taperAngle)
        if self.tipShape == TIP_BALL:
            return _roundedCutterRadius(depth, self.ballRadius, 0.0, taper)
        if self.tipShape == TIP_FLAT:
            return self.tipDiameter / 2.0 + depth * math.tan(taper)
        # The tip diameter is where the flanks, carried on past the corner radius, meet the tip plane.
        cornerCentreRadius = self.tipDiameter / 2.0 - self.cornerRadius * (1.0 - math.sin(taper)) / math.cos(taper)
        return _roundedCutterRadius(depth, self.cornerRadius, cornerCentreRadius, taper)

    def toDict(self) -> dict:
        return asdict(self)


PARAMETER_FIELDS = (
    ParameterField("tipShape", "Tip shape", TIP_GROUP, CHOICE, choices=TIP_SHAPES),
    ParameterField("ballRadius", "Ball radius", TIP_GROUP, LENGTH, 0.01),
    ParameterField(
        "tipDiameter", "Tip diameter", TIP_GROUP, LENGTH, 0.01,
        tooltip="The cutter's diameter at its tip: the rib's thickness at its top.",
    ),
    ParameterField("cornerRadius", "Corner radius", TIP_GROUP, LENGTH, 0.01),
    ParameterField(
        "taperAngle", "Taper angle", TAPER_GROUP, ANGLE, 0.0, MAX_TAPER_ANGLE,
        tooltip="Per side, from the cutter's axis; this is the rib's draft. 0 for a straight cutter.",
    ),
    ParameterField(
        "ribHeight", "Rib height", RIB_GROUP, LENGTH, 0.01,
        tooltip="From the sketch plane to the very top of the rib.",
    ),
    ParameterField(
        "crossingFilletRadius", "Rib crossings vertical fillet radius", RIB_GROUP, LENGTH,
        tooltip="Rounds the vertical edges where ribs meet or cross; 0 leaves them sharp. Not built yet.",
    ),
)

TIP_SIZE_FIELD_NAMES_BY_SHAPE = {
    TIP_BALL: ("ballRadius",),
    TIP_FLAT: ("tipDiameter",),
    TIP_CORNER_RADIUS: ("tipDiameter", "cornerRadius"),
}
TIP_SIZE_FIELD_NAMES = ("ballRadius", "tipDiameter", "cornerRadius")


def fromDict(values: dict) -> RibParameters:
    knownNames = {field.name for field in fields(RibParameters)}
    return RibParameters(**{name: value for name, value in values.items() if name in knownNames})


def isFieldRelevant(parameters: RibParameters, name: str) -> bool:
    if name in TIP_SIZE_FIELD_NAMES:
        return name in TIP_SIZE_FIELD_NAMES_BY_SHAPE[parameters.tipShape]
    return True


def _roundedCutterRadius(depth: float, roundRadius: float, roundCentreRadius: float, taper: float) -> float:
    """Radius of a cutter whose tip is rounded with roundRadius about a centre roundCentreRadius off
    its axis, depth below the tip; above the tangent point it runs on as the tapered flank."""
    tangentDepth = roundRadius * (1.0 - math.sin(taper))
    if depth <= tangentDepth:
        return roundCentreRadius + math.sqrt(roundRadius**2 - (roundRadius - depth) ** 2)
    return roundCentreRadius + roundRadius * math.cos(taper) + (depth - tangentDepth) * math.tan(taper)


def _assertFieldsMatchParameters() -> None:
    declared = {field.name for field in fields(RibParameters)}
    described = {field.name for field in PARAMETER_FIELDS}
    if declared != described:
        raise RuntimeError("PARAMETER_FIELDS is out of sync with RibParameters: {0}".format(declared ^ described))


_assertFieldsMatchParameters()
