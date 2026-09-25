# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The rib wizard task panel: the cutter the ribs are "machined" with, picked from tip shape
# tiles, with the taper angle shown on a drawing of the chosen cutter.

import os

import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets

from morefeatures import IMAGES_DIRECTORY, config
from morefeatures.rib import builder
from morefeatures.rib import parameters as ribparameters
from morefeatures.taskpanels import fieldform

TILE_IMAGE_SIZE = 88
RIB_SHAPE_TITLE = "Rib Shape (Tool Cross-section)"
TIP_IMAGE_FILES = {
    ribparameters.TIP_BALL: "RibTipBall.svg",
    ribparameters.TIP_FLAT: "RibTipFlat.svg",
    ribparameters.TIP_CORNER_RADIUS: "RibTipCornerRadius.svg",
}
TAPER_IMAGE_FILES = {
    ribparameters.TIP_BALL: "RibTaperBall.svg",
    ribparameters.TIP_FLAT: "RibTaperFlat.svg",
    ribparameters.TIP_CORNER_RADIUS: "RibTaperCornerRadius.svg",
}
TIP_TOOLTIPS = {
    ribparameters.TIP_BALL: "Ball end mill: a fully rounded rib top.",
    ribparameters.TIP_FLAT: "Flat end mill: a flat rib top with sharp edges.",
    ribparameters.TIP_CORNER_RADIUS: "Corner radius end mill: a flat rib top with rounded edges.",
}
TILE_STYLE_SHEET = (
    "QToolButton { border: 3px solid transparent; border-radius: 6px; padding: 2px; }"
    "QToolButton:hover { border-color: palette(mid); }"
    "QToolButton:checked { border-color: palette(highlight); }"
)
# Picked with the tip tiles rather than a generated editor.
TIP_SHAPE_FIELD_NAME = "tipShape"


class RibTaskPanel:
    """Opened on a rib feature whose transaction builder.createRibs() or
    builder.beginEditingRibs() has just opened; OK commits it, Cancel aborts it."""

    def __init__(self, ribFeature, isNewFeature: bool):
        request = builder.readRequest(ribFeature)
        self.ribFeature = ribFeature
        self.isNewFeature = isNewFeature
        self.sketch = request.sketch
        self.body = request.body
        self.tipShape = request.parameters.tipShape
        self.taperIcons = {
            shape: QtGui.QIcon(os.path.join(IMAGES_DIRECTORY, fileName)) for shape, fileName in TAPER_IMAGE_FILES.items()
        }

        editorFields = tuple(
            field for field in ribparameters.PARAMETER_FIELDS if field.name != TIP_SHAPE_FIELD_NAME
        )
        self.fieldEditors = fieldform.FieldEditors(editorFields, self._onParametersChanged)
        self.form = self._buildForm()
        self._loadRequest(request)
        self.fieldEditors.bindExpressions(ribFeature)
        self._onParametersChanged()

    def accept(self) -> bool:
        parameters = self._currentParameters()
        config.setLastRibParameters(parameters)
        builder.commitRibs(self.ribFeature, builder.RibRequest(self.sketch, self.body, parameters))
        self.sketch.ViewObject.Visibility = False
        if self.ribFeature.BaseFeature is not None:
            self.ribFeature.BaseFeature.ViewObject.Visibility = False
        if self.body.Tip.Name != self.ribFeature.Name:
            self.ribFeature.ViewObject.Visibility = False
            self.body.Tip.ViewObject.Visibility = True
        self._finishEditing()
        return True

    def reject(self) -> bool:
        builder.abortRibs(self.ribFeature)
        self._finishEditing()
        return True

    def _finishEditing(self) -> None:
        if not self.isNewFeature:
            Gui.ActiveDocument.resetEdit()

    def _loadRequest(self, request: builder.RibRequest) -> None:
        self.fieldEditors.setValues(request.parameters.toDict())
        self.tipButtons[self.tipShape].setChecked(True)

    def _currentParameters(self) -> ribparameters.RibParameters:
        return ribparameters.fromDict(dict(self.fieldEditors.values(), tipShape=self.tipShape))

    def _onTipShapeChosen(self, tipShape: str) -> None:
        self.tipShape = tipShape
        self._onParametersChanged()

    def _onParametersChanged(self) -> None:
        parameters = self._currentParameters()
        for name in ribparameters.TIP_SIZE_FIELD_NAMES:
            self.fieldEditors.setFieldVisible(name, ribparameters.isFieldRelevant(parameters, name))
        self.fieldEditors.setFieldMaximum("cornerRadius", parameters.maxCornerRadius)
        self.taperImage.setPixmap(self.taperIcons[parameters.tipShape].pixmap(_tileSize()))
        self.baseWidthLabel.setText("Rib width at base: {0:.2f} mm".format(parameters.baseWidth))

    def _buildForm(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("Rib Wizard")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.addWidget(QtWidgets.QLabel("Path sketch: {0}".format(self.sketch.Label)))
        layout.addWidget(self._buildTipGroup())
        layout.addWidget(self._buildTaperGroup())
        layout.addWidget(self._buildRibGroup())
        layout.addWidget(self._buildBaseWidthLabel())
        return widget

    def _buildTipGroup(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox(RIB_SHAPE_TITLE)
        layout = QtWidgets.QVBoxLayout(group)
        layout.addLayout(self._buildTipTiles())
        sizeLayout = QtWidgets.QFormLayout()
        for name in ribparameters.TIP_SIZE_FIELD_NAMES:
            sizeLayout.addRow(self.fieldEditors.label(name), self.fieldEditors.editor(name))
        layout.addLayout(sizeLayout)
        return group

    def _buildTipTiles(self) -> QtWidgets.QHBoxLayout:
        row = QtWidgets.QHBoxLayout()
        self.tipButtonGroup = QtWidgets.QButtonGroup()
        self.tipButtonGroup.setExclusive(True)
        self.tipButtons = {}
        row.addStretch()
        for tipShape in ribparameters.TIP_SHAPES:
            button = _createTipTile(tipShape)
            button.clicked.connect(lambda isChecked=False, shape=tipShape: self._onTipShapeChosen(shape))
            self.tipButtonGroup.addButton(button)
            self.tipButtons[tipShape] = button
            row.addWidget(button)
        row.addStretch()
        tileWidth = max(button.sizeHint().width() for button in self.tipButtons.values())
        for button in self.tipButtons.values():
            button.setFixedWidth(tileWidth)
        return row

    def _buildTaperGroup(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox(ribparameters.TAPER_GROUP)
        layout = QtWidgets.QHBoxLayout(group)
        self.taperImage = QtWidgets.QLabel()
        self.taperImage.setFixedSize(_tileSize())
        self.taperImage.setToolTip("The taper angle is measured per side, from the cutter's axis.")
        layout.addWidget(self.taperImage)

        inputLayout = QtWidgets.QVBoxLayout()
        inputLayout.addStretch()
        inputLayout.addWidget(self.fieldEditors.label("taperAngle"))
        inputLayout.addWidget(self.fieldEditors.editor("taperAngle"))
        inputLayout.addStretch()
        layout.addLayout(inputLayout)
        return group

    def _buildRibGroup(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox(ribparameters.RIB_GROUP)
        layout = QtWidgets.QVBoxLayout(group)
        heightLayout = QtWidgets.QFormLayout()
        heightLayout.addRow(self.fieldEditors.label("ribHeight"), self.fieldEditors.editor("ribHeight"))
        layout.addLayout(heightLayout)
        layout.addWidget(self.fieldEditors.label("crossingFilletRadius"))
        layout.addWidget(self.fieldEditors.editor("crossingFilletRadius"))
        return group

    def _buildBaseWidthLabel(self) -> QtWidgets.QLabel:
        self.baseWidthLabel = QtWidgets.QLabel()
        self.baseWidthLabel.setToolTip(
            "Where the rib meets the sketch plane, following from the tip, the taper angle and the rib height."
        )
        return self.baseWidthLabel


def _createTipTile(tipShape: str) -> QtWidgets.QToolButton:
    button = QtWidgets.QToolButton()
    button.setCheckable(True)
    button.setIcon(QtGui.QIcon(os.path.join(IMAGES_DIRECTORY, TIP_IMAGE_FILES[tipShape])))
    button.setIconSize(_tileSize())
    button.setText(tipShape)
    button.setToolTip(TIP_TOOLTIPS[tipShape])
    button.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
    button.setStyleSheet(TILE_STYLE_SHEET)
    return button


def _tileSize() -> QtCore.QSize:
    return QtCore.QSize(TILE_IMAGE_SIZE, TILE_IMAGE_SIZE)
