# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin

class StartupPlugin(octoprint.plugin.StartupPlugin):
    def on_after_startup(self):
        self.node_version = self.run_client('--version')
        if self.node_version:
            self._logger.info("Found node version: %s", self.node_version)
        else:
            self._logger.warning("Could not find node version")

        self.node_uuid = self.run_client('--node-uuid')
        if self.node_uuid:
            self._logger.info("Found node uuid: %s", self.node_uuid)
        else:
            self._logger.warning("Could not find node uuid")
