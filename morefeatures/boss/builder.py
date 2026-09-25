# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The seam between the boss wizard's GUI and the CAD logic: the task panel edits a boss feature
# inside one transaction and hands over a complete BossRequest to commit into it.

from dataclasses import dataclass

from morefeatures import preview
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
    skippedGussetsByPointId: dict


def createBosses(sketch, body, parameters: BossParameters):
    """Opens a transaction that commitBosses() or abortBosses() must close."""
    body.Document.openTransaction(CREATE_TRANSACTION_NAME)
    bossFeature = feature.createBossFeature(body, sketch)
    feature.writeParameters(bossFeature, parameters)
    return bossFeature


def beginEditingBosses(bossFeature) -> None:
    """Opens a transaction that commitBosses() or abortBosses() must close."""
    bossFeature.Document.openTransaction(EDIT_TRANSACTION_NAME)


def previewBosses(bossFeature, request: BossRequest) -> None:
    """Recomputes only the boss feature, as a quick preview; features after it catch up on commit."""
    preview.setPreviewing(bossFeature, True)
    _writeRequest(bossFeature, request)
    bossFeature.recompute()


def commitBosses(bossFeature, request: BossRequest) -> None:
    document = bossFeature.Document
    preview.setPreviewing(bossFeature, False)
    _writeRequest(bossFeature, request)
    document.recompute()
    document.commitTransaction()


def abortBosses(bossFeature) -> None:
    document = bossFeature.Document
    preview.setPreviewing(bossFeature, False)
    document.abortTransaction()


def readRequest(bossFeature) -> BossRequest:
    ignoredPointIds, rotationOffsetsByPointId, skippedGussetsByPointId = feature.readInstances(bossFeature)
    return BossRequest(
        bossFeature.Sketch,
        bossFeature.getParentGeoFeatureGroup(),
        feature.readParameters(bossFeature),
        ignoredPointIds,
        rotationOffsetsByPointId,
        skippedGussetsByPointId,
    )


def _writeRequest(bossFeature, request: BossRequest) -> None:
    feature.writeInstances(
        bossFeature, request.ignoredPointIds, request.rotationOffsetsByPointId, request.skippedGussetsByPointId
    )
    feature.writeParameters(bossFeature, request.parameters)
