# coding=utf-8
#pylint: disable=no-member
from __future__ import absolute_import

import octoprint.plugin

from octoprint_authentise import helpers


class StartupPlugin(octoprint.plugin.StartupPlugin):
    node_uuid = None
    node_version = None

    def on_after_startup(self):
        self.node_version = helpers.run_client_and_wait(self._settings, args=['--version'], logger=self._logger)
        if self.node_version:
            self._logger.info("Found node version: %s", self.node_version)
        else:
            self._logger.warning("Could not find node version")

        self.node_uuid = helpers.run_client_and_wait(self._settings, args=['--node-uuid'], logger=self._logger)
        if self.node_uuid:
            self._logger.info("Found node uuid: %s", self.node_uuid)
        else:
            self._logger.warning("Could not find node uuid")
