# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# Which of a Body's features a wizard shows while it edits one of them. Cancel restores nothing
# by hand: aborting the wizard's transaction takes every visibility change back with it.


def showFeatureAlone(feature, body) -> None:
    for obj in (feature.BaseFeature, body.Tip):
        if obj is not None and obj.Name != feature.Name:
            obj.ViewObject.Visibility = False
    feature.ViewObject.Visibility = True


def showCommittedFeature(feature, body, sketch) -> None:
    """As PartDesign leaves a Pad on OK: sketch and base feature hidden, the Body's tip shown."""
    sketch.ViewObject.Visibility = False
    if feature.BaseFeature is not None:
        feature.BaseFeature.ViewObject.Visibility = False
    if body.Tip.Name != feature.Name:
        feature.ViewObject.Visibility = False
        body.Tip.ViewObject.Visibility = True
