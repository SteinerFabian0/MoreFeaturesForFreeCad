# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The Pocket Push command: validates the selection, then opens the pocket push task panel.

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

from morefeatures import config, selection
from morefeatures.pocketpush import builder
from morefeatures.taskpanels import pocketpushpanel

COMMAND_NAME = "MoreFeatures_PocketPush"
USAGE_HINT = (
    "Select a sketch inside a PartDesign Body, drawn on the face the pocket opens in. Each closed outline "
    "in it is pushed into the part as a drafted cavity, wrapped in walls of constant thickness that stand "
    "out of the opposite face where the part is too thin."
)


class PocketPushCommand:
    def GetResources(self):
        return {
            "Pixmap": "PocketPush",
            "MenuText": "Pocket Push",
            "ToolTip": "Push a pocket through the part, with drafted walls of constant thickness around it.\n"
            + USAGE_HINT,
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
            _showSelectionProblem("The selected sketch has no outline.")
            return
        pocketPushFeature = builder.createPocketPush(sketch, body, config.getLastPocketPushParameters())
        Gui.Control.showDialog(pocketpushpanel.PocketPushTaskPanel(pocketPushFeature, isNewFeature=True))

    def IsActive(self):
        return App.ActiveDocument is not None and Gui.Control.activeDialog() is False


def install() -> None:
    Gui.addCommand(COMMAND_NAME, PocketPushCommand())


def _showSelectionProblem(problem: str) -> None:
    QtWidgets.QMessageBox.information(Gui.getMainWindow(), "Pocket Push", problem + "\n\n" + USAGE_HINT)
