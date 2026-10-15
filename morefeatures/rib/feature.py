# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The Rib Wizard's document object: one PartDesign feature that builds the ribs from its path
# sketch and cutter parameters, and fuses them into the part on each recompute.

import functools

import FreeCAD as App
import Part

from morefeatures import addoncheck, featureproperties, preview
from morefeatures.rib import cache, geometry, viewprovider
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
        cache.addKeyProperty(obj)
        addoncheck.installAddonCheck(obj)
        obj.Proxy = self

    def onDocumentRestored(self, obj) -> None:
        featureproperties.addMissingParameterProperties(
            obj, ribparameters.PARAMETER_FIELDS, ribparameters.RibParameters().toDict()
        )
        cache.addKeyProperty(obj)
        preview.addPreviewProperty(obj)
        addoncheck.installAddonCheck(obj)

    def execute(self, obj) -> None:
        sketchNormal = obj.Sketch.Placement.Rotation.multVec(SKETCH_NORMAL)
        baseShape = obj.BaseFeature.Shape if obj.BaseFeature is not None else None
        pathEdges = obj.Sketch.Shape.Edges
        parameters = readParameters(obj)
        buriedJunctions = geometry.findBuriedJunctions(pathEdges, sketchNormal, baseShape)
        ribsKey = cache.ribsKey(pathEdges, sketchNormal, parameters, buriedJunctions)
        ribs = cache.cachedRibs(obj, ribsKey)
        if preview.isPreviewing(obj):
            if ribs is None:
                pieces = geometry.buildRibPieces(pathEdges, sketchNormal, parameters, buriedJunctions)
                ribs = Part.makeCompound(pieces)
                cache.keepUnfused(obj, ribs)
            baseShapes = [baseShape] if baseShape is not None else []
            obj.Shape = Part.makeCompound(baseShapes + [ribs])
            return
        if ribs is None:
            ribs = geometry.buildRibs(pathEdges, sketchNormal, parameters, buriedJunctions)
            cache.keepRibs(obj, ribs, ribsKey)
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
    baseShape = obj.BaseFeature.Shape
    fused = baseShape.fuse(ribs)
    if not fused.isValid():
        # One boolean with every separate rib network now and then leaves an invalid solid where
        # fusing the networks in one at a time does not.
        fused = functools.reduce(lambda part, network: part.fuse(network), ribs.Solids, baseShape)
        # Features after this one cannot fillet or cut an invalid solid, so it must not leave one behind.
        if not fused.isValid():
            raise ValueError("The ribs could not be fused into the part as a valid solid.")
    if obj.Refine:
        fused = fused.removeSplitter()
    return fused.Solids[0] if len(fused.Solids) == 1 else fused
