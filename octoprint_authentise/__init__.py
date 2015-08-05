# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin

from octoprint_authentise import (asset, blueprint, comm, settings, startup,
                                  template, update)

__plugin_name__ = "Authentise"
__plugin_implementation__ = None
__plugin_hooks__ = None

class AuthentisePlugin( #pylint: disable=too-many-ancestors
    startup.StartupPlugin,
    template.TemplatePlugin,
    settings.SettingsPlugin,
    asset.AssetPlugin,
    blueprint.BlueprintPlugin,
    update.UpdatePlugin,
    comm.MachineCom,
):
    pass

def __plugin_load__():
    global __plugin_implementation__ #pylint: disable=global-statement
    __plugin_implementation__ = AuthentisePlugin()

    global __plugin_hooks__ #pylint: disable=global-statement
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
