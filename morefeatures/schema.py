# Building blocks every feature's parameter set is described with: the field schema
# that drives the task panel editors.

from dataclasses import dataclass

LENGTH = "Length"
ANGLE = "Angle"
COUNT = "Count"
FLAG = "Flag"
CHOICE = "Choice"


@dataclass(frozen=True)
class ParameterField:
    name: str
    label: str
    group: str
    kind: str
    minimum: float = 0.0
    maximum: float = 10000.0
    choices: tuple = ()
    tooltip: str = ""
