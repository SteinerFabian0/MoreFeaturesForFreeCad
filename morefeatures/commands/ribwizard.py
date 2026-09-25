# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The Rib Wizard command: validates the selection, then opens the rib task panel.

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

from morefeatures import config, selection
from morefeatures.rib import builder
from morefeatures.taskpanels import ribpanel

COMMAND_NAME = "MoreFeatures_RibWizard"
USAGE_HINT = (
    "Select a sketch inside a PartDesign Body. Its lines are the centre paths of the cutter "
    "the ribs are machined with; they need not be connected."
)


class RibWizardCommand:
    def GetResources(self):
        return {
            "Pixmap": "RibWizard",
            "MenuText": "Rib Wizard",
            "ToolTip": "Grow drafted ribs along every line of a sketch, shaped by a mould maker's cutter.\n"
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
        # A sketch's shape leaves out construction geometry, which never becomes a rib.
        if not sketch.Shape.Edges:
            _showSelectionProblem("The selected sketch has no lines.")
            return
        ribFeature = builder.createRibs(sketch, body, config.getLastRibParameters())
        Gui.Control.showDialog(ribpanel.RibTaskPanel(ribFeature, isNewFeature=True))

    def IsActive(self):
        return App.ActiveDocument is not None and Gui.Control.activeDialog() is False


def install() -> None:
    Gui.addCommand(COMMAND_NAME, RibWizardCommand())


def _showSelectionProblem(problem: str) -> None:
    QtWidgets.QMessageBox.information(Gui.getMainWindow(), "Rib Wizard", problem + "\n\n" + USAGE_HINT)
