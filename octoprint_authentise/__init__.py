# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
from octoprint_authentise import blueprint, asset, settings, startup, template, update, comm

__plugin_name__ = "Authentise"

class AuthentisePlugin(
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
    global __plugin_implementation__
    __plugin_implementation__ = AuthentisePlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
