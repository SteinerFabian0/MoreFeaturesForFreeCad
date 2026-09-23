# The Boss Wizard command: validates the selection, then opens the boss task panel.

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

from morefeatures import sketchpoints
from morefeatures.taskpanels import bosspanel

COMMAND_NAME = "MoreFeatures_BossWizard"
SKETCH_TYPE_ID = "Sketcher::SketchObject"
BODY_TYPE_ID = "PartDesign::Body"
USAGE_HINT = "Select a sketch inside a PartDesign Body. Every point in the sketch marks one boss."


class BossWizardCommand:
    def GetResources(self):
        return {
            "Pixmap": "BossWizard",
            "MenuText": "Boss Wizard",
            "ToolTip": "Place mouldable bosses on every point of a sketch.\n" + USAGE_HINT,
        }

    def Activated(self):
        sketch = _findSketch(Gui.Selection.getSelection())
        if sketch is None:
            _showSelectionProblem("No sketch selected.")
            return
        body = _findBody(sketch)
        if body is None:
            _showSelectionProblem("The selected sketch is not inside a PartDesign Body.")
            return
        if not sketchpoints.hasPoints(sketch):
            _showSelectionProblem("The selected sketch has no points.")
            return
        Gui.Control.showDialog(bosspanel.BossTaskPanel(sketch, body))

    def IsActive(self):
        return App.ActiveDocument is not None and Gui.Control.activeDialog() is False


def install() -> None:
    Gui.addCommand(COMMAND_NAME, BossWizardCommand())


def _findSketch(selection: list):
    return next((selected for selected in selection if selected.TypeId == SKETCH_TYPE_ID), None)


def _findBody(sketch):
    parent = sketch.getParentGeoFeatureGroup()
    return parent if parent is not None and parent.TypeId == BODY_TYPE_ID else None


def _showSelectionProblem(problem: str) -> None:
    QtWidgets.QMessageBox.information(Gui.getMainWindow(), "Boss Wizard", problem + "\n\n" + USAGE_HINT)
