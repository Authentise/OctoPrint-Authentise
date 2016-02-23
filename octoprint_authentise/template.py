# coding=utf-8
#pylint: disable=no-member
from __future__ import absolute_import

import octoprint.plugin


class TemplatePlugin(octoprint.plugin.TemplatePlugin):
    def get_template_vars(self):
        return dict(
            node_uuid=self.node_uuid,
            node_version=self.node_version,
            version=self._plugin_version,
            frame_src=self._settings.get(["frame_src"]),
        )

    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=False),
            dict(type="tab"),
            dict(type="generic", template="authentise_generic.jinja2"),
        ]
