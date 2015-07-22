# coding=utf-8
from __future__ import absolute_import

import sys
import os
import subprocess

import octoprint.plugin

__plugin_name__ = "Authentise"

# AUTHENTISE_CLIENT_PATH = 'authentise-streaming-client'
AUTHENTISE_CLIENT_PATH = '/Applications/Authentise.app/Contents/Resources/streamus-client'

class AuthentisePlugin(octoprint.plugin.StartupPlugin,
                       octoprint.plugin.TemplatePlugin,
                       octoprint.plugin.SettingsPlugin,
                       octoprint.plugin.AssetPlugin):

    def _run_client(self, *args):
        try:
            return subprocess.check_output((AUTHENTISE_CLIENT_PATH,) + args)
        except Exception as e:
            self._logger.error("Error running client command `%s` using parameters: %s", e, args)
            return

    def on_after_startup(self):
        self.node_version = self._run_client('--version')
        if self.node_version:
            self._logger.info("Found node version: %s", self.node_version)
        else:
            self._logger.warning("Could not find node version")

        self.node_uuid = self._run_client('--node-uuid', '--logging-level', 'error')
        if self.node_uuid:
            self._logger.info("Found node uuid: %s", self.node_uuid)
        else:
            self._logger.warning("Could not find node uuid")

    def get_assets(self):
        return dict(
            js=["js/authentise.js"]
        )

    def get_update_information(self):
        return dict(
            authentise=dict(
                displayName="Authentise Plugin",
                displayVersion=self._plugin_version,
                type="github_release",
                user="OctoPrint",
                repo="OctoPrint-Authentise",
                current=self._plugin_version,
                pip="https://github.com/Authentise/OctoPrint-Authentise/archive/{target_version}.zip"
            )
        )

    def get_template_configs(self):
        return []

    def get_template_vars(self):
        return dict(
            node_uuid=(self.node_uuid or 'Unknown'),
            node_version=(self.node_version or 'Unknown'),
            version=self._plugin_version,
        )


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = AuthentisePlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
