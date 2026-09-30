# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The Sketch Mirror command: takes the selected sketch elements, then waits for the mirror line.

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

from morefeatures import selection
from morefeatures.sketchmirror import builder, subelements
from morefeatures.sketchmirror.linepicker import MirrorLinePicker

COMMAND_NAME = "MoreFeatures_SketchMirror"
USAGE_HINT = (
    "While editing a sketch, select the lines, arcs, circles and points to mirror, run Sketch Mirror, "
    "then click the line or axis to mirror them about."
)


class SketchMirrorCommand:
    def __init__(self):
        self._linePicker = None

    def GetResources(self):
        return {
            "Pixmap": "SketchMirror",
            "MenuText": "Sketch Mirror",
            "ToolTip": "Mirror sketch elements about a line, with a copy held symmetric to its original.\n"
            + USAGE_HINT,
        }

    def Activated(self):
        sketch = selection.findSketchInEdit()
        geometryIndices = subelements.findMirrorableGeometry(sketch, _selectedElementNames(sketch))
        if not geometryIndices:
            _showSelectionProblem("Nothing to mirror is selected in the sketch.")
            return
        self._stopPicking()
        self._linePicker = MirrorLinePicker(sketch, lambda lineGeoId: _mirror(sketch, geometryIndices, lineGeoId))
        self._linePicker.start()

    def IsActive(self):
        return selection.findSketchInEdit() is not None

    def _stopPicking(self) -> None:
        if self._linePicker is not None:
            self._linePicker.stop()


def install() -> None:
    Gui.addCommand(COMMAND_NAME, SketchMirrorCommand())


def _selectedElementNames(sketch) -> list:
    return [
        subelements.findElementName(sketch, selected.ObjectName, subElementName)
        for selected in Gui.Selection.getSelectionEx(sketch.Document.Name)
        for subElementName in selected.SubElementNames
    ]


def _mirror(sketch, geometryIndices: list, mirrorLineGeoId: int) -> None:
    # The mirror line itself may have been selected along with the elements.
    elementIndices = [index for index in geometryIndices if index != mirrorLineGeoId]
    skippedTypeNames = builder.commitMirror(sketch, elementIndices, mirrorLineGeoId)
    Gui.Selection.clearSelection()
    if skippedTypeNames:
        App.Console.PrintWarning(
            "Sketch Mirror: not mirrored, not supported yet: {0}.\n".format(", ".join(skippedTypeNames))
        )


def _showSelectionProblem(problem: str) -> None:
    QtWidgets.QMessageBox.information(Gui.getMainWindow(), "Sketch Mirror", problem + "\n\n" + USAGE_HINT)
