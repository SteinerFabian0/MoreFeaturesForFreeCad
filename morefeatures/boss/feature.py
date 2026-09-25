# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The Boss Wizard's document object: one PartDesign feature that rebuilds every boss from its
# sketch points and parameters on each recompute.

import FreeCAD as App
import Part

from morefeatures import addoncheck, featureproperties, preview, sketchpoints
from morefeatures.boss import basefillet, geometry, viewprovider
from morefeatures.boss import parameters as bossparameters

FEATURE_TYPE_ID = "PartDesign::FeatureAdditivePython"
FEATURE_NAME = "Boss"
INSTANCES_GROUP = "Instances"
SKIPPED_GUSSETS_PROPERTY = "SkippedGussets"


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
        _addSkippedGussetsProperty(obj)
        preview.addPreviewProperty(obj)
        featureproperties.addParameterProperties(obj, bossparameters.PARAMETER_FIELDS)
        addoncheck.installAddonCheck(obj)
        obj.Proxy = self

    def onDocumentRestored(self, obj) -> None:
        _addSkippedGussetsProperty(obj)
        preview.addPreviewProperty(obj)
        addoncheck.installAddonCheck(obj)

    def execute(self, obj) -> None:
        parameters = readParameters(obj)
        placedBosses = _placeBosses(obj, parameters)
        bosses = [placedBoss.template.transformed(placedBoss.placement.toMatrix()) for placedBoss in placedBosses]
        obj.AddSubShape = Part.makeCompound(bosses)
        if preview.isPreviewing(obj):
            obj.Shape = _buildPreview(obj, parameters, placedBosses, bosses)
        else:
            obj.Shape = _buildFinalShape(obj, parameters, placedBosses, bosses)

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


def writeInstances(
    obj, ignoredPointIds: list, rotationOffsetsByPointId: dict, skippedGussetsByPointId: dict
) -> None:
    obj.IgnoredPointIds = list(ignoredPointIds)
    # Keys are strings because the property is saved as JSON, which has no integer keys.
    obj.RotationOffsets = {str(pointId): offset for pointId, offset in rotationOffsetsByPointId.items()}
    setattr(
        obj,
        SKIPPED_GUSSETS_PROPERTY,
        {str(pointId): sorted(indices) for pointId, indices in skippedGussetsByPointId.items() if indices},
    )


def readInstances(obj) -> tuple:
    rotationOffsets = obj.RotationOffsets or {}
    skippedGussets = getattr(obj, SKIPPED_GUSSETS_PROPERTY) or {}
    return (
        list(obj.IgnoredPointIds),
        {int(pointId): offset for pointId, offset in rotationOffsets.items()},
        {int(pointId): set(indices) for pointId, indices in skippedGussets.items()},
    )


def writeParameters(obj, parameters: bossparameters.BossParameters) -> None:
    featureproperties.writeParameterProperties(obj, bossparameters.PARAMETER_FIELDS, parameters.toDict())


def readParameters(obj) -> bossparameters.BossParameters:
    return bossparameters.fromDict(
        featureproperties.readParameterProperties(obj, bossparameters.PARAMETER_FIELDS)
    )


def _addSkippedGussetsProperty(obj) -> None:
    # Files saved before gussets could be skipped lack this property.
    if SKIPPED_GUSSETS_PROPERTY not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyPythonObject",
            SKIPPED_GUSSETS_PROPERTY,
            INSTANCES_GROUP,
            "Indices of the gussets left out per point, keyed by the point's geometry id.",
        )


def _buildFinalShape(obj, parameters: bossparameters.BossParameters, placedBosses: list, bosses: list) -> Part.Shape:
    result = _fuseIntoBase(obj, bosses)
    if bosses and obj.BaseFeature is not None and parameters.baseFilletRadius > 0.0:
        result = basefillet.filletBossBases(result, placedBosses, parameters.baseFilletRadius)
    if bosses and parameters.hasBore():
        boreTool = geometry.buildBoreTool(parameters)
        # Bored after the fuse, so each bore may run on into the part below its boss.
        result = result.cut([boreTool.transformed(placedBoss.placement.toMatrix()) for placedBoss in placedBosses])
    return result.removeSplitter() if obj.Refine else result


def _buildPreview(obj, parameters: bossparameters.BossParameters, placedBosses: list, bosses: list) -> Part.Shape:
    """Fast enough to rebuild on every input change: no fuse, no base fillet, and each bore is cut
    into its own boss only."""
    boredBosses = bosses
    if parameters.hasBore():
        boreTool = geometry.buildBoreTool(parameters)
        boredBosses = [
            boss.cut(boreTool.transformed(placedBoss.placement.toMatrix()))
            for boss, placedBoss in zip(bosses, placedBosses)
        ]
    baseShapes = [obj.BaseFeature.Shape] if obj.BaseFeature is not None else []
    return Part.makeCompound(baseShapes + boredBosses)


def _placeBosses(obj, parameters: bossparameters.BossParameters) -> list:
    """Bosses with the same gussets left out share one template."""
    ignoredPointIds = set(obj.IgnoredPointIds)
    rotationOffsets = obj.RotationOffsets or {}
    skippedGussets = getattr(obj, SKIPPED_GUSSETS_PROPERTY) or {}
    templatesByGussetIndices = {}
    placedBosses = []
    points = [point for point in sketchpoints.readSketchPoints(obj.Sketch) if point.geometryId not in ignoredPointIds]
    for point in points:
        pointKey = str(point.geometryId)
        gussetIndices = parameters.keptGussetIndices(skippedGussets.get(pointKey, ()))
        if gussetIndices not in templatesByGussetIndices:
            templatesByGussetIndices[gussetIndices] = geometry.buildBossTemplate(parameters, gussetIndices)
        placement = obj.Sketch.Placement.multiply(
            App.Placement(point.localPosition, App.Rotation(geometry.LOCAL_AXIS, rotationOffsets.get(pointKey, 0.0)))
        )
        placedBosses.append(
            basefillet.PlacedBoss(
                templatesByGussetIndices[gussetIndices],
                placement,
                len(gussetIndices),
                gussetIndices == parameters.allGussetIndices(),
            )
        )
    return placedBosses


def _fuseIntoBase(obj, bosses: list) -> Part.Shape:
    baseShapes = [obj.BaseFeature.Shape] if obj.BaseFeature is not None else []
    first, *others = baseShapes + bosses
    return first.fuse(others) if others else first
