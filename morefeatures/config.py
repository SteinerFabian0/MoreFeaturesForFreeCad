# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# Persisted settings via FreeCAD's parameter store: the last-used values of each wizard.

import json

import FreeCAD as App

from morefeatures.boss import parameters as bossparameters

PARAMETER_PATH = "User parameter:BaseApp/Preferences/Mod/MoreFeaturesForFreeCad"
LAST_BOSS_PARAMETERS_KEY = "LastBossParameters"


def getLastBossParameters() -> bossparameters.BossParameters:
    storedJson = _parameters().GetString(LAST_BOSS_PARAMETERS_KEY, "")
    if not storedJson:
        return bossparameters.BossParameters()
    return bossparameters.fromDict(json.loads(storedJson))


def setLastBossParameters(parameters: bossparameters.BossParameters) -> None:
    _parameters().SetString(LAST_BOSS_PARAMETERS_KEY, json.dumps(parameters.toDict()))


def _parameters():
    return App.ParamGet(PARAMETER_PATH)
