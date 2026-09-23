# Bootstrap loaded by FreeCAD at GUI startup; real logic lives in morefeatures/.

# FreeCAD execs this file with separate globals and locals dicts, so names
# bound here are invisible to class bodies and methods. Everything below
# therefore resolves its imports locally or is assigned after the class body.

import os

import FreeCADGui as Gui

from morefeatures import ICONS_DIRECTORY, registry


class MoreFeaturesWorkbench(Gui.Workbench):
    MenuText = "More Features"
    ToolTip = "Wizards for multi-step features such as mouldable bosses"

    def Initialize(self):
        from morefeatures import registry

        self.appendToolbar("More Features", registry.commandNames())
        self.appendMenu("More Features", registry.commandNames())

    def Activated(self):
        pass

    def Deactivated(self):
        pass

    def GetClassName(self):
        return "Gui::PythonWorkbench"


MoreFeaturesWorkbench.Icon = os.path.join(ICONS_DIRECTORY, "MoreFeatures.svg")

Gui.addIconPath(ICONS_DIRECTORY)
Gui.addWorkbench(MoreFeaturesWorkbench())

# Registered at startup rather than in Initialize() so the commands are usable
# (and findable from the S-menu) from any workbench, not only this one.
registry.installCommands()
