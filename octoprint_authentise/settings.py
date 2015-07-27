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
