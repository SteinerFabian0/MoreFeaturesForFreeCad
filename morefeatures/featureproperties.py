# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# Mirrors a ParameterField schema onto a document object as FreeCAD properties, so every input
# appears in the property view and is saved with the file.

from morefeatures import schema

PROPERTY_TYPES = {
    schema.LENGTH: "App::PropertyLength",
    schema.ANGLE: "App::PropertyAngle",
    schema.COUNT: "App::PropertyInteger",
    schema.FLAG: "App::PropertyBool",
    schema.CHOICE: "App::PropertyEnumeration",
}
QUANTITY_KINDS = (schema.LENGTH, schema.ANGLE)


def addParameterProperties(obj, parameterFields: tuple) -> None:
    for field in parameterFields:
        obj.addProperty(PROPERTY_TYPES[field.kind], propertyName(field), field.group, field.tooltip or field.label)
        if field.kind == schema.CHOICE:
            setattr(obj, propertyName(field), list(field.choices))


def writeParameterProperties(obj, parameterFields: tuple, values: dict) -> None:
    for field in parameterFields:
        setattr(obj, propertyName(field), values[field.name])


def readParameterProperties(obj, parameterFields: tuple) -> dict:
    return {field.name: _readProperty(obj, field) for field in parameterFields}


def propertyName(field: schema.ParameterField) -> str:
    return field.name[0].upper() + field.name[1:]


def _readProperty(obj, field: schema.ParameterField):
    value = getattr(obj, propertyName(field))
    if field.kind in QUANTITY_KINDS:
        return float(value.Value)
    return value
