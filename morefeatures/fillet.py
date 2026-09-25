# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# Filleting that fails with a message naming the fillet, instead of an OpenCascade error or a
# silently broken shape.

import Part


def makeCheckedFillet(shape: Part.Shape, radius: float, edges: list, filletName: str) -> Part.Shape:
    failure = "The {0} fillet radius {1} mm does not fit.".format(filletName, radius)
    try:
        filleted = shape.makeFillet(radius, edges)
    except Part.OCCError as error:
        raise ValueError(failure) from error
    if not filleted.isValid():
        raise ValueError(failure)
    return filleted
