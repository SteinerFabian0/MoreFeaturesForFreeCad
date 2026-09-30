# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The boss wizard's inputs: their values, and the field schema the task panel is built from.

import math
from dataclasses import asdict, dataclass, fields

from morefeatures.schema import ANGLE, CHOICE, COUNT, FLAG, LENGTH, ParameterField

BOSS_TYPE_THREAD = "Thread"
BOSS_TYPE_SCREW_HEAD = "Screw head"
BOSS_TYPES = (BOSS_TYPE_THREAD, BOSS_TYPE_SCREW_HEAD)

SUPPORT_NONE = "None"
SUPPORT_GUSSETS = "Gussets"
SUPPORT_RIBS = "Ribs"
SUPPORT_MODES = (SUPPORT_NONE, SUPPORT_GUSSETS, SUPPORT_RIBS)

MAX_DRAFT_ANGLE = 45.0
MIN_GUSSET_COUNT = 1
MAX_GUSSET_COUNT = 4
MIN_GUSSET_ANGLE = 20.0
MAX_GUSSET_ANGLE = 70.0
MAX_BORE_DEPTH_BEYOND_HEIGHT = 0.6
GUSSET_TOP_CLEARANCE = 0.5

BOSS_GROUP = "Boss"
THREAD_BORE_GROUP = "Thread Bore"
INSET_GROUP = "Bore Inset"
SCREW_BORE_GROUP = "Screw Bore"
SCREW_SEAT_GROUP = "Screw Seat Bore"
RUBBER_PAD_GROUP = "Rubber Pad Cutout"
SUPPORT_GROUP = "Supports"
GUSSET_GROUP = "Gussets"


@dataclass
class BossParameters:
    bossType: str = BOSS_TYPE_THREAD
    wallThickness: float = 1.3
    height: float = 5.6
    draftAngle: float = 1.0
    baseFilletRadius: float = 0.5
    topFilletRadius: float = 0.2

    boreDiameter: float = 2.1
    boreDepth: float = 5.8
    boreDraftAngle: float = 0.5

    hasBoreInset: bool = False
    insetDiameter: float = 2.6
    insetDepth: float = 0.25

    screwBoreDiameter: float = 3.0
    screwBoreDraftAngle: float = 1.0
    entryChamferSize: float = 0.2
    topWallThickness: float = 1.7

    screwSeatDiameter: float = 5.8
    screwSeatDraftAngle: float = 1.0
    screwSeatFilletRadius: float = 0.2

    hasRubberPadCutout: bool = False
    rubberPadCutoutDiameter: float = 12.3
    rubberPadCutoutDepth: float = 0.6

    supportMode: str = SUPPORT_GUSSETS
    gussetCount: int = 4
    gussetAngle: float = 45.0
    gussetDraftAngle: float = 2.0
    gussetBaseThickness: float = 1.2
    gussetBaseLength: float = 2.5

    @property
    def maxBoreDepth(self) -> float:
        return self.height + MAX_BORE_DEPTH_BEYOND_HEIGHT

    @property
    def effectiveBoreDepth(self) -> float:
        return min(self.boreDepth, self.maxBoreDepth)

    def isScrewHeadBoss(self) -> bool:
        return self.bossType == BOSS_TYPE_SCREW_HEAD

    def hasThreadBore(self) -> bool:
        return not self.isScrewHeadBoss() and self.boreDiameter > 0.0 and self.boreDepth > 0.0

    def hasInset(self) -> bool:
        return not self.isScrewHeadBoss() and self.hasBoreInset

    def hasRubberPad(self) -> bool:
        return self.isScrewHeadBoss() and self.hasRubberPadCutout

    def hasBore(self) -> bool:
        return self.isScrewHeadBoss() or self.hasThreadBore()

    @property
    def seatHeight(self) -> float:
        return self.height - self.topWallThickness

    @property
    def baseDiameter(self) -> float:
        return 2.0 * (self._drivingOuterRadius + self._drivingHeight * self._outerTaper)

    def wallThicknessForBaseDiameter(self, baseDiameter: float) -> float:
        return baseDiameter / 2.0 - self._drivingHeight * self._outerTaper - self._drivingBoreRadius

    def outerRadiusAt(self, height: float) -> float:
        return self.baseDiameter / 2.0 - height * self._outerTaper

    @property
    def _drivingHeight(self) -> float:
        """Where wallThickness is measured: the screw seat, or the top of a thread boss."""
        return self.seatHeight if self.isScrewHeadBoss() else self.height

    @property
    def _drivingOuterRadius(self) -> float:
        return self._drivingBoreRadius + self.wallThickness

    @property
    def _drivingBoreRadius(self) -> float:
        if self.isScrewHeadBoss():
            return self.screwSeatDiameter / 2.0
        return self.boreDiameter / 2.0 if self.hasThreadBore() else 0.0

    @property
    def _outerTaper(self) -> float:
        return _taper(self.draftAngle)

    @property
    def wallMeasurementHeight(self) -> float:
        """The boss base, or a thread bore's bottom where that stops above the base."""
        if self.isScrewHeadBoss():
            return 0.0
        return max(self.height - self.effectiveBoreDepth, 0.0)

    @property
    def wallThicknessAtBase(self) -> float:
        """Of the boss wall at wallMeasurementHeight."""
        return self.outerRadiusAt(self.wallMeasurementHeight) - self._boreRadiusAt(self.wallMeasurementHeight)

    def screwBoreRadiusAt(self, height: float) -> float:
        return self.screwBoreDiameter / 2.0 + (self.height - height) * _taper(self.screwBoreDraftAngle)

    def screwSeatBoreRadiusAt(self, height: float) -> float:
        return self.screwSeatDiameter / 2.0 + (self.seatHeight - height) * _taper(self.screwSeatDraftAngle)

    @property
    def entryChamferRadiusAtSeat(self) -> float:
        """The 45° chamfer meets the screw bore wall entryChamferSize above the seat."""
        return self.screwBoreRadiusAt(self.seatHeight + self.entryChamferSize) + self.entryChamferSize

    @property
    def flatSeatWidth(self) -> float:
        """Of the ring the screw head presses against, between the entry chamfer and the seat fillet."""
        return self.screwSeatDiameter / 2.0 - self.screwSeatFilletRadius - self.entryChamferRadiusAtSeat

    def _boreRadiusAt(self, height: float) -> float:
        """Below the screw seat for a screw head boss."""
        if self.isScrewHeadBoss():
            return self.screwSeatBoreRadiusAt(height)
        return self.boreDiameter / 2.0 - (self.height - height) * _taper(self.boreDraftAngle)

    @property
    def maxGussetHeight(self) -> float:
        # The rim stays free of gussets so the top fillet runs round a plain circle.
        return max(self.height - GUSSET_TOP_CLEARANCE, 0.0)

    @property
    def gussetHeight(self) -> float:
        return min(self._uncappedGussetHeight(), self.maxGussetHeight)

    def isGussetHeightCapped(self) -> bool:
        return self._uncappedGussetHeight() > self.maxGussetHeight

    def _uncappedGussetHeight(self) -> float:
        return self.gussetBaseLength * math.tan(math.radians(self.gussetAngle))

    def hasGussets(self) -> bool:
        return self.supportMode == SUPPORT_GUSSETS

    def hasSupports(self) -> bool:
        return self.supportMode != SUPPORT_NONE

    @property
    def gussetAngleStep(self) -> float:
        return 360.0 / self.gussetCount

    def allGussetIndices(self) -> tuple:
        return tuple(range(self.gussetCount)) if self.hasGussets() else ()

    def keptGussetIndices(self, skippedGussetIndices) -> tuple:
        return tuple(index for index in self.allGussetIndices() if index not in skippedGussetIndices)

    def toDict(self) -> dict:
        return asdict(self)


PARAMETER_FIELDS = (
    ParameterField("bossType", "Boss type", BOSS_GROUP, CHOICE, choices=BOSS_TYPES),
    ParameterField(
        "boreDiameter", "Thread bore diameter", THREAD_BORE_GROUP, LENGTH,
        tooltip="The hole the screw threads into, measured at the bore entry on the boss top.",
    ),
    ParameterField(
        "boreDepth", "Thread bore depth", THREAD_BORE_GROUP, LENGTH,
        tooltip="Measured from the bore entry to its flat bottom. At most {0} mm deeper than the boss is high.".format(
            MAX_BORE_DEPTH_BEYOND_HEIGHT
        ),
    ),
    ParameterField(
        "boreDraftAngle", "Thread bore draft angle", THREAD_BORE_GROUP, ANGLE, 0.0, MAX_DRAFT_ANGLE,
        tooltip="The thread bore narrows towards its bottom.",
    ),
    ParameterField("hasBoreInset", "Enable bore inset", INSET_GROUP, FLAG),
    ParameterField("insetDiameter", "Inset diameter", INSET_GROUP, LENGTH),
    ParameterField(
        "insetDepth", "Inset depth", INSET_GROUP, LENGTH, tooltip="The inset uses the thread bore draft angle."
    ),
    ParameterField(
        "screwBoreDiameter", "Screw bore diameter", SCREW_BORE_GROUP, LENGTH, 0.01,
        tooltip="The hole the screw shank passes through, measured at the boss top, where it is narrowest.",
    ),
    ParameterField(
        "screwBoreDraftAngle", "Screw bore draft angle", SCREW_BORE_GROUP, ANGLE, 0.0, MAX_DRAFT_ANGLE,
        tooltip="The screw bore widens downwards, towards the screw seat.",
    ),
    ParameterField(
        "entryChamferSize", "Entry chamfer size", SCREW_BORE_GROUP, LENGTH,
        tooltip="A 45° chamfer where the screw bore opens into the screw seat, clearing the screw's under-head "
        "fillet. 0 for none.",
    ),
    ParameterField(
        "topWallThickness", "Top wall thickness", SCREW_BORE_GROUP, LENGTH, 0.01,
        tooltip="From the boss top down to the screw seat, the face the screw head presses against.",
    ),
    ParameterField(
        "screwSeatDiameter", "Screw seat diameter", SCREW_SEAT_GROUP, LENGTH, 0.01,
        tooltip="The bore the screw head sits in, measured at the screw seat. From there it runs down through "
        "the part below the boss.",
    ),
    ParameterField(
        "screwSeatDraftAngle", "Screw seat bore draft angle", SCREW_SEAT_GROUP, ANGLE, 0.0, MAX_DRAFT_ANGLE,
        tooltip="The screw seat bore widens downwards, towards the part's bottom face.",
    ),
    ParameterField(
        "screwSeatFilletRadius", "Screw seat fillet radius", SCREW_SEAT_GROUP, LENGTH,
        tooltip="Rounds the corner where the screw seat meets the screw seat bore's wall. 0 for none.",
    ),
    ParameterField(
        "wallThickness", "Wall thickness", BOSS_GROUP, LENGTH, 0.01,
        tooltip="Sizes the boss by its wall where it is thinnest: around the bore entry at the top of a thread "
        "boss, around the screw seat of a screw head boss. The outer draft thickens it further down.",
    ),
    ParameterField(
        "height", "Boss height", BOSS_GROUP, LENGTH, 0.01, tooltip="From the sketch plane to the boss top."
    ),
    ParameterField("draftAngle", "Outside draft angle", BOSS_GROUP, ANGLE, 0.0, MAX_DRAFT_ANGLE),
    ParameterField(
        "baseFilletRadius", "Boss base fillet", BOSS_GROUP, LENGTH,
        tooltip="Rounds the boss into the face it stands on. With gussets, the same radius also rounds "
        "the gussets into that face and into the boss.",
    ),
    ParameterField(
        "topFilletRadius", "Outer top edge fillet", BOSS_GROUP, LENGTH, tooltip="Rounds the boss's outer top edge."
    ),
    ParameterField("hasRubberPadCutout", "Enable rubber pad cutout", RUBBER_PAD_GROUP, FLAG),
    ParameterField("rubberPadCutoutDiameter", "Cutout diameter", RUBBER_PAD_GROUP, LENGTH, 0.01),
    ParameterField(
        "rubberPadCutoutDepth", "Cutout depth", RUBBER_PAD_GROUP, LENGTH, 0.01,
        tooltip="Measured from the part's bottom face below each boss.",
    ),
    ParameterField("supportMode", "Supports", SUPPORT_GROUP, CHOICE, choices=SUPPORT_MODES),
    ParameterField("gussetCount", "Gusset count", GUSSET_GROUP, COUNT, MIN_GUSSET_COUNT, MAX_GUSSET_COUNT),
    ParameterField(
        "gussetAngle", "Gusset angle", GUSSET_GROUP, ANGLE, MIN_GUSSET_ANGLE, MAX_GUSSET_ANGLE,
        tooltip="Measured from the base plane; steeper gussets take less horizontal space.",
    ),
    ParameterField("gussetDraftAngle", "Gusset draft angle", GUSSET_GROUP, ANGLE, 0.0, MAX_DRAFT_ANGLE),
    ParameterField("gussetBaseThickness", "Gusset base thickness", GUSSET_GROUP, LENGTH),
    ParameterField(
        "gussetBaseLength", "Gusset base length", GUSSET_GROUP, LENGTH,
        tooltip="How far the gusset reaches outward from the boss base diameter.",
    ),
)

THREAD_FIELD_NAMES = tuple(
    field.name for field in PARAMETER_FIELDS if field.group in (THREAD_BORE_GROUP, INSET_GROUP)
)
SCREW_HEAD_GROUPS = (SCREW_BORE_GROUP, SCREW_SEAT_GROUP, RUBBER_PAD_GROUP)
SCREW_HEAD_FIELD_NAMES = tuple(field.name for field in PARAMETER_FIELDS if field.group in SCREW_HEAD_GROUPS)
INSET_FIELD_NAMES = ("insetDiameter", "insetDepth")
RUBBER_PAD_FIELD_NAMES = ("rubberPadCutoutDiameter", "rubberPadCutoutDepth")
GUSSET_FIELD_NAMES = tuple(field.name for field in PARAMETER_FIELDS if field.name.startswith("gusset"))


def _taper(draftAngle: float) -> float:
    return math.tan(math.radians(draftAngle))


def fromDict(values: dict) -> BossParameters:
    knownNames = {field.name for field in fields(BossParameters)}
    return BossParameters(**{name: value for name, value in values.items() if name in knownNames})


def isFieldRelevant(parameters: BossParameters, name: str) -> bool:
    if name in INSET_FIELD_NAMES:
        return parameters.hasInset()
    if name in RUBBER_PAD_FIELD_NAMES:
        return parameters.hasRubberPad()
    if name in THREAD_FIELD_NAMES:
        return not parameters.isScrewHeadBoss()
    if name in SCREW_HEAD_FIELD_NAMES:
        return parameters.isScrewHeadBoss()
    if name in GUSSET_FIELD_NAMES:
        return parameters.hasGussets()
    return True


def _assertFieldsMatchParameters() -> None:
    declared = {field.name for field in fields(BossParameters)}
    described = {field.name for field in PARAMETER_FIELDS}
    if declared != described:
        raise RuntimeError("PARAMETER_FIELDS is out of sync with BossParameters: {0}".format(declared ^ described))


_assertFieldsMatchParameters()
