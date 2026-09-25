# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The boss wizard task panel: which sketch points get a boss, how the boss is shaped,
# and how each boss's gussets or ribs are rotated and which of its gussets are left out.

import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

from morefeatures import config, sketchpoints
from morefeatures.boss import builder
from morefeatures.boss import parameters as bossparameters
from morefeatures.taskpanels import fieldform, pointpicker

BOSS_COLUMN = 0
POSITION_COLUMN = 1
TABLE_HEADERS = ("Boss", "Position")

POINT_ID_ROLE = QtCore.Qt.UserRole
MINIMUM_PICK_DISTANCE = 1.0
MAX_ROTATION_OFFSET = 360.0
MIN_VISIBLE_INSTANCE_ROWS = 4
PICK_BUTTON_IDLE_TEXT = "Ignore instances..."
PICK_BUTTON_ACTIVE_TEXT = "Done ignoring"
# Long enough that typing a number or holding a spin arrow rebuilds the preview once, not per step.
PREVIEW_DELAY_MS = 200


class BossTaskPanel:
    """Opened on a boss feature whose transaction builder.createBosses() or
    builder.beginEditingBosses() has just opened; OK commits it, Cancel aborts it."""

    def __init__(self, bossFeature, isNewFeature: bool):
        request = builder.readRequest(bossFeature)
        self.bossFeature = bossFeature
        self.isNewFeature = isNewFeature
        self.sketch = request.sketch
        self.body = request.body
        self.sketchPoints = sketchpoints.readSketchPoints(self.sketch)
        self.ignoredPointIds = set()
        self.rotationOffsetsByPointId = {point.geometryId: 0.0 for point in self.sketchPoints}
        self.skippedGussetsByPointId = {point.geometryId: set() for point in self.sketchPoints}
        self.rowsByPointId = {point.geometryId: row for row, point in enumerate(self.sketchPoints)}
        self.wasSketchVisible = self.sketch.ViewObject.Visibility
        self.pointPicker = pointpicker.PointPicker(self._togglePointNearest)
        self.visibilityBeforeEditing = [(obj, obj.ViewObject.Visibility) for obj in self._objectsShownAroundEditing()]
        self.previewTimer = QtCore.QTimer()
        self.previewTimer.setSingleShot(True)
        self.previewTimer.setInterval(PREVIEW_DELAY_MS)
        self.previewTimer.timeout.connect(self._refreshPreview)

        self.parameterForm = fieldform.FieldForm(bossparameters.PARAMETER_FIELDS, self._onParametersChanged)
        self._loadRequest(request)
        self.parameterForm.bindExpressions(bossFeature)
        self.gussetHeightLabel = QtWidgets.QLabel()
        self.parameterForm.widget.layout().addWidget(self.gussetHeightLabel)
        self.parameterForm.widget.layout().addWidget(self._buildSupportTuningGroup())

        self.form = [self._buildInstancesWidget(), self.parameterForm.widget]
        self._fillInstanceTable()
        if self.sketchPoints:
            self.instanceTable.selectRow(0)
        self._onParametersChanged()
        self._showBossFeatureAlone()
        self._refreshPreview()

    def accept(self) -> bool:
        self.previewTimer.stop()
        self._stopPicking()
        request = self._currentRequest()
        config.setLastBossParameters(request.parameters)
        builder.commitBosses(self.bossFeature, request)
        self.sketch.ViewObject.Visibility = False
        if self.bossFeature.BaseFeature is not None:
            self.bossFeature.BaseFeature.ViewObject.Visibility = False
        if self.body.Tip.Name != self.bossFeature.Name:
            self.bossFeature.ViewObject.Visibility = False
            self.body.Tip.ViewObject.Visibility = True
        self._finishEditing()
        return True

    def reject(self) -> bool:
        self.previewTimer.stop()
        self._stopPicking()
        builder.abortBosses(self.bossFeature)
        for obj, wasVisible in self.visibilityBeforeEditing:
            obj.ViewObject.Visibility = wasVisible
        self._finishEditing()
        return True

    def _objectsShownAroundEditing(self) -> list:
        """The boss feature is left out when new, because Cancel deletes it."""
        candidates = [self.bossFeature, self.bossFeature.BaseFeature, self.body.Tip]
        objectsByName = {
            obj.Name: obj
            for obj in candidates
            if obj is not None and not (self.isNewFeature and obj.Name == self.bossFeature.Name)
        }
        return list(objectsByName.values())

    def _showBossFeatureAlone(self) -> None:
        for obj, _ in self.visibilityBeforeEditing:
            obj.ViewObject.Visibility = False
        self.bossFeature.ViewObject.Visibility = True

    def _schedulePreview(self) -> None:
        self.previewTimer.start()

    def _refreshPreview(self) -> None:
        builder.previewBosses(self.bossFeature, self._currentRequest())
        isValid = self.bossFeature.isValid()
        self.previewProblemLabel.setVisible(not isValid)
        if not isValid:
            self.previewProblemLabel.setText("Preview failed: {0}".format(self.bossFeature.getStatusString()))

    def _currentRequest(self) -> builder.BossRequest:
        parameters = self._currentParameters()
        return builder.BossRequest(
            self.sketch,
            self.body,
            parameters,
            sorted(self.ignoredPointIds),
            dict(self.rotationOffsetsByPointId),
            self._skippedGussetsWithinCount(parameters.gussetCount),
        )

    def _loadRequest(self, request: builder.BossRequest) -> None:
        self.parameterForm.setValues(request.parameters.toDict())
        self.ignoredPointIds = set(request.ignoredPointIds) & set(self.rowsByPointId)
        for pointId, rotationOffset in request.rotationOffsetsByPointId.items():
            if pointId in self.rotationOffsetsByPointId:
                self.rotationOffsetsByPointId[pointId] = rotationOffset
        for pointId, skippedGussets in request.skippedGussetsByPointId.items():
            if pointId in self.skippedGussetsByPointId:
                self.skippedGussetsByPointId[pointId] = set(skippedGussets)

    def _skippedGussetsWithinCount(self, gussetCount: int) -> dict:
        return {
            pointId: {index for index in skippedGussets if index < gussetCount}
            for pointId, skippedGussets in self.skippedGussetsByPointId.items()
        }

    def _finishEditing(self) -> None:
        if not self.isNewFeature:
            Gui.ActiveDocument.resetEdit()

    def _buildInstancesWidget(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("Instances")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.addWidget(QtWidgets.QLabel("Body: {0}\nSketch: {1}".format(self.body.Label, self.sketch.Label)))

        self.instanceTable = QtWidgets.QTableWidget(len(self.sketchPoints), len(TABLE_HEADERS))
        self.instanceTable.setHorizontalHeaderLabels(list(TABLE_HEADERS))
        self.instanceTable.verticalHeader().setVisible(False)
        self.instanceTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.instanceTable.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.instanceTable.horizontalHeader().setSectionResizeMode(
            POSITION_COLUMN, QtWidgets.QHeaderView.Stretch
        )
        self.instanceTable.setToolTip("Select a boss to fine-tune its gussets or ribs below.")
        self.instanceTable.itemChanged.connect(self._onInstanceItemChanged)
        self.instanceTable.itemSelectionChanged.connect(self._refreshSupportTuning)
        self.instanceTable.setMinimumHeight(_tableHeightForRows(self.instanceTable, MIN_VISIBLE_INSTANCE_ROWS))
        layout.addWidget(self.instanceTable)

        self.instanceCountLabel = QtWidgets.QLabel()
        layout.addWidget(self.instanceCountLabel)
        self.previewProblemLabel = QtWidgets.QLabel()
        self.previewProblemLabel.setWordWrap(True)
        self.previewProblemLabel.setStyleSheet("color: red")
        self.previewProblemLabel.setVisible(False)
        layout.addWidget(self.previewProblemLabel)

        self.pickButton = QtWidgets.QPushButton(PICK_BUTTON_IDLE_TEXT)
        self.pickButton.setCheckable(True)
        self.pickButton.setToolTip("Click points in the 3D view to toggle whether they get a boss.")
        self.pickButton.toggled.connect(self._onPickButtonToggled)
        layout.addWidget(self.pickButton)
        return widget

    def _buildSupportTuningGroup(self) -> QtWidgets.QGroupBox:
        self.supportTuningGroup = QtWidgets.QGroupBox()
        layout = QtWidgets.QVBoxLayout(self.supportTuningGroup)
        self.noSelectionLabel = QtWidgets.QLabel("Select a boss in the instance list to fine-tune it.")
        layout.addWidget(self.noSelectionLabel)
        self.supportTuningEditors = QtWidgets.QWidget()
        layout.addWidget(self.supportTuningEditors)

        editorsLayout = QtWidgets.QVBoxLayout(self.supportTuningEditors)
        editorsLayout.setContentsMargins(0, 0, 0, 0)
        editorsLayout.addLayout(self._buildRotationRow())
        self.gussetCheckBoxes = [self._createGussetCheckBox(index) for index in range(bossparameters.MAX_GUSSET_COUNT)]
        for checkBox in self.gussetCheckBoxes:
            editorsLayout.addWidget(checkBox)
        applyButton = QtWidgets.QPushButton("Apply to all bosses")
        applyButton.setToolTip("Gives every boss this rotation and leaves out the same gussets.")
        applyButton.clicked.connect(self._applySupportTuningToAll)
        editorsLayout.addWidget(applyButton)
        return self.supportTuningGroup

    def _buildRotationRow(self) -> QtWidgets.QHBoxLayout:
        row = QtWidgets.QHBoxLayout()
        self.rotationEditor = _createRotationEditor()
        self.rotationEditor.valueChanged.connect(self._onRotationEdited)
        row.addWidget(QtWidgets.QLabel("Rotation"))
        row.addWidget(self.rotationEditor)
        return row

    def _createGussetCheckBox(self, gussetIndex: int) -> QtWidgets.QCheckBox:
        checkBox = QtWidgets.QCheckBox()
        checkBox.setToolTip("Untick to leave this gusset out; the others keep their angles.")
        checkBox.toggled.connect(lambda isKept, index=gussetIndex: self._onGussetToggled(index, isKept))
        return checkBox

    def _fillInstanceTable(self) -> None:
        self.instanceTable.blockSignals(True)
        for row, point in enumerate(self.sketchPoints):
            hasBoss = point.geometryId not in self.ignoredPointIds
            bossItem = QtWidgets.QTableWidgetItem(_describePoint(point))
            bossItem.setData(POINT_ID_ROLE, point.geometryId)
            bossItem.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable)
            bossItem.setCheckState(QtCore.Qt.Checked if hasBoss else QtCore.Qt.Unchecked)
            self.instanceTable.setItem(row, BOSS_COLUMN, bossItem)

            positionItem = QtWidgets.QTableWidgetItem(_describeLocalPosition(point))
            positionItem.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            self.instanceTable.setItem(row, POSITION_COLUMN, positionItem)
        self.instanceTable.blockSignals(False)
        self.instanceTable.resizeColumnToContents(BOSS_COLUMN)
        self._refreshInstanceCount()

    def _selectedPoint(self):
        selectedRows = self.instanceTable.selectionModel().selectedRows()
        return self.sketchPoints[selectedRows[0].row()] if selectedRows else None

    def _onRotationEdited(self, rotationOffset: float) -> None:
        self.rotationOffsetsByPointId[self._selectedPoint().geometryId] = rotationOffset
        self._refreshSupportTuning()
        self._schedulePreview()

    def _onGussetToggled(self, gussetIndex: int, isKept: bool) -> None:
        skippedGussets = self.skippedGussetsByPointId[self._selectedPoint().geometryId]
        if isKept:
            skippedGussets.discard(gussetIndex)
        else:
            skippedGussets.add(gussetIndex)
        self._schedulePreview()

    def _applySupportTuningToAll(self) -> None:
        selectedPointId = self._selectedPoint().geometryId
        for point in self.sketchPoints:
            self.rotationOffsetsByPointId[point.geometryId] = self.rotationOffsetsByPointId[selectedPointId]
            self.skippedGussetsByPointId[point.geometryId] = set(self.skippedGussetsByPointId[selectedPointId])
        self._schedulePreview()

    def _refreshSupportTuning(self) -> None:
        parameters = self._currentParameters()
        point = self._selectedPoint()
        self.supportTuningGroup.setVisible(parameters.hasSupports())
        self.noSelectionLabel.setVisible(point is None)
        self.supportTuningEditors.setVisible(point is not None)
        if point is None:
            self.supportTuningGroup.setTitle("Fine-tuning")
            return
        self.supportTuningGroup.setTitle("{0} of {1}".format(parameters.supportMode, _describePoint(point)))
        self.supportTuningEditors.setEnabled(point.geometryId not in self.ignoredPointIds)
        rotationOffset = self.rotationOffsetsByPointId[point.geometryId]
        _setValueSilently(self.rotationEditor, rotationOffset)
        skippedGussets = self.skippedGussetsByPointId[point.geometryId]
        for index, checkBox in enumerate(self.gussetCheckBoxes):
            checkBox.setVisible(parameters.hasGussets() and index < parameters.gussetCount)
            checkBox.setText(_describeGusset(parameters, index, rotationOffset))
            checkBox.blockSignals(True)
            checkBox.setChecked(index not in skippedGussets)
            checkBox.blockSignals(False)

    def _onInstanceItemChanged(self, item: QtWidgets.QTableWidgetItem) -> None:
        if item.column() != BOSS_COLUMN:
            return
        pointId = item.data(POINT_ID_ROLE)
        if item.checkState() == QtCore.Qt.Checked:
            self.ignoredPointIds.discard(pointId)
        else:
            self.ignoredPointIds.add(pointId)
        self._refreshInstanceCount()
        self._refreshSupportTuning()
        self._schedulePreview()

    def _togglePointNearest(self, position) -> None:
        pickDistance = max(self._currentParameters().baseDiameter / 2.0, MINIMUM_PICK_DISTANCE)
        point = sketchpoints.findPointNearest(self.sketch, self.sketchPoints, position, pickDistance)
        if point is None:
            return
        bossItem = self.instanceTable.item(self.rowsByPointId[point.geometryId], BOSS_COLUMN)
        hasBoss = bossItem.checkState() == QtCore.Qt.Checked
        bossItem.setCheckState(QtCore.Qt.Unchecked if hasBoss else QtCore.Qt.Checked)
        self.instanceTable.selectRow(bossItem.row())
        self.instanceTable.scrollToItem(bossItem)

    def _refreshInstanceCount(self) -> None:
        bossCount = len(self.sketchPoints) - len(self.ignoredPointIds)
        self.instanceCountLabel.setText("{0} of {1} points get a boss".format(bossCount, len(self.sketchPoints)))

    def _onPickButtonToggled(self, isPicking: bool) -> None:
        if isPicking:
            self.sketch.ViewObject.Visibility = True
            self.pointPicker.start()
            self.pickButton.setText(PICK_BUTTON_ACTIVE_TEXT)
        else:
            self._stopPicking()

    def _stopPicking(self) -> None:
        self.pointPicker.stop()
        self.sketch.ViewObject.Visibility = self.wasSketchVisible
        self.pickButton.blockSignals(True)
        self.pickButton.setChecked(False)
        self.pickButton.blockSignals(False)
        self.pickButton.setText(PICK_BUTTON_IDLE_TEXT)

    def _onParametersChanged(self) -> None:
        parameters = self._currentParameters()
        for field in bossparameters.PARAMETER_FIELDS:
            self.parameterForm.setFieldVisible(field.name, bossparameters.isFieldRelevant(parameters, field.name))
        self.parameterForm.setFieldMaximum("boreDepth", parameters.maxBoreDepth)
        self.gussetHeightLabel.setVisible(parameters.hasGussets())
        self.gussetHeightLabel.setText(_describeGussetHeight(parameters))
        self._refreshSupportTuning()
        self._schedulePreview()

    def _currentParameters(self) -> bossparameters.BossParameters:
        return bossparameters.fromDict(self.parameterForm.values())


def _createRotationEditor() -> QtWidgets.QDoubleSpinBox:
    editor = QtWidgets.QDoubleSpinBox()
    editor.setRange(-MAX_ROTATION_OFFSET, MAX_ROTATION_OFFSET)
    editor.setDecimals(1)
    editor.setSuffix(" °")
    editor.setToolTip("Rotates this boss about its own axis, turning its gussets or ribs.")
    return editor


def _setValueSilently(editor: QtWidgets.QDoubleSpinBox, value: float) -> None:
    editor.blockSignals(True)
    editor.setValue(value)
    editor.blockSignals(False)


def _tableHeightForRows(table: QtWidgets.QTableWidget, rowCount: int) -> int:
    return (
        table.horizontalHeader().sizeHint().height()
        + rowCount * table.verticalHeader().defaultSectionSize()
        + 2 * table.frameWidth()
    )


def _describePoint(point: sketchpoints.SketchPoint) -> str:
    return "Point {0}".format(point.geometryIndex + 1)


def _describeLocalPosition(point: sketchpoints.SketchPoint) -> str:
    return "({0:.2f}, {1:.2f})".format(point.localPosition.x, point.localPosition.y)


def _describeGusset(parameters: bossparameters.BossParameters, gussetIndex: int, rotationOffset: float) -> str:
    angle = (rotationOffset + gussetIndex * parameters.gussetAngleStep) % 360.0
    return "Gusset {0} at {1:.1f}°".format(gussetIndex + 1, angle)


def _describeGussetHeight(parameters: bossparameters.BossParameters) -> str:
    cappedNote = (
        "  (capped {0} mm below the boss top)".format(bossparameters.GUSSET_TOP_CLEARANCE)
        if parameters.isGussetHeightCapped()
        else ""
    )
    return "Gusset height: {0:.2f} mm{1}".format(parameters.gussetHeight, cappedNote)
