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
PROBE_TOLERANCE = 1e-4
LEGACY_BASE_DIAMETER_PROPERTY = "BaseDiameter"


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
        legacyBaseDiameter = _takeLegacyBaseDiameter(obj)
        featureproperties.addMissingParameterProperties(
            obj, bossparameters.PARAMETER_FIELDS, bossparameters.BossParameters().toDict()
        )
        if legacyBaseDiameter is not None:
            obj.WallThickness = readParameters(obj).wallThicknessForBaseDiameter(legacyBaseDiameter)
        preview.addPreviewProperty(obj)
        addoncheck.installAddonCheck(obj)

    def execute(self, obj) -> None:
        parameters = readParameters(obj)
        placedBosses = _placeBosses(obj, parameters)
        bosses = [placedBoss.template.transformed(placedBoss.placement.toMatrix()) for placedBoss in placedBosses]
        obj.AddSubShape = Part.makeCompound(bosses)
        cutters = _buildPlacedCutters(obj, parameters, placedBosses)
        if preview.isPreviewing(obj):
            obj.Shape = _buildPreview(obj, parameters, bosses, cutters)
        else:
            obj.Shape = _buildFinalShape(obj, parameters, placedBosses, bosses, cutters)

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


def _takeLegacyBaseDiameter(obj):
    """Files saved before the wall thickness sized the boss carry its base diameter instead."""
    if LEGACY_BASE_DIAMETER_PROPERTY not in obj.PropertiesList:
        return None
    baseDiameter = getattr(obj, LEGACY_BASE_DIAMETER_PROPERTY).Value
    obj.removeProperty(LEGACY_BASE_DIAMETER_PROPERTY)
    return baseDiameter


def _buildFinalShape(
    obj, parameters: bossparameters.BossParameters, placedBosses: list, bosses: list, cutters: list
) -> Part.Shape:
    result = _fuseIntoBase(obj, bosses)
    if bosses and obj.BaseFeature is not None and parameters.baseFilletRadius > 0.0:
        result = basefillet.filletBossBases(result, placedBosses, parameters.baseFilletRadius)
    if cutters:
        # Cut after the fuse, so each bore may run on into the part below its boss.
        result = result.cut(cutters)
    return result.removeSplitter() if obj.Refine else result


def _buildPreview(obj, parameters: bossparameters.BossParameters, bosses: list, cutters: list) -> Part.Shape:
    """Fast enough to rebuild on every input change: no fuse, no base fillet, and each boss is cut
    by its own cutter only."""
    cutBosses = [boss.cut(cutter) for boss, cutter in zip(bosses, cutters)] if cutters else bosses
    baseShapes = [obj.BaseFeature.Shape] if obj.BaseFeature is not None else []
    if baseShapes and cutters and parameters.isScrewHeadBoss():
        # A screw head boss's bore and rubber pad cutout are mostly in the part, not the boss.
        baseShapes = [baseShapes[0].cut(cutters)]
    return Part.makeCompound(baseShapes + cutBosses)


def _buildPlacedCutters(obj, parameters: bossparameters.BossParameters, placedBosses: list) -> list:
    """One cutter per placed boss, or none at all."""
    if parameters.isScrewHeadBoss():
        baseShape = obj.BaseFeature.Shape if obj.BaseFeature is not None else None
        return [
            geometry.buildScrewHeadCutter(
                parameters, _measurePartThicknessBelow(baseShape, placedBoss.placement)
            ).transformed(placedBoss.placement.toMatrix())
            for placedBoss in placedBosses
        ]
    if not parameters.hasThreadBore():
        return []
    boreTool = geometry.buildBoreTool(parameters)
    return [boreTool.transformed(placedBoss.placement.toMatrix()) for placedBoss in placedBosses]


def _measurePartThicknessBelow(baseShape, placement: App.Placement) -> float:
    """How far the part reaches straight down from the boss's sketch point, along the boss axis."""
    if baseShape is None:
        return 0.0
    origin = placement.Base
    downward = placement.Rotation.multVec(geometry.LOCAL_AXIS).negative()
    reach = baseShape.BoundBox.DiagonalLength + geometry.CUT_OVERSHOOT
    probe = Part.makeLine(origin - downward * geometry.CUT_OVERSHOOT, origin + downward * reach)
    spans = sorted(
        sorted((vertex.Point - origin).dot(downward) for vertex in edge.Vertexes)
        for edge in baseShape.common(probe).Edges
    )
    thickness = 0.0
    for spanTop, spanBottom in spans:
        if abs(spanTop - thickness) < PROBE_TOLERANCE:
            thickness = spanBottom
    if thickness == 0.0:
        raise ValueError(
            "A screw head boss's sketch point is not on the part; draw the sketch on the face the bosses grow from."
        )
    return thickness


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
                gussetIndices == parameters.allGussetIndices() or not gussetIndices,
            )
        )
    return placedBosses


def _fuseIntoBase(obj, bosses: list) -> Part.Shape:
    baseShapes = [obj.BaseFeature.Shape] if obj.BaseFeature is not None else []
    first, *others = baseShapes + bosses
    return first.fuse(others) if others else first
