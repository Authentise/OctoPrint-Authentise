# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin

class SettingsPlugin(octoprint.plugin.SettingsPlugin):
    def get_settings_defaults(self):
        return dict(
            api_key=None,
            api_secret=None,
            claimed_by=None,
        )

    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.claim_node(data['api_key'], data['api_secret'])
