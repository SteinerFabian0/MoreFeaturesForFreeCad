# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# How the Pocket Push feature shows in the GUI: shaded like any PartDesign feature, with its outline
# sketch nested under it the way a Pad nests its profile, and reopening the wizard on double-click.

import os

import FreeCADGui as Gui

from morefeatures import ICONS_DIRECTORY

DEFAULT_DISPLAY_MODE = "Flat Lines"
ICON_PATH = os.path.join(ICONS_DIRECTORY, "PocketPush.svg")
DEFAULT_EDIT_MODE = 0


class PocketPushViewProvider:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj) -> None:
        self.featureObject = vobj.Object

    def getDefaultDisplayMode(self) -> str:
        return DEFAULT_DISPLAY_MODE

    def getIcon(self) -> str:
        return ICON_PATH

    def claimChildren(self) -> list:
        return [self.featureObject.Sketch] if self.featureObject.Sketch is not None else []

    def doubleClicked(self, vobj) -> bool:
        Gui.ActiveDocument.setEdit(vobj.Object, DEFAULT_EDIT_MODE)
        return True

    def setEdit(self, vobj, mode):
        if mode != DEFAULT_EDIT_MODE:
            return None
        if vobj.Object.Sketch is None:
            return False
        # Imported here because the panel's import chain leads back to this module.
        from morefeatures.pocketpush import builder
        from morefeatures.taskpanels import pocketpushpanel

        builder.beginEditingPocketPush(vobj.Object)
        Gui.Control.showDialog(pocketpushpanel.PocketPushTaskPanel(vobj.Object, isNewFeature=False))
        return True

    def unsetEdit(self, vobj, mode):
        if mode != DEFAULT_EDIT_MODE:
            return None
        Gui.Control.closeDialog()
        return True

    def dumps(self):
        return None

    def loads(self, state):
        return None
