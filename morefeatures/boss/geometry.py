# The boss built once in its own frame: base centred on the origin, axis +Z. Every instance
# in the part is a placed copy of this template.

import math

import Part
from FreeCAD import Vector

from morefeatures.boss.parameters import BossParameters

ORIGIN = Vector(0.0, 0.0, 0.0)
LOCAL_AXIS = Vector(0.0, 0.0, 1.0)
CUT_OVERSHOOT = 1.0
GUSSET_END_FRACTION_OF_TOP_RADIUS = 0.5
MIN_GUSSET_PROFILE_HEIGHT_FACTOR = 3.0
FLAT_FACE_TOLERANCE = 1e-6


def buildBossTemplate(parameters: BossParameters) -> Part.Shape:
    boss = _buildBossBody(parameters)
    if parameters.hasGussets() and parameters.maxGussetHeight > 0.0:
        boss = boss.fuse(_buildGussets(parameters))
    if parameters.hasBoreInset:
        boss = boss.cut(_buildInset(parameters))
    boss = boss.removeSplitter()
    if parameters.topFilletRadius > 0.0:
        boss = _filletTopEdge(boss, parameters)
    return boss


def _buildBossBody(parameters: BossParameters) -> Part.Shape:
    return _makeFrustum(parameters.baseDiameter / 2.0, _topRadius(parameters), parameters.height, ORIGIN)


def _topRadius(parameters: BossParameters) -> float:
    return parameters.baseDiameter / 2.0 - parameters.height * math.tan(math.radians(parameters.draftAngle))


def _buildGussets(parameters: BossParameters) -> list:
    gusset = _buildGusset(parameters)
    angleStep = 360.0 / parameters.gussetCount
    return [gusset.rotated(ORIGIN, LOCAL_AXIS, index * angleStep) for index in range(parameters.gussetCount)]


def _buildGusset(parameters: BossParameters) -> Part.Shape:
    reach = parameters.baseDiameter / 2.0 + parameters.gussetBaseLength
    # Ends inside the boss, short of the axis, so opposite gussets never share an end face.
    run = reach - GUSSET_END_FRACTION_OF_TOP_RADIUS * _topRadius(parameters)
    rise = run * math.tan(math.radians(parameters.gussetAngle))
    # Deep enough that the profile's bottom edge stays below z = 0 over the whole run; otherwise
    # steep gussets leave a gap underneath and come loose from the boss.
    profileDepth = max(MIN_GUSSET_PROFILE_HEIGHT_FACTOR * parameters.height, rise)
    profile = Part.Face(_buildGussetProfileWire(parameters, reach, profileDepth))
    return profile.extrude(Vector(-run, 0.0, rise)).common(_buildGussetHeightBand(parameters, reach))


def _buildGussetProfileWire(parameters: BossParameters, reach: float, profileDepth: float) -> Part.Wire:
    """The gusset's cross-section in the plane x = reach, ridge top on z = 0, hanging down to
    z = -profileDepth; across the gusset is +Y."""
    draft = math.radians(parameters.gussetDraftAngle)
    ridgeRadius = parameters.gussetBaseThickness / (2.0 * math.cos(draft))
    tangentHalfWidth = ridgeRadius * math.cos(draft)
    tangentZ = -ridgeRadius * (1.0 - math.sin(draft))
    footHalfWidth = tangentHalfWidth + (tangentZ + profileDepth) * math.tan(draft)
    footZ = -profileDepth

    def profilePoint(across: float, z: float) -> Vector:
        return Vector(reach, across, z)

    ridge = Part.Arc(
        profilePoint(-tangentHalfWidth, tangentZ), profilePoint(0.0, 0.0), profilePoint(tangentHalfWidth, tangentZ)
    )
    return Part.Wire(
        [
            ridge.toShape(),
            Part.makeLine(profilePoint(tangentHalfWidth, tangentZ), profilePoint(footHalfWidth, footZ)),
            Part.makeLine(profilePoint(footHalfWidth, footZ), profilePoint(-footHalfWidth, footZ)),
            Part.makeLine(profilePoint(-footHalfWidth, footZ), profilePoint(-tangentHalfWidth, tangentZ)),
        ]
    )


def _buildGussetHeightBand(parameters: BossParameters, reach: float) -> Part.Shape:
    halfSize = reach + CUT_OVERSHOOT
    return Part.makeBox(2.0 * halfSize, 2.0 * halfSize, parameters.maxGussetHeight, Vector(-halfSize, -halfSize, 0.0))


def _buildInset(parameters: BossParameters) -> Part.Shape:
    taper = math.tan(math.radians(parameters.boreDraftAngle))
    entryRadius = parameters.insetDiameter / 2.0
    bottomRadius = entryRadius - parameters.insetDepth * taper
    overshootRadius = entryRadius + CUT_OVERSHOOT * taper
    bottomPosition = Vector(0.0, 0.0, parameters.height - parameters.insetDepth)
    return _makeFrustum(bottomRadius, overshootRadius, parameters.insetDepth + CUT_OVERSHOOT, bottomPosition)


def buildBoreTool(parameters: BossParameters) -> Part.Shape:
    """The bore's cutting tool in the template frame: entry diameter on the boss top, narrowing
    by the bore draft down to a flat bottom, overshooting above the top."""
    depth = parameters.effectiveBoreDepth
    taper = math.tan(math.radians(parameters.boreDraftAngle))
    entryRadius = parameters.boreDiameter / 2.0
    bottomRadius = entryRadius - depth * taper
    if bottomRadius <= 0.0:
        raise ValueError("The bore draft closes the bore before it reaches its depth.")
    overshootRadius = entryRadius + CUT_OVERSHOOT * taper
    bottomPosition = Vector(0.0, 0.0, parameters.height - depth)
    return _makeFrustum(bottomRadius, overshootRadius, depth + CUT_OVERSHOOT, bottomPosition)


def _filletTopEdge(boss: Part.Shape, parameters: BossParameters) -> Part.Shape:
    topFace = _findTopFace(boss, parameters.height)
    if topFace is None:
        raise ValueError("The boss has no flat top left to fillet; the inset is as wide as the top.")
    try:
        filleted = boss.makeFillet(parameters.topFilletRadius, topFace.OuterWire.Edges)
    except Part.OCCError as error:
        raise ValueError(_describeFilletFailure(parameters)) from error
    if not filleted.isValid():
        raise ValueError(_describeFilletFailure(parameters))
    return filleted


def _findTopFace(boss: Part.Shape, height: float):
    return next(
        (
            face
            for face in boss.Faces
            if isinstance(face.Surface, Part.Plane)
            and math.isclose(face.BoundBox.ZMin, height, abs_tol=FLAT_FACE_TOLERANCE)
            and math.isclose(face.BoundBox.ZMax, height, abs_tol=FLAT_FACE_TOLERANCE)
        ),
        None,
    )


def _describeFilletFailure(parameters: BossParameters) -> str:
    return "The top fillet radius {0} mm does not fit the boss top.".format(parameters.topFilletRadius)


def _makeFrustum(bottomRadius: float, topRadius: float, height: float, position: Vector) -> Part.Shape:
    if math.isclose(bottomRadius, topRadius):
        return Part.makeCylinder(bottomRadius, height, position, LOCAL_AXIS)
    return Part.makeCone(bottomRadius, topRadius, height, position, LOCAL_AXIS)
