# The seam between the boss wizard's GUI and the CAD logic that will build the bosses.
# The task panel hands over a complete BossRequest; nothing is built yet.

from dataclasses import dataclass

import FreeCAD as App

from morefeatures.boss.parameters import BossParameters


@dataclass
class BossRequest:
    sketch: object
    body: object
    parameters: BossParameters
    ignoredPointIds: list
    rotationOffsetsByPointId: dict


def buildBosses(request: BossRequest) -> None:
    App.Console.PrintMessage(
        "Boss wizard: geometry is not implemented yet. Body '{0}', sketch '{1}', ignored points {2}, "
        "rotation offsets {3}, parameters {4}\n".format(
            request.body.Label,
            request.sketch.Label,
            request.ignoredPointIds,
            request.rotationOffsetsByPointId,
            request.parameters.toDict(),
        )
    )
