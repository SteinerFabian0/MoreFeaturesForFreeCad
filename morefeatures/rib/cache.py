# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The fused ribs stay in the feature's AddSubShape, saved with the file, along with a key of everything
# they were built from, so a change elsewhere in the Body only fuses them into the new part again.

import hashlib
import pathlib

import Part
from FreeCAD import Vector

from morefeatures import addoncheck, cutterprofile, preview
from morefeatures.rib import geometry
from morefeatures.rib.parameters import RibParameters

KEY_PROPERTY = "RibsKey"
# Five points along a path edge tell lines, arcs and full circles apart.
EDGE_SAMPLES = (0.0, 0.25, 0.5, 0.75, 1.0)
# A sketch solved again to the same geometry can differ in the last digits.
KEY_DECIMALS = 9


def _sourceFingerprint(modules: tuple) -> str:
    return hashlib.sha256(b"".join(pathlib.Path(module.__file__).read_bytes() for module in modules)).hexdigest()


# Ribs saved in a file are built again once the code that builds them has changed.
BUILDER_FINGERPRINT = _sourceFingerprint((geometry, cutterprofile))


def addKeyProperty(obj) -> None:
    """Files saved before the cache existed get it too, empty, so their ribs are built again once."""
    if KEY_PROPERTY not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyString",
            KEY_PROPERTY,
            addoncheck.BASE_GROUP,
            "",
            addoncheck.PROPERTY_HIDDEN | preview.PROPERTY_OUTPUT,
        )


def ribsKey(pathEdges: list, sketchNormal: Vector, parameters: RibParameters, buriedJunctions: list) -> str:
    paths = [
        (type(edge.Curve).__name__, [_rounded(_pointAlong(edge, fraction)) for fraction in EDGE_SAMPLES])
        for edge in pathEdges
    ]
    buried = [_rounded(junction) for junction in buriedJunctions]
    inputs = (BUILDER_FINGERPRINT, paths, _rounded(sketchNormal), parameters, buried)
    return hashlib.sha256(repr(inputs).encode()).hexdigest()


def cachedRibs(obj, key: str):
    """The ribs built for this key, or None."""
    if getattr(obj, KEY_PROPERTY) != key or obj.AddSubShape.isNull():
        return None
    return obj.AddSubShape


def keepRibs(obj, ribs: Part.Shape, key: str) -> None:
    obj.AddSubShape = ribs
    setattr(obj, KEY_PROPERTY, key)


def keepUnfused(obj, pieces: Part.Shape) -> None:
    """A preview's sweeps, which no key may find as the ribs."""
    setattr(obj, KEY_PROPERTY, "")
    obj.AddSubShape = pieces


def _pointAlong(edge: Part.Edge, fraction: float) -> Vector:
    return edge.valueAt(edge.FirstParameter + fraction * (edge.LastParameter - edge.FirstParameter))


def _rounded(vector: Vector) -> tuple:
    return tuple(round(coordinate, KEY_DECIMALS) for coordinate in vector)
