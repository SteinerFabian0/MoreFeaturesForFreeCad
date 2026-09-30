# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# Task panel editors generated from a ParameterField schema, values read and written as a plain
# dict, laid out by each panel.

from typing import Callable

import FreeCADGui as Gui
from PySide import QtWidgets

from morefeatures import featureproperties, schema

QUANTITY_UNITS = {
    schema.LENGTH: "mm",
    schema.ANGLE: "deg",
}
EXPRESSION_KINDS = (schema.LENGTH, schema.ANGLE, schema.COUNT)


class FieldEditors:
    """One labelled editor per field, not yet laid out."""

    def __init__(self, parameterFields: tuple, onValuesChanged: Callable[[], None]):
        self._fieldsByName = {field.name: field for field in parameterFields}
        self._editors = {}
        self._labels = {}
        self._onValuesChanged = onValuesChanged
        for field in parameterFields:
            self._addEditor(field)

    def editor(self, name: str) -> QtWidgets.QWidget:
        return self._editors[name]

    def label(self, name: str) -> QtWidgets.QLabel:
        return self._labels[name]

    def values(self) -> dict:
        return {name: _readEditor(editor, self._fieldsByName[name].kind) for name, editor in self._editors.items()}

    def setValues(self, values: dict) -> None:
        for name, editor in self._editors.items():
            editor.blockSignals(True)
            _writeEditor(editor, self._fieldsByName[name].kind, values[name])
            editor.blockSignals(False)

    def bindExpressions(self, obj) -> None:
        """obj must carry the schema's properties (featureproperties.addParameterProperties)."""
        for name, editor in self._editors.items():
            field = self._fieldsByName[name]
            if field.kind in EXPRESSION_KINDS:
                Gui.ExpressionBinding(editor).bind(obj, featureproperties.propertyName(field))

    def setFieldMaximum(self, name: str, maximum: float) -> None:
        editor = self._editors[name]
        kind = self._fieldsByName[name].kind
        editor.setProperty("maximum", maximum)
        if _readEditor(editor, kind) > maximum:
            editor.blockSignals(True)
            _writeEditor(editor, kind, maximum)
            editor.blockSignals(False)

    def setFieldLabel(self, name: str, text: str) -> None:
        self._labels[name].setText(text)

    def setFieldVisible(self, name: str, isVisible: bool) -> None:
        self._labels[name].setVisible(isVisible)
        self._editors[name].setVisible(isVisible)

    def _addEditor(self, field: schema.ParameterField) -> None:
        editor = _createEditor(field)
        label = QtWidgets.QLabel(field.label)
        if field.tooltip:
            label.setToolTip(field.tooltip)
            editor.setToolTip(field.tooltip)
        self._connectChangeSignal(editor, field.kind)
        self._editors[field.name] = editor
        self._labels[field.name] = label

    def _connectChangeSignal(self, editor: QtWidgets.QWidget, kind: str) -> None:
        notify = lambda *changed: self._onValuesChanged()
        if kind == schema.FLAG:
            editor.toggled.connect(notify)
        elif kind == schema.CHOICE:
            editor.currentIndexChanged.connect(notify)
        else:
            editor.valueChanged.connect(notify)


def buildFormLayout(fieldEditors: FieldEditors, fieldNames: tuple) -> QtWidgets.QFormLayout:
    formLayout = QtWidgets.QFormLayout()
    for name in fieldNames:
        formLayout.addRow(fieldEditors.label(name), fieldEditors.editor(name))
    return formLayout


def groupedByGroupName(parameterFields: tuple) -> list:
    groups = {}
    for field in parameterFields:
        groups.setdefault(field.group, []).append(field)
    return list(groups.items())


def _createEditor(field: schema.ParameterField) -> QtWidgets.QWidget:
    if field.kind in QUANTITY_UNITS:
        editor = Gui.UiLoader().createWidget("Gui::QuantitySpinBox")
        editor.setProperty("unit", QUANTITY_UNITS[field.kind])
        editor.setProperty("minimum", field.minimum)
        editor.setProperty("maximum", field.maximum)
        return editor
    if field.kind == schema.COUNT:
        editor = Gui.UiLoader().createWidget("Gui::IntSpinBox")
        editor.setRange(int(field.minimum), int(field.maximum))
        return editor
    if field.kind == schema.FLAG:
        return QtWidgets.QCheckBox()
    editor = QtWidgets.QComboBox()
    editor.addItems(list(field.choices))
    return editor


def _readEditor(editor: QtWidgets.QWidget, kind: str):
    if kind in QUANTITY_UNITS:
        return float(editor.property("rawValue"))
    if kind == schema.COUNT:
        return editor.value()
    if kind == schema.FLAG:
        return editor.isChecked()
    return editor.currentText()


def _writeEditor(editor: QtWidgets.QWidget, kind: str, value) -> None:
    if kind in QUANTITY_UNITS:
        editor.setProperty("rawValue", float(value))
    elif kind == schema.COUNT:
        editor.setValue(int(value))
    elif kind == schema.FLAG:
        editor.setChecked(bool(value))
    else:
        editor.setCurrentText(str(value))
