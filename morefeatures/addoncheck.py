# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# Makes a saved feature fail its recompute with a clear error when this addon is not installed,
# instead of silently keeping its stale shape.

ADDON_NAME = "MoreFeaturesForFreeCad"
REQUIRED_ADDON_PROPERTY = "RequiredAddon"
ADDON_PRESENCE_PROPERTY = "RequiresMoreFeaturesForFreeCadAddon"
BASE_GROUP = "Base"
PROPERTY_READ_ONLY = 1
PROPERTY_HIDDEN = 4
PROPERTY_NOT_SAVED = 32


def installAddonCheck(obj) -> None:
    """Must run on creation and again on every document restore."""
    # Never saved, so the expression below only resolves while this addon has loaded the file.
    obj.addProperty(
        "App::PropertyString", ADDON_PRESENCE_PROPERTY, BASE_GROUP, "", PROPERTY_NOT_SAVED | PROPERTY_HIDDEN
    )
    setattr(obj, ADDON_PRESENCE_PROPERTY, ADDON_NAME)
    # Files saved before this check existed lack the saved half.
    if REQUIRED_ADDON_PROPERTY not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyString",
            REQUIRED_ADDON_PROPERTY,
            BASE_GROUP,
            "Recomputing this feature needs this addon installed.",
            PROPERTY_READ_ONLY,
        )
        obj.setExpression(REQUIRED_ADDON_PROPERTY, ADDON_PRESENCE_PROPERTY)
