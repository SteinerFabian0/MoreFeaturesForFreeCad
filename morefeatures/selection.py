# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# Finding what a wizard command works on in the current selection.

import FreeCADGui as Gui

SKETCH_TYPE_ID = "Sketcher::SketchObject"
BODY_TYPE_ID = "PartDesign::Body"


def findSketch(selection: list):
    return next((selected for selected in selection if selected.TypeId == SKETCH_TYPE_ID), None)


def findBody(sketch):
    parent = sketch.getParentGeoFeatureGroup()
    return parent if parent is not None and parent.TypeId == BODY_TYPE_ID else None


def findSketchInEdit():
    guiDocument = Gui.ActiveDocument
    viewProviderInEdit = guiDocument.getInEdit() if guiDocument is not None else None
    if viewProviderInEdit is None or viewProviderInEdit.Object.TypeId != SKETCH_TYPE_ID:
        return None
    return viewProviderInEdit.Object
