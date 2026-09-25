# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# The hidden flag a feature is recomputed under while its wizard shows a live preview.

from morefeatures import addoncheck

PREVIEW_PROPERTY = "IsPreviewing"
# An output property never marks the feature as needing a recompute when it changes.
PROPERTY_OUTPUT = 8


def addPreviewProperty(obj) -> None:
    """Must run on creation and again on every document restore, since the flag is never saved."""
    obj.addProperty(
        "App::PropertyBool",
        PREVIEW_PROPERTY,
        addoncheck.BASE_GROUP,
        "",
        addoncheck.PROPERTY_HIDDEN | PROPERTY_OUTPUT | addoncheck.PROPERTY_NOT_SAVED,
    )


def setPreviewing(obj, isPreviewing: bool) -> None:
    setattr(obj, PREVIEW_PROPERTY, isPreviewing)


def isPreviewing(obj) -> bool:
    return getattr(obj, PREVIEW_PROPERTY)
