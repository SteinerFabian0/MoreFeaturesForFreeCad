# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The pocket push wizard's inputs: the cavity pushed into the part and the walls around it, and the
# field schema the task panel and the feature's properties are built from.

import math
from dataclasses import asdict, dataclass, fields

from morefeatures.schema import ANGLE, FLAG, LENGTH, ParameterField

MAX_DRAFT_ANGLE = 30.0

POCKET_GROUP = "Pocket"
WALL_GROUP = "Walls"
FILLET_GROUP = "Fillets"


@dataclass
class PocketPushParameters:
    cavityDepth: float = 10.0
    draftAngle: float = 1.0
    sideWallThickness: float = 2.0
    topWallThickness: float = 2.0
    isReversed: bool = False
    innerCornerRadius: float = 1.0
    topFilletRadius: float = 0.0
    isTopFilletAuto: bool = True

    @property
    def outerCornerRadius(self) -> float:
        return self.innerCornerRadius + self.sideWallThickness

    @property
    def topFilletRadiusInEffect(self) -> float:
        return self.outerCornerRadius if self.isTopFilletAuto else self.topFilletRadius

    @property
    def outerHeight(self) -> float:
        return self.cavityDepth + self.topWallThickness

    @property
    def sideWallOffset(self) -> float:
        """How far out the walls stand in the sketch plane, for sideWallThickness square to the drafted wall."""
        return self.sideWallThickness / math.cos(math.radians(self.draftAngle))

    def toDict(self) -> dict:
        return asdict(self)


PARAMETER_FIELDS = (
    ParameterField(
        "cavityDepth", "Cavity depth", POCKET_GROUP, LENGTH, 0.01,
        tooltip="From the sketch plane to the cavity's floor.",
    ),
    ParameterField(
        "draftAngle", "Draft angle", POCKET_GROUP, ANGLE, 0.0, MAX_DRAFT_ANGLE,
        tooltip="Of the cavity's and the outer walls; the cavity is widest at the sketch plane.",
    ),
    ParameterField(
        "isReversed", "Reversed", POCKET_GROUP, FLAG,
        tooltip="Push along the sketch normal instead of against it.",
    ),
    ParameterField(
        "sideWallThickness", "Side wall thickness", WALL_GROUP, LENGTH, 0.01,
        tooltip="Measured square to the drafted wall.",
    ),
    ParameterField(
        "topWallThickness", "Top wall thickness", WALL_GROUP, LENGTH, 0.01,
        tooltip="Above the cavity's floor.",
    ),
    ParameterField(
        "innerCornerRadius", "Inner corner radius", FILLET_GROUP, LENGTH,
        tooltip="Rounds the cavity's corners along the pull direction. The outside corners get this radius "
        "plus the side wall thickness, so the wall keeps its thickness around them. 0 leaves them sharp.",
    ),
    ParameterField(
        "topFilletRadius", "Top surface fillet", FILLET_GROUP, LENGTH,
        tooltip="Rounds the outer edge around the top of the walls; 0 leaves it sharp.",
    ),
    ParameterField(
        "isTopFilletAuto", "Auto", FILLET_GROUP, FLAG,
        tooltip="Round the top surface with the outside corner radius: inner corner radius plus side wall thickness.",
    ),
)


def fromDict(values: dict) -> PocketPushParameters:
    knownNames = {field.name for field in fields(PocketPushParameters)}
    return PocketPushParameters(**{name: value for name, value in values.items() if name in knownNames})


def _assertFieldsMatchParameters() -> None:
    declared = {field.name for field in fields(PocketPushParameters)}
    described = {field.name for field in PARAMETER_FIELDS}
    if declared != described:
        raise RuntimeError(
            "PARAMETER_FIELDS is out of sync with PocketPushParameters: {0}".format(declared ^ described)
        )


_assertFieldsMatchParameters()
