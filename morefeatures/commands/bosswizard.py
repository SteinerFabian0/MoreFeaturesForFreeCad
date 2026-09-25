# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The Boss Wizard command: validates the selection, then opens the boss task panel.

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

from morefeatures import config, selection, sketchpoints
from morefeatures.boss import builder
from morefeatures.taskpanels import bosspanel

COMMAND_NAME = "MoreFeatures_BossWizard"
USAGE_HINT = "Select a sketch inside a PartDesign Body. Every point in the sketch marks one boss."


class BossWizardCommand:
    def GetResources(self):
        return {
            "Pixmap": "BossWizard",
            "MenuText": "Boss Wizard",
            "ToolTip": "Place mouldable bosses on every point of a sketch.\n" + USAGE_HINT,
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
        if not sketchpoints.hasPoints(sketch):
            _showSelectionProblem("The selected sketch has no points.")
            return
        bossFeature = builder.createBosses(sketch, body, config.getLastBossParameters())
        Gui.Control.showDialog(bosspanel.BossTaskPanel(bossFeature, isNewFeature=True))

    def IsActive(self):
        return App.ActiveDocument is not None and Gui.Control.activeDialog() is False


def install() -> None:
    Gui.addCommand(COMMAND_NAME, BossWizardCommand())


def _showSelectionProblem(problem: str) -> None:
    QtWidgets.QMessageBox.information(Gui.getMainWindow(), "Boss Wizard", problem + "\n\n" + USAGE_HINT)
