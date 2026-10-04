# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The seam between the pocket push wizard's GUI and the CAD logic: the task panel edits a pocket
# push feature inside one transaction and hands over a complete PocketPushRequest to commit into it.

from dataclasses import dataclass

from morefeatures.pocketpush import feature
from morefeatures.pocketpush.parameters import PocketPushParameters

CREATE_TRANSACTION_NAME = "Pocket Push"
EDIT_TRANSACTION_NAME = "Edit Pocket Push"


@dataclass
class PocketPushRequest:
    sketch: object
    body: object
    parameters: PocketPushParameters


def createPocketPush(sketch, body, parameters: PocketPushParameters):
    """Opens a transaction that commitPocketPush() or abortPocketPush() must close."""
    body.Document.openTransaction(CREATE_TRANSACTION_NAME)
    pocketPushFeature = feature.createPocketPushFeature(body, sketch)
    feature.writeParameters(pocketPushFeature, parameters)
    return pocketPushFeature


def beginEditingPocketPush(pocketPushFeature) -> None:
    """Opens a transaction that commitPocketPush() or abortPocketPush() must close."""
    pocketPushFeature.Document.openTransaction(EDIT_TRANSACTION_NAME)


def previewPocketPush(pocketPushFeature, request: PocketPushRequest) -> None:
    """Recomputes only the pocket push feature; features after it catch up on commit."""
    feature.writeParameters(pocketPushFeature, request.parameters)
    pocketPushFeature.recompute()


def commitPocketPush(pocketPushFeature, request: PocketPushRequest) -> None:
    document = pocketPushFeature.Document
    feature.writeParameters(pocketPushFeature, request.parameters)
    document.recompute()
    document.commitTransaction()


def abortPocketPush(pocketPushFeature) -> None:
    pocketPushFeature.Document.abortTransaction()


def readRequest(pocketPushFeature) -> PocketPushRequest:
    return PocketPushRequest(
        pocketPushFeature.Sketch,
        pocketPushFeature.getParentGeoFeatureGroup(),
        feature.readParameters(pocketPushFeature),
    )
