# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The seam between the hole fill wizard's GUI and the CAD logic: the task panel edits a hole fill
# feature inside one transaction and hands over a complete HoleFillRequest to commit into it.

from dataclasses import dataclass

from morefeatures.holefill import feature
from morefeatures.holefill.parameters import HoleFillParameters

CREATE_TRANSACTION_NAME = "Hole Fill"
EDIT_TRANSACTION_NAME = "Edit Hole Fill"


@dataclass
class HoleFillRequest:
    sketch: object
    body: object
    parameters: HoleFillParameters


def createHoleFill(sketch, body, parameters: HoleFillParameters):
    """Opens a transaction that commitHoleFill() or abortHoleFill() must close."""
    body.Document.openTransaction(CREATE_TRANSACTION_NAME)
    holeFillFeature = feature.createHoleFillFeature(body, sketch)
    feature.writeParameters(holeFillFeature, parameters)
    return holeFillFeature


def beginEditingHoleFill(holeFillFeature) -> None:
    """Opens a transaction that commitHoleFill() or abortHoleFill() must close."""
    holeFillFeature.Document.openTransaction(EDIT_TRANSACTION_NAME)


def previewHoleFill(holeFillFeature, request: HoleFillRequest) -> None:
    """Recomputes only the hole fill feature; features after it catch up on commit."""
    feature.writeParameters(holeFillFeature, request.parameters)
    holeFillFeature.recompute()


def commitHoleFill(holeFillFeature, request: HoleFillRequest) -> None:
    document = holeFillFeature.Document
    feature.writeParameters(holeFillFeature, request.parameters)
    document.recompute()
    document.commitTransaction()


def abortHoleFill(holeFillFeature) -> None:
    holeFillFeature.Document.abortTransaction()


def readRequest(holeFillFeature) -> HoleFillRequest:
    return HoleFillRequest(
        holeFillFeature.Sketch,
        holeFillFeature.getParentGeoFeatureGroup(),
        feature.readParameters(holeFillFeature),
    )
