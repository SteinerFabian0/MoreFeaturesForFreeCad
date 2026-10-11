# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The hole fill wizard task panel: the holes' diameter and pitch, shown on a drawing of the pattern,
# with the resulting hole count and open area, previewed live.

import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

from morefeatures import config
from morefeatures.holefill import builder
from morefeatures.holefill import parameters as holefillparameters
from morefeatures.taskpanels import featurevisibility, fieldform, tiles

PATTERN_IMAGE_FILE = "HoleFillPattern.svg"
PATTERN_IMAGE_SIZE = 160
# Long enough that typing a number or holding a spin arrow rebuilds the preview once, not per step.
PREVIEW_DELAY_MS = 200


class HoleFillTaskPanel:
    """Opened on a hole fill feature whose transaction builder.createHoleFill() or
    builder.beginEditingHoleFill() has just opened; OK commits it, Cancel aborts it."""

    def __init__(self, holeFillFeature, isNewFeature: bool):
        request = builder.readRequest(holeFillFeature)
        self.holeFillFeature = holeFillFeature
        self.isNewFeature = isNewFeature
        self.sketch = request.sketch
        self.body = request.body
        self.previewTimer = QtCore.QTimer()
        self.previewTimer.setSingleShot(True)
        self.previewTimer.setInterval(PREVIEW_DELAY_MS)
        self.previewTimer.timeout.connect(self._refreshPreview)

        self.fieldEditors = fieldform.FieldEditors(holefillparameters.PARAMETER_FIELDS, self._onParametersChanged)
        self.form = self._buildForm()
        self.fieldEditors.setValues(request.parameters.toDict())
        self.fieldEditors.bindExpressions(holeFillFeature)
        self._onParametersChanged()
        featurevisibility.showFeatureAlone(holeFillFeature, self.body)
        self._refreshPreview()

    def accept(self) -> bool:
        self.previewTimer.stop()
        request = self._currentRequest()
        config.setLastHoleFillParameters(request.parameters)
        builder.commitHoleFill(self.holeFillFeature, request)
        featurevisibility.showCommittedFeature(self.holeFillFeature, self.body, self.sketch)
        self._finishEditing()
        return True

    def reject(self) -> bool:
        self.previewTimer.stop()
        builder.abortHoleFill(self.holeFillFeature)
        self._finishEditing()
        return True

    def _refreshPreview(self) -> None:
        self.previewTimer.stop()
        builder.previewHoleFill(self.holeFillFeature, self._currentRequest())
        isValid = self.holeFillFeature.isValid()
        self.previewProblemLabel.setVisible(not isValid)
        self.holeCountLabel.setVisible(isValid)
        if isValid:
            self.holeCountLabel.setText("Holes: {0}".format(self.holeFillFeature.HoleCount))
        else:
            self.previewProblemLabel.setText("Preview failed: {0}".format(self.holeFillFeature.getStatusString()))

    def _finishEditing(self) -> None:
        if not self.isNewFeature:
            Gui.ActiveDocument.resetEdit()

    def _currentRequest(self) -> builder.HoleFillRequest:
        parameters = holefillparameters.fromDict(self.fieldEditors.values())
        return builder.HoleFillRequest(self.sketch, self.body, parameters)

    def _onParametersChanged(self) -> None:
        parameters = self._currentRequest().parameters
        self.landWidthLabel.setText("Land between holes: {0:.2f} mm".format(parameters.landWidth))
        self.openAreaLabel.setText("Open area: {0:.1f} %".format(100.0 * parameters.openAreaRatio))
        self.previewTimer.start()

    def _buildForm(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("Hole Fill")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.addWidget(QtWidgets.QLabel("Perimeter sketch: {0}".format(self.sketch.Label)))
        layout.addWidget(self._buildPatternImage())
        layout.addWidget(self._buildHolesGroup())
        layout.addWidget(self._buildPreviewProblemLabel())
        return widget

    def _buildPatternImage(self) -> QtWidgets.QLabel:
        image = QtWidgets.QLabel()
        image.setAlignment(QtCore.Qt.AlignCenter)
        image.setPixmap(tiles.loadImage(PATTERN_IMAGE_FILE).pixmap(PATTERN_IMAGE_SIZE, PATTERN_IMAGE_SIZE))
        return image

    def _buildHolesGroup(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox(holefillparameters.HOLES_GROUP)
        layout = QtWidgets.QVBoxLayout(group)
        fieldNames = tuple(field.name for field in holefillparameters.PARAMETER_FIELDS)
        layout.addLayout(fieldform.buildFormLayout(self.fieldEditors, fieldNames))
        self.landWidthLabel = QtWidgets.QLabel()
        self.landWidthLabel.setToolTip("Pitch minus hole diameter: the narrowest material between two holes.")
        self.openAreaLabel = QtWidgets.QLabel()
        self.openAreaLabel.setToolTip(
            "Share of the pattern that is open, not counting the solid border along the perimeter."
        )
        self.holeCountLabel = QtWidgets.QLabel()
        self.holeCountLabel.setToolTip("Holes that fit inside the perimeter whole.")
        for label in (self.landWidthLabel, self.openAreaLabel, self.holeCountLabel):
            layout.addWidget(label)
        return group

    def _buildPreviewProblemLabel(self) -> QtWidgets.QLabel:
        self.previewProblemLabel = QtWidgets.QLabel()
        self.previewProblemLabel.setWordWrap(True)
        self.previewProblemLabel.setStyleSheet("color: red")
        self.previewProblemLabel.setVisible(False)
        return self.previewProblemLabel
