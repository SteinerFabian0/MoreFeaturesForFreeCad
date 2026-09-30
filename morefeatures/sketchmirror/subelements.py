# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# Selected sketch sub-elements ("Edge3", "Vertex7", "H_Axis", ...) as sketcher geometry ids.

import re
from typing import Optional

import Part

AXIS_GEO_IDS = {"H_Axis": -1, "V_Axis": -2}
NUMBERED_ELEMENT = re.compile(r"^(Edge|ExternalEdge|Vertex)(\d+)$")


def findElementName(sketch, objectName: str, subElementName: str) -> Optional[str]:
    """The element name ("Edge3") of a selection on the sketch, which may be reported through its
    parents: a sketch edited inside a Body is selected as the Body with "Sketch.Edge3"."""
    *objectPath, elementName = [objectName] + subElementName.split(".")
    return elementName if objectPath[-1] == sketch.Name else None


def findMirrorableGeometry(sketch, elementNames: list) -> list:
    """Indices of the selected edges and standalone points, sorted, without internal alignment
    geometry (an ellipse's axes, a B-spline's poles), which belongs to its curve. Names that are
    None or empty (selections elsewhere, or of the whole sketch) are passed over."""
    selectedIndices = {_findGeometryIndex(sketch, name) for name in elementNames if name}
    selectedIndices.discard(None)
    internalIndices = {
        constraint.First for constraint in sketch.Constraints if constraint.Type == "InternalAlignment"
    }
    return sorted(selectedIndices - internalIndices)


def findLineGeoId(sketch, elementName: str) -> Optional[int]:
    geoId = AXIS_GEO_IDS.get(elementName, _findEdgeGeoId(elementName))
    if geoId is None or not isinstance(geometryOf(sketch, geoId), Part.LineSegment):
        return None
    return geoId


def geometryOf(sketch, geoId: int):
    # Negative geo ids count down through the axes, then the external geometry, as ExternalGeo lists them.
    return sketch.Geometry[geoId] if geoId >= 0 else sketch.ExternalGeo[-geoId - 1]


def _findGeometryIndex(sketch, elementName: str) -> Optional[int]:
    match = NUMBERED_ELEMENT.match(elementName)
    if match is None or match.group(1) == "ExternalEdge":
        return None
    elementIndex = int(match.group(2)) - 1
    if match.group(1) == "Edge":
        return elementIndex
    geometryIndex, _ = sketch.getGeoVertexIndex(elementIndex)
    return geometryIndex if geometryIndex >= 0 and _isPoint(sketch, geometryIndex) else None


def _findEdgeGeoId(elementName: str) -> Optional[int]:
    match = NUMBERED_ELEMENT.match(elementName)
    if match is None or match.group(1) == "Vertex":
        return None
    edgeIndex = int(match.group(2)) - 1
    # ExternalEdge1 is geo id -3, after the two axes.
    return edgeIndex if match.group(1) == "Edge" else -3 - edgeIndex


def _isPoint(sketch, geometryIndex: int) -> bool:
    return isinstance(sketch.Geometry[geometryIndex], Part.Point)
