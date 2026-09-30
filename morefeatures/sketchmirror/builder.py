# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# Mirrors sketch elements about a line of the same sketch: a copy of each, held symmetric to its
# original by constraints, so the copy follows every later change of the original.

import Sketcher

from morefeatures.sketchmirror import geometry, subelements

TRANSACTION_NAME = "Sketch Mirror"


def commitMirror(sketch, geometryIndices: list, mirrorLineGeoId: int) -> tuple:
    """One undo step. Returns the type names of the elements not mirrored, since their type is not
    supported yet."""
    sketch.Document.openTransaction(TRANSACTION_NAME)
    try:
        skippedTypeNames = mirrorElements(sketch, geometryIndices, mirrorLineGeoId)
    except Exception:
        sketch.Document.abortTransaction()
        raise
    sketch.Document.commitTransaction()
    sketch.solve()
    return skippedTypeNames


def mirrorElements(sketch, geometryIndices: list, mirrorLineGeoId: int) -> tuple:
    """Returns the type names of the elements not mirrored, as commitMirror() does."""
    mirrorLine = geometry.mirrorLineAlong(subelements.geometryOf(sketch, mirrorLineGeoId))
    mirroredByIndex = {index: geometry.mirrorGeometry(sketch.Geometry[index], mirrorLine) for index in geometryIndices}
    skippedTypeNames = tuple(
        type(sketch.Geometry[index]).__name__ for index, mirrored in mirroredByIndex.items() if mirrored is None
    )
    constraints = []
    for originalIndex, mirrored in mirroredByIndex.items():
        if mirrored is not None:
            copyIndex = sketch.addGeometry(mirrored.geometry, sketch.getConstruction(originalIndex))
            constraints.extend(
                _buildMirrorConstraints(sketch, originalIndex, copyIndex, mirrored, mirrorLine, mirrorLineGeoId)
            )
    sketch.addConstraint(constraints)
    return skippedTypeNames


def _buildMirrorConstraints(
    sketch,
    originalIndex: int,
    copyIndex: int,
    mirrored: geometry.MirroredGeometry,
    mirrorLine: geometry.MirrorLine,
    mirrorLineGeoId: int,
) -> list:
    constraints = [
        _buildPointConstraint(
            originalIndex,
            originalPosition,
            copyIndex,
            copyPosition,
            mirrorLineGeoId,
            mirrorLine.isOnLine(sketch.getPoint(originalIndex, originalPosition)),
        )
        for originalPosition, copyPosition in mirrored.matchingPositions
    ]
    if mirrored.hasEqualRadius:
        constraints.append(Sketcher.Constraint("Equal", originalIndex, copyIndex))
    return constraints


def _buildPointConstraint(
    originalIndex: int, originalPosition: int, copyIndex: int, copyPosition: int, mirrorLineGeoId: int, isOnLine: bool
):
    # Symmetry about the line is degenerate for a point on it, which the solver reports as a
    # conflict; coincident also joins a mirrored half profile to its original there.
    if isOnLine:
        return Sketcher.Constraint("Coincident", originalIndex, originalPosition, copyIndex, copyPosition)
    return Sketcher.Constraint("Symmetric", originalIndex, originalPosition, copyIndex, copyPosition, mirrorLineGeoId)
