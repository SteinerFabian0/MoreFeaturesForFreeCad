# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The pocket push wizard task panel: the cavity's depth and draft, the thickness of the walls
# around it and their fillets, previewed live.

import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

from morefeatures import config
from morefeatures.pocketpush import builder
from morefeatures.pocketpush import parameters as pocketpushparameters
from morefeatures.taskpanels import featurevisibility, fieldform

# Long enough that typing a number or holding a spin arrow rebuilds the preview once, not per step.
PREVIEW_DELAY_MS = 200


class PocketPushTaskPanel:
    """Opened on a pocket push feature whose transaction builder.createPocketPush() or
    builder.beginEditingPocketPush() has just opened; OK commits it, Cancel aborts it."""

    def __init__(self, pocketPushFeature, isNewFeature: bool):
        request = builder.readRequest(pocketPushFeature)
        self.pocketPushFeature = pocketPushFeature
        self.isNewFeature = isNewFeature
        self.sketch = request.sketch
        self.body = request.body
        self.previewTimer = QtCore.QTimer()
        self.previewTimer.setSingleShot(True)
        self.previewTimer.setInterval(PREVIEW_DELAY_MS)
        self.previewTimer.timeout.connect(self._refreshPreview)

        self.fieldEditors = fieldform.FieldEditors(pocketpushparameters.PARAMETER_FIELDS, self._onParametersChanged)
        self.form = self._buildForm()
        self.fieldEditors.setValues(request.parameters.toDict())
        self.fieldEditors.bindExpressions(pocketPushFeature)
        self._onParametersChanged()
        featurevisibility.showFeatureAlone(pocketPushFeature, self.body)
        self._refreshPreview()

    def accept(self) -> bool:
        self.previewTimer.stop()
        request = self._currentRequest()
        config.setLastPocketPushParameters(request.parameters)
        builder.commitPocketPush(self.pocketPushFeature, request)
        featurevisibility.showCommittedFeature(self.pocketPushFeature, self.body, self.sketch)
        self._finishEditing()
        return True

    def reject(self) -> bool:
        self.previewTimer.stop()
        builder.abortPocketPush(self.pocketPushFeature)
        self._finishEditing()
        return True

    def _refreshPreview(self) -> None:
        self.previewTimer.stop()
        builder.previewPocketPush(self.pocketPushFeature, self._currentRequest())
        isValid = self.pocketPushFeature.isValid()
        self.previewProblemLabel.setVisible(not isValid)
        if not isValid:
            self.previewProblemLabel.setText("Preview failed: {0}".format(self.pocketPushFeature.getStatusString()))

    def _finishEditing(self) -> None:
        if not self.isNewFeature:
            Gui.ActiveDocument.resetEdit()

    def _currentRequest(self) -> builder.PocketPushRequest:
        parameters = pocketpushparameters.fromDict(self.fieldEditors.values())
        return builder.PocketPushRequest(self.sketch, self.body, parameters)

    def _onParametersChanged(self) -> None:
        parameters = self._currentRequest().parameters
        self.fieldEditors.editor("topFilletRadius").setVisible(not parameters.isTopFilletAuto)
        self.autoTopFilletLabel.setVisible(parameters.isTopFilletAuto)
        self.autoTopFilletLabel.setText("{0:.2f} mm".format(parameters.outerCornerRadius))
        self.outerCornerRadiusLabel.setText("Outer corner radius: {0:.2f} mm".format(parameters.outerCornerRadius))
        self.outerHeightLabel.setText("Outer height from sketch plane: {0:.2f} mm".format(parameters.outerHeight))
        self.previewTimer.start()

    def _buildForm(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("Pocket Push")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.addWidget(QtWidgets.QLabel("Outline sketch: {0}".format(self.sketch.Label)))
        for groupName, groupFields in fieldform.groupedByGroupName(pocketpushparameters.PARAMETER_FIELDS):
            if groupName != pocketpushparameters.FILLET_GROUP:
                layout.addWidget(self._buildFieldGroup(groupName, groupFields))
        layout.addWidget(self._buildFilletGroup())
        layout.addWidget(self._buildOuterHeightLabel())
        layout.addWidget(self._buildPreviewProblemLabel())
        return widget

    def _buildFieldGroup(self, groupName: str, groupFields: list) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox(groupName)
        fieldNames = tuple(field.name for field in groupFields)
        group.setLayout(fieldform.buildFormLayout(self.fieldEditors, fieldNames))
        return group

    def _buildFilletGroup(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox(pocketpushparameters.FILLET_GROUP)
        layout = QtWidgets.QVBoxLayout(group)
        formLayout = fieldform.buildFormLayout(self.fieldEditors, ("innerCornerRadius",))
        formLayout.addRow(self.fieldEditors.label("topFilletRadius"), self._buildTopFilletRow())
        layout.addLayout(formLayout)
        self.outerCornerRadiusLabel = QtWidgets.QLabel()
        self.outerCornerRadiusLabel.setToolTip("Inner corner radius plus side wall thickness.")
        layout.addWidget(self.outerCornerRadiusLabel)
        return group

    def _buildTopFilletRow(self) -> QtWidgets.QWidget:
        row = QtWidgets.QWidget()
        rowLayout = QtWidgets.QHBoxLayout(row)
        rowLayout.setContentsMargins(0, 0, 0, 0)
        self.autoTopFilletLabel = QtWidgets.QLabel()
        self.autoTopFilletLabel.setToolTip("The outer corner radius.")
        autoCheckBox = self.fieldEditors.editor("isTopFilletAuto")
        autoCheckBox.setText(self.fieldEditors.label("isTopFilletAuto").text())
        rowLayout.addWidget(self.fieldEditors.editor("topFilletRadius"), 1)
        rowLayout.addWidget(self.autoTopFilletLabel, 1)
        rowLayout.addWidget(autoCheckBox)
        return row

    def _buildOuterHeightLabel(self) -> QtWidgets.QLabel:
        self.outerHeightLabel = QtWidgets.QLabel()
        self.outerHeightLabel.setToolTip("Cavity depth plus top wall thickness: where the outside of the walls ends.")
        return self.outerHeightLabel

    def _buildPreviewProblemLabel(self) -> QtWidgets.QLabel:
        self.previewProblemLabel = QtWidgets.QLabel()
        self.previewProblemLabel.setWordWrap(True)
        self.previewProblemLabel.setStyleSheet("color: red")
        self.previewProblemLabel.setVisible(False)
        return self.previewProblemLabel
