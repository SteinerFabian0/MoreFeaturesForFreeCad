# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The seam between the rib wizard's GUI and the CAD logic: the task panel edits a rib feature
# inside one transaction and hands over a complete RibRequest to commit into it.

from dataclasses import dataclass

from morefeatures.rib import feature
from morefeatures.rib.parameters import RibParameters

CREATE_TRANSACTION_NAME = "Rib Wizard"
EDIT_TRANSACTION_NAME = "Edit Rib"


@dataclass
class RibRequest:
    sketch: object
    body: object
    parameters: RibParameters


def createRibs(sketch, body, parameters: RibParameters):
    """Opens a transaction that commitRibs() or abortRibs() must close."""
    body.Document.openTransaction(CREATE_TRANSACTION_NAME)
    ribFeature = feature.createRibFeature(body, sketch)
    feature.writeParameters(ribFeature, parameters)
    return ribFeature


def beginEditingRibs(ribFeature) -> None:
    """Opens a transaction that commitRibs() or abortRibs() must close."""
    ribFeature.Document.openTransaction(EDIT_TRANSACTION_NAME)


def commitRibs(ribFeature, request: RibRequest) -> None:
    document = ribFeature.Document
    feature.writeParameters(ribFeature, request.parameters)
    document.recompute()
    document.commitTransaction()


def abortRibs(ribFeature) -> None:
    ribFeature.Document.abortTransaction()


def readRequest(ribFeature) -> RibRequest:
    return RibRequest(ribFeature.Sketch, ribFeature.getParentGeoFeatureGroup(), feature.readParameters(ribFeature))
