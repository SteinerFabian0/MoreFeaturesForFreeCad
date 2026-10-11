# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The Hole Fill wizard's document object: one PartDesign feature that recuts every hole of the pattern
# from its perimeter sketch and parameters on each recompute.

import FreeCAD as App
import Part

from morefeatures import addoncheck, featureproperties, preview
from morefeatures.holefill import geometry, viewprovider
from morefeatures.holefill import parameters as holefillparameters

FEATURE_TYPE_ID = "PartDesign::FeatureSubtractivePython"
FEATURE_NAME = "HoleFill"
PERIMETER_GROUP = "Perimeter"


class HoleFillFeature:
    def __init__(self, obj):
        obj.addProperty(
            "App::PropertyLink", "Sketch", PERIMETER_GROUP, "The holes fill this sketch's one closed perimeter."
        )
        obj.addProperty(
            "App::PropertyInteger",
            "HoleCount",
            holefillparameters.HOLES_GROUP,
            "How many holes fit inside the perimeter.",
            addoncheck.PROPERTY_READ_ONLY | preview.PROPERTY_OUTPUT,
        )
        featureproperties.addParameterProperties(obj, holefillparameters.PARAMETER_FIELDS)
        addoncheck.installAddonCheck(obj)
        obj.Proxy = self

    def onDocumentRestored(self, obj) -> None:
        featureproperties.addMissingParameterProperties(
            obj, holefillparameters.PARAMETER_FIELDS, holefillparameters.HoleFillParameters().toDict()
        )
        addoncheck.installAddonCheck(obj)

    def execute(self, obj) -> None:
        if obj.BaseFeature is None:
            raise ValueError("There is no part to cut the holes into yet.")
        holeCuts = geometry.buildHoleCuts(obj.Sketch, obj.BaseFeature.Shape, readParameters(obj))
        obj.HoleCount = holeCuts.holeCount
        obj.AddSubShape = holeCuts.material
        obj.Shape = _cutFromBase(obj, holeCuts.material)

    def dumps(self):
        return None

    def loads(self, state):
        return None


def createHoleFillFeature(body, sketch):
    obj = body.newObject(FEATURE_TYPE_ID, FEATURE_NAME)
    HoleFillFeature(obj)
    if App.GuiUp:
        viewprovider.HoleFillViewProvider(obj.ViewObject)
        # The view object was created before it had a proxy, so it never picked a display mode.
        obj.ViewObject.DisplayMode = viewprovider.DEFAULT_DISPLAY_MODE
    obj.Sketch = sketch
    return obj


def writeParameters(obj, parameters: holefillparameters.HoleFillParameters) -> None:
    featureproperties.writeParameterProperties(obj, holefillparameters.PARAMETER_FIELDS, parameters.toDict())


def readParameters(obj) -> holefillparameters.HoleFillParameters:
    return holefillparameters.fromDict(
        featureproperties.readParameterProperties(obj, holefillparameters.PARAMETER_FIELDS)
    )


def _cutFromBase(obj, material: Part.Shape) -> Part.Shape:
    perforated = obj.BaseFeature.Shape.cut(material)
    if obj.Refine:
        perforated = perforated.removeSplitter()
    if len(perforated.Solids) != 1:
        raise ValueError("The holes cut the part apart.")
    # Features after this one cannot fillet or cut an invalid solid, so it must not leave one behind.
    if not perforated.Solids[0].isValid():
        raise ValueError("The holes could not be cut into the part as a valid solid.")
    return perforated.Solids[0]
