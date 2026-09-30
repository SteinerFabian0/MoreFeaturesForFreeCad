# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The rib wizard task panel: the cutter the ribs are "machined" with, picked from tip shape
# tiles, with the taper angle shown on a drawing of the chosen cutter.

import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

from morefeatures import config
from morefeatures.rib import builder
from morefeatures.rib import parameters as ribparameters
from morefeatures.taskpanels import featurevisibility, fieldform, tiles

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
# Picked with the tip tiles rather than a generated editor.
TIP_SHAPE_FIELD_NAME = "tipShape"
# Long enough that typing a number or holding a spin arrow rebuilds the preview once, not per step.
PREVIEW_DELAY_MS = 200


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
        self.taperIcons = {shape: tiles.loadImage(fileName) for shape, fileName in TAPER_IMAGE_FILES.items()}
        self.previewTimer = QtCore.QTimer()
        self.previewTimer.setSingleShot(True)
        self.previewTimer.setInterval(PREVIEW_DELAY_MS)
        self.previewTimer.timeout.connect(self._refreshPreview)

        editorFields = tuple(
            field for field in ribparameters.PARAMETER_FIELDS if field.name != TIP_SHAPE_FIELD_NAME
        )
        self.fieldEditors = fieldform.FieldEditors(editorFields, self._onParametersChanged)
        self.form = self._buildForm()
        self._loadRequest(request)
        self.fieldEditors.bindExpressions(ribFeature)
        self._onParametersChanged()
        featurevisibility.showFeatureAlone(ribFeature, self.body)
        self._refreshPreview()

    def accept(self) -> bool:
        self.previewTimer.stop()
        request = self._currentRequest()
        config.setLastRibParameters(request.parameters)
        builder.commitRibs(self.ribFeature, request)
        featurevisibility.showCommittedFeature(self.ribFeature, self.body, self.sketch)
        self._finishEditing()
        return True

    def reject(self) -> bool:
        self.previewTimer.stop()
        builder.abortRibs(self.ribFeature)
        self._finishEditing()
        return True

    def _refreshPreview(self) -> None:
        self.previewTimer.stop()
        builder.previewRibs(self.ribFeature, self._currentRequest())
        isValid = self.ribFeature.isValid()
        self.previewProblemLabel.setVisible(not isValid)
        if not isValid:
            self.previewProblemLabel.setText("Preview failed: {0}".format(self.ribFeature.getStatusString()))

    def _finishEditing(self) -> None:
        if not self.isNewFeature:
            Gui.ActiveDocument.resetEdit()

    def _loadRequest(self, request: builder.RibRequest) -> None:
        self.fieldEditors.setValues(request.parameters.toDict())
        self.tipTiles.select(self.tipShape)

    def _currentRequest(self) -> builder.RibRequest:
        return builder.RibRequest(self.sketch, self.body, self._currentParameters())

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
        self.taperImage.setPixmap(self.taperIcons[parameters.tipShape].pixmap(tiles.tileSize()))
        self.baseWidthLabel.setText("Rib width at base: {0:.2f} mm".format(parameters.baseWidth))
        self.previewTimer.start()

    def _buildForm(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("Rib Wizard")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.addWidget(QtWidgets.QLabel("Path sketch: {0}".format(self.sketch.Label)))
        layout.addWidget(self._buildTipGroup())
        layout.addWidget(self._buildTaperGroup())
        layout.addWidget(self._buildRibGroup())
        layout.addWidget(self._buildBaseWidthLabel())
        layout.addWidget(self._buildPreviewProblemLabel())
        return widget

    def _buildTipGroup(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox(RIB_SHAPE_TITLE)
        layout = QtWidgets.QVBoxLayout(group)
        self.tipTiles = tiles.TileRow(ribparameters.TIP_SHAPES, TIP_IMAGE_FILES, TIP_TOOLTIPS, self._onTipShapeChosen)
        layout.addWidget(self.tipTiles.widget)
        sizeLayout = QtWidgets.QFormLayout()
        for name in ribparameters.TIP_SIZE_FIELD_NAMES:
            sizeLayout.addRow(self.fieldEditors.label(name), self.fieldEditors.editor(name))
        layout.addLayout(sizeLayout)
        return group

    def _buildTaperGroup(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox(ribparameters.TAPER_GROUP)
        layout = QtWidgets.QHBoxLayout(group)
        self.taperImage = QtWidgets.QLabel()
        self.taperImage.setFixedSize(tiles.tileSize())
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

    def _buildPreviewProblemLabel(self) -> QtWidgets.QLabel:
        self.previewProblemLabel = QtWidgets.QLabel()
        self.previewProblemLabel.setWordWrap(True)
        self.previewProblemLabel.setStyleSheet("color: red")
        self.previewProblemLabel.setVisible(False)
        return self.previewProblemLabel

