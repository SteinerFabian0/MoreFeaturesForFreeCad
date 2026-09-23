# Dev-only: run from the FreeCAD Python console to pick up morefeatures/ edits
# without restarting FreeCAD. InitGui.py-level changes still need a restart, and
# so do edits to a command class itself: FreeCAD keeps the instance registered at
# startup, though the modules that instance calls into are reloaded.

import importlib

import morefeatures
from morefeatures import config, registry, schema, sketchpoints
from morefeatures.boss import builder, parameters
from morefeatures.commands import bosswizard
from morefeatures.taskpanels import bosspanel, fieldform, pointpicker

for module in (
    morefeatures,
    schema,
    parameters,
    config,
    sketchpoints,
    builder,
    fieldform,
    pointpicker,
    bosspanel,
    bosswizard,
    registry,
):
    importlib.reload(module)
