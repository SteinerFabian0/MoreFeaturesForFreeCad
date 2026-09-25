# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The Rib Wizard's document object: one PartDesign feature that rebuilds the ribs from its path
# sketch and cutter parameters on each recompute.

import FreeCAD as App
import Part

from morefeatures import addoncheck, featureproperties, preview
from morefeatures.rib import geometry, viewprovider
from morefeatures.rib import parameters as ribparameters

FEATURE_TYPE_ID = "PartDesign::FeatureAdditivePython"
FEATURE_NAME = "Rib"
PATH_GROUP = "Path"
SKETCH_NORMAL = App.Vector(0.0, 0.0, 1.0)


class RibFeature:
    def __init__(self, obj):
        obj.addProperty(
            "App::PropertyLink", "Sketch", PATH_GROUP, "The lines in this sketch are the cutter's centre paths."
        )
        preview.addPreviewProperty(obj)
        featureproperties.addParameterProperties(obj, ribparameters.PARAMETER_FIELDS)
        addoncheck.installAddonCheck(obj)
        obj.Proxy = self

    def onDocumentRestored(self, obj) -> None:
        preview.addPreviewProperty(obj)
        addoncheck.installAddonCheck(obj)

    def execute(self, obj) -> None:
        sketchNormal = obj.Sketch.Placement.Rotation.multVec(SKETCH_NORMAL)
        ribs = geometry.buildRibs(obj.Sketch.Shape.Edges, sketchNormal, readParameters(obj))
        obj.AddSubShape = ribs
        if preview.isPreviewing(obj):
            baseShapes = [obj.BaseFeature.Shape] if obj.BaseFeature is not None else []
            obj.Shape = Part.makeCompound(baseShapes + [ribs])
        else:
            obj.Shape = _fuseIntoBase(obj, ribs)

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


def _fuseIntoBase(obj, ribs: Part.Shape) -> Part.Shape:
    if obj.BaseFeature is None:
        return ribs
    fused = obj.BaseFeature.Shape.fuse(ribs)
    if obj.Refine:
        fused = fused.removeSplitter()
    return fused.Solids[0] if len(fused.Solids) == 1 else fused
