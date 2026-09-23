# Every command the addon provides. Adding a feature means adding its command module here.

from morefeatures.commands import bosswizard

COMMAND_MODULES = (bosswizard,)


def installCommands() -> None:
    for commandModule in COMMAND_MODULES:
        commandModule.install()


def commandNames() -> list:
    return [commandModule.COMMAND_NAME for commandModule in COMMAND_MODULES]
