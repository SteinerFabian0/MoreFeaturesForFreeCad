# The boss wizard task panel: which sketch points get a boss, how each one is rotated,
# and how the boss is shaped.

from PySide import QtCore, QtWidgets

from morefeatures import config, sketchpoints
from morefeatures.boss import builder
from morefeatures.boss import parameters as bossparameters
from morefeatures.taskpanels import fieldform, pointpicker

BOSS_COLUMN = 0
POSITION_COLUMN = 1
ROTATION_COLUMN = 2
TABLE_HEADERS = ("Boss", "Position", "Rotation")

POINT_ID_ROLE = QtCore.Qt.UserRole
MINIMUM_PICK_DISTANCE = 1.0
MAX_ROTATION_OFFSET = 360.0
PICK_BUTTON_IDLE_TEXT = "Ignore instances..."
PICK_BUTTON_ACTIVE_TEXT = "Done ignoring"


class BossTaskPanel:
    def __init__(self, sketch, body):
        self.sketch = sketch
        self.body = body
        self.sketchPoints = sketchpoints.readSketchPoints(sketch)
        self.ignoredPointIds = set()
        self.rotationOffsetsByPointId = {point.geometryId: 0.0 for point in self.sketchPoints}
        self.rowsByPointId = {point.geometryId: row for row, point in enumerate(self.sketchPoints)}
        self.wasSketchVisible = sketch.ViewObject.Visibility
        self.pointPicker = pointpicker.PointPicker(self._togglePointNearest)

        self.parameterForm = fieldform.FieldForm(bossparameters.PARAMETER_FIELDS, self._onParametersChanged)
        self.parameterForm.setValues(config.getLastBossParameters().toDict())
        self.gussetHeightLabel = QtWidgets.QLabel()
        self.parameterForm.widget.layout().addWidget(self.gussetHeightLabel)

        self.form = [self._buildInstancesWidget(), self.parameterForm.widget]
        self._fillInstanceTable()
        self._onParametersChanged()

    def accept(self) -> bool:
        self._stopPicking()
        parameters = self._currentParameters()
        config.setLastBossParameters(parameters)
        builder.buildBosses(
            builder.BossRequest(
                self.sketch,
                self.body,
                parameters,
                sorted(self.ignoredPointIds),
                dict(self.rotationOffsetsByPointId),
            )
        )
        return True

    def reject(self) -> bool:
        self._stopPicking()
        return True

    def _buildInstancesWidget(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("Instances")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.addWidget(QtWidgets.QLabel("Body: {0}\nSketch: {1}".format(self.body.Label, self.sketch.Label)))

        self.instanceTable = QtWidgets.QTableWidget(len(self.sketchPoints), len(TABLE_HEADERS))
        self.instanceTable.setHorizontalHeaderLabels(list(TABLE_HEADERS))
        self.instanceTable.verticalHeader().setVisible(False)
        self.instanceTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.instanceTable.horizontalHeader().setSectionResizeMode(
            POSITION_COLUMN, QtWidgets.QHeaderView.Stretch
        )
        self.instanceTable.itemChanged.connect(self._onInstanceItemChanged)
        layout.addWidget(self.instanceTable)

        self.instanceCountLabel = QtWidgets.QLabel()
        layout.addWidget(self.instanceCountLabel)
        layout.addLayout(self._buildRotationForAllRow())

        self.pickButton = QtWidgets.QPushButton(PICK_BUTTON_IDLE_TEXT)
        self.pickButton.setCheckable(True)
        self.pickButton.setToolTip("Click points in the 3D view to toggle whether they get a boss.")
        self.pickButton.toggled.connect(self._onPickButtonToggled)
        layout.addWidget(self.pickButton)
        return widget

    def _buildRotationForAllRow(self) -> QtWidgets.QHBoxLayout:
        row = QtWidgets.QHBoxLayout()
        self.rotationForAll = _createRotationEditor()
        applyButton = QtWidgets.QPushButton("Apply to all")
        applyButton.clicked.connect(self._applyRotationToAll)
        row.addWidget(QtWidgets.QLabel("Rotation"))
        row.addWidget(self.rotationForAll)
        row.addWidget(applyButton)
        return row

    def _fillInstanceTable(self) -> None:
        self.instanceTable.blockSignals(True)
        for row, point in enumerate(self.sketchPoints):
            bossItem = QtWidgets.QTableWidgetItem("Point {0}".format(point.geometryIndex + 1))
            bossItem.setData(POINT_ID_ROLE, point.geometryId)
            bossItem.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable)
            bossItem.setCheckState(QtCore.Qt.Checked)
            self.instanceTable.setItem(row, BOSS_COLUMN, bossItem)

            positionItem = QtWidgets.QTableWidgetItem(_describeLocalPosition(point))
            positionItem.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            self.instanceTable.setItem(row, POSITION_COLUMN, positionItem)

            self.instanceTable.setCellWidget(row, ROTATION_COLUMN, self._createInstanceRotationEditor(point))
        self.instanceTable.blockSignals(False)
        self.instanceTable.resizeColumnToContents(BOSS_COLUMN)
        self._refreshInstanceCount()

    def _createInstanceRotationEditor(self, point: sketchpoints.SketchPoint) -> QtWidgets.QDoubleSpinBox:
        editor = _createRotationEditor()
        editor.setValue(self.rotationOffsetsByPointId[point.geometryId])
        editor.valueChanged.connect(
            lambda value, pointId=point.geometryId: self._setRotationOffset(pointId, value)
        )
        return editor

    def _setRotationOffset(self, pointId: int, rotationOffset: float) -> None:
        self.rotationOffsetsByPointId[pointId] = rotationOffset

    def _applyRotationToAll(self) -> None:
        for row in range(self.instanceTable.rowCount()):
            self.instanceTable.cellWidget(row, ROTATION_COLUMN).setValue(self.rotationForAll.value())

    def _onInstanceItemChanged(self, item: QtWidgets.QTableWidgetItem) -> None:
        if item.column() != BOSS_COLUMN:
            return
        pointId = item.data(POINT_ID_ROLE)
        hasBoss = item.checkState() == QtCore.Qt.Checked
        if hasBoss:
            self.ignoredPointIds.discard(pointId)
        else:
            self.ignoredPointIds.add(pointId)
        self.instanceTable.cellWidget(item.row(), ROTATION_COLUMN).setEnabled(hasBoss)
        self._refreshInstanceCount()

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
        self.gussetHeightLabel.setVisible(parameters.hasGussets())
        self.gussetHeightLabel.setText(_describeGussetHeight(parameters))

    def _currentParameters(self) -> bossparameters.BossParameters:
        return bossparameters.fromDict(self.parameterForm.values())


def _createRotationEditor() -> QtWidgets.QDoubleSpinBox:
    editor = QtWidgets.QDoubleSpinBox()
    editor.setRange(-MAX_ROTATION_OFFSET, MAX_ROTATION_OFFSET)
    editor.setDecimals(1)
    editor.setSuffix(" °")
    editor.setToolTip("Rotates this boss about its own axis, turning its gussets or ribs.")
    return editor


def _describeLocalPosition(point: sketchpoints.SketchPoint) -> str:
    return "({0:.2f}, {1:.2f})".format(point.localPosition.x, point.localPosition.y)


def _describeGussetHeight(parameters: bossparameters.BossParameters) -> str:
    cappedNote = "  (capped at boss height)" if parameters.isGussetHeightCapped() else ""
    return "Gusset height: {0:.2f} mm{1}".format(parameters.gussetHeight, cappedNote)
