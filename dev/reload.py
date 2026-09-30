# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# Dev-only: run from the FreeCAD Python console to pick up morefeatures/ edits
# without restarting FreeCAD. InitGui.py-level changes still need a restart, and
# so do edits to a command class itself: FreeCAD keeps the instance registered at
# startup, though the modules that instance calls into are reloaded.

import importlib

import morefeatures
from morefeatures import (
    config,
    cutterprofile,
    featureproperties,
    fillet,
    preview,
    registry,
    schema,
    selection,
    sketchpoints,
)
from morefeatures.boss import basefillet, builder, feature, geometry, parameters, viewprovider
from morefeatures.commands import bosswizard, ribwizard, sketchmirror
from morefeatures.rib import builder as ribbuilder
from morefeatures.rib import feature as ribfeature
from morefeatures.rib import geometry as ribgeometry
from morefeatures.rib import parameters as ribparameters
from morefeatures.rib import viewprovider as ribviewprovider
from morefeatures.sketchmirror import builder as sketchmirrorbuilder
from morefeatures.sketchmirror import geometry as sketchmirrorgeometry
from morefeatures.sketchmirror import linepicker, subelements
from morefeatures.taskpanels import bosspanel, featurevisibility, fieldform, pointpicker, ribpanel, tiles

for module in (
    morefeatures,
    schema,
    featureproperties,
    preview,
    cutterprofile,
    fillet,
    parameters,
    ribparameters,
    config,
    selection,
    sketchpoints,
    geometry,
    basefillet,
    viewprovider,
    feature,
    builder,
    ribgeometry,
    ribviewprovider,
    ribfeature,
    ribbuilder,
    sketchmirrorgeometry,
    subelements,
    sketchmirrorbuilder,
    linepicker,
    fieldform,
    tiles,
    pointpicker,
    featurevisibility,
    bosspanel,
    ribpanel,
    bosswizard,
    ribwizard,
    sketchmirror,
    registry,
):
    importlib.reload(module)
