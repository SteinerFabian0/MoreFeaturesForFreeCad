# The boss wizard's inputs: their values, and the field schema the task panel is built from.

import math
from dataclasses import asdict, dataclass, fields

from morefeatures.schema import ANGLE, CHOICE, COUNT, FLAG, LENGTH, ParameterField

SUPPORT_NONE = "None"
SUPPORT_GUSSETS = "Gussets"
SUPPORT_RIBS = "Ribs"
SUPPORT_MODES = (SUPPORT_NONE, SUPPORT_GUSSETS, SUPPORT_RIBS)

MAX_DRAFT_ANGLE = 45.0
MIN_GUSSET_COUNT = 2
MAX_GUSSET_COUNT = 4

BOSS_GROUP = "Boss"
BORE_GROUP = "Bore"
INSET_GROUP = "Bore Inset"
SUPPORT_GROUP = "Supports"


@dataclass
class BossParameters:
    baseDiameter: float = 8.0
    height: float = 10.0
    draftAngle: float = 1.0
    baseFilletRadius: float = 1.0
    topFilletRadius: float = 0.3

    boreDiameter: float = 3.0
    boreDepth: float = 8.0
    boreDraftAngle: float = 0.5

    hasBoreInset: bool = False
    insetDiameter: float = 4.5
    insetDepth: float = 1.0

    supportMode: str = SUPPORT_NONE
    gussetCount: int = 4
    gussetAngle: float = 60.0
    gussetDraftAngle: float = 1.0
    gussetBaseThickness: float = 1.5
    gussetBaseLength: float = 4.0
    gussetFilletRadius: float = 0.5

    @property
    def gussetHeight(self) -> float:
        return min(self._uncappedGussetHeight(), self.height)

    def isGussetHeightCapped(self) -> bool:
        return self._uncappedGussetHeight() > self.height

    def _uncappedGussetHeight(self) -> float:
        return self.gussetBaseLength * math.tan(math.radians(self.gussetAngle))

    def hasGussets(self) -> bool:
        return self.supportMode == SUPPORT_GUSSETS

    def toDict(self) -> dict:
        return asdict(self)


PARAMETER_FIELDS = (
    ParameterField("baseDiameter", "Base diameter", BOSS_GROUP, LENGTH, 0.01),
    ParameterField("height", "Height", BOSS_GROUP, LENGTH, 0.01),
    ParameterField("draftAngle", "Draft angle", BOSS_GROUP, ANGLE, 0.0, MAX_DRAFT_ANGLE),
    ParameterField("baseFilletRadius", "Base fillet radius", BOSS_GROUP, LENGTH),
    ParameterField("topFilletRadius", "Top fillet radius", BOSS_GROUP, LENGTH),
    ParameterField("boreDiameter", "Bore diameter", BORE_GROUP, LENGTH, tooltip="Measured at the bore entry."),
    ParameterField(
        "boreDepth", "Bore depth", BORE_GROUP, LENGTH, tooltip="Measured from the bore entry to its flat bottom."
    ),
    ParameterField("boreDraftAngle", "Bore draft angle", BORE_GROUP, ANGLE, 0.0, MAX_DRAFT_ANGLE),
    ParameterField("hasBoreInset", "Enable bore inset", INSET_GROUP, FLAG),
    ParameterField("insetDiameter", "Inset diameter", INSET_GROUP, LENGTH),
    ParameterField(
        "insetDepth", "Inset depth", INSET_GROUP, LENGTH, tooltip="The inset uses the bore draft angle."
    ),
    ParameterField("supportMode", "Supports", SUPPORT_GROUP, CHOICE, choices=SUPPORT_MODES),
    ParameterField("gussetCount", "Gusset count", SUPPORT_GROUP, COUNT, MIN_GUSSET_COUNT, MAX_GUSSET_COUNT),
    ParameterField(
        "gussetAngle", "Gusset angle", SUPPORT_GROUP, ANGLE, 0.01, 89.99,
        tooltip="Measured from the base plane; steeper gussets take less horizontal space.",
    ),
    ParameterField("gussetDraftAngle", "Gusset draft angle", SUPPORT_GROUP, ANGLE, 0.0, MAX_DRAFT_ANGLE),
    ParameterField("gussetBaseThickness", "Gusset base thickness", SUPPORT_GROUP, LENGTH),
    ParameterField(
        "gussetBaseLength", "Gusset base length", SUPPORT_GROUP, LENGTH,
        tooltip="How far the gusset reaches outward from the boss base diameter.",
    ),
    ParameterField("gussetFilletRadius", "Gusset vertical fillet radius", SUPPORT_GROUP, LENGTH),
)

INSET_FIELD_NAMES = ("insetDiameter", "insetDepth")
GUSSET_FIELD_NAMES = tuple(field.name for field in PARAMETER_FIELDS if field.name.startswith("gusset"))


def fromDict(values: dict) -> BossParameters:
    knownNames = {field.name for field in fields(BossParameters)}
    return BossParameters(**{name: value for name, value in values.items() if name in knownNames})


def isFieldRelevant(parameters: BossParameters, name: str) -> bool:
    if name in INSET_FIELD_NAMES:
        return parameters.hasBoreInset
    if name in GUSSET_FIELD_NAMES:
        return parameters.hasGussets()
    return True


def _assertFieldsMatchParameters() -> None:
    declared = {field.name for field in fields(BossParameters)}
    described = {field.name for field in PARAMETER_FIELDS}
    if declared != described:
        raise RuntimeError("PARAMETER_FIELDS is out of sync with BossParameters: {0}".format(declared ^ described))


_assertFieldsMatchParameters()
