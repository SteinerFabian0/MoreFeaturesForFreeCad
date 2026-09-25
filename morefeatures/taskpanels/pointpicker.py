# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# Click-to-toggle picking in the 3D view: while active, every click reports the picked
# 3D position and the selection is cleared again so the next click registers.

from typing import Callable

import FreeCADGui as Gui
from FreeCAD import Vector
from PySide import QtCore


class PointPicker:
    def __init__(self, onPicked: Callable[[Vector], None]):
        self._onPicked = onPicked
        self._isActive = False

    def isActive(self) -> bool:
        return self._isActive

    def start(self) -> None:
        Gui.Selection.clearSelection()
        Gui.Selection.addObserver(self)
        self._isActive = True

    def stop(self) -> None:
        if self._isActive:
            Gui.Selection.removeObserver(self)
            self._isActive = False

    def addSelection(self, documentName: str, objectName: str, subElementName: str, position) -> None:
        self._onPicked(Vector(*position))
        # Clearing from inside the observer callback re-enters the selection machinery.
        QtCore.QTimer.singleShot(0, Gui.Selection.clearSelection)
