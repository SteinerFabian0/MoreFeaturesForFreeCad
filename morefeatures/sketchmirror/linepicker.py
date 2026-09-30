# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# Waits for a line of the sketch being edited to be clicked. The elements selected before stay
# selected meanwhile, so they show what will be mirrored; clearing the selection (Esc, or a click
# into empty space) cancels.

from typing import Callable

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from morefeatures.cursorhint import CursorHint
from morefeatures.sketchmirror import subelements

PICK_PROMPT = "Sketch Mirror: pick the mirror line (a line or an axis). Esc cancels."
WRONG_PICK_WARNING = "Sketch Mirror: {0} is not a line. Pick a line or an axis to mirror about.\n"
CURSOR_PROMPT = "Click mirror line"
CURSOR_WRONG_PICK_PROMPT = "Not a line - click mirror line"


class MirrorLinePicker:
    def __init__(self, sketch, onPicked: Callable[[int], None]):
        self._sketch = sketch
        self._onPicked = onPicked
        self._isActive = False
        self._cursorHint = CursorHint(CURSOR_PROMPT)

    def start(self) -> None:
        Gui.Selection.addObserver(self)
        self._isActive = True
        Gui.getMainWindow().statusBar().showMessage(PICK_PROMPT)
        self._cursorHint.show()

    def stop(self) -> None:
        if self._isActive:
            Gui.Selection.removeObserver(self)
            self._isActive = False
            Gui.getMainWindow().statusBar().clearMessage()
            self._cursorHint.close()

    def addSelection(self, documentName: str, objectName: str, subElementName: str, position) -> None:
        elementName = subelements.findElementName(self._sketch, objectName, subElementName)
        if documentName != self._sketch.Document.Name or elementName is None:
            return
        lineGeoId = subelements.findLineGeoId(self._sketch, elementName)
        if lineGeoId is None:
            App.Console.PrintWarning(WRONG_PICK_WARNING.format(elementName))
            self._cursorHint.setText(CURSOR_WRONG_PICK_PROMPT)
            # Changing the selection from inside the observer callback re-enters the selection machinery.
            QtCore.QTimer.singleShot(
                0, lambda: Gui.Selection.removeSelection(documentName, objectName, subElementName)
            )
            return
        self.stop()
        # Deferred as well: the sketch must not change while the sketcher is still handling the click.
        QtCore.QTimer.singleShot(0, lambda: self._onPicked(lineGeoId))

    def clearSelection(self, documentName: str) -> None:
        self.stop()
