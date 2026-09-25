# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

import os

ADDON_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES_DIRECTORY = os.path.join(ADDON_DIRECTORY, "Resources")
ICONS_DIRECTORY = os.path.join(RESOURCES_DIRECTORY, "icons")
UI_DIRECTORY = os.path.join(RESOURCES_DIRECTORY, "ui")
