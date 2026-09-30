# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# A label that follows the mouse over the 3D view, telling what to click next, for commands
# that wait for a click without a task panel of their own.

import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets

FOLLOW_INTERVAL_MS = 16
CURSOR_OFFSET = QtCore.QPoint(18, 18)
STYLE_SHEET = (
    "QLabel { background: palette(highlight); color: palette(highlighted-text);"
    " border-radius: 3px; padding: 3px 7px; }"
)


class CursorHint:
    def __init__(self, text: str):
        mainWindow = Gui.getMainWindow()
        self._viewArea = mainWindow.findChild(QtWidgets.QMdiArea)
        # A child of the main window rather than a floating tool tip window: Wayland does not let
        # an application place its own top-level windows.
        self._label = QtWidgets.QLabel(text, mainWindow)
        self._label.setStyleSheet(STYLE_SHEET)
        self._label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self._label.adjustSize()
        self._label.hide()
        # Polled rather than tracked through mouse events, which the 3D view consumes.
        self._followTimer = QtCore.QTimer(self._label)
        self._followTimer.setInterval(FOLLOW_INTERVAL_MS)
        self._followTimer.timeout.connect(self._followCursor)

    def show(self) -> None:
        self._followTimer.start()
        self._followCursor()

    def setText(self, text: str) -> None:
        self._label.setText(text)
        self._label.adjustSize()

    def close(self) -> None:
        self._followTimer.stop()
        self._label.hide()
        self._label.deleteLater()

    def _followCursor(self) -> None:
        cursorPosition = QtGui.QCursor.pos()
        isOverView = self._viewArea.rect().contains(self._viewArea.mapFromGlobal(cursorPosition))
        self._label.setVisible(isOverView)
        if isOverView:
            self._label.move(self._label.parentWidget().mapFromGlobal(cursorPosition) + CURSOR_OFFSET)
            self._label.raise_()
