# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# A row of picture buttons to pick one choice from, as the wizards' mode and shape pickers.

import os
from typing import Callable

from PySide import QtCore, QtGui, QtWidgets

from morefeatures import IMAGES_DIRECTORY

TILE_IMAGE_SIZE = 88
TILE_STYLE_SHEET = (
    "QToolButton { border: 3px solid transparent; border-radius: 6px; padding: 2px; }"
    "QToolButton:hover { border-color: palette(mid); }"
    "QToolButton:checked { border-color: palette(highlight); }"
)


class TileRow:
    def __init__(
        self, choices: tuple, imageFilesByChoice: dict, toolTipsByChoice: dict, onChosen: Callable[[str], None]
    ):
        self.widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(self.widget)
        layout.setContentsMargins(0, 0, 0, 0)
        self._buttonGroup = QtWidgets.QButtonGroup()
        self._buttonGroup.setExclusive(True)
        self._buttons = {}
        layout.addStretch()
        for choice in choices:
            button = _createTile(choice, toolTipsByChoice[choice])
            button.clicked.connect(lambda isChecked=False, picked=choice: onChosen(picked))
            self._buttonGroup.addButton(button)
            self._buttons[choice] = button
            layout.addWidget(button)
        layout.addStretch()
        self.setImages(imageFilesByChoice)
        tileWidth = max(button.sizeHint().width() for button in self._buttons.values())
        tileHeight = max(button.sizeHint().height() for button in self._buttons.values())
        for button in self._buttons.values():
            button.setFixedSize(tileWidth, tileHeight)
        # FreeCAD's theme style sheet lowers every tool button's minimum height, so a panel taller than
        # the task view would squeeze the tiles; the plain row widget keeps its minimum.
        self.widget.setMinimumHeight(tileHeight)

    def select(self, choice: str) -> None:
        self._buttons[choice].setChecked(True)

    def setImages(self, imageFilesByChoice: dict) -> None:
        for choice, button in self._buttons.items():
            button.setIcon(loadImage(imageFilesByChoice[choice]))

    def disableChoice(self, choice: str, toolTip: str) -> None:
        self._buttons[choice].setEnabled(False)
        self._buttons[choice].setToolTip(toolTip)


def loadImage(fileName: str) -> QtGui.QIcon:
    return QtGui.QIcon(os.path.join(IMAGES_DIRECTORY, fileName))


def tileSize() -> QtCore.QSize:
    return QtCore.QSize(TILE_IMAGE_SIZE, TILE_IMAGE_SIZE)


def _createTile(choice: str, toolTip: str) -> QtWidgets.QToolButton:
    button = QtWidgets.QToolButton()
    button.setCheckable(True)
    button.setIconSize(tileSize())
    button.setText(choice)
    button.setToolTip(toolTip)
    button.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
    button.setStyleSheet(TILE_STYLE_SHEET)
    return button
