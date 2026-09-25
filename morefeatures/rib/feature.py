# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The Rib Wizard's document object: one PartDesign feature that owns its path sketch and the
# cutter parameters. It adds no geometry yet and passes the Body's shape on unchanged.

import FreeCAD as App
import Part

from morefeatures import addoncheck, featureproperties
from morefeatures.rib import viewprovider
from morefeatures.rib import parameters as ribparameters

FEATURE_TYPE_ID = "PartDesign::FeatureAdditivePython"
FEATURE_NAME = "Rib"
PATH_GROUP = "Path"


class RibFeature:
    def __init__(self, obj):
        obj.addProperty(
            "App::PropertyLink", "Sketch", PATH_GROUP, "The lines in this sketch are the cutter's centre paths."
        )
        featureproperties.addParameterProperties(obj, ribparameters.PARAMETER_FIELDS)
        addoncheck.installAddonCheck(obj)
        obj.Proxy = self

    def onDocumentRestored(self, obj) -> None:
        addoncheck.installAddonCheck(obj)

    def execute(self, obj) -> None:
        obj.AddSubShape = Part.Shape()
        obj.Shape = obj.BaseFeature.Shape if obj.BaseFeature is not None else Part.Shape()

    def dumps(self):
        return None

    def loads(self, state):
        return None


def createRibFeature(body, sketch):
    obj = body.newObject(FEATURE_TYPE_ID, FEATURE_NAME)
    RibFeature(obj)
    if App.GuiUp:
        viewprovider.RibViewProvider(obj.ViewObject)
        # The view object was created before it had a proxy, so it never picked a display mode.
        obj.ViewObject.DisplayMode = viewprovider.DEFAULT_DISPLAY_MODE
    obj.Sketch = sketch
    return obj


def writeParameters(obj, parameters: ribparameters.RibParameters) -> None:
    featureproperties.writeParameterProperties(obj, ribparameters.PARAMETER_FIELDS, parameters.toDict())


def readParameters(obj) -> ribparameters.RibParameters:
    return ribparameters.fromDict(featureproperties.readParameterProperties(obj, ribparameters.PARAMETER_FIELDS))
