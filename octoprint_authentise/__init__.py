# coding=utf-8
from __future__ import absolute_import

import sys
import os
import subprocess
import requests

import octoprint.plugin

__plugin_name__ = "Authentise"

# AUTHENTISE_CLIENT_PATH = 'authentise-streaming-client'
AUTHENTISE_CLIENT_PATH = '/Applications/Authentise.app/Contents/Resources/streamus-client'
AUTHENTISE_PRINT_API = 'https://print.dev-auth.com'

class AuthentisePlugin(octoprint.plugin.StartupPlugin,
                       octoprint.plugin.TemplatePlugin,
                       octoprint.plugin.SettingsPlugin,
                       octoprint.plugin.AssetPlugin):

    def _run_client(self, *args):
        command = (
            AUTHENTISE_CLIENT_PATH,
            '--logging-level',
            'error',
            '-c',
            '/Applications/Authentise.app/Contents/Resources/client.conf',
        ) + args

        try:
            return subprocess.check_output(command).strip()
        except Exception as e:
            self._logger.error("Error running client command `%s` using parameters: %s", e, args)
            return

    def _claim_node(self, api_key, api_secret):
        if not self.node_uuid:
            self._logger.error("No node uuid available to claim")
            return False

        if not api_key:
            self._logger.error("No API Key available to claim node")
            return False

        if not api_secret:
            self._logger.error("No API secret available to claim node")
            return False

        claim_code = self._run_client('--connection-code')
        if claim_code:
            self._logger.info("Got claim code: %s", claim_code)
        else:
            self._logger.error("Could not get a claim code from Authentise")
            return False

        url = "{}/client/claim/{}/".format(AUTHENTISE_PRINT_API, claim_code)
        response = requests.put(url, auth=(api_key, api_secret))

        if response.ok:
            self._logger.info(response.json)
            self._logger.info("Claimed node: %s", self.node_uuid)
            return True

        self._logger.error(
            "Could not use claim code %s for node %s.  Response is %s, %s",
            claim_code,
            self.node_uuid,
            response.status_code,
            response.text,
        )
        return False

    def on_after_startup(self):
        self.node_version = self._run_client('--version')
        if self.node_version:
            self._logger.info("Found node version: %s", self.node_version)
        else:
            self._logger.warning("Could not find node version")

        self.node_uuid = self._run_client('--node-uuid')
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

    def get_settings_defaults(self):
        return dict(
            api_key=None,
            api_secret=None,
        )

    def get_template_vars(self):
        return dict(
            node_uuid=(self.node_uuid or 'Unknown'),
            node_version=(self.node_version or 'Unknown'),
            version=self._plugin_version,
        )

    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=False)
        ]

    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self._claim_node(data['api_key'], data['api_secret'])


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = AuthentisePlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
