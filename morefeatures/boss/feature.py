# The Boss Wizard's document object: one PartDesign feature that rebuilds every boss from its
# sketch points and parameters on each recompute.

import FreeCAD as App
import Part

from morefeatures import featureproperties, sketchpoints
from morefeatures.boss import geometry, viewprovider
from morefeatures.boss import parameters as bossparameters

FEATURE_TYPE_ID = "PartDesign::FeatureAdditivePython"
FEATURE_NAME = "Boss"
INSTANCES_GROUP = "Instances"


class BossFeature:
    def __init__(self, obj):
        obj.addProperty("App::PropertyLink", "Sketch", INSTANCES_GROUP, "Every point in this sketch marks one boss.")
        obj.addProperty(
            "App::PropertyIntegerList", "IgnoredPointIds", INSTANCES_GROUP, "Geometry ids of points without a boss."
        )
        obj.addProperty(
            "App::PropertyPythonObject",
            "RotationOffsets",
            INSTANCES_GROUP,
            "Rotation offset in degrees per point, keyed by the point's geometry id.",
        )
        featureproperties.addParameterProperties(obj, bossparameters.PARAMETER_FIELDS)
        obj.Proxy = self

    def execute(self, obj) -> None:
        parameters = readParameters(obj)
        matrices = [placement.toMatrix() for placement in _instancePlacements(obj)]
        template = geometry.buildBossTemplate(parameters)
        bosses = [template.transformed(matrix) for matrix in matrices]
        bores = []
        if parameters.hasBore():
            boreTool = geometry.buildBoreTool(parameters)
            bores = [boreTool.transformed(matrix) for matrix in matrices]
        obj.AddSubShape = Part.makeCompound(bosses)
        obj.Shape = _fuseIntoBaseAndBore(obj, bosses, bores)

    def dumps(self):
        return None

    def loads(self, state):
        return None


def createBossFeature(body, sketch):
    obj = body.newObject(FEATURE_TYPE_ID, FEATURE_NAME)
    BossFeature(obj)
    if App.GuiUp:
        viewprovider.BossViewProvider(obj.ViewObject)
        # The view object was created before it had a proxy, so it never picked a display mode.
        obj.ViewObject.DisplayMode = viewprovider.DEFAULT_DISPLAY_MODE
    obj.Sketch = sketch
    return obj


def writeInstances(obj, ignoredPointIds: list, rotationOffsetsByPointId: dict) -> None:
    obj.IgnoredPointIds = list(ignoredPointIds)
    # Keys are strings because the property is saved as JSON, which has no integer keys.
    obj.RotationOffsets = {str(pointId): offset for pointId, offset in rotationOffsetsByPointId.items()}


def readInstances(obj) -> tuple:
    rotationOffsets = obj.RotationOffsets or {}
    return list(obj.IgnoredPointIds), {int(pointId): offset for pointId, offset in rotationOffsets.items()}


def writeParameters(obj, parameters: bossparameters.BossParameters) -> None:
    featureproperties.writeParameterProperties(obj, bossparameters.PARAMETER_FIELDS, parameters.toDict())


def readParameters(obj) -> bossparameters.BossParameters:
    return bossparameters.fromDict(
        featureproperties.readParameterProperties(obj, bossparameters.PARAMETER_FIELDS)
    )


def _instancePlacements(obj) -> list:
    ignoredPointIds = set(obj.IgnoredPointIds)
    rotationOffsets = obj.RotationOffsets or {}
    return [
        obj.Sketch.Placement.multiply(
            App.Placement(
                point.localPosition,
                App.Rotation(geometry.LOCAL_AXIS, rotationOffsets.get(str(point.geometryId), 0.0)),
            )
        )
        for point in sketchpoints.readSketchPoints(obj.Sketch)
        if point.geometryId not in ignoredPointIds
    ]


def _fuseIntoBaseAndBore(obj, bosses: list, bores: list) -> Part.Shape:
    baseShapes = [obj.BaseFeature.Shape] if obj.BaseFeature is not None else []
    first, *others = baseShapes + bosses
    if not others:
        return first
    # Bored after the fuse, so each bore may run on into the part below its boss.
    result = first.fuse(others)
    if bores:
        result = result.cut(bores)
    return result.removeSplitter() if obj.Refine else result
