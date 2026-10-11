# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The Hole Fill command: validates the selection, then opens the hole fill task panel.

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

from morefeatures import config, selection
from morefeatures.holefill import builder
from morefeatures.taskpanels import holefillpanel

COMMAND_NAME = "MoreFeatures_HoleFill"
USAGE_HINT = (
    "Select a sketch inside a PartDesign Body, drawn on the face the holes open in, holding one closed "
    "perimeter. The perimeter is filled with round holes in a hexagonal pattern, each cut through the "
    "part until it comes out of it, as for a perforated speaker grille."
)


class HoleFillCommand:
    def GetResources(self):
        return {
            "Pixmap": "HoleFill",
            "MenuText": "Hole Fill",
            "ToolTip": "Fill a perimeter with round holes in a hexagonal pattern.\n" + USAGE_HINT,
        }

    def Activated(self):
        sketch = selection.findSketch(Gui.Selection.getSelection())
        if sketch is None:
            _showSelectionProblem("No sketch selected.")
            return
        body = selection.findBody(sketch)
        if body is None:
            _showSelectionProblem("The selected sketch is not inside a PartDesign Body.")
            return
        if not sketch.Shape.Wires:
            _showSelectionProblem("The selected sketch has no perimeter.")
            return
        holeFillFeature = builder.createHoleFill(sketch, body, config.getLastHoleFillParameters())
        Gui.Control.showDialog(holefillpanel.HoleFillTaskPanel(holeFillFeature, isNewFeature=True))

    def IsActive(self):
        return App.ActiveDocument is not None and Gui.Control.activeDialog() is False


def install() -> None:
    Gui.addCommand(COMMAND_NAME, HoleFillCommand())


def _showSelectionProblem(problem: str) -> None:
    QtWidgets.QMessageBox.information(Gui.getMainWindow(), "Hole Fill", problem + "\n\n" + USAGE_HINT)
