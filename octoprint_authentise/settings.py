# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin


class SettingsPlugin(octoprint.plugin.SettingsPlugin):
    def get_settings_defaults(self):
        return dict(
            api_key=None,
            api_secret=None,
            authentise_url='https://print.authentise.com',
            authentise_user_url='https://users.authentise.com',
            streamus_client_path='streamus-client',
            streamus_config_path=None,
            frame_src='https://app.authentise.com/#/models',
        )
