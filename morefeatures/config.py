# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Fabian Steiner

# Persisted settings via FreeCAD's parameter store: the last-used values of each wizard.

import json

import FreeCAD as App

from morefeatures.boss import parameters as bossparameters
from morefeatures.rib import parameters as ribparameters

PARAMETER_PATH = "User parameter:BaseApp/Preferences/Mod/MoreFeaturesForFreeCad"
LAST_BOSS_PARAMETERS_KEY = "LastBossParameters"
LAST_RIB_PARAMETERS_KEY = "LastRibParameters"


def getLastBossParameters() -> bossparameters.BossParameters:
    storedJson = _parameters().GetString(LAST_BOSS_PARAMETERS_KEY, "")
    if not storedJson:
        return bossparameters.BossParameters()
    return bossparameters.fromDict(json.loads(storedJson))


def setLastBossParameters(parameters: bossparameters.BossParameters) -> None:
    _parameters().SetString(LAST_BOSS_PARAMETERS_KEY, json.dumps(parameters.toDict()))


def getLastRibParameters() -> ribparameters.RibParameters:
    storedJson = _parameters().GetString(LAST_RIB_PARAMETERS_KEY, "")
    if not storedJson:
        return ribparameters.RibParameters()
    return ribparameters.fromDict(json.loads(storedJson))


def setLastRibParameters(parameters: ribparameters.RibParameters) -> None:
    _parameters().SetString(LAST_RIB_PARAMETERS_KEY, json.dumps(parameters.toDict()))


def _parameters():
    return App.ParamGet(PARAMETER_PATH)
