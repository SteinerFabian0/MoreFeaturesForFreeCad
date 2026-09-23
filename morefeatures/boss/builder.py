# The seam between the boss wizard's GUI and the CAD logic: the task panel hands over a complete
# BossRequest, and this turns it into a boss feature in the Body, or reads one back for editing.

from dataclasses import dataclass

from morefeatures.boss import feature
from morefeatures.boss.parameters import BossParameters

CREATE_TRANSACTION_NAME = "Boss Wizard"
EDIT_TRANSACTION_NAME = "Edit Boss"


@dataclass
class BossRequest:
    sketch: object
    body: object
    parameters: BossParameters
    ignoredPointIds: list
    rotationOffsetsByPointId: dict


def buildBosses(request: BossRequest):
    document = request.body.Document
    document.openTransaction(CREATE_TRANSACTION_NAME)
    bossFeature = feature.createBossFeature(request.body, request.sketch)
    _writeRequest(bossFeature, request)
    document.recompute()
    document.commitTransaction()
    return bossFeature


def updateBosses(bossFeature, request: BossRequest):
    document = bossFeature.Document
    document.openTransaction(EDIT_TRANSACTION_NAME)
    _writeRequest(bossFeature, request)
    document.recompute()
    document.commitTransaction()
    return bossFeature


def readRequest(bossFeature) -> BossRequest:
    ignoredPointIds, rotationOffsetsByPointId = feature.readInstances(bossFeature)
    return BossRequest(
        bossFeature.Sketch,
        bossFeature.getParentGeoFeatureGroup(),
        feature.readParameters(bossFeature),
        ignoredPointIds,
        rotationOffsetsByPointId,
    )


def _writeRequest(bossFeature, request: BossRequest) -> None:
    feature.writeInstances(bossFeature, request.ignoredPointIds, request.rotationOffsetsByPointId)
    feature.writeParameters(bossFeature, request.parameters)
