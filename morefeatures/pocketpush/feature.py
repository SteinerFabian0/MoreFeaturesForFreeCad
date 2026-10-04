# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The Pocket Push wizard's document object: one PartDesign feature that rebuilds the pushed pockets
# from its outline sketch and parameters on each recompute.

import FreeCAD as App
import Part

from morefeatures import addoncheck, featureproperties
from morefeatures.pocketpush import geometry, viewprovider
from morefeatures.pocketpush import parameters as pocketpushparameters

FEATURE_TYPE_ID = "PartDesign::FeatureAdditivePython"
FEATURE_NAME = "PocketPush"
OUTLINE_GROUP = "Outline"
SKETCH_NORMAL = App.Vector(0.0, 0.0, 1.0)
HEALING_TOLERANCE = 1e-7


class PocketPushFeature:
    def __init__(self, obj):
        obj.addProperty(
            "App::PropertyLink", "Sketch", OUTLINE_GROUP, "Each closed outline in this sketch is pushed as one pocket."
        )
        featureproperties.addParameterProperties(obj, pocketpushparameters.PARAMETER_FIELDS)
        addoncheck.installAddonCheck(obj)
        obj.Proxy = self

    def onDocumentRestored(self, obj) -> None:
        featureproperties.addMissingParameterProperties(
            obj, pocketpushparameters.PARAMETER_FIELDS, pocketpushparameters.PocketPushParameters().toDict()
        )
        addoncheck.installAddonCheck(obj)

    def execute(self, obj) -> None:
        sketchNormal = obj.Sketch.Placement.Rotation.multVec(SKETCH_NORMAL)
        pockets = geometry.buildPushedPockets(obj.Sketch.Shape, sketchNormal, readParameters(obj))
        obj.AddSubShape = pockets.walls.cut(pockets.cavities)
        obj.Shape = _pushIntoBase(obj, pockets)

    def dumps(self):
        return None

    def loads(self, state):
        return None


def createPocketPushFeature(body, sketch):
    obj = body.newObject(FEATURE_TYPE_ID, FEATURE_NAME)
    PocketPushFeature(obj)
    if App.GuiUp:
        viewprovider.PocketPushViewProvider(obj.ViewObject)
        # The view object was created before it had a proxy, so it never picked a display mode.
        obj.ViewObject.DisplayMode = viewprovider.DEFAULT_DISPLAY_MODE
    obj.Sketch = sketch
    return obj


def writeParameters(obj, parameters: pocketpushparameters.PocketPushParameters) -> None:
    featureproperties.writeParameterProperties(obj, pocketpushparameters.PARAMETER_FIELDS, parameters.toDict())


def readParameters(obj) -> pocketpushparameters.PocketPushParameters:
    return pocketpushparameters.fromDict(
        featureproperties.readParameterProperties(obj, pocketpushparameters.PARAMETER_FIELDS)
    )


def _pushIntoBase(obj, pockets: geometry.PushedPockets) -> Part.Shape:
    base = obj.BaseFeature.Shape.fuse(pockets.walls) if obj.BaseFeature is not None else pockets.walls
    pushed = base.cut(pockets.cavities)
    if obj.Refine:
        pushed = pushed.removeSplitter()
    if len(pushed.Solids) != 1:
        raise ValueError("The walls do not join the part as one solid; draw the outlines on the part.")
    return _healed(pushed.Solids[0])


def _healed(solid: Part.Solid) -> Part.Solid:
    """Features after this one cannot fillet or cut an invalid solid, so it must not leave one behind."""
    if not solid.isValid():
        # The booleans have left a face oriented against its neighbours; healing turns it round.
        solid.fix(HEALING_TOLERANCE, HEALING_TOLERANCE, HEALING_TOLERANCE)
    if not solid.isValid():
        raise ValueError("The pushed pockets could not be joined into the part as a valid solid.")
    return solid
