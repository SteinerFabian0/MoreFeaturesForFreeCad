# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The hole fill wizard's inputs: the round holes of a hexagonal pattern and how far apart they stand,
# and the field schema the task panel and the feature's properties are built from.

import math
from dataclasses import asdict, dataclass, fields

from morefeatures.schema import FLAG, LENGTH, ParameterField

HOLES_GROUP = "Holes"


@dataclass
class HoleFillParameters:
    holeDiameter: float = 0.9
    pitch: float = 1.7
    isReversed: bool = False

    @property
    def holeRadius(self) -> float:
        return self.holeDiameter / 2.0

    @property
    def rowSpacing(self) -> float:
        return self.pitch * math.sqrt(3.0) / 2.0

    @property
    def landWidth(self) -> float:
        return self.pitch - self.holeDiameter

    @property
    def openAreaRatio(self) -> float:
        """Of an endless pattern: one hole per hexagonal cell of pitch × row spacing."""
        return math.pi * self.holeRadius ** 2 / (self.pitch * self.rowSpacing)

    def toDict(self) -> dict:
        return asdict(self)


PARAMETER_FIELDS = (
    ParameterField(
        "holeDiameter", "Hole diameter", HOLES_GROUP, LENGTH, 0.01,
        tooltip="Of every round hole.",
    ),
    ParameterField(
        "pitch", "Pitch", HOLES_GROUP, LENGTH, 0.01,
        tooltip="From a hole's centre to the centre of each of its six neighbours. Must be larger than "
        "the hole diameter.",
    ),
    ParameterField(
        "isReversed", "Reversed", HOLES_GROUP, FLAG,
        tooltip="Cut along the sketch normal instead of against it.",
    ),
)


def fromDict(values: dict) -> HoleFillParameters:
    knownNames = {field.name for field in fields(HoleFillParameters)}
    return HoleFillParameters(**{name: value for name, value in values.items() if name in knownNames})


def _assertFieldsMatchParameters() -> None:
    declared = {field.name for field in fields(HoleFillParameters)}
    described = {field.name for field in PARAMETER_FIELDS}
    if declared != described:
        raise RuntimeError(
            "PARAMETER_FIELDS is out of sync with HoleFillParameters: {0}".format(declared ^ described)
        )


_assertFieldsMatchParameters()
